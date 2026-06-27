-- TheraSIK MCP Server — Database Schema
-- Auto-executed by Postgres on first container start

-- ── Users ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    email       TEXT    NOT NULL UNIQUE,
    name        TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes       TEXT
);

-- ── API Keys ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_keys (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Stored as SHA-256(SECRET_SALT + raw_key); raw key shown once on creation
    key_hash        TEXT    NOT NULL UNIQUE,

    -- Human-readable prefix for display (e.g. "isk_live_Ab3x...")
    key_prefix      TEXT    NOT NULL,

    -- Plan tier
    tier            TEXT    NOT NULL DEFAULT 'starter',   -- starter|pro|team|enterprise

    -- Monthly call quota (-1 = unlimited)
    monthly_quota   INTEGER NOT NULL DEFAULT 2000,

    -- Validity window
    valid_from      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until     TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '1 year'),

    -- Status
    active          BOOLEAN NOT NULL DEFAULT TRUE,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash   ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user   ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(active, valid_until);

-- ── Usage Events ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS usage_events (
    id          BIGSERIAL PRIMARY KEY,
    key_id      INTEGER NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    tool_name   TEXT    NOT NULL,
    called_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_ms INTEGER,
    cached      BOOLEAN NOT NULL DEFAULT FALSE,
    status      TEXT    NOT NULL DEFAULT 'ok'   -- ok | error | rate_limited
);

CREATE INDEX IF NOT EXISTS idx_usage_key_month
    ON usage_events(key_id, date_trunc('month', called_at));

CREATE INDEX IF NOT EXISTS idx_usage_tool ON usage_events(tool_name);

-- ── Monthly usage summary view (fast for /v1/usage/me) ───────────────────────
CREATE OR REPLACE VIEW monthly_usage AS
    SELECT
        key_id,
        date_trunc('month', called_at)::DATE AS month,
        COUNT(*)                              AS total_calls,
        COUNT(*) FILTER (WHERE cached)        AS cached_calls,
        COUNT(*) FILTER (WHERE status = 'ok') AS ok_calls,
        COUNT(*) FILTER (WHERE status = 'error') AS error_calls
    FROM usage_events
    GROUP BY key_id, date_trunc('month', called_at);

-- ── Seed: demo user + key for local smoke testing ───────────────────────────
-- Raw key: isk_live_SMOKE_TEST_KEY_000  (never use in production)
-- Hash = sha256("SALT" + raw_key) — replaced in smoke test with actual salt
INSERT INTO users (email, name) VALUES ('smoke@localhost', 'Smoke Test')
    ON CONFLICT DO NOTHING;
