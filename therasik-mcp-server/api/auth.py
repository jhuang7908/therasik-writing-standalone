"""
auth.py — API key validation, rate limiting, quota enforcement, usage logging.

Pipeline per request (runs as FastAPI middleware):
  1. Extract X-API-Key header
  2. Hash key → lookup in Postgres (cached in Redis 5 min)
  3. Check key is active + not expired
  4. Redis token-bucket rate limit (per-minute)
  5. Check monthly call quota
  6. Allow request to proceed
  7. Log usage_event (fire-and-forget, non-blocking)
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status
from sqlalchemy import text

from .db import get_session

# ── Config ────────────────────────────────────────────────────────────────────
SECRET_SALT  = os.environ.get("SECRET_SALT", "dev_salt_change_in_production")
REDIS_URL    = os.environ.get("REDIS_URL", "redis://localhost:6379")

# Rate limit: max calls per minute per key (per tier)
RATE_LIMITS  = {
    "starter":    10,
    "pro":        30,
    "team":       60,
    "enterprise": 200,
}
DEFAULT_RATE = 10

# Redis TTL for cached key lookups (seconds)
KEY_CACHE_TTL = 300  # 5 minutes

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


# ── Key hashing ───────────────────────────────────────────────────────────────
def hash_key(raw_key: str) -> str:
    return hashlib.sha256(f"{SECRET_SALT}{raw_key}".encode()).hexdigest()


# ── Key lookup (Postgres + Redis cache) ──────────────────────────────────────
async def lookup_key(raw_key: str) -> dict:
    """
    Returns key metadata dict or raises HTTPException.
    Caches result in Redis for 5 minutes to avoid hammering Postgres.
    """
    key_hash = hash_key(raw_key)
    r = await get_redis()

    # Redis cache hit
    cached = await r.get(f"key:{key_hash}")
    if cached:
        return json.loads(cached)

    # Postgres lookup
    async with get_session() as session:
        row = await session.execute(
            text("""
                SELECT k.id, k.user_id, k.tier, k.monthly_quota,
                       k.active, k.valid_until
                FROM   api_keys k
                WHERE  k.key_hash = :kh
            """),
            {"kh": key_hash},
        )
        rec = row.mappings().first()

    if not rec:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    if not rec["active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key is revoked.",
        )

    now = datetime.now(timezone.utc)
    if rec["valid_until"] and rec["valid_until"] < now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key has expired. Please renew your subscription.",
        )

    data = {
        "key_id":        rec["key_id"]        if "key_id" in rec else rec["id"],
        "id":            rec["id"],
        "user_id":       rec["user_id"],
        "tier":          rec["tier"],
        "monthly_quota": rec["monthly_quota"],
    }
    # Cache in Redis
    await r.setex(f"key:{key_hash}", KEY_CACHE_TTL, json.dumps(data, default=str))
    return data


# ── Rate limiting (token bucket via Redis) ────────────────────────────────────
async def check_rate_limit(key_id: int, tier: str) -> None:
    """
    Simple sliding-window counter: max N calls per 60-second window.
    Raises 429 if exceeded.
    """
    r       = await get_redis()
    bucket  = f"rl:{key_id}:{int(time.time()) // 60}"
    limit   = RATE_LIMITS.get(tier, DEFAULT_RATE)
    current = await r.incr(bucket)
    if current == 1:
        await r.expire(bucket, 120)  # 2-minute TTL (covers window boundary)
    if current > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({limit} req/min for {tier} tier). Slow down.",
        )


# ── Monthly quota ─────────────────────────────────────────────────────────────
async def check_monthly_quota(key_id: int, monthly_quota: int) -> None:
    """
    Count calls this calendar month from usage_events table.
    Uses a Redis counter refreshed at month boundary for performance.
    """
    if monthly_quota == -1:
        return  # unlimited (enterprise)

    r           = await get_redis()
    month_key   = f"quota:{key_id}:{datetime.now(timezone.utc).strftime('%Y-%m')}"
    used_cached = await r.get(month_key)

    if used_cached is None:
        # Cold start: count from Postgres
        async with get_session() as session:
            row = await session.execute(
                text("""
                    SELECT COUNT(*) AS n
                    FROM   usage_events
                    WHERE  key_id = :kid
                      AND  date_trunc('month', called_at) =
                           date_trunc('month', NOW())
                """),
                {"kid": key_id},
            )
            used = row.scalar() or 0
        await r.setex(month_key, 3700, str(used))  # cache ~1 hour
    else:
        used = int(used_cached)

    if used >= monthly_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Monthly quota exhausted ({monthly_quota} calls). "
                   "Upgrade your plan or wait until next month.",
        )


# ── Usage logging (fire-and-forget) ──────────────────────────────────────────
async def log_usage(
    key_id: int,
    tool_name: str,
    duration_ms: int = 0,
    cached: bool = False,
    status_str: str = "ok",
) -> None:
    """Non-blocking usage event write. Increments Redis quota counter."""
    try:
        async with get_session() as session:
            await session.execute(
                text("""
                    INSERT INTO usage_events
                        (key_id, tool_name, duration_ms, cached, status)
                    VALUES (:kid, :tool, :dur, :cached, :status)
                """),
                {
                    "kid":    key_id,
                    "tool":   tool_name,
                    "dur":    duration_ms,
                    "cached": cached,
                    "status": status_str,
                },
            )
        # Increment Redis quota counter
        r         = await get_redis()
        month_key = f"quota:{key_id}:{datetime.now(timezone.utc).strftime('%Y-%m')}"
        await r.incr(month_key)
        # Update last_used_at
        async with get_session() as session:
            await session.execute(
                text("UPDATE api_keys SET last_used_at = NOW() WHERE id = :kid"),
                {"kid": key_id},
            )
    except Exception:
        pass  # Usage logging must never break the main request


# ── FastAPI middleware ────────────────────────────────────────────────────────
async def auth_gate(request: Request, call_next):
    """
    FastAPI middleware: validates API key, enforces rate/quota, logs usage.
    Bypass paths: /health, /docs, /openapi.json
    """
    bypass = {"/health", "/docs", "/openapi.json", "/redoc"}
    # Public registration + payment routes (no API key required)
    bypass_prefixes = ("/register", "/verify/", "/checkout", "/stripe/webhook",
                       "/pricing", "/payment-success", "/upgrade")
    if request.url.path in bypass:
        return await call_next(request)
    if request.url.path.startswith(bypass_prefixes):
        return await call_next(request)

    # LLM proxy supports both Bearer token and X-API-Key
    raw_key = request.headers.get("X-API-Key", "").strip()
    if not raw_key:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            raw_key = auth[7:].strip()
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header.",
        )

    t0      = time.monotonic()
    key_rec = await lookup_key(raw_key)
    key_id  = key_rec["id"]
    tier    = key_rec["tier"]

    await check_rate_limit(key_id, tier)
    await check_monthly_quota(key_id, key_rec["monthly_quota"])

    # Attach key info to request state for downstream use
    request.state.key_id  = key_id
    request.state.user_id = key_rec["user_id"]
    request.state.tier    = tier

    response = await call_next(request)

    duration_ms = int((time.monotonic() - t0) * 1000)
    tool_name   = request.url.path.split("/")[-1] or "unknown"
    import asyncio
    asyncio.create_task(log_usage(key_id, tool_name, duration_ms))

    return response
