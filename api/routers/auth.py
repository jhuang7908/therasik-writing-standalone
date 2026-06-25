"""
Trial auth: username + numeric PIN. Session token for Console.
"""
from __future__ import annotations

import re
import secrets
import time
import os
from typing import Any, Dict, Optional

import sqlite3
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from api import auth_db


def _tenant_from_request(request: Request) -> str:
    host = (request.headers.get("host", "") or "").split(":")[0].lower()
    xfh = (request.headers.get("x-forwarded-host", "") or "").split(":")[0].lower()
    req_host = ((request.url.hostname or "") if request.url else "").lower()
    site_hdr = (request.headers.get("x-public-site", "") or "").strip().lower()
    site_q = (request.query_params.get("site", "") or "").strip().lower()
    probe = " ".join([host, xfh, req_host, site_hdr, site_q])
    if "therasik" in probe:
        return "therasik"
    return "insynbio"


def _bind_tenant(request: Request) -> str:
    """Ensure SQLite auth DB namespace matches the incoming site/domain."""
    tenant = _tenant_from_request(request)
    auth_db.push_namespace(tenant)
    auth_db.init_db()
    return tenant


def _tenant_scope(request: Request):
    # Router dependency alone is not enough for sync endpoints: FastAPI resolves
    # dependencies in the async worker but runs sync handlers in a thread pool
    # where ContextVar tenant does not carry over. Each handler must call
    # _bind_tenant(request) before touching auth_db.
    _bind_tenant(request)


router = APIRouter(prefix="/auth", tags=["Auth"], dependencies=[Depends(_tenant_scope)])


def _unl(u: Dict[str, Any]) -> bool:
    return bool(int(u.get("credits_unlimited") or 0))

USERNAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{2,31}$")
PASSWORD_RE = re.compile(r"^[A-Za-z0-9@#$%^&+=!?._-]{8,64}$")
_LOGIN_FAILURES: Dict[str, Dict[str, Any]] = {}


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    email: str = Field(..., description="Valid email address")
    password: Optional[str] = Field(None, min_length=8, max_length=64)
    confirm_password: Optional[str] = Field(None, min_length=8, max_length=64)
    coupon_code: Optional[str] = None
    # Backward-compatible aliases used by the older console.
    pin: Optional[str] = None
    confirm_pin: Optional[str] = None
    accept_terms: bool = False
    marketing_opt_in: bool = False
    # Optional opt-in for affiliated-company newsletters (separate from product update opt-in).
    news_opt_in: bool = False


class VerifyEmailRequest(BaseModel):
    username: str
    code: str


class ResendVerificationRequest(BaseModel):
    username: str


class LoginRequest(BaseModel):
    username: str
    password: Optional[str] = None
    pin: Optional[str] = None


class ForgotUsernameRequest(BaseModel):
    email: str


class ForgotPasswordRequest(BaseModel):
    username_or_email: str


class ResetPasswordRequest(BaseModel):
    username_or_email: str
    code: str
    password: str
    confirm_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    credits: int
    role: str
    credits_unlimited: bool = False
    is_verified: bool = False


class MeResponse(BaseModel):
    username: str
    email: Optional[str] = None
    credits: int
    role: str
    credits_unlimited: bool = False
    is_verified: bool = False


class DebitRequest(BaseModel):
    service_id: str
    amount: int = Field(..., ge=1)
    run_id: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class DebitResponse(BaseModel):
    ok: bool
    balance: int
    debited: int
    message: str


class GateDebitRequest(BaseModel):
    service_id: str
    amount: int = Field(..., ge=1)
    run_id: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


def _gate_payload(
    x_gate_user: Optional[str] = Header(None, alias="X-InSynBio-Gate-User"),
    x_gate_role: Optional[str] = Header("user", alias="X-InSynBio-Gate-Role"),
) -> Dict[str, str]:
    user = (x_gate_user or "").strip().lower()
    role = (x_gate_role or "user").strip().lower()
    allowed = {"guest": "user", "zhanglab": "user", "admin": "admin"}
    if user not in allowed:
        raise HTTPException(401, "Missing or invalid gate user")
    if role != allowed[user]:
        role = allowed[user]
    return {"username": user, "role": role}


def _validate_username_pin(username: str, pin: str) -> None:
    if not USERNAME_RE.match(username.strip()):
        raise HTTPException(
            422,
            "Username: 3–32 chars, start with letter, [a-zA-Z0-9_]",
        )
    if not PASSWORD_RE.match(pin or ""):
        raise HTTPException(
            422,
            "Password must be 8–64 chars using letters, numbers, or @#$%^&+=!?._-",
        )


def _password(req: Any) -> str:
    return str(getattr(req, "password", None) or getattr(req, "pin", None) or "")


def _confirm_password(req: RegisterRequest) -> str:
    return str(req.confirm_password or req.confirm_pin or "")


def _validate_email(email: str) -> None:
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (email or "").strip()):
        raise HTTPException(422, "Invalid email address")


def _user_lookup(username_or_email: str) -> Optional[Dict[str, Any]]:
    raw = (username_or_email or "").strip()
    if "@" in raw:
        return auth_db.get_user_by_email(raw)
    return auth_db.get_user_by_username(raw)


def _check_login_rate_limit(username: str) -> None:
    key = username.strip().lower()
    rec = _LOGIN_FAILURES.get(key)
    now = time.time()
    if rec and rec.get("locked_until", 0) > now:
        raise HTTPException(429, "Too many failed attempts. Please wait and try again.")


def _record_login_failure(username: str) -> None:
    key = username.strip().lower()
    rec = _LOGIN_FAILURES.setdefault(key, {"count": 0, "locked_until": 0})
    rec["count"] = int(rec.get("count") or 0) + 1
    if rec["count"] >= 6:
        rec["locked_until"] = time.time() + 5 * 60


def _record_login_success(username: str) -> None:
    _LOGIN_FAILURES.pop(username.strip().lower(), None)


def _bearer_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    return authorization[7:].strip()


def get_session_payload(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> Dict[str, Any]:
    _bind_tenant(request)
    token = _bearer_token(authorization)
    payload = auth_db.verify_session(token)
    if not payload or "uid" not in payload:
        raise HTTPException(401, "Invalid or expired session")
    expected = _tenant_from_request(request)
    token_tenant = str(payload.get("tenant") or "").strip().lower()
    # Old sessions without tenant are treated as insynbio-only.
    if (token_tenant or "insynbio") != expected:
        raise HTTPException(401, "Session is not valid for this domain")
    return payload


_PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "qq.com", "yahoo.com", "outlook.com", "hotmail.com",
    "163.com", "126.com", "icloud.com", "foxmail.com", "sina.com", "live.com",
}


def _is_personal_email(email: str) -> bool:
    return (email or "").split("@")[-1].strip().lower() in _PERSONAL_EMAIL_DOMAINS


def _is_edu_email(email: str) -> bool:
    domain = (email or "").split("@")[-1].strip().lower()
    return domain.endswith(".edu") or domain.endswith(".edu.cn")


def _credit_tier(tenant: str) -> Dict[str, int]:
    """Per-tenant base / coupon credit tiers, env-overridable."""
    tenant = (tenant or "insynbio").strip().lower()
    if tenant == "therasik":
        return {
            "base_personal": 2000,
            "base_business": 2000,
            "wechat_bonus": 1000,
            "coupon_personal": 4000,
            "coupon_business": 4000,
        }
    from api.pricing_constants import TRIAL_SIGNUP_CREDITS

    return {
        "base_personal": TRIAL_SIGNUP_CREDITS,
        "base_business": TRIAL_SIGNUP_CREDITS,
        "wechat_bonus": 0,        # WeChat bonus is Therasik-only
        "coupon_personal": 0,     # Coupon tiers set per coupon at issuance
        "coupon_business": 0,
    }


def _determine_base_trial_credits(email: str, tenant: str = "insynbio") -> int:
    """Credits granted immediately at registration (no coupon applied yet)."""
    tier = _credit_tier(tenant)
    base = tier["base_personal"] if _is_personal_email(email) else tier["base_business"]
    
    # Academic bonus: +20% for .edu / .edu.cn emails
    if _is_edu_email(email):
        base = int(base * 1.2)
        
    return base


def _apply_pending_coupon_after_verify(uid: int, email: str, tenant: str) -> Dict[str, Any]:
    """Apply a deferred coupon after the user has verified their email.

    Returns a dict {applied, bonus, new_balance, code} for logging / response use.
    """
    code = auth_db.pop_pending_coupon(uid)
    if not code:
        return {"applied": False, "bonus": 0, "code": None}

    tier = _credit_tier(tenant)
    is_personal = _is_personal_email(email)
    cc_lower = code.strip().lower()
    bonus = 0

    if cc_lower in ("wechat", "weixin", "微信"):
        bonus = tier["wechat_bonus"]
    else:
        coupon = auth_db.get_valid_coupon(code)
        if coupon:
            try:
                auth_db.record_coupon_use(code)
            except Exception:
                pass
            # Admin-defined coupons replace the base allotment with the "coupon tier";
            # we grant the delta as a bonus on top of what was already given.
            target = tier["coupon_personal"] if is_personal else tier["coupon_business"]
            base = tier["base_personal"] if is_personal else tier["base_business"]
            bonus = max(0, target - base)

    new_balance = None
    if bonus > 0:
        try:
            new_balance = auth_db.add_credits(uid, bonus)
        except Exception:
            new_balance = None

    return {"applied": bonus > 0, "bonus": bonus, "code": code, "new_balance": new_balance}


def _notify_verification_code_sent(
    *,
    tenant: str,
    username: str,
    email: str,
    credits_granted: int,
    coupon_code: Optional[str] = None,
    marketing_opt_in: bool = False,
    news_opt_in: bool = False,
    source: str = "register",
) -> None:
    """Notify the admin when a verification code is sent.

    The customer-facing verification email is BCC'd to the admin inbox, but this
    separate notification makes registration/contact details easy to scan.
    """
    try:
        extra_bits = [f"source={source}", f"tenant={tenant}"]
        if tenant == "therasik":
            if _is_edu_email(email):
                extra_bits.append("academic_email=yes (+20% signup credits)")
            if _is_personal_email(email):
                extra_bits.append("email_type=personal")
            else:
                extra_bits.append("email_type=company_or_academic")
            if coupon_code:
                cc = coupon_code.strip()
                if cc.lower() in ("wechat", "weixin", "微信"):
                    extra_bits.append("wechat_bonus_pending=yes (after verification)")
        auth_db.send_admin_notification(
            event="VERIFICATION_CODE_SENT",
            username=username,
            user_email=email,
            credits_granted=int(credits_granted or 0),
            coupon_code=(coupon_code or "").strip(),
            coupon_bonus=0,
            marketing_opt_in=marketing_opt_in,
            news_opt_in=news_opt_in,
            extra="; ".join(extra_bits),
        )
    except Exception:
        pass


# Backwards-compatible shim: older call sites that used the legacy combined function
# now receive base credits only; coupon credits land after email verification.
def _determine_trial_credits(
    email: str,
    coupon_code: Optional[str] = None,
    tenant: str = "insynbio",
) -> int:
    return _determine_base_trial_credits(email, tenant=tenant)


def _sync_admin_from_peer_tenant(password: str, tenant: str) -> Optional[Dict[str, Any]]:
    """Allow admin to log in across isolated tenant DBs."""
    other = "therasik" if tenant == "insynbio" else "insynbio"
    token = auth_db.push_namespace(other)
    try:
        src = auth_db.get_user_by_username("admin")
    finally:
        auth_db.pop_namespace(token)
    if not src or not auth_db.verify_pin(src, password):
        return None

    dst = auth_db.get_user_by_username("admin")
    if not dst:
        uid = auth_db.create_user(
            "admin",
            password,
            email=src.get("email"),
            role="owner",
            credits=auth_db.OWNER_DEFAULT_CREDITS,
            credits_unlimited=1,
            terms_accepted=True,
            marketing_opt_in=False,
        )
        auth_db.ensure_owner_profile(uid)
        return auth_db.get_user_by_id(uid)

    uid = int(dst["id"])
    if not auth_db.verify_pin(dst, password):
        auth_db.set_user_password(uid, password)
    auth_db.ensure_owner_profile(uid)
    return auth_db.get_user_by_id(uid)


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, request: Request) -> TokenResponse:
    tenant = _bind_tenant(request)
    if os.environ.get("INSYNBIO_ALLOW_REGISTER", "1").strip() not in ("1", "true", "yes"):
        raise HTTPException(403, "Registration disabled (set INSYNBIO_ALLOW_REGISTER=1)")

    password = _password(req)
    confirm = _confirm_password(req)
    _validate_username_pin(req.username, password)
    _validate_email(req.email)
    if not confirm:
        raise HTTPException(422, "Please confirm your password")
    if password != confirm:
        raise HTTPException(422, "Passwords do not match")
    if not req.accept_terms:
        raise HTTPException(422, "Terms and Privacy Policy acceptance is required")

    auth_db.init_db()
    by_name = auth_db.get_user_by_username(req.username)
    by_email = auth_db.get_user_by_email(req.email)

    if by_name and int(by_name.get("is_verified") or 0):
        raise HTTPException(409, "Username already taken")
    if by_email and int(by_email.get("is_verified") or 0):
        raise HTTPException(409, "Email already registered")
    if by_name and by_email and int(by_name["id"]) != int(by_email["id"]):
        raise HTTPException(409, "Username and email belong to different pending registrations")

    try:
        credits_to_grant = _determine_base_trial_credits(req.email, tenant=tenant)
        pending_coupon = (req.coupon_code or "").strip() or None
        if by_name or by_email:
            existing = by_name or by_email
            uid = int(existing["id"])
            auth_db.update_unverified_user(
                uid,
                username=req.username,
                email=req.email,
                pin=password,
                credits=credits_to_grant,
                terms_accepted=req.accept_terms,
                marketing_opt_in=req.marketing_opt_in,
                news_opt_in=req.news_opt_in,
                pending_coupon=pending_coupon,
            )
        else:
            uid = auth_db.create_user(
                req.username,
                password,
                email=req.email,
                role="trial",
                credits=credits_to_grant,
                terms_accepted=req.accept_terms,
                marketing_opt_in=req.marketing_opt_in,
                news_opt_in=req.news_opt_in,
                pending_coupon=pending_coupon,
            )
    except sqlite3.IntegrityError:
        raise HTTPException(409, "Username or email already taken")

    u = auth_db.get_user_by_id(uid)
    if not u:
        raise HTTPException(500, "User create failed")

    # Generate and send verification code
    code = "".join(secrets.choice("0123456789") for _ in range(6))
    auth_db.set_verification_code(uid, code)
    print(f"VERIFY_CODE[{tenant}] for {req.email} ({req.username}): {code}", flush=True)
    auth_db.send_verification_email(req.email, code, username=req.username)
    _notify_verification_code_sent(
        tenant=tenant,
        username=req.username,
        email=req.email,
        credits_granted=credits_to_grant,
        coupon_code=pending_coupon,
        marketing_opt_in=req.marketing_opt_in,
        news_opt_in=req.news_opt_in,
        source="register",
    )

    tok = auth_db.sign_session(uid, u["username"], u["role"], tenant=tenant)
    return TokenResponse(
        access_token=tok,
        username=u["username"],
        credits=int(u["credits"]),
        role=str(u["role"]),
        credits_unlimited=_unl(u),
        is_verified=bool(u.get("is_verified", 0)),
    )


@router.post("/verify-email")
def verify_email(req: VerifyEmailRequest, request: Request):
    tenant = _bind_tenant(request)
    u = _user_lookup(req.username)
    if not u:
        raise HTTPException(404, "User not found")

    code = re.sub(r"\D", "", (req.code or "").strip())
    if len(code) != 6:
        raise HTTPException(400, "Invalid or expired verification code")

    uid = int(u["id"])
    ok = auth_db.verify_user_email(uid, code)
    if not ok:
        print(
            f"VERIFY_FAIL[{tenant}] user={u.get('username')} id={u.get('id')} code={code}",
            flush=True,
        )
        raise HTTPException(400, "Invalid or expired verification code")

    email = u.get("email") or ""
    coupon_result = _apply_pending_coupon_after_verify(uid, email, tenant)

    # Fire admin notification (silently — never block the response).
    try:
        refreshed = auth_db.get_user_by_id(uid) or u
        auth_db.send_admin_notification(
            event="EMAIL_VERIFIED",
            username=u.get("username", ""),
            user_email=email,
            credits_granted=int(refreshed.get("credits") or 0),
            coupon_code=coupon_result.get("code") or "",
            coupon_bonus=int(coupon_result.get("bonus") or 0),
            marketing_opt_in=bool(int(refreshed.get("marketing_opt_in") or 0)),
            news_opt_in=bool(int(refreshed.get("news_opt_in") or 0)),
        )
    except Exception:
        pass

    return {
        "ok": True,
        "message": "Email verified successfully",
        "coupon_applied": bool(coupon_result.get("applied")),
        "coupon_bonus": int(coupon_result.get("bonus") or 0),
        "coupon_code": coupon_result.get("code"),
        "credits_balance": coupon_result.get("new_balance"),
    }


@router.post("/resend-verification")
def resend_verification(req: ResendVerificationRequest, request: Request) -> Dict[str, Any]:
    tenant = _bind_tenant(request)
    u = _user_lookup(req.username)
    if u and not int(u.get("is_verified") or 0) and u.get("email"):
        code = "".join(secrets.choice("0123456789") for _ in range(6))
        auth_db.set_verification_code(int(u["id"]), code)
        print(f"VERIFY_CODE[{tenant}] resend for {u['email']} ({u['username']}): {code}", flush=True)
        auth_db.send_verification_email(str(u["email"]), code, username=str(u["username"]))
        _notify_verification_code_sent(
            tenant=tenant,
            username=str(u["username"]),
            email=str(u["email"]),
            credits_granted=int(u.get("credits") or 0),
            marketing_opt_in=bool(int(u.get("marketing_opt_in") or 0)),
            news_opt_in=bool(int(u.get("news_opt_in") or 0)),
            source="resend_verification",
        )
    return {"ok": True, "message": "If the account exists, a verification code was sent."}


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request) -> TokenResponse:
    tenant = _bind_tenant(request)
    password = _password(req)
    _validate_username_pin(req.username, password)
    _check_login_rate_limit(req.username)
    is_admin = req.username.strip().lower() == "admin"
    u = auth_db.get_user_by_username(req.username)
    if (not u or not auth_db.verify_pin(u, password)) and is_admin:
        u = _sync_admin_from_peer_tenant(password, tenant)
    if not u or not auth_db.verify_pin(u, password):
        _record_login_failure(req.username)
        raise HTTPException(401, "Invalid username or PIN")
    if str(u.get("role") or "") != "owner" and not int(u.get("is_verified") or 0):
        raise HTTPException(403, "Email verification required before login")

    _record_login_success(req.username)
    tok = auth_db.sign_session(int(u["id"]), u["username"], u["role"], tenant=tenant)
    return TokenResponse(
        access_token=tok,
        username=u["username"],
        credits=int(u["credits"]),
        role=str(u["role"]),
        credits_unlimited=_unl(u),
        is_verified=bool(u.get("is_verified", 0)),
    )


@router.post("/forgot-username")
def forgot_username(req: ForgotUsernameRequest, request: Request) -> Dict[str, Any]:
    _bind_tenant(request)
    _validate_email(req.email)
    u = auth_db.get_user_by_email(req.email)
    if u:
        brand = auth_db.get_mail_brand()
        if brand["tenant"] == "therasik":
            subject = "Therasik Console 账户用户名 / Account Username"
            body = (
                f"您好 {u['username']}，\n\n"
                f"与此邮箱关联的用户名为：{u['username']}\n\n"
                "如非本人操作，请忽略本邮件。\n\n"
                f"Therasik Console\n{brand['contact']}\n\n"
                "---\n\n"
                f"Hello {u['username']},\n\n"
                f"The username associated with this email is: {u['username']}\n\n"
                "If you did not request this, please ignore this message.\n\n"
                f"Therasik Console\n{brand['contact']}"
            )
        else:
            subject = "InSynBio Console Account Username"
            body = (
                f"Hello {u['username']},\n\n"
                f"The username associated with this email is: {u['username']}\n\n"
                "If you did not request this, please ignore this message.\n\n"
                f"InSynBio Console\n{brand['contact']}"
            )
        auth_db.send_service_email(req.email, subject, body)
    return {"ok": True, "message": "If the email is registered, account details were sent."}


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, request: Request) -> Dict[str, Any]:
    tenant = _bind_tenant(request)
    u = _user_lookup(req.username_or_email)
    if u and u.get("email"):
        code = "".join(secrets.choice("0123456789") for _ in range(6))
        auth_db.set_verification_code(int(u["id"]), code)
        print(f"RESET_CODE[{tenant}] for {u['email']}: {code}", flush=True)
        auth_db.send_verification_email(str(u["email"]), code, username=str(u["username"]))
    return {"ok": True, "message": "If the account exists, a reset code was sent."}


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, request: Request) -> Dict[str, Any]:
    _bind_tenant(request)
    u = _user_lookup(req.username_or_email)
    if not u:
        raise HTTPException(400, "Invalid or expired reset code")
    _validate_username_pin(str(u["username"]), req.password)
    if req.password != req.confirm_password:
        raise HTTPException(422, "Passwords do not match")
    code = re.sub(r"\D", "", (req.code or "").strip())
    if not auth_db.verify_user_email(int(u["id"]), code):
        raise HTTPException(400, "Invalid or expired reset code")
    auth_db.set_user_password(int(u["id"]), req.password)
    return {"ok": True, "message": "Password updated. Please log in."}


@router.get("/me", response_model=MeResponse)
def me(request: Request, payload: Dict[str, Any] = Depends(get_session_payload)) -> MeResponse:
    _bind_tenant(request)
    u = auth_db.get_user_by_id(int(payload["uid"]))
    if not u:
        raise HTTPException(401, "User not found")
    return MeResponse(
        username=u["username"],
        email=u.get("email"),
        credits=int(u["credits"]),
        role=str(u["role"]),
        credits_unlimited=_unl(u),
        is_verified=bool(u.get("is_verified", 0)),
    )


@router.get("/gate/me", response_model=MeResponse)
def gate_me(request: Request, gate: Dict[str, str] = Depends(_gate_payload)) -> MeResponse:
    _bind_tenant(request)
    u = auth_db.ensure_gate_user(gate["username"], gate["role"])
    return MeResponse(
        username=str(u["username"]),
        credits=int(u["credits"]),
        role=str(u["role"]),
        credits_unlimited=_unl(u),
    )


@router.post("/debit", response_model=DebitResponse)
def debit(
    request: Request,
    body: DebitRequest,
    payload: Dict[str, Any] = Depends(get_session_payload),
) -> DebitResponse:
    _bind_tenant(request)
    uid = int(payload["uid"])
    
    # Waive cost for demo sequences (up to 10 times)
    amount = body.amount
    if body.extra and body.extra.get("demoId"):
        demo_count = auth_db.count_demo_runs(uid)
        if demo_count < 10:
            amount = 0
        else:
            # After 10 times, demo runs cost normal credits
            pass
    
    ok, bal, msg = auth_db.debit_user(
        uid, amount, body.service_id, body.run_id, body.extra
    )
    debited = 0 if (ok and (str(msg) == "unlimited" or amount == 0)) else (body.amount if ok else 0)
    return DebitResponse(
        ok=ok,
        balance=bal,
        debited=debited,
        message=str(msg),
    )


@router.post("/gate/debit", response_model=DebitResponse)
def gate_debit(
    request: Request,
    body: GateDebitRequest,
    gate: Dict[str, str] = Depends(_gate_payload),
) -> DebitResponse:
    _bind_tenant(request)
    u = auth_db.ensure_gate_user(gate["username"], gate["role"])
    
    # Waive cost for demo sequences (up to 10 times)
    amount = body.amount
    if body.extra and body.extra.get("demoId"):
        demo_count = auth_db.count_demo_runs(uid)
        if demo_count < 10:
            amount = 0
        else:
            # After 10 times, demo runs cost normal credits
            pass
        
    ok, bal, msg = auth_db.debit_user(
        int(u["id"]), amount, body.service_id, body.run_id, body.extra
    )
    debited = 0 if (ok and (str(msg) == "unlimited" or amount == 0)) else (body.amount if ok else 0)
    return DebitResponse(
        ok=ok,
        balance=bal,
        debited=debited,
        message=str(msg),
    )


@router.get("/ledger")
def ledger(
    request: Request,
    payload: Dict[str, Any] = Depends(get_session_payload),
    limit: int = 50,
) -> Dict[str, Any]:
    _bind_tenant(request)
    uid = int(payload["uid"])
    rows = auth_db.ledger_for_user(uid, min(limit, 200))
    return {"items": rows}


@router.get("/gate/ledger")
def gate_ledger(
    request: Request,
    gate: Dict[str, str] = Depends(_gate_payload),
    limit: int = 50,
) -> Dict[str, Any]:
    _bind_tenant(request)
    u = auth_db.ensure_gate_user(gate["username"], gate["role"])
    rows = auth_db.ledger_for_user(int(u["id"]), min(limit, 200))
    return {"items": rows}


class EmailSmokeRequest(BaseModel):
    tenant: str = Field(..., description="insynbio or therasik")
    to: str = Field(..., description="Recipient email for the smoke test")


@router.post("/admin/email-smoke")
def admin_email_smoke(
    request: Request,
    body: EmailSmokeRequest,
    payload: Dict[str, Any] = Depends(get_session_payload),
) -> Dict[str, Any]:
    """Admin-only outbound SMTP smoke test. Sends a small message via the
    selected tenant SMTP profile and returns structured status. Does not
    create any user, does not generate verification codes, and does not
    accept anonymous callers.
    """
    _bind_tenant(request)
    u = auth_db.get_user_by_id(int(payload["uid"]))
    if not u:
        raise HTTPException(401, "User not found")
    role = str(u.get("role") or "").strip().lower()
    if role not in ("admin", "owner"):
        raise HTTPException(403, "admin only")

    tenant_q = (body.tenant or "").strip().lower()
    if tenant_q not in ("insynbio", "therasik"):
        raise HTTPException(400, "tenant must be 'insynbio' or 'therasik'")
    to_addr = (body.to or "").strip()
    if "@" not in to_addr or len(to_addr) > 320:
        raise HTTPException(400, "invalid recipient email")

    result = auth_db.send_smoke_email(tenant_q, to_addr)
    return result
