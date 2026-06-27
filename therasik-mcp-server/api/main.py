"""
main.py — FastAPI application entry point.

Mounts:
  - Auth middleware (every request except /health)
  - GET  /health           — liveness probe
  - GET  /v1/usage/me      — self-service usage dashboard
  - POST /mcp/v1           — fastmcp SSE transport (23 MCP tools)
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .auth import auth_gate, hash_key, get_redis
from .db import engine, get_session

# ── Lifespan: startup / shutdown ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify DB connectivity on startup
    try:
        async with get_session() as s:
            await s.execute(text("SELECT 1"))
        print("[therasik] Postgres: connected")
    except Exception as exc:
        print(f"[therasik] WARNING: Postgres not ready: {exc}")

    # Verify Redis connectivity
    try:
        r = await get_redis()
        await r.ping()
        print("[therasik] Redis: connected")
    except Exception as exc:
        print(f"[therasik] WARNING: Redis not ready: {exc}")

    yield

    await engine.dispose()


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="TheraSIK Writing MCP API",
    version="1.0.0",
    description="InSynBio Academic Writing Engine — MCP over HTTP/SSE",
    docs_url="/docs",
    lifespan=lifespan,
)

# CORS: allow insynbio.com and localhost (for Hermes/Cursor clients)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://insynbio.com",
        "https://www.insynbio.com",
        "http://localhost",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth gate (runs on every request)
app.middleware("http")(auth_gate)


# ── Health endpoint ───────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version}


# ── Self-service usage endpoint ───────────────────────────────────────────────
@app.get("/v1/usage/me")
async def usage_me(request: Request):
    """
    Returns this month's usage for the authenticated API key.
    Clients (Hermes Agent) can call this to monitor their quota.
    """
    key_id = getattr(request.state, "key_id", None)
    if key_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    now   = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")

    async with get_session() as session:
        # Monthly summary
        row = await session.execute(
            text("""
                SELECT
                    COUNT(*)                              AS total_calls,
                    COUNT(*) FILTER (WHERE cached)        AS cached_calls,
                    COUNT(*) FILTER (WHERE status = 'ok') AS ok_calls,
                    COUNT(*) FILTER (WHERE status = 'error') AS error_calls
                FROM usage_events
                WHERE key_id = :kid
                  AND date_trunc('month', called_at) = date_trunc('month', NOW())
            """),
            {"kid": key_id},
        )
        stats = row.mappings().first()

        # Key metadata
        key_row = await session.execute(
            text("""
                SELECT tier, monthly_quota, valid_until, last_used_at
                FROM   api_keys
                WHERE  id = :kid
            """),
            {"kid": key_id},
        )
        key_info = key_row.mappings().first()

    used     = stats["total_calls"] or 0
    quota    = key_info["monthly_quota"] if key_info else 0
    pct      = round(used / max(quota, 1) * 100, 1) if quota > 0 else 0

    return {
        "month":          month,
        "tier":           key_info["tier"]         if key_info else "unknown",
        "monthly_quota":  quota,
        "calls_used":     used,
        "calls_cached":   stats["cached_calls"]    or 0,
        "calls_ok":       stats["ok_calls"]        or 0,
        "calls_error":    stats["error_calls"]     or 0,
        "usage_pct":      pct,
        "valid_until":    str(key_info["valid_until"]) if key_info else None,
        "last_used_at":   str(key_info["last_used_at"]) if key_info else None,
        "warning":        "Approaching quota limit (>80% used)" if pct > 80 else None,
    }


# ── MCP SSE endpoint ──────────────────────────────────────────────────────────
# fastmcp mounts its SSE handler here.
# The existing 23 MCP tools are imported from the tools module.
# This is wired up in a separate file to keep main.py clean.

def _mount_mcp():
    """Lazy import of MCP tools to avoid circular deps at import time."""
    try:
        from .mcp_app import mcp_asgi_app
        app.mount("/mcp/v1", mcp_asgi_app)
        print("[therasik] MCP tools mounted at /mcp/v1")
    except ImportError as exc:
        print(f"[therasik] WARNING: MCP tools not mounted: {exc}")


def _mount_llm_proxy():
    """Mount OpenAI-compatible LLM proxy for 2-in-1 key support."""
    try:
        from .llm_proxy import router as llm_router
        app.include_router(llm_router, tags=["LLM Proxy"])
        print("[therasik] LLM proxy mounted at /v1/chat/completions")
    except Exception as exc:
        print(f"[therasik] WARNING: LLM proxy not mounted: {exc}")


def _mount_registration():
    """Mount self-service registration, payment, and account routes."""
    try:
        from .registration import router as reg_router
        app.include_router(reg_router, tags=["Registration"])
        print("[therasik] Registration routes mounted")
    except Exception as exc:
        print(f"[therasik] WARNING: Registration not mounted: {exc}")


_mount_mcp()
_mount_llm_proxy()
_mount_registration()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
