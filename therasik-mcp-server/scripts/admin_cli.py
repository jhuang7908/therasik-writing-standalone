"""
admin_cli.py — TheraSIK MCP Server management CLI.

Usage:
    python scripts/admin_cli.py keygen  --email user@example.com --tier pro
    python scripts/admin_cli.py revoke  --key-prefix isk_live_Ab3x
    python scripts/admin_cli.py quota   --key-prefix isk_live_Ab3x --quota 5000
    python scripts/admin_cli.py usage   --key-prefix isk_live_Ab3x
    python scripts/admin_cli.py list
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

import asyncpg
import typer
from rich.console import Console
from rich.table import Table

app  = typer.Typer(help="TheraSIK MCP Server — Admin CLI")
cons = Console()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://therasik:therasik@localhost:5432/therasik",
)
SECRET_SALT = os.environ.get("SECRET_SALT", "dev_salt_change_in_production")

TIER_QUOTAS = {
    "starter":    2000,
    "pro":        20000,
    "team":       100000,
    "enterprise": -1,
}


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(f"{SECRET_SALT}{raw_key}".encode()).hexdigest()


async def _get_conn():
    url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    return await asyncpg.connect(url)


# ── keygen ────────────────────────────────────────────────────────────────────
@app.command()
def keygen(
    email: str  = typer.Option(..., help="User email"),
    name:  str  = typer.Option("",  help="User display name"),
    tier:  str  = typer.Option("starter", help="starter|pro|team|enterprise"),
    years: int  = typer.Option(1,   help="Key validity in years"),
    quota: int  = typer.Option(-1,  help="Monthly quota override (-1 = use tier default)"),
):
    """Generate a new API key for a user."""
    async def _run():
        conn = await _get_conn()
        try:
            # Upsert user
            user_id = await conn.fetchval(
                """
                INSERT INTO users (email, name) VALUES ($1, $2)
                ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                email, name or email.split("@")[0],
            )

            # Generate key
            raw      = "isk_live_" + secrets.token_urlsafe(24)
            kh       = hash_key(raw)
            prefix   = raw[:20] + "..."
            mq       = quota if quota != -1 else TIER_QUOTAS.get(tier, 2000)
            valid_until = datetime.now(timezone.utc) + timedelta(days=365 * years)

            await conn.execute(
                """
                INSERT INTO api_keys
                    (user_id, key_hash, key_prefix, tier, monthly_quota, valid_until)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                user_id, kh, prefix, tier, mq, valid_until,
            )

            cons.print(f"\n[bold green]API Key created[/bold green]")
            cons.print(f"  Email       : {email}")
            cons.print(f"  Tier        : {tier}")
            cons.print(f"  Monthly quota: {mq} calls")
            cons.print(f"  Valid until : {valid_until.date()}")
            cons.print(f"\n[bold yellow]  RAW KEY (show once):[/bold yellow]")
            cons.print(f"  [bold]{raw}[/bold]\n")
            cons.print("[dim]  Send this key to the customer. It cannot be recovered.[/dim]\n")
        finally:
            await conn.close()

    asyncio.run(_run())


# ── revoke ────────────────────────────────────────────────────────────────────
@app.command()
def revoke(
    key_prefix: str = typer.Option(..., "--key-prefix", help="Key prefix (isk_live_...)"),
):
    """Revoke an API key immediately."""
    async def _run():
        conn = await _get_conn()
        try:
            n = await conn.fetchval(
                "UPDATE api_keys SET active=FALSE WHERE key_prefix LIKE $1 RETURNING id",
                key_prefix.rstrip(".") + "%",
            )
            if n:
                cons.print(f"[green]Revoked key: {key_prefix}[/green]")
            else:
                cons.print(f"[red]Key not found: {key_prefix}[/red]")
        finally:
            await conn.close()

    asyncio.run(_run())


# ── quota ─────────────────────────────────────────────────────────────────────
@app.command()
def quota(
    key_prefix: str = typer.Option(..., "--key-prefix"),
    new_quota:  int = typer.Option(..., "--quota"),
):
    """Update monthly quota for a key."""
    async def _run():
        conn = await _get_conn()
        try:
            await conn.execute(
                "UPDATE api_keys SET monthly_quota=$1 WHERE key_prefix LIKE $2",
                new_quota, key_prefix.rstrip(".") + "%",
            )
            cons.print(f"[green]Quota updated to {new_quota}/month for {key_prefix}[/green]")
        finally:
            await conn.close()

    asyncio.run(_run())


# ── usage ─────────────────────────────────────────────────────────────────────
@app.command()
def usage(
    key_prefix: str = typer.Option("", "--key-prefix", help="Filter by key prefix (optional)"),
    month:      str = typer.Option("", "--month", help="YYYY-MM (default: current month)"),
):
    """Show usage report."""
    async def _run():
        conn = await _get_conn()
        try:
            month_filter = month or datetime.now(timezone.utc).strftime("%Y-%m")
            rows = await conn.fetch(
                """
                SELECT k.key_prefix, k.tier, k.monthly_quota,
                       COUNT(u.id) AS calls,
                       COUNT(u.id) FILTER (WHERE u.cached) AS cached,
                       COUNT(u.id) FILTER (WHERE u.status='error') AS errors
                FROM   api_keys k
                LEFT   JOIN usage_events u
                       ON  u.key_id = k.id
                       AND to_char(u.called_at, 'YYYY-MM') = $1
                WHERE  ($2 = '' OR k.key_prefix LIKE $3)
                GROUP  BY k.id, k.key_prefix, k.tier, k.monthly_quota
                ORDER  BY calls DESC
                """,
                month_filter, key_prefix, key_prefix.rstrip(".") + "%",
            )
            t = Table(title=f"Usage — {month_filter}", show_lines=True)
            t.add_column("Key prefix")
            t.add_column("Tier")
            t.add_column("Used", justify="right")
            t.add_column("Quota", justify="right")
            t.add_column("Cached", justify="right")
            t.add_column("Errors", justify="right")
            for r in rows:
                used = r["calls"] or 0
                q    = r["monthly_quota"]
                pct  = f"{round(used/max(q,1)*100)}%" if q > 0 else "unlim"
                t.add_row(
                    r["key_prefix"], r["tier"],
                    f"{used} ({pct})", str(q),
                    str(r["cached"] or 0), str(r["errors"] or 0),
                )
            cons.print(t)
        finally:
            await conn.close()

    asyncio.run(_run())


# ── list ──────────────────────────────────────────────────────────────────────
@app.command(name="list")
def list_keys():
    """List all API keys."""
    async def _run():
        conn = await _get_conn()
        try:
            rows = await conn.fetch(
                """
                SELECT u.email, k.key_prefix, k.tier, k.monthly_quota,
                       k.active, k.valid_until, k.last_used_at
                FROM   api_keys k
                JOIN   users u ON u.id = k.user_id
                ORDER  BY k.created_at DESC
                """
            )
            t = Table(title="API Keys", show_lines=True)
            t.add_column("Email")
            t.add_column("Prefix")
            t.add_column("Tier")
            t.add_column("Quota/mo", justify="right")
            t.add_column("Active")
            t.add_column("Valid until")
            t.add_column("Last used")
            for r in rows:
                t.add_row(
                    r["email"], r["key_prefix"], r["tier"],
                    str(r["monthly_quota"]),
                    "[green]yes[/green]" if r["active"] else "[red]no[/red]",
                    str(r["valid_until"].date()) if r["valid_until"] else "-",
                    str(r["last_used_at"].date()) if r["last_used_at"] else "never",
                )
            cons.print(t)
        finally:
            await conn.close()

    asyncio.run(_run())


if __name__ == "__main__":
    app()
