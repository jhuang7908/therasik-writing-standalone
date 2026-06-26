"""
cache.py — Redis result cache for deterministic MCP tools.

Only tools whose output is fully determined by their inputs are cached.
Tools that call LLMs (multi_expert_review, ai_diagnostician) are NOT cached
because output varies per call and caching would mislead users.

Cache key: sha256(tool_name + canonical_json(args))
TTL policy:
  - get_journal_requirements / list_journals  → 7 days  (data rarely changes)
  - check_grammar                             → 24 hours (LT model stable)
  - format_citations / verify_citations_s2   → 48 hours
  - generate_stat_figure                     → 24 hours

Design: wrap any async/sync callable with cache_wrap().
  On miss  → call original fn → store result → return result
  On hit   → return cached result, log cached=True in usage_events
"""
from __future__ import annotations

import functools
import hashlib
import json
import os
from typing import Any, Callable

import redis.asyncio as aioredis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


# ── TTL map (seconds) ─────────────────────────────────────────────────────────
CACHE_TTL: dict[str, int] = {
    "get_journal_requirements": 7 * 86400,   # 7 days
    "list_journals":            7 * 86400,
    "check_grammar":            86400,        # 24 h
    "format_citations":         2 * 86400,
    "verify_citations_s2":      2 * 86400,
    "generate_stat_figure":     86400,
    "get_submission_system_guide": 3 * 86400,
}

# Tools that must NEVER be cached (LLM-backed, non-deterministic)
NO_CACHE: set[str] = {
    "run_multi_expert_review",
    "run_qa_gate",
    "polish_manuscript",
    "search_literature",      # live external API
    "scrape_journal_requirements",
}


def _cache_key(tool_name: str, args: dict) -> str:
    """Stable cache key: sha256(tool_name + sorted JSON of args)."""
    payload = json.dumps({"t": tool_name, "a": args}, sort_keys=True, ensure_ascii=False)
    return "cache:" + hashlib.sha256(payload.encode()).hexdigest()[:32]


async def get_cached(tool_name: str, args: dict) -> tuple[Any | None, bool]:
    """
    Returns (result, True) on cache hit, (None, False) on miss.
    Never raises — cache failure must not break the tool call.
    """
    if tool_name in NO_CACHE or tool_name not in CACHE_TTL:
        return None, False
    try:
        r   = await _get_redis()
        hit = await r.get(_cache_key(tool_name, args))
        if hit:
            return json.loads(hit), True
    except Exception:
        pass
    return None, False


async def set_cached(tool_name: str, args: dict, result: Any) -> None:
    """
    Store result in Redis. Silently skips on any error.
    Only stores JSON-serialisable results.
    """
    if tool_name in NO_CACHE or tool_name not in CACHE_TTL:
        return
    try:
        r   = await _get_redis()
        ttl = CACHE_TTL[tool_name]
        key = _cache_key(tool_name, args)
        await r.setex(key, ttl, json.dumps(result, ensure_ascii=False, default=str))
    except Exception:
        pass


async def invalidate(tool_name: str, args: dict) -> bool:
    """Force-expire a cache entry (e.g. after admin data update). Returns True if deleted."""
    try:
        r = await _get_redis()
        n = await r.delete(_cache_key(tool_name, args))
        return bool(n)
    except Exception:
        return False


async def cache_stats() -> dict:
    """Return cache key counts per tool prefix (for admin monitoring)."""
    try:
        r    = await _get_redis()
        keys = await r.keys("cache:*")
        return {"total_cached_entries": len(keys)}
    except Exception:
        return {"total_cached_entries": "unavailable"}
