"""
Lightweight SQLite auth for Console trials: username + numeric PIN.
SMS / OAuth can replace verify path later; PIN stays as fallback.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
from contextvars import ContextVar, Token as ContextToken
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "api" / ".data"
DB_PATH = DATA_DIR / "insynbio_auth.db"
_DB_NAMESPACE: ContextVar[str] = ContextVar("insynbio_auth_db_namespace", default="insynbio")

from api.pricing_constants import TRIAL_SIGNUP_CREDITS as _PRICING_TRIAL_CREDITS

# New trial accounts (override with env INSYNBIO_TRIAL_CREDITS)
TRIAL_SIGNUP_CREDITS = int(os.environ.get("INSYNBIO_TRIAL_CREDITS", str(_PRICING_TRIAL_CREDITS)))
OWNER_DEFAULT_CREDITS = int(os.environ.get("INSYNBIO_OWNER_CREDITS", "1000000"))
# Owner bootstrap: skip real deduction (still logs usage with amount 0)
OWNER_UNLIMITED_DEFAULT = os.environ.get("INSYNBIO_OWNER_UNLIMITED", "1").strip().lower() in (
    "1",
    "true",
    "yes",
)

_lock = threading.Lock()


def _sanitize_namespace(namespace: str) -> str:
    ns = (namespace or "insynbio").strip().lower()
    if not ns:
        ns = "insynbio"
    return "".join(ch for ch in ns if ch.isalnum() or ch in ("_", "-")) or "insynbio"


def current_namespace() -> str:
    return _sanitize_namespace(_DB_NAMESPACE.get())


def push_namespace(namespace: str) -> ContextToken:
    return _DB_NAMESPACE.set(_sanitize_namespace(namespace))


def pop_namespace(token: ContextToken) -> None:
    _DB_NAMESPACE.reset(token)


def _db_path() -> Path:
    ns = current_namespace()
    if ns == "insynbio":
        return DB_PATH
    return DATA_DIR / f"{ns}_auth.db"


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_db_path()), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    email TEXT UNIQUE COLLATE NOCASE,
                    pin_salt BLOB NOT NULL,
                    pin_hash TEXT NOT NULL,
                    credits INTEGER NOT NULL DEFAULT 0,
                    role TEXT NOT NULL DEFAULT 'trial',
                    created_at TEXT NOT NULL,
                    credits_unlimited INTEGER NOT NULL DEFAULT 0,
                    is_verified INTEGER NOT NULL DEFAULT 0,
                    verification_code TEXT,
                    verification_expiry INTEGER,
                    terms_accepted_at TEXT,
                    marketing_opt_in INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS usage_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    at_iso TEXT NOT NULL,
                    service_id TEXT,
                    credits INTEGER NOT NULL,
                    run_id TEXT,
                    extra_json TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE INDEX IF NOT EXISTS idx_ledger_user ON usage_ledger(user_id);
                
                CREATE TABLE IF NOT EXISTS coupons (
                    code TEXT PRIMARY KEY COLLATE NOCASE,
                    expires_at INTEGER NOT NULL,
                    max_uses INTEGER NOT NULL DEFAULT 0,
                    times_used INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.commit()
            _migrate_users(conn)
        finally:
            conn.close()


def _migrate_users(conn: sqlite3.Connection) -> None:
    """Add new columns for existing DBs."""
    columns = [
        ("credits_unlimited", "INTEGER NOT NULL DEFAULT 0"),
        # SQLite cannot add a UNIQUE column via ALTER TABLE; uniqueness is
        # enforced for new DBs by CREATE TABLE and in API checks for old DBs.
        ("email", "TEXT COLLATE NOCASE"),
        ("is_verified", "INTEGER NOT NULL DEFAULT 0"),
        ("verification_code", "TEXT"),
        ("verification_expiry", "INTEGER"),
        ("terms_accepted_at", "TEXT"),
        ("marketing_opt_in", "INTEGER NOT NULL DEFAULT 0"),
        # Coupon code captured at registration. Applied after email verification
        # (e.g. WeChat coupon grants +10,000 credits only post-verify).
        ("pending_coupon", "TEXT"),
        # Separate opt-in for affiliated-company newsletters (different from
        # product update opt-in stored in marketing_opt_in).
        ("news_opt_in", "INTEGER NOT NULL DEFAULT 0"),
    ]
    for col_name, col_def in columns:
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
            conn.commit()
        except sqlite3.OperationalError:
            pass


def _hash_pin(pin: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", pin.encode("utf-8"), salt, 120_000, dklen=32
    ).hex()


def create_user(
    username: str,
    pin: str,
    *,
    email: Optional[str] = None,
    role: str = "trial",
    credits: Optional[int] = None,
    credits_unlimited: Optional[int] = None,
    terms_accepted: bool = False,
    marketing_opt_in: bool = False,
    news_opt_in: bool = False,
    pending_coupon: Optional[str] = None,
) -> int:
    init_db()
    if credits is None:
        credits = OWNER_DEFAULT_CREDITS if role == "owner" else TRIAL_SIGNUP_CREDITS
    if credits_unlimited is None:
        credits_unlimited = 1 if (role == "owner" and OWNER_UNLIMITED_DEFAULT) else 0
    salt = secrets.token_bytes(16)
    ph = _hash_pin(pin, salt)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                """
                INSERT INTO users (
                    username, email, pin_salt, pin_hash, credits, role,
                    created_at, credits_unlimited, is_verified,
                    terms_accepted_at, marketing_opt_in, news_opt_in, pending_coupon
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username.strip(),
                    email.strip() if email else None,
                    sqlite3.Binary(salt),
                    ph,
                    credits,
                    role,
                    now,
                    credits_unlimited,
                    1 if role == "owner" else 0,  # Owners are auto-verified
                    now if terms_accepted else None,
                    1 if marketing_opt_in else 0,
                    1 if news_opt_in else 0,
                    (pending_coupon or "").strip() or None,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    init_db()
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT id, username, email, pin_salt, pin_hash, credits, role, created_at, credits_unlimited, is_verified, verification_code, verification_expiry, marketing_opt_in, news_opt_in FROM users WHERE username = ? COLLATE NOCASE",
                (username.strip(),),
            ).fetchone()
            if not row:
                return None
            return dict(row)
        finally:
            conn.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    init_db()
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT id, username, email, pin_salt, pin_hash, credits, role, created_at, credits_unlimited, is_verified, verification_code, verification_expiry, marketing_opt_in, news_opt_in FROM users WHERE email = ? COLLATE NOCASE",
                (email.strip(),),
            ).fetchone()
            if not row:
                return None
            return dict(row)
        finally:
            conn.close()


def get_valid_coupon(code: str) -> Optional[Dict[str, Any]]:
    if not code:
        return None
    init_db()
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM coupons WHERE code = ? COLLATE NOCASE", (code.strip(),)
            ).fetchone()
            if not row:
                return None
            c = dict(row)
            if c["expires_at"] < time.time():
                return None
            if c["max_uses"] > 0 and c["times_used"] >= c["max_uses"]:
                return None
            return c
        finally:
            conn.close()


def record_coupon_use(code: str) -> None:
    if not code:
        return
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "UPDATE coupons SET times_used = times_used + 1 WHERE code = ? COLLATE NOCASE", (code.strip(),)
            )
            conn.commit()
        finally:
            conn.close()


def create_coupon(code: str, expires_in_days: int = 30, max_uses: int = 0) -> None:
    init_db()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    expires_at = int(time.time()) + expires_in_days * 86400
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO coupons (code, expires_at, max_uses, created_at) VALUES (?, ?, ?, ?)",
                (code.strip(), expires_at, max_uses, now)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass # already exists
        finally:
            conn.close()


def set_verification_code(uid: int, code: str, expiry_sec: int = 3600) -> None:
    expiry = int(time.time()) + expiry_sec
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "UPDATE users SET verification_code = ?, verification_expiry = ? WHERE id = ?",
                (code, expiry, uid),
            )
            conn.commit()
        finally:
            conn.close()


def verify_user_email(uid: int, code: str) -> bool:
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT verification_code, verification_expiry FROM users WHERE id = ?",
                (uid,),
            ).fetchone()
            if not row:
                return False
            if row["verification_code"] == code and row["verification_expiry"] > time.time():
                conn.execute(
                    "UPDATE users SET is_verified = 1, verification_code = NULL, verification_expiry = NULL WHERE id = ?",
                    (uid,),
                )
                conn.commit()
                return True
            return False
        finally:
            conn.close()


def add_credits(uid: int, amount: int) -> int:
    with _lock:
        conn = _connect()
        try:
            conn.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (amount, uid))
            conn.commit()
            row = conn.execute("SELECT credits FROM users WHERE id = ?", (uid,)).fetchone()
            return int(row["credits"])
        finally:
            conn.close()


def update_unverified_user(
    uid: int,
    *,
    username: str,
    email: str,
    pin: str,
    credits: int,
    terms_accepted: bool,
    marketing_opt_in: bool,
    news_opt_in: bool = False,
    pending_coupon: Optional[str] = None,
) -> None:
    salt = secrets.token_bytes(16)
    ph = _hash_pin(pin, salt)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                UPDATE users
                SET username = ?, email = ?, pin_salt = ?, pin_hash = ?,
                    credits = ?, terms_accepted_at = ?, marketing_opt_in = ?,
                    news_opt_in = ?, pending_coupon = ?,
                    verification_code = NULL, verification_expiry = NULL
                WHERE id = ? AND is_verified = 0
                """,
                (
                    username.strip(),
                    email.strip(),
                    sqlite3.Binary(salt),
                    ph,
                    credits,
                    now if terms_accepted else None,
                    1 if marketing_opt_in else 0,
                    1 if news_opt_in else 0,
                    (pending_coupon or "").strip() or None,
                    uid,
                ),
            )
            conn.commit()
        finally:
            conn.close()


def pop_pending_coupon(uid: int) -> Optional[str]:
    """Return and clear the pending_coupon for a user (used after email verification)."""
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT pending_coupon FROM users WHERE id = ?", (uid,)
            ).fetchone()
            if not row:
                return None
            code = row["pending_coupon"]
            if not code:
                return None
            conn.execute(
                "UPDATE users SET pending_coupon = NULL WHERE id = ?", (uid,)
            )
            conn.commit()
            return str(code).strip() or None
        finally:
            conn.close()


def set_user_password(uid: int, pin: str) -> None:
    salt = secrets.token_bytes(16)
    ph = _hash_pin(pin, salt)
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "UPDATE users SET pin_salt = ?, pin_hash = ? WHERE id = ?",
                (sqlite3.Binary(salt), ph, uid),
            )
            conn.commit()
        finally:
            conn.close()


def ensure_owner_profile(uid: int) -> None:
    """Force owner role + unlimited credits for platform admin user."""
    with _lock:
        conn = _connect()
        try:
            row = conn.execute("SELECT credits FROM users WHERE id = ?", (uid,)).fetchone()
            if not row:
                return
            current_credits = int(row["credits"] or 0)
            target_credits = max(current_credits, OWNER_DEFAULT_CREDITS)
            conn.execute(
                """
                UPDATE users
                SET role = 'owner',
                    credits_unlimited = 1,
                    is_verified = 1,
                    credits = ?
                WHERE id = ?
                """,
                (target_credits, uid),
            )
            conn.commit()
        finally:
            conn.close()


def _mail_profile() -> Dict[str, Any]:
    """Tenant-specific SMTP + branding.

    Therasik uses Namecheap Private Email (mail.privateemail.com, port 465 SSL).
    Set THERASIK_SMTP_PASS on the server; do not reuse InSynBio SMTP credentials.
    """
    ns = current_namespace()
    if ns == "therasik":
        default_sender = "contact@therasik.com"
        sender = os.environ.get("THERASIK_EMAIL_SENDER", default_sender)
        host = os.environ.get("THERASIK_SMTP_HOST", "mail.privateemail.com")
        port = int(os.environ.get("THERASIK_SMTP_PORT", "465"))
        user = os.environ.get("THERASIK_SMTP_USER", sender)
        password = os.environ.get("THERASIK_SMTP_PASS")
        contact = os.environ.get("THERASIK_EMAIL_CONTACT", default_sender)
        brand = "Therasik Console"
        verify_subject = "Therasik Console 验证码 / Verification Code"
        default_user_label = "Therasik 用户"
    else:
        host = os.environ.get("INSYNBIO_SMTP_HOST")
        port = int(os.environ.get("INSYNBIO_SMTP_PORT", "587"))
        user = os.environ.get("INSYNBIO_SMTP_USER")
        password = os.environ.get("INSYNBIO_SMTP_PASS")
        sender = os.environ.get("INSYNBIO_EMAIL_SENDER", "contact@insynbio.com")
        contact = os.environ.get("INSYNBIO_EMAIL_CONTACT", "contact@insynbio.com")
        brand = "InSynBio Console"
        verify_subject = "InSynBio Console Verification Code"
        default_user_label = "InSynBio user"
    # Admin BCC: owner gets a silent copy of every outgoing customer email.
    # Defaults to the sender address (contact@therasik.com / contact@insynbio.com).
    # Override via THERASIK_EMAIL_ADMIN_BCC or INSYNBIO_EMAIL_ADMIN_BCC.
    if ns == "therasik":
        admin_bcc = os.environ.get("THERASIK_EMAIL_ADMIN_BCC", "contact@therasik.com")
    else:
        admin_bcc = os.environ.get("INSYNBIO_EMAIL_ADMIN_BCC", sender)

    return {
        "tenant": ns,
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "sender": sender,
        "contact": contact,
        "brand": brand,
        "verify_subject": verify_subject,
        "default_user_label": default_user_label,
        "admin_bcc": admin_bcc,
    }


def get_mail_brand() -> Dict[str, str]:
    """Public tenant mail branding for auth routes."""
    m = _mail_profile()
    return {"tenant": m["tenant"], "brand": m["brand"], "contact": m["contact"]}


def smtp_configured(tenant: str) -> bool:
    """Cheap presence check of SMTP env vars for a tenant.

    Does not open any TCP connection. Used by /api/health to surface whether
    the running process actually inherited SMTP credentials.
    """
    ns = (tenant or "insynbio").strip().lower()
    tok = push_namespace(ns)
    try:
        m = _mail_profile()
    finally:
        pop_namespace(tok)
    return bool(m.get("host")) and bool(m.get("user")) and bool(m.get("password"))


def _smtp_send(mail: Dict[str, Any], msg, recipients: List[str]) -> Tuple[bool, str]:
    """Centralised SMTP transport. Returns (ok, error)."""
    import smtplib
    host = mail["host"]
    port = int(mail["port"])
    user = mail["user"]
    password = mail["password"]
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=20) as server:
                server.login(user, password)
                server.send_message(msg, to_addrs=recipients)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.starttls()
                server.login(user, password)
                server.send_message(msg, to_addrs=recipients)
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def send_verification_email(email: str, code: str, username: str = "") -> bool:
    """Send verification email using SMTP settings from environment."""
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    mail = _mail_profile()
    smtp_host = mail["host"]
    smtp_port = mail["port"]
    smtp_user = mail["user"]
    smtp_pass = mail["password"]
    sender = mail["sender"]
    brand = mail["brand"]
    contact = mail["contact"]

    if not all([smtp_host, smtp_user, smtp_pass]):
        hint = (
            "set THERASIK_SMTP_PASS (Private Email for contact@therasik.com)"
            if mail["tenant"] == "therasik"
            else "set INSYNBIO_SMTP_*"
        )
        print(
            f"[AUTH][{mail['tenant']}] Email verification code for {email}: {code} (SMTP not configured; {hint})",
            flush=True,
        )
        return True

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = email
    msg["Subject"] = mail["verify_subject"]
    if mail.get("admin_bcc") and mail["admin_bcc"] != email:
        msg["Bcc"] = mail["admin_bcc"]

    hello = username or mail["default_user_label"]
    if mail["tenant"] == "therasik":
        body = f"""
您好 {hello}，

您的 Therasik Console 验证码为：{code}

验证码 1 小时内有效。如非本人操作，请忽略本邮件。

Therasik Console
{contact}

---
Hello {hello},

Your Therasik Console verification code is: {code}

This code will expire in 1 hour.

If you did not request this, please ignore this email.

Therasik Console
{contact}
"""
    else:
        body = f"""
Hello {hello},

Your InSynBio Console verification code is: {code}

This code will expire in 1 hour.

If you did not request this, please ignore this email.

InSynBio Console
{contact}
"""
    msg.attach(MIMEText(body, "plain", "utf-8"))

    all_recipients = [email]
    if msg.get("Bcc"):
        all_recipients.append(msg["Bcc"])
    ok, err = _smtp_send(mail, msg, all_recipients)
    if ok:
        print(
            f"EMAIL_SENT[{mail['tenant']}] verification to={email} host={smtp_host}:{smtp_port}",
            flush=True,
        )
    else:
        print(
            f"EMAIL_FAILED[{mail['tenant']}] verification to={email} host={smtp_host}:{smtp_port} error={err}",
            flush=True,
        )
    return ok


def send_service_email(email: str, subject: str, body: str) -> bool:
    """Send a service email such as account recovery."""
    from email.mime.text import MIMEText

    mail = _mail_profile()
    smtp_host = mail["host"]
    smtp_port = mail["port"]
    smtp_user = mail["user"]
    smtp_pass = mail["password"]
    sender = mail["sender"]

    if not all([smtp_host, smtp_user, smtp_pass]):
        print(f"[AUTH][{mail['tenant']}] Service email to {email}: {subject}\n{body}", flush=True)
        return False

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = sender
    msg["To"] = email
    msg["Subject"] = subject
    admin_bcc = mail.get("admin_bcc", "")
    if admin_bcc and admin_bcc != email:
        msg["Bcc"] = admin_bcc
    all_recipients = [email] + ([admin_bcc] if admin_bcc and admin_bcc != email else [])
    ok, err = _smtp_send(mail, msg, all_recipients)
    if ok:
        print(
            f"EMAIL_SENT[{mail['tenant']}] service to={email} host={smtp_host}:{smtp_port}",
            flush=True,
        )
    else:
        print(
            f"EMAIL_FAILED[{mail['tenant']}] service to={email} host={smtp_host}:{smtp_port} error={err}",
            flush=True,
        )
    return ok


def send_smoke_email(tenant: str, to: str) -> Dict[str, Any]:
    """Admin smoke-test email. Sends a small message via the tenant SMTP profile
    and returns structured status. Does not generate or store a verification code.
    """
    from email.mime.text import MIMEText

    ns = (tenant or "insynbio").strip().lower()
    tok = push_namespace(ns)
    try:
        mail = _mail_profile()
    finally:
        pop_namespace(tok)

    smtp_host = mail.get("host")
    smtp_port = mail.get("port")
    smtp_user = mail.get("user")
    smtp_pass = mail.get("password")
    sender = mail.get("sender")
    brand = mail.get("brand", "")
    if not all([smtp_host, smtp_user, smtp_pass, sender, to]):
        return {
            "ok": False,
            "tenant": ns,
            "host": smtp_host,
            "port": smtp_port,
            "sender": sender,
            "error": "smtp_not_configured_or_missing_recipient",
        }

    body = (
        f"This is a smoke-test email from the {brand} server.\n"
        f"Tenant: {ns}\n"
        f"Sent via: {smtp_host}:{smtp_port}\n"
        f"From: {sender}\n"
        f"If you received this, outbound email is working."
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = f"[{brand or ns}] SMTP smoke test"
    ok, err = _smtp_send(mail, msg, [to])
    if ok:
        print(
            f"EMAIL_SENT[{ns}] smoke to={to} host={smtp_host}:{smtp_port}",
            flush=True,
        )
    else:
        print(
            f"EMAIL_FAILED[{ns}] smoke to={to} host={smtp_host}:{smtp_port} error={err}",
            flush=True,
        )
    return {
        "ok": ok,
        "tenant": ns,
        "host": smtp_host,
        "port": smtp_port,
        "sender": sender,
        "to": to,
        "error": err or None,
    }


def send_admin_notification(
    *,
    event: str,
    username: str,
    user_email: str,
    credits_granted: int = 0,
    coupon_code: str = "",
    coupon_bonus: int = 0,
    marketing_opt_in: bool = False,
    news_opt_in: bool = False,
    extra: str = "",
) -> bool:
    """Send a structured new-user or event notification to the admin inbox.

    This is a separate message from the verification BCC; it goes only to the
    admin address and contains a summary of the registration event.
    Errors are silently logged — never block the user-facing response.
    """
    from email.mime.text import MIMEText

    mail = _mail_profile()
    smtp_host = mail["host"]
    smtp_port = mail["port"]
    smtp_user = mail["user"]
    smtp_pass = mail["password"]
    sender = mail["sender"]
    admin_bcc = mail.get("admin_bcc", sender)
    brand = mail["brand"]
    tenant = mail["tenant"]

    if not all([smtp_host, smtp_user, smtp_pass]):
        print(
            f"[ADMIN_NOTIFY][{tenant}] {event} | user={username} email={user_email} "
            f"credits={credits_granted} coupon={coupon_code or '-'} bonus={coupon_bonus} "
            f"marketing={marketing_opt_in} news={news_opt_in}",
            flush=True,
        )
        return False

    import time as _time
    ts = _time.strftime("%Y-%m-%d %H:%M:%S UTC", _time.gmtime())

    lines = [
        f"[{brand}] 新用户注册通知 / New User Registration",
        "=" * 52,
        f"事件 / Event   : {event}",
        f"时间 / Time    : {ts}",
        f"用户名 / User  : {username}",
        f"邮箱 / Email   : {user_email}",
        f"Credits 赠送   : {credits_granted:,}",
    ]
    if coupon_code:
        lines.append(f"优惠码 / Coupon: {coupon_code}  (+{coupon_bonus:,} bonus credits)")
    lines += [
        f"产品邮件 / Mktg: {'Yes' if marketing_opt_in else 'No'}",
        f"关联新闻 / News: {'Yes' if news_opt_in else 'No'}",
    ]
    if extra:
        lines.append(f"备注 / Note    : {extra}")
    lines.append("=" * 52)

    msg = MIMEText("\n".join(lines), "plain", "utf-8")
    msg["From"] = sender
    msg["To"] = admin_bcc
    msg["Subject"] = f"[{brand}] 新用户注册 / New Registration — {username}"

    ok, err = _smtp_send(mail, msg, [admin_bcc])
    if ok:
        print(
            f"EMAIL_SENT[{tenant}] admin_notify event={event} user={username} to={admin_bcc}",
            flush=True,
        )
    else:
        print(
            f"EMAIL_FAILED[{tenant}] admin_notify event={event} user={username} to={admin_bcc} error={err}",
            flush=True,
        )
    return ok


def get_user_by_id(uid: int) -> Optional[Dict[str, Any]]:
    init_db()
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT id, username, email, credits, role, created_at, credits_unlimited, is_verified, marketing_opt_in, news_opt_in FROM users WHERE id = ?",
                (uid,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


def ensure_gate_user(username: str, role: str = "user") -> Dict[str, Any]:
    """Create or update a console gate account wallet.

    Gate users come from ``api/static/login.html``. They need server-side
    credits so zhanglab/guest balances are consistent across devices. Admin is
    unlimited and still logs zero-credit audit rows.
    """
    init_db()
    u = get_user_by_username(username)
    is_admin = username.strip().lower() == "admin" or role == "admin"
    target_role = "owner" if is_admin else "gate"
    target_unlimited = 1 if is_admin else 0
    if not u:
        # PIN is not used for gate auth; it only satisfies the DB schema.
        create_user(
            username.strip(),
            "000000",
            role=target_role,
            credits=OWNER_DEFAULT_CREDITS,
            credits_unlimited=target_unlimited,
        )
        u = get_user_by_username(username)
        if not u:
            raise RuntimeError("gate user create failed")
        return u

    with _lock:
        conn = _connect()
        try:
            old_role = str(u.get("role") or "")
            if old_role not in {"gate", "owner"}:
                conn.execute(
                    "UPDATE users SET role = ?, credits = ?, credits_unlimited = ? WHERE id = ?",
                    (target_role, OWNER_DEFAULT_CREDITS, target_unlimited, int(u["id"])),
                )
            else:
                conn.execute(
                    "UPDATE users SET role = ?, credits_unlimited = ? WHERE id = ?",
                    (target_role, target_unlimited, int(u["id"])),
                )
            conn.commit()
        finally:
            conn.close()
    return get_user_by_username(username) or u


def verify_pin(user: Dict[str, Any], pin: str) -> bool:
    salt = bytes(user["pin_salt"])
    return hmac.compare_digest(_hash_pin(pin, salt), user["pin_hash"])


def debit_user(uid: int, amount: int, service_id: str, run_id: Optional[str], extra: Optional[Dict]) -> Tuple[bool, int, str]:
    """Returns (ok, new_balance, message)."""
    if amount <= 0:
        u = get_user_by_id(uid)
        if not u:
            return False, 0, "user_not_found"
        return True, int(u["credits"]), "noop"

    init_db()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    extra_json = json.dumps(extra or {}, ensure_ascii=False)
    with _lock:
        conn = _connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT credits, credits_unlimited FROM users WHERE id = ?", (uid,)
            ).fetchone()
            if not row:
                conn.rollback()
                return False, 0, "user_not_found"
            bal = int(row["credits"])
            if int(row["credits_unlimited"] or 0):
                waived = {"waived": True, "would_charge": amount, **(extra or {})}
                conn.execute(
                    """
                    INSERT INTO usage_ledger (user_id, at_iso, service_id, credits, run_id, extra_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        uid,
                        now,
                        service_id,
                        0,
                        run_id or "",
                        json.dumps(waived, ensure_ascii=False),
                    ),
                )
                conn.commit()
                return True, bal, "unlimited"
            if bal < amount:
                conn.rollback()
                return False, bal, "insufficient_credits"
            new_bal = bal - amount
            conn.execute("UPDATE users SET credits = ? WHERE id = ?", (new_bal, uid))
            conn.execute(
                """
                INSERT INTO usage_ledger (user_id, at_iso, service_id, credits, run_id, extra_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (uid, now, service_id, amount, run_id or "", extra_json),
            )
            conn.commit()
            return True, new_bal, "ok"
        finally:
            conn.close()


def bootstrap_from_env() -> None:
    """INSYNBIO_BOOTSTRAP_OWNER=user:pin creates owner if missing (once)."""
    raw = os.environ.get("INSYNBIO_BOOTSTRAP_OWNER", "").strip()
    if not raw or ":" not in raw:
        return
    user, _, pin = raw.partition(":")
    user, pin = user.strip(), pin.strip()
    if not user or not pin or len(pin) < 4:
        return
    init_db()
    if get_user_by_username(user):
        return
    try:
        create_user(user, pin, role="owner", credits=OWNER_DEFAULT_CREDITS)
    except sqlite3.IntegrityError:
        pass


# ── Signed session token (stdlib only; replace with SMS + short-lived OTP later) ──

def _secret() -> bytes:
    s = os.environ.get("INSYNBIO_AUTH_SECRET", "").strip()
    if not s:
        s = "dev-insecure-change-INSYNBIO_AUTH_SECRET"
    return s.encode("utf-8")


def sign_session(
    user_id: int,
    username: str,
    role: str,
    ttl_sec: int = 604800,
    tenant: Optional[str] = None,
) -> str:
    """7-day default session."""
    import base64

    payload = {
        "uid": user_id,
        "sub": username,
        "role": role,
        "tenant": _sanitize_namespace(tenant or current_namespace()),
        "exp": int(time.time()) + ttl_sec,
    }
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    b64 = base64.urlsafe_b64encode(body).decode().rstrip("=")
    sig = hmac.new(_secret(), b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"v1.{b64}.{sig}"


def verify_session(token: str) -> Optional[Dict[str, Any]]:
    try:
        if not token.startswith("v1."):
            return None
        _, b64, sig = token.split(".", 2)
        import base64

        pad = "=" * (-len(b64) % 4)
        expect = hmac.new(_secret(), b64.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expect, sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(b64 + pad))
        if int(payload.get("exp", 0)) < time.time():
            return None
        return payload
    except Exception:
        return None


def count_demo_runs(uid: int) -> int:
    """Count how many times a user has run a demo (waived cost)."""
    init_db()
    with _lock:
        conn = _connect()
        try:
            # We look for entries in usage_ledger where credits=0 and extra_json contains demoId
            # Note: this is a heuristic based on how /auth/debit works.
            count = conn.execute(
                """
                SELECT COUNT(*) FROM usage_ledger 
                WHERE user_id = ? AND credits = 0 AND extra_json LIKE '%"demoId"%'
                """,
                (uid,),
            ).fetchone()[0]
            return int(count)
        finally:
            conn.close()


def count_assistant_chats(uid: int) -> int:
    """Count how many times a user has used the AI assistant."""
    init_db()
    with _lock:
        conn = _connect()
        try:
            # Look for service_id starting with 'therasik_assistant' or 'insynbio_assistant'
            count = conn.execute(
                """
                SELECT COUNT(*) FROM usage_ledger 
                WHERE user_id = ? AND (service_id LIKE '%assistant_brief%' OR service_id LIKE '%assistant_detail%')
                """,
                (uid,),
            ).fetchone()[0]
            return int(count)
        finally:
            conn.close()


def ledger_for_user(uid: int, limit: int = 50) -> List[Dict[str, Any]]:
    init_db()
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                """
                SELECT at_iso, service_id, credits, run_id, extra_json
                FROM usage_ledger WHERE user_id = ? ORDER BY id DESC LIMIT ?
                """,
                (uid, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
