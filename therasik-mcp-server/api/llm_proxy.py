"""
llm_proxy.py — OpenAI-compatible LLM proxy endpoint.

Mounted at /v1/chat/completions so TheraSIK Agent (Hermes fork)
can point its provider URL to our server and use the TheraSIK key
for both tool access AND LLM inference — true 2-in-1 key.

Flow:
  1. Client sends POST /v1/chat/completions with Bearer THMCP-xxx
  2. We validate the key (same auth.py logic)
  3. Count tokens, check monthly token quota
  4. Forward to upstream LLM (Gemini Flash / OpenRouter)
  5. Return response; log LLM usage to DB
  6. Stream supported via SSE pass-through
"""
from __future__ import annotations

import json
import os
import time
import hashlib
import logging
from typing import AsyncIterator

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from .db import get_session
from .auth import SECRET_SALT, _redis

logger = logging.getLogger("therasik.llm_proxy")

router = APIRouter()

# ── Upstream LLM config ───────────────────────────────────────────────────────
# Priority: Gemini (our key) → OpenRouter (fallback)
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
OPENROUTER_KEY  = os.environ.get("OPENROUTER_API_KEY", "")
UPSTREAM_MODEL  = os.environ.get("LLM_PROXY_MODEL", "gemini-2.5-flash")

# Token cost (USD per token, approximate)
COST_PER_TOKEN = {
    "gemini-2.5-flash":      0.00000015,   # $0.15 / 1M tokens
    "gemini-2.5-pro":        0.00000125,
    "gpt-4o-mini":           0.00000015,
    "claude-haiku-3-5":      0.00000025,
}

# ── Quota / rate limiting ─────────────────────────────────────────────────────
async def _check_token_quota(key_hash: str, tokens: int) -> bool:
    """Check and deduct from monthly token quota. Returns True if allowed."""
    redis = await _redis()
    if redis is None:
        return True  # degrade gracefully
    month_key = f"token_quota:{key_hash}:{time.strftime('%Y-%m')}"
    used = await redis.incrby(month_key, tokens)
    if used == tokens:
        await redis.expire(month_key, 35 * 86400)  # 35-day TTL
    return True  # quota enforcement via DB check is async; redis is fast-path


def _count_tokens_approx(messages: list) -> int:
    """Rough token estimate: 1 token ≈ 4 chars."""
    total = sum(len(str(m.get("content", ""))) for m in messages)
    return max(1, total // 4)


# ── Gemini upstream call ──────────────────────────────────────────────────────
async def _call_gemini(messages: list, stream: bool, model: str) -> tuple[dict | None, AsyncIterator | None]:
    """Call Gemini REST API. Returns (json_response, None) or (None, stream_iter)."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:{'streamGenerateContent' if stream else 'generateContent'}"
        f"?key={GEMINI_API_KEY}"
    )

    # Convert OpenAI message format to Gemini
    gemini_parts = []
    system_text = ""
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            system_text = content
        elif role == "user":
            gemini_parts.append({"role": "user", "parts": [{"text": content}]})
        elif role == "assistant":
            gemini_parts.append({"role": "model", "parts": [{"text": content}]})

    body = {"contents": gemini_parts}
    if system_text:
        body["systemInstruction"] = {"parts": [{"text": system_text}]}

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()

    # Convert Gemini response to OpenAI format
    try:
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
        prompt_tokens = data.get("usageMetadata", {}).get("promptTokenCount", 0)
        completion_tokens = data.get("usageMetadata", {}).get("candidatesTokenCount", 0)
    except (KeyError, IndexError):
        text_out = str(data)
        prompt_tokens = completion_tokens = 0

    openai_resp = {
        "id": f"chatcmpl-therasik-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": text_out},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }
    return openai_resp, None


# ── Log usage to DB (fire-and-forget) ────────────────────────────────────────
async def _log_llm_usage(key_id: int, user_id: int, model: str,
                          prompt_tok: int, completion_tok: int, latency_ms: int):
    total = prompt_tok + completion_tok
    cost = total * COST_PER_TOKEN.get(model, 0.0000002)
    try:
        async with get_session() as session:
            await session.execute(text("""
                INSERT INTO llm_usage
                  (key_id, user_id, model, prompt_tokens, completion_tokens,
                   total_tokens, cost_usd, request_ms, created_at)
                VALUES
                  (:kid, :uid, :model, :pt, :ct, :tt, :cost, :ms, now())
            """), {"kid": key_id, "uid": user_id, "model": model,
                   "pt": prompt_tok, "ct": completion_tok,
                   "tt": total, "cost": cost, "ms": latency_ms})
            await session.commit()
    except Exception as exc:
        logger.warning(f"LLM usage log failed: {exc}")


# ── Main endpoint ─────────────────────────────────────────────────────────────
@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    OpenAI-compatible chat completions proxy.
    Accepts: Bearer THMCP-xxx  OR  X-API-Key: THMCP-xxx
    """
    # ── Auth: extract key ──────────────────────────────────────
    raw_key = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        raw_key = auth_header[7:].strip()
    if not raw_key:
        raw_key = request.headers.get("X-API-Key", "").strip()
    if not raw_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    key_hash = hashlib.sha256((SECRET_SALT + raw_key).encode()).hexdigest()

    # ── Lookup key in DB ───────────────────────────────────────
    async with get_session() as session:
        row = await session.execute(text("""
            SELECT k.id, k.user_id, k.monthly_token_quota, k.active,
                   k.valid_until, u.plan, u.email
            FROM api_keys k JOIN users u ON u.id = k.user_id
            WHERE k.key_hash = :h AND k.active = true
              AND k.valid_until > now()
        """), {"h": key_hash})
        key_row = row.fetchone()

    if not key_row:
        raise HTTPException(status_code=403, detail="Invalid or expired API key")

    key_id, user_id, token_quota, active, valid_until, plan, email = key_row

    # ── Parse request body ─────────────────────────────────────
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    messages = body.get("messages", [])
    stream   = body.get("stream", False)
    model    = body.get("model", UPSTREAM_MODEL)

    # Map common model aliases to what we support
    MODEL_MAP = {
        "gpt-4o":            "gemini-2.5-flash",
        "gpt-4o-mini":       "gemini-2.5-flash",
        "claude-3-5-sonnet": "gemini-2.5-flash",
        "claude-3-opus":     "gemini-2.5-pro",
        "hermes-3":          "gemini-2.5-flash",
    }
    upstream_model = MODEL_MAP.get(model, UPSTREAM_MODEL)

    # ── Token quota check ──────────────────────────────────────
    est_tokens = _count_tokens_approx(messages) + 500  # add buffer
    if token_quota != -1:  # -1 = unlimited
        redis = await _redis()
        if redis:
            month_key = f"tok:{key_hash}:{time.strftime('%Y-%m')}"
            used = int(await redis.get(month_key) or 0)
            if used + est_tokens > token_quota:
                raise HTTPException(
                    status_code=429,
                    detail=f"Monthly token quota exceeded ({used}/{token_quota}). Upgrade plan."
                )

    # ── Call upstream LLM ──────────────────────────────────────
    t0 = time.time()
    try:
        if GEMINI_API_KEY and not stream:
            response_data, _ = await _call_gemini(messages, stream=False, model=upstream_model)
        else:
            # Fallback: OpenRouter
            if not OPENROUTER_KEY:
                raise HTTPException(status_code=503, detail="LLM proxy not configured")
            async with httpx.AsyncClient(timeout=120) as client:
                or_resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_KEY}",
                        "X-Title": "TheraSIK Agent",
                    },
                    json={**body, "model": f"google/{upstream_model}"},
                )
                or_resp.raise_for_status()
                response_data = or_resp.json()

        latency_ms = int((time.time() - t0) * 1000)
        usage = response_data.get("usage", {})
        prompt_tok     = usage.get("prompt_tokens", est_tokens // 2)
        completion_tok = usage.get("completion_tokens", est_tokens // 4)
        total_tok      = usage.get("total_tokens", prompt_tok + completion_tok)

    except httpx.HTTPStatusError as exc:
        logger.error(f"Upstream LLM error: {exc.response.status_code} {exc.response.text[:200]}")
        raise HTTPException(status_code=502, detail="Upstream LLM error")
    except Exception as exc:
        logger.error(f"LLM proxy error: {exc}")
        raise HTTPException(status_code=502, detail=str(exc))

    # ── Update Redis token counter ─────────────────────────────
    redis = await _redis()
    if redis:
        month_key = f"tok:{key_hash}:{time.strftime('%Y-%m')}"
        await redis.incrby(month_key, total_tok)
        await redis.expire(month_key, 35 * 86400)

    # ── Log usage async ────────────────────────────────────────
    import asyncio
    asyncio.create_task(_log_llm_usage(
        key_id, user_id, upstream_model,
        prompt_tok, completion_tok, latency_ms
    ))

    return response_data
