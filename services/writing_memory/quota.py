"""
Per-IP daily quota for the InSynBio Scientific Writing service.

MVP policy (third-party validation phase):
    plan   :  2 calls / IP / day   — heaviest (~$0.20 each)
    draft  :  6 calls / IP / day   — section drafting, vision, legends
    polish : 10 calls / IP / day   — rewrite, claim_check, similar, cite tools

Storage is a single SQLite file (`quota.db`) — atomic enough for one
uvicorn worker and zero dependencies beyond stdlib.  If you scale to
multiple workers later, swap the backing store for Redis with the same
public API in this module.

Trust model
-----------
The server-side Claude API key is shared by all anonymous visitors.
Quota is keyed on the originating IP as seen by the reverse proxy.
The reverse proxy MUST set `X-Forwarded-For`; if it doesn't, the quota
will fall back to the socket address and a single shared NAT will look
like one visitor.
"""

from __future__ import annotations

import base64
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import HTTPException, Request

# ──────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────

QuotaClass = Literal["plan", "draft", "polish"]

# User-based quotas (Simple Auth)
# Admin: Unlimited
# Guest: Polish 10/day, Write 5/day (Write = plan + draft)
USERS = {
    "Admin": {
        "password": "Rocky123",
        "limits": {
            "plan": 9999,
            "draft": 9999,
            "polish": 9999,
        }
    },
    "Guest": {
        "password": "InsynBio2026",
        "limits": {
            "plan": 5,
            "draft": 5,
            "polish": 10,
        }
    }
}

# Usernames in this list bypass quota entirely (case-insensitive).
# Configure via env, e.g.:
#   WM_UNLIMITED_USERS="Admin,NextVivo,p01,owner_account"
UNLIMITED_USERS: set[str] = set(
    u.strip().lower()
    for u in os.getenv("WM_UNLIMITED_USERS", "Admin,NextVivo,p01").split(",")
    if u.strip()
)

# Read overrides from environment so deployers can tune without code edits.
DEFAULT_LIMITS: dict[QuotaClass, int] = {
    "plan":   int(os.getenv("WM_QUOTA_PLAN",   "2")),
    "draft":  int(os.getenv("WM_QUOTA_DRAFT",  "6")),
    "polish": int(os.getenv("WM_QUOTA_POLISH", "10")),
}

# Map each endpoint path to its quota class.
ENDPOINT_TO_CLASS: dict[str, QuotaClass] = {
    # heavy planning
    "/plan_paper":          "plan",
    "/recommend_journal":   "plan",

    # medium drafting / structured outputs
    "/draft_section":       "draft",
    "/draft_figure_legend": "draft",
    "/describe_figure":     "draft",
    "/parse_table":         "draft",

    # cheap polish / verification
    "/rewrite":             "polish",
    "/claim_check":         "polish",
    "/reduce_ai_tone":      "polish",
    "/reviewer_sim":        "polish",
    "/similar":             "polish",
    "/find_references":     "polish",
    "/verify_pmid":         "polish",
    "/insert_citations":    "polish",
    "/check_submission":    "polish",
    "/draft_cover_letter":  "draft",
    "/export_docx":         "draft",
    "/finalize_package":            "polish",
    "/prepare_submission_packages": "plan",
    "/manuscript_qc_score":         "polish",
    "/manuscript_qc_autofix":       "plan",
    "/fix_sentence":                "polish",
    "/polish_all":                  "plan",
    "/suggest_titles":              "polish",
    "/suggest_reviewers":           "polish",
    "/analyze_figure_quantitative": "polish",
    "/fill_markers":                None,          # free — no LLM call
    "/consistency_check":           "polish",
    "/methods_template":            None,          # free — no LLM call
    "/methods_template_types":      None,          # free
    "/extract_references_from_pdf": "draft",
    "/journal_context_preview":     None,          # free — diagnostic, no LLM
    "/learn_journal_style": "draft",
    "/check_style_safety":    "polish",
}

# Trusted-IP allowlist — bypasses quota.  Use for internal smoke tests.
TRUSTED_IPS: set[str] = set(
    ip.strip() for ip in os.getenv("WM_TRUSTED_IPS", "127.0.0.1,::1").split(",") if ip.strip()
)

# Where the SQLite file lives (must persist across container restarts).
DB_PATH = Path(os.getenv("WM_QUOTA_DB", "services/writing_memory/data/quota.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# One re-entrant lock per process; SQLite is fine for our write volume.
_LOCK = threading.Lock()


# ──────────────────────────────────────────────────────────────────────
# Storage
# ──────────────────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS usage (
            ip          TEXT NOT NULL,
            date        TEXT NOT NULL,   -- UTC YYYY-MM-DD
            quota_class TEXT NOT NULL,
            n           INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (ip, date, quota_class)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_or_user  TEXT NOT NULL,
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            action      TEXT NOT NULL,
            details     TEXT
        )
        """
    )
    return conn


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _client_ip(request: Request) -> str:
    # Trust the reverse proxy when X-Forwarded-For is present.
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # First IP in the chain is the real client.
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────

def _get_auth_user(request: Request) -> Optional[str]:
    """
    Extract username from Basic Auth header.

    Rules:
    - Password is OPTIONAL.
    - Admin requires the correct password (otherwise treated as anonymous IP).
    - Any other non-empty username gets Guest-tier limits, tracked independently.

    Returns the canonical username string, or None for anonymous.
    """
    auth = request.headers.get("authorization")
    if not auth or not auth.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(auth[6:]).decode("utf-8")
        username, password = decoded.split(":", 1) if ":" in decoded else (decoded, "")
        username = username.strip()
        if not username:
            return None
        if username.lower() == "admin":
            if password == USERS["Admin"]["password"]:
                return "Admin"
            return None  # Wrong Admin password → anonymous
        # Any other name → Guest tier, individual tracking
        return username[:40]  # cap length to avoid DB abuse
    except Exception:
        pass
    return None


def get_user_limits(username: Optional[str]) -> dict:
    """Return effective per-class limits for a username (Admin/Guest/None)."""
    if username and username.strip().lower() in UNLIMITED_USERS:
        return {
            "plan": 999999,
            "draft": 999999,
            "polish": 999999,
        }
    if username == "Admin":
        return USERS["Admin"]["limits"]
    if username:
        return USERS["Guest"]["limits"]
    return DEFAULT_LIMITS


def current_usage(ip_or_user: str) -> dict[str, dict[str, int]]:
    """Return {class: {used, limit, remaining}} for the given IP or user today."""
    today = _today_utc()
    out: dict[str, dict[str, int]] = {}

    # Determine limits: key looks like "user:<name>" or a plain IP
    if ip_or_user.startswith("user:"):
        username = ip_or_user[5:]
        limits = get_user_limits(username)
    else:
        limits = DEFAULT_LIMITS

    with _LOCK, _connect() as conn:
        for cls, limit in limits.items():
            row = conn.execute(
                "SELECT n FROM usage WHERE ip=? AND date=? AND quota_class=?",
                (ip_or_user, today, cls),
            ).fetchone()
            used = row[0] if row else 0
            out[cls] = {
                "used":      used,
                "limit":     limit,
                "remaining": max(0, limit - used),
            }
    return out


def _bump(ip_or_user: str, cls: QuotaClass, action: str = "") -> int:
    today = _today_utc()
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT INTO usage (ip, date, quota_class, n) VALUES (?, ?, ?, 1)
            ON CONFLICT (ip, date, quota_class) DO UPDATE SET n = n + 1
            """,
            (ip_or_user, today, cls),
        )
        if action:
            conn.execute(
                "INSERT INTO history (ip_or_user, action) VALUES (?, ?)",
                (ip_or_user, action),
            )
        row = conn.execute(
            "SELECT n FROM usage WHERE ip=? AND date=? AND quota_class=?",
            (ip_or_user, today, cls),
        ).fetchone()
        conn.commit()
        return row[0] if row else 0


def check_and_consume(request: Request) -> None:
    """FastAPI dependency: raise 429 if over-quota, else bump the counter."""
    path = request.url.path
    cls  = ENDPOINT_TO_CLASS.get(path)
    if cls is None:
        # Endpoint not metered — let it through.
        return

    # 1. Check for User Auth
    username = _get_auth_user(request)
    if username:
        if username.strip().lower() in UNLIMITED_USERS:
            # Unlimited internal account: bypass quota and skip counter bump.
            return
        key = f"user:{username}"
        limits = get_user_limits(username)
    else:
        # 2. Fallback to IP
        ip = _client_ip(request)
        if ip in TRUSTED_IPS:
            return
        key = ip
        limits = DEFAULT_LIMITS

    limit = limits[cls]
    current = current_usage(key).get(cls, {}).get("used", 0)
    
    if current >= limit:
        raise HTTPException(
            status_code=429,
            detail={
                "error":   "quota_exceeded",
                "class":   cls,
                "limit":   limit,
                "used":    current,
                "user":    username or "anonymous",
                "message": (
                    f"Daily {cls} quota reached ({current}/{limit}). "
                    "Quotas reset at 00:00 UTC. For higher limits, contact the InSynBio team."
                ),
            },
        )
    # Log the action name (path without leading slash)
    action_name = path[1:] if path.startswith("/") else path
    _bump(key, cls, action=action_name)


def get_history(ip_or_user: str, limit: int = 20) -> list[dict]:
    """Return recent actions for the given IP or user."""
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            "SELECT timestamp, action FROM history WHERE ip_or_user=? ORDER BY timestamp DESC LIMIT ?",
            (ip_or_user, limit),
        ).fetchall()
    return [{"timestamp": r[0], "action": r[1]} for r in rows]


# ──────────────────────────────────────────────────────────────────────
# Optional admin helpers
# ──────────────────────────────────────────────────────────────────────

def reset_ip(ip: str) -> int:
    """Wipe today's counters for one IP.  Returns number of rows removed."""
    today = _today_utc()
    with _LOCK, _connect() as conn:
        cur = conn.execute("DELETE FROM usage WHERE ip=? AND date=?", (ip, today))
        conn.commit()
        return cur.rowcount


def stats_today() -> list[dict]:
    """All counters for today — handy for admin dashboards."""
    today = _today_utc()
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            "SELECT ip, quota_class, n FROM usage WHERE date=? ORDER BY n DESC",
            (today,),
        ).fetchall()
    return [{"ip": r[0], "class": r[1], "used": r[2]} for r in rows]
