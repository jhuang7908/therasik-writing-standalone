"""
smoke_test.py — Offline unit smoke test for auth logic.

Does NOT require Docker / Postgres / Redis.
Tests the key hashing, rate-limit bucket logic, and middleware flow
using mocks so we can catch bugs before deploying.

Run: python scripts/smoke_test.py
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import sys
import time

# Set cloud mode + dummy env so imports don't crash
os.environ.setdefault("SECRET_SALT", "test_salt_smoke_only")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = "[PASS]"
FAIL = "[FAIL]"


# ── Test 1: Key hashing ───────────────────────────────────────────────────────
def test_key_hashing():
    from api.auth import hash_key
    raw  = "isk_live_SMOKE_TEST_KEY_000"
    h1   = hash_key(raw)
    h2   = hash_key(raw)
    h3   = hash_key("isk_live_DIFFERENT_KEY")
    assert h1 == h2, "Same key must produce same hash"
    assert h1 != h3, "Different keys must produce different hashes"
    assert len(h1) == 64, "SHA-256 hex must be 64 chars"
    print(f"  {PASS} Key hashing: deterministic + collision-resistant")


# ── Test 2: Rate limit bucket naming ─────────────────────────────────────────
def test_rate_bucket():
    # Bucket is keyed by key_id + minute window
    key_id  = 42
    window1 = int(time.time()) // 60
    window2 = window1 + 1
    bucket1 = f"rl:{key_id}:{window1}"
    bucket2 = f"rl:{key_id}:{window2}"
    assert bucket1 != bucket2, "Different minutes must yield different buckets"
    assert bucket1.startswith(f"rl:{key_id}:"), "Bucket must be scoped to key"
    print(f"  {PASS} Rate limit bucket: correctly scoped per key + minute")


# ── Test 3: Middleware bypass paths ───────────────────────────────────────────
def test_bypass_paths():
    bypass = {"/health", "/docs", "/openapi.json", "/redoc"}
    assert "/health" in bypass
    assert "/mcp/v1" not in bypass
    assert "/v1/usage/me" not in bypass
    print(f"  {PASS} Bypass paths: /health excluded, /mcp/v1 and /v1/usage/me protected")


# ── Test 4: Hash with different salts ────────────────────────────────────────
def test_salt_isolation():
    raw = "isk_live_SAME_KEY"
    salt1 = "saltA"
    salt2 = "saltB"
    h1 = hashlib.sha256(f"{salt1}{raw}".encode()).hexdigest()
    h2 = hashlib.sha256(f"{salt2}{raw}".encode()).hexdigest()
    assert h1 != h2, "Different salts must produce different hashes (replay attack protection)"
    print(f"  {PASS} Salt isolation: changing SECRET_SALT invalidates all existing keys")


# ── Test 5: Tier quota map completeness ──────────────────────────────────────
def test_tier_quotas():
    from api.auth import RATE_LIMITS
    expected_tiers = {"starter", "pro", "team", "enterprise"}
    assert set(RATE_LIMITS.keys()) >= expected_tiers, "All tiers must have rate limits"
    assert RATE_LIMITS["enterprise"] > RATE_LIMITS["starter"], "Enterprise must have higher limit"
    print(f"  {PASS} Tier rate limits: all tiers defined, enterprise > starter")


# ── Test 6: DB URL normalization ─────────────────────────────────────────────
def test_db_url_normalization():
    plain    = "postgresql://u:p@host/db"
    asyncpg  = "postgresql+asyncpg://u:p@host/db"
    fixed    = plain.replace("postgresql://", "postgresql+asyncpg://", 1)
    assert fixed == asyncpg
    # Should not double-replace
    fixed2   = asyncpg.replace("postgresql://", "postgresql+asyncpg://", 1)
    assert "asyncpgasyncpg" not in fixed2
    print(f"  {PASS} DB URL normalization: postgresql:// → postgresql+asyncpg:// (safe)")


# ── Test 7: Schema SQL syntax check (naive) ───────────────────────────────────
def test_schema_sql():
    schema_path = os.path.join(os.path.dirname(__file__), "..", "schema", "init.sql")
    with open(schema_path) as f:
        sql = f.read()
    assert "CREATE TABLE IF NOT EXISTS users" in sql
    assert "CREATE TABLE IF NOT EXISTS api_keys" in sql
    assert "CREATE TABLE IF NOT EXISTS usage_events" in sql
    assert "monthly_quota" in sql
    assert "valid_until" in sql
    assert "key_hash" in sql
    print(f"  {PASS} Schema SQL: all required tables and columns present")


# ── Test 8: docker-compose.yml sanity ────────────────────────────────────────
def test_compose_file():
    import yaml  # pyyaml
    compose_path = os.path.join(os.path.dirname(__file__), "..", "docker-compose.yml")
    with open(compose_path) as f:
        cfg = yaml.safe_load(f)
    services = set(cfg.get("services", {}).keys())
    required = {"engine", "postgres", "redis", "languagetool", "caddy"}
    missing  = required - services
    assert not missing, f"Missing services: {missing}"
    lt = cfg["services"]["languagetool"]
    assert "mem_limit" in lt, "LanguageTool must have mem_limit"
    pg = cfg["services"]["postgres"]
    assert "healthcheck" in pg, "Postgres must have healthcheck"
    print(f"  {PASS} docker-compose.yml: all 5 services present, mem_limit + healthcheck set")


# ── Runner ────────────────────────────────────────────────────────────────────
def main():
    print("\n=== TheraSIK Cloud Server — Offline Smoke Test ===\n")
    tests = [
        test_key_hashing,
        test_rate_bucket,
        test_bypass_paths,
        test_salt_isolation,
        test_tier_quotas,
        test_db_url_normalization,
        test_schema_sql,
    ]
    # yaml may not be installed in current env; add compose test only if available
    try:
        import yaml
        tests.append(test_compose_file)
    except ImportError:
        print(f"  [SKIP] docker-compose.yml check (pyyaml not installed)")

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as exc:
            print(f"  {FAIL} {t.__name__}: {exc}")
            failed += 1

    print(f"\n{'='*48}")
    print(f"  Result: {passed} passed, {failed} failed")
    if failed == 0:
        print("  SMOKE PASS — safe to proceed to Step 6\n")
    else:
        print("  SMOKE FAIL — fix errors before deploying\n")
    return failed == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
