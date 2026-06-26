"""Create or update a Console trial / owner account.

Usage:
    python scripts/create_trial_account.py --username zhanglab --password insynbio2026 --credits 100000

Behavior:
- Creates user with role=trial (demo runs are free; self-supplied sequences deduct credits).
- Marks is_verified=1 so /auth/login bypasses email verification.
- If user already exists, password is reset and credits are set (not added).
- Password validation matches /auth/register rules (8-64 chars, [A-Za-z0-9@#$%^&+=!?._-]).

The demo-free / custom-deduct policy is already implemented server-side in
api/routers/auth.py — when the Console sends extra.demoId on /auth/debit (or
/auth/gate/debit), amount is forced to 0.
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import auth_db  # noqa: E402

USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,31}$")
PASSWORD_RE = re.compile(r"^[A-Za-z0-9@#$%^&+=!?._-]{8,64}$")


def _validate(username: str, password: str) -> None:
    if not USERNAME_RE.match(username):
        raise SystemExit(
            "ERROR: username must be 3-32 chars, start with a letter, only [A-Za-z0-9_]"
        )
    if not PASSWORD_RE.match(password):
        raise SystemExit(
            "ERROR: password must be 8-64 chars using letters, digits, or @#$%^&+=!?._-"
        )


def upsert_account(
    username: str,
    password: str,
    credits: int,
    role: str = "trial",
    unlimited: bool = False,
) -> dict:
    _validate(username, password)
    auth_db.init_db()

    existing = auth_db.get_user_by_username(username)
    unl_flag = 1 if unlimited else 0

    if existing is None:
        uid = auth_db.create_user(
            username=username,
            pin=password,
            role=role,
            credits=credits,
            credits_unlimited=unl_flag,
            terms_accepted=True,
        )
        # auth_db.create_user marks owner as auto-verified; for trial we set it
        # manually so /auth/login does not block on email verification.
        with auth_db._lock:
            conn = auth_db._connect()
            try:
                conn.execute(
                    "UPDATE users SET is_verified = 1 WHERE id = ?", (uid,)
                )
                conn.commit()
            finally:
                conn.close()
        action = "created"
    else:
        uid = int(existing["id"])
        auth_db.set_user_password(uid, password)
        with auth_db._lock:
            conn = auth_db._connect()
            try:
                conn.execute(
                    """
                    UPDATE users
                    SET credits = ?, credits_unlimited = ?, role = ?, is_verified = 1,
                        terms_accepted_at = COALESCE(terms_accepted_at, ?)
                    WHERE id = ?
                    """,
                    (
                        credits,
                        unl_flag,
                        role,
                        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        uid,
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        action = "updated"

    refreshed = auth_db.get_user_by_username(username) or {}
    return {
        "action": action,
        "uid": int(refreshed.get("id") or 0),
        "username": str(refreshed.get("username") or ""),
        "role": str(refreshed.get("role") or ""),
        "credits": int(refreshed.get("credits") or 0),
        "credits_unlimited": int(refreshed.get("credits_unlimited") or 0),
        "is_verified": int(refreshed.get("is_verified") or 0),
        "db_path": str(auth_db.DB_PATH),
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--credits", type=int, default=100_000)
    p.add_argument(
        "--role",
        default="trial",
        choices=["trial", "owner", "gate"],
        help="trial: demo free + custom deducts (default). owner: bootstrap admin.",
    )
    p.add_argument(
        "--unlimited",
        action="store_true",
        help="Skip ALL deductions (overrides demo-free / custom-deduct policy).",
    )
    args = p.parse_args()

    info = upsert_account(
        args.username,
        args.password,
        args.credits,
        role=args.role,
        unlimited=args.unlimited,
    )

    print(f"[{info['action']}] uid={info['uid']} username={info['username']}")
    print(f"  role               = {info['role']}")
    print(f"  credits            = {info['credits']:,}")
    print(f"  credits_unlimited  = {info['credits_unlimited']}")
    print(f"  is_verified        = {info['is_verified']}")
    print(f"  DB path            = {info['db_path']}")
    if info["role"] == "trial" and not info["credits_unlimited"]:
        print(
            "  Policy             = demo runs FREE (waived), custom sequences DEDUCT credits"
        )


if __name__ == "__main__":
    main()
