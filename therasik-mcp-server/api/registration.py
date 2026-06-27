"""
registration.py — Self-service registration, email verification,
dashboard login, and API key management.

Industry-standard flow (OpenAI / Anthropic / Cursor model):
  1. POST /register         → create unverified user, send verify link
  2. GET  /verify/{token}   → activate account, redirect to dashboard
  3. GET  /dashboard        → key management UI (session-gated)
  4. POST /keys             → create new key (returned ONCE, then only prefix shown)
  5. DELETE /keys/{prefix}  → revoke a key
  6. POST /checkout         → Stripe upgrade (upgrades plan, no new key)
  7. POST /stripe/webhook   → payment confirmed → upgrade plan quota in-place

One account = N keys (labeled, revocable). Plan quota shared across all active keys.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import smtplib
import logging
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import stripe
from fastapi import APIRouter, Cookie, HTTPException, Request, BackgroundTasks, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import text

from .db import get_session
from .auth import SECRET_SALT

logger = logging.getLogger("therasik.registration")
router = APIRouter()

# ── Config ─────────────────────────────────────────────────────────────────────
STRIPE_SECRET      = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SEC = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
SMTP_HOST          = os.environ.get("THERASIK_SMTP_HOST", "mail.privateemail.com")
SMTP_PORT          = int(os.environ.get("THERASIK_SMTP_PORT", 587))
SMTP_USER          = os.environ.get("THERASIK_SMTP_USER", "contact@therasik.com")
SMTP_PASS          = os.environ.get("THERASIK_SMTP_PASS", "")
SMTP_FROM          = os.environ.get("THERASIK_EMAIL_SENDER", "TheraSIK <contact@therasik.com>")
BASE_URL           = os.environ.get("THERASIK_BASE_URL", "https://mcp.therasik.com")
SESSION_SECRET     = os.environ.get("THERASIK_SESSION_SECRET", SECRET_SALT + "_session")

if STRIPE_SECRET:
    stripe.api_key = STRIPE_SECRET

STRIPE_PRICES = {
    "starter":     os.environ.get("STRIPE_PRICE_STARTER", ""),
    "pro":         os.environ.get("STRIPE_PRICE_PRO", ""),
    "team":        os.environ.get("STRIPE_PRICE_TEAM", ""),
    "institution": os.environ.get("STRIPE_PRICE_INSTITUTION", ""),
}

PLAN_QUOTAS = {
    "free":        {"tool_quota": 100,   "token_quota": 100_000,   "tier": "free"},
    "starter":     {"tool_quota": 1000,  "token_quota": 500_000,   "tier": "starter"},
    "pro":         {"tool_quota": 5000,  "token_quota": 2_000_000, "tier": "pro"},
    "team":        {"tool_quota": 20000, "token_quota": 8_000_000, "tier": "team"},
    "institution": {"tool_quota": -1,    "token_quota": -1,        "tier": "enterprise"},
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def _send_email(to: str, subject: str, html: str):
    if not SMTP_PASS:
        logger.warning(f"SMTP not configured — skipping email to {to}: {subject}")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SMTP_FROM
        msg["To"]      = to
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_USER, to, msg.as_string())
        logger.info(f"Email sent → {to}: {subject}")
    except Exception as exc:
        logger.error(f"Email failed → {to}: {exc}")


def _make_session_token(email: str) -> str:
    """Short-lived signed session token for dashboard access."""
    payload  = f"{email}:{int(datetime.now(timezone.utc).timestamp())}"
    sig      = hmac.new(SESSION_SECRET.encode(), payload.encode(), "sha256").hexdigest()
    return f"{payload}:{sig}"


def _verify_session_token(token: str, max_age_h: int = 24) -> str | None:
    """Returns email if valid, else None."""
    try:
        parts = token.rsplit(":", 2)
        if len(parts) != 3:
            return None
        email, ts_str, sig = parts
        payload  = f"{email}:{ts_str}"
        expected = hmac.new(SESSION_SECRET.encode(), payload.encode(), "sha256").hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        age = datetime.now(timezone.utc).timestamp() - float(ts_str)
        if age > max_age_h * 3600:
            return None
        return email
    except Exception:
        return None


def _generate_api_key() -> tuple[str, str, str]:
    """Returns (raw_key, key_hash, key_prefix)."""
    raw    = "THMCP-" + secrets.token_urlsafe(32)
    hashed = hashlib.sha256((SECRET_SALT + raw).encode()).hexdigest()
    prefix = raw[:12]  # "THMCP-xxxxxx"
    return raw, hashed, prefix


# ── Dashboard HTML helper ──────────────────────────────────────────────────────
def _dashboard_html(email: str, plan: str, keys: list[dict],
                    new_key: str | None = None) -> str:
    plan_badge = {
        "free": "#94a3b8", "starter": "#3b82f6",
        "pro": "#8b5cf6", "team": "#059669", "institution": "#dc2626"
    }.get(plan, "#64748b")

    new_key_block = ""
    if new_key:
        new_key_block = f"""
        <div style="background:#fefce8;border:2px solid #fbbf24;border-radius:10px;
                    padding:20px;margin:20px 0">
          <p style="margin:0 0 8px;font-weight:700;color:#92400e">
            ⚠️ Copy your key now — it will not be shown again
          </p>
          <code id="newkey" style="display:block;background:#fff;border:1px solid #fbbf24;
                border-radius:6px;padding:12px;font-size:13px;word-break:break-all;
                cursor:pointer" onclick="navigator.clipboard.writeText(this.innerText)
                .then(()=>this.style.background='#f0fdf4')">{new_key}</code>
          <p style="margin:8px 0 0;color:#92400e;font-size:12px">
            Click the key to copy. Store it securely (password manager).
          </p>
        </div>"""

    keys_rows = ""
    for k in keys:
        created = str(k.get("created_at", ""))[:10]
        last    = str(k.get("last_used_at", "") or "never")[:16]
        label   = k.get("label") or "(unlabeled)"
        prefix  = k.get("key_prefix", "")
        keys_rows += f"""
        <tr>
          <td style="padding:10px 8px"><code>{prefix}...</code></td>
          <td style="padding:10px 8px;color:#64748b">{label}</td>
          <td style="padding:10px 8px;color:#64748b">{created}</td>
          <td style="padding:10px 8px;color:#64748b">{last}</td>
          <td style="padding:10px 8px">
            <form method="post" action="/keys/{prefix}/revoke" style="margin:0"
                  onsubmit="return confirm('Revoke this key?')">
              <button type="submit"
                style="background:#fee2e2;color:#dc2626;border:1px solid #fca5a5;
                       border-radius:4px;padding:4px 10px;cursor:pointer;font-size:12px">
                Revoke
              </button>
            </form>
          </td>
        </tr>"""

    if not keys_rows:
        keys_rows = """<tr><td colspan="5" style="padding:20px;color:#94a3b8;text-align:center">
            No API keys yet. Create your first key below.</td></tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>TheraSIK — API Keys</title>
  <style>
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
          background:#f8fafc;margin:0;padding:0;color:#1e293b}}
    .nav{{background:#fff;border-bottom:1px solid #e2e8f0;padding:14px 32px;
          display:flex;align-items:center;gap:12px}}
    .logo{{font-weight:800;font-size:18px;color:#1e293b}}
    .badge{{background:{plan_badge};color:#fff;border-radius:20px;
            padding:3px 10px;font-size:11px;font-weight:700;text-transform:uppercase}}
    .container{{max-width:860px;margin:32px auto;padding:0 20px}}
    h2{{font-size:20px;margin:24px 0 12px}}
    .card{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;
           padding:24px;margin-bottom:24px}}
    table{{width:100%;border-collapse:collapse;font-size:14px}}
    th{{text-align:left;padding:10px 8px;color:#64748b;font-weight:600;
        border-bottom:1px solid #e2e8f0;font-size:12px;text-transform:uppercase}}
    tr:hover{{background:#f8fafc}}
    .btn{{background:#2563eb;color:#fff;border:none;border-radius:6px;
          padding:10px 20px;font-size:14px;cursor:pointer;font-weight:600}}
    .btn:hover{{background:#1d4ed8}}
    input[type=text]{{border:1px solid #e2e8f0;border-radius:6px;padding:8px 12px;
                      font-size:14px;width:260px;margin-right:8px}}
    .info{{color:#64748b;font-size:13px;margin-top:8px}}
  </style>
</head>
<body>
<div class="nav">
  <span class="logo">TheraSIK</span>
  <span class="badge">{plan}</span>
  <span style="margin-left:auto;color:#64748b;font-size:13px">{email}</span>
  <a href="/pricing" style="margin-left:16px;color:#2563eb;font-size:13px">Upgrade</a>
</div>
<div class="container">
  <h2>API Keys</h2>
  {new_key_block}
  <div class="card">
    <table>
      <thead><tr>
        <th>Key Prefix</th><th>Label</th><th>Created</th>
        <th>Last Used</th><th>Action</th>
      </tr></thead>
      <tbody>{keys_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h3 style="margin:0 0 12px;font-size:16px">Create New Key</h3>
    <form method="post" action="/keys">
      <input type="text" name="label" placeholder="Label (e.g. Hermes Agent, Lab Mac)">
      <button type="submit" class="btn">+ Create Key</button>
    </form>
    <p class="info">The key will be shown <strong>once</strong>.
       Store it in your password manager or environment variables.</p>
  </div>

  <div style="color:#94a3b8;font-size:11px;text-align:center;padding:20px 0">
    TheraSIK Agent — Your Zotero library and manuscripts stay on your machine.
    We never see your files. &nbsp;·&nbsp; MCP URL: <code>https://mcp.therasik.com/mcp/sse</code>
  </div>
</div>
</body></html>"""


# ── 1. Register ────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    name:  str = ""


@router.post("/register")
async def register(req: RegisterRequest, background: BackgroundTasks):
    async with get_session() as session:
        existing = await session.execute(
            text("SELECT id FROM users WHERE email = :e"), {"e": req.email}
        )
        if existing.fetchone():
            raise HTTPException(409, "Email already registered")

        await session.execute(text("""
            INSERT INTO users (email, name, plan, verified, created_at)
            VALUES (:email, :name, 'free', false, now())
        """), {"email": req.email, "name": req.name or req.email.split("@")[0]})

        token = secrets.token_urlsafe(32)
        await session.execute(text("""
            INSERT INTO reg_tokens (email, token, expires_at)
            VALUES (:email, :token, now() + interval '24 hours')
        """), {"email": req.email, "token": token})
        await session.commit()

    verify_url = f"{BASE_URL}/verify/{token}"
    html = f"""
    <p>Click the link below to verify your TheraSIK account:</p>
    <p style="margin:24px 0">
      <a href="{verify_url}"
         style="background:#2563eb;color:#fff;padding:12px 28px;border-radius:6px;
                text-decoration:none;font-weight:600">Verify Email Address</a>
    </p>
    <p style="color:#94a3b8;font-size:12px">
      This link expires in 24 hours. If you didn't register, ignore this email.
    </p>"""
    background.add_task(
        _send_email, req.email, "Verify your TheraSIK account", html
    )
    return {"status": "verification_sent", "email": req.email}


# ── 2. Verify email → redirect to dashboard ────────────────────────────────────
@router.get("/verify/{token}")
async def verify_email(token: str):
    async with get_session() as session:
        row = await session.execute(
            text("SELECT email, used, expires_at FROM reg_tokens WHERE token = :t"),
            {"t": token}
        )
        rec = row.fetchone()
        if not rec:
            return HTMLResponse("<h2>Invalid link.</h2>", 404)
        email, used, expires_at = rec
        if used:
            return HTMLResponse("<h2>Link already used. <a href='/dashboard'>Go to Dashboard</a></h2>")
        if datetime.now(timezone.utc) > expires_at:
            return HTMLResponse("<h2>Link expired. Please register again.</h2>", 410)

        await session.execute(
            text("UPDATE users SET verified=true WHERE email=:e"), {"e": email}
        )
        await session.execute(
            text("UPDATE reg_tokens SET used=true WHERE token=:t"), {"t": token}
        )
        await session.commit()

    # Set signed session cookie → redirect to dashboard
    session_tok = _make_session_token(email)
    resp = RedirectResponse("/dashboard", status_code=303)
    resp.set_cookie(
        "therasik_session", session_tok,
        max_age=86400, httponly=True, samesite="lax",
        secure=(BASE_URL.startswith("https"))
    )
    return resp


# ── 3. Dashboard ───────────────────────────────────────────────────────────────
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request,
                    therasik_session: str | None = Cookie(default=None)):
    email = _verify_session_token(therasik_session or "")
    if not email:
        return HTMLResponse("""
        <html><body style="font-family:sans-serif;text-align:center;padding:60px">
        <h2>Session expired</h2>
        <p>Please <a href="/pricing">register</a> or request a new sign-in link.</p>
        </body></html>""", 401)

    async with get_session() as session:
        user_row = await session.execute(
            text("SELECT plan FROM users WHERE email=:e"), {"e": email}
        )
        plan = (user_row.fetchone() or ["free"])[0]

        keys_rows = await session.execute(text("""
            SELECT key_prefix, label, created_at, last_used_at
            FROM api_keys
            WHERE user_id = (SELECT id FROM users WHERE email=:e)
              AND active = true
            ORDER BY created_at DESC
        """), {"e": email})
        keys = [dict(r._mapping) for r in keys_rows.fetchall()]

    return HTMLResponse(_dashboard_html(email, plan, keys))


# ── 4. Create key ──────────────────────────────────────────────────────────────
@router.post("/keys", response_class=HTMLResponse)
async def create_key(request: Request,
                     label: str = Form(default=""),
                     therasik_session: str | None = Cookie(default=None)):
    email = _verify_session_token(therasik_session or "")
    if not email:
        return RedirectResponse("/dashboard", 303)

    raw, hashed, prefix = _generate_api_key()

    async with get_session() as session:
        user_row = await session.execute(
            text("SELECT id, plan FROM users WHERE email=:e"), {"e": email}
        )
        rec = user_row.fetchone()
        if not rec:
            raise HTTPException(404, "User not found")
        user_id, plan = rec
        quotas  = PLAN_QUOTAS.get(plan, PLAN_QUOTAS["free"])
        expires = datetime.now(timezone.utc) + timedelta(days=365)

        await session.execute(text("""
            INSERT INTO api_keys
              (user_id, key_hash, key_prefix, label, tier,
               monthly_quota, monthly_token_quota, valid_until, active, created_at)
            VALUES
              (:uid, :hash, :pfx, :label, :tier, :mq, :tq, :exp, true, now())
        """), {
            "uid":   user_id,
            "hash":  hashed,
            "pfx":   prefix,
            "label": label[:80] if label else None,
            "tier":  quotas["tier"],
            "mq":    quotas["tool_quota"],
            "tq":    quotas["token_quota"],
            "exp":   expires,
        })

        keys_rows = await session.execute(text("""
            SELECT key_prefix, label, created_at, last_used_at
            FROM api_keys
            WHERE user_id=:uid AND active=true ORDER BY created_at DESC
        """), {"uid": user_id})
        keys = [dict(r._mapping) for r in keys_rows.fetchall()]
        await session.commit()

    resp = HTMLResponse(_dashboard_html(email, plan, keys, new_key=raw))
    resp.set_cookie("therasik_session", _make_session_token(email),
                    max_age=86400, httponly=True, samesite="lax",
                    secure=(BASE_URL.startswith("https")))
    return resp


# ── 5. Revoke key ──────────────────────────────────────────────────────────────
@router.post("/keys/{prefix}/revoke", response_class=HTMLResponse)
async def revoke_key(prefix: str, request: Request,
                     therasik_session: str | None = Cookie(default=None)):
    email = _verify_session_token(therasik_session or "")
    if not email:
        return RedirectResponse("/dashboard", 303)

    async with get_session() as session:
        await session.execute(text("""
            UPDATE api_keys SET active=false
            WHERE key_prefix=:pfx
              AND user_id=(SELECT id FROM users WHERE email=:e)
        """), {"pfx": prefix, "e": email})
        await session.commit()

    return RedirectResponse("/dashboard", 303)


# ── 6. Checkout ────────────────────────────────────────────────────────────────
class CheckoutRequest(BaseModel):
    email: EmailStr
    plan:  str


@router.post("/checkout")
async def create_checkout(req: CheckoutRequest):
    if not STRIPE_SECRET:
        raise HTTPException(503, "Payment not configured")
    price_id = STRIPE_PRICES.get(req.plan)
    if not price_id:
        raise HTTPException(400, f"Unknown plan: {req.plan}")

    async with get_session() as session:
        row = await session.execute(
            text("SELECT id FROM users WHERE email=:e AND verified=true"),
            {"e": req.email}
        )
        if not row.fetchone():
            raise HTTPException(404, "Unverified account — verify email first")

    sess = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        customer_email=req.email,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{BASE_URL}/dashboard",
        cancel_url=f"{BASE_URL}/pricing",
        metadata={"email": req.email, "plan": req.plan},
    )
    return {"checkout_url": sess.url}


# ── 7. Stripe webhook → upgrade plan in-place (no new key) ────────────────────
@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, background: BackgroundTasks):
    payload = await request.body()
    sig     = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SEC)
    except Exception as exc:
        raise HTTPException(400, str(exc))

    if event["type"] == "checkout.session.completed":
        sess  = event["data"]["object"]
        email = sess["metadata"]["email"]
        plan  = sess["metadata"]["plan"]
        quotas  = PLAN_QUOTAS.get(plan, PLAN_QUOTAS["starter"])
        expires = datetime.now(timezone.utc) + timedelta(days=365)

        async with get_session() as session:
            uid_row = await session.execute(
                text("SELECT id FROM users WHERE email=:e"), {"e": email}
            )
            user_id = uid_row.fetchone()[0]

            # Upgrade plan on user record
            await session.execute(
                text("UPDATE users SET plan=:p WHERE id=:uid"),
                {"p": plan, "uid": user_id}
            )
            # Upgrade ALL active keys for this user in-place — no new key issued
            await session.execute(text("""
                UPDATE api_keys
                SET tier=:tier, monthly_quota=:mq,
                    monthly_token_quota=:tq, valid_until=:exp
                WHERE user_id=:uid AND active=true
            """), {"tier": quotas["tier"], "mq": quotas["tool_quota"],
                   "tq": quotas["token_quota"], "exp": expires, "uid": user_id})

            await session.execute(text("""
                INSERT INTO payments (user_id, stripe_session, amount_usd, plan, status, paid_at)
                VALUES (:uid, :sess, :amt, :plan, 'paid', now())
            """), {"uid": user_id, "sess": sess["id"],
                   "amt": (sess.get("amount_total") or 0) / 100, "plan": plan})
            await session.commit()

        html = f"""
        <p>Your TheraSIK account has been upgraded to <strong>{plan.title()}</strong>.</p>
        <p>Your existing API key(s) now have the new quota — no changes needed in your config.</p>
        <p style="margin-top:20px">
          <a href="{BASE_URL}/dashboard"
             style="background:#2563eb;color:#fff;padding:10px 24px;
                    border-radius:6px;text-decoration:none">Open Dashboard</a>
        </p>"""
        background.add_task(
            _send_email, email, f"TheraSIK — Upgraded to {plan.title()}", html
        )

    return {"received": True}


# ── 8. Pricing page (simple) ───────────────────────────────────────────────────
@router.get("/pricing", response_class=HTMLResponse)
async def pricing():
    return HTMLResponse("""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>TheraSIK Pricing</title>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#f8fafc;margin:0;padding:40px 20px;color:#1e293b;text-align:center}
h1{font-size:32px;margin-bottom:8px}
.sub{color:#64748b;margin-bottom:48px}
.plans{display:flex;gap:20px;justify-content:center;flex-wrap:wrap;max-width:900px;margin:0 auto}
.plan{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:28px;width:200px}
.plan.popular{border:2px solid #2563eb}
.price{font-size:28px;font-weight:800;margin:12px 0 4px}
.period{color:#64748b;font-size:13px}
ul{text-align:left;padding-left:20px;font-size:13px;color:#475569;line-height:1.9}
.btn{display:inline-block;margin-top:20px;background:#2563eb;color:#fff;
     padding:10px 20px;border-radius:6px;text-decoration:none;font-weight:600;font-size:14px}
.free-btn{background:#e2e8f0;color:#1e293b}
</style></head>
<body>
<h1>TheraSIK Agent</h1>
<p class="sub">AI Writing Suite for Researchers — your literature stays local</p>
<div class="plans">
  <div class="plan">
    <strong>Free</strong>
    <div class="price">$0</div>
    <ul><li>100 tool calls/mo</li><li>100K LLM tokens</li><li>1 API key</li></ul>
    <a href="#register" class="btn free-btn">Get Started</a>
  </div>
  <div class="plan popular">
    <strong>Starter</strong>
    <div class="price">$12</div><div class="period">/month</div>
    <ul><li>1,000 calls/mo</li><li>500K tokens</li><li>5 API keys</li></ul>
    <a href="#" class="btn">Subscribe</a>
  </div>
  <div class="plan">
    <strong>Pro</strong>
    <div class="price">$39</div><div class="period">/month</div>
    <ul><li>5,000 calls/mo</li><li>2M tokens</li><li>Unlimited keys</li></ul>
    <a href="#" class="btn">Subscribe</a>
  </div>
  <div class="plan">
    <strong>Team</strong>
    <div class="price">$99</div><div class="period">/month</div>
    <ul><li>20,000 calls/mo</li><li>8M tokens</li><li>Multi-seat</li></ul>
    <a href="#" class="btn">Subscribe</a>
  </div>
</div>
<p style="margin-top:48px;color:#94a3b8;font-size:12px">
  MCP URL: mcp.therasik.com &nbsp;·&nbsp;
  Compatible with Hermes Agent, Cursor, Claude Desktop, and any MCP client
</p>
</body></html>""")
