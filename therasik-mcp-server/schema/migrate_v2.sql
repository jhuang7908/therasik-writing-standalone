-- ============================================================
-- TheraSIK MCP Schema v2 — Multi-user + LLM proxy billing
-- Run: sudo -u postgres psql -d therasik_mcp -f migrate_v2.sql
-- ============================================================

-- ── Extend users table ────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS name       text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS org        text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS plan       text    NOT NULL DEFAULT 'free';
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS verified   boolean NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notes      text;

-- ── Extend api_keys table ────────────────────────────────────
-- monthly_quota already exists; add token quota for LLM proxy
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS monthly_token_quota bigint NOT NULL DEFAULT 500000;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS tokens_used_this_month bigint NOT NULL DEFAULT 0;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS tokens_reset_at timestamptz NOT NULL DEFAULT date_trunc('month', now()) + interval '1 month';

-- ── Payments table ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payments (
    id              serial PRIMARY KEY,
    user_id         integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stripe_session  text,
    stripe_pi       text,
    amount_usd      numeric(10,2) NOT NULL,
    plan            text NOT NULL,          -- starter / pro / team / institution
    period_months   integer NOT NULL DEFAULT 12,
    status          text NOT NULL DEFAULT 'pending',  -- pending / paid / failed / refunded
    created_at      timestamptz NOT NULL DEFAULT now(),
    paid_at         timestamptz
);
CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);

-- ── Literature: stays 100% local on user's machine ───────────
-- Architecture: "Cursor model" — literature never leaves user's device.
-- Zotero.sqlite is read locally by the TheraSIK Agent local MCP server.
-- The cloud server only receives text queries, never bibliography content.
-- NO server-side literature table needed.

-- ── LLM proxy usage (separate from tool usage_events) ────────
CREATE TABLE IF NOT EXISTS llm_usage (
    id              bigserial PRIMARY KEY,
    key_id          integer NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    user_id         integer NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    model           text NOT NULL,
    prompt_tokens   integer NOT NULL DEFAULT 0,
    completion_tokens integer NOT NULL DEFAULT 0,
    total_tokens    integer NOT NULL DEFAULT 0,
    cost_usd        numeric(12,8) NOT NULL DEFAULT 0,
    request_ms      integer,                            -- latency
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_llm_usage_key  ON llm_usage(key_id, created_at);
CREATE INDEX IF NOT EXISTS idx_llm_usage_user ON llm_usage(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_llm_usage_month ON llm_usage(user_id, date_trunc('month', created_at));

-- ── Monthly LLM usage view ────────────────────────────────────
CREATE OR REPLACE VIEW monthly_llm_usage AS
SELECT
    u.email,
    u.plan,
    date_trunc('month', l.created_at) AS month,
    sum(l.total_tokens)               AS tokens,
    sum(l.cost_usd)                   AS cost_usd,
    count(*)                          AS requests
FROM llm_usage l
JOIN users u ON u.id = l.user_id
GROUP BY u.email, u.plan, date_trunc('month', l.created_at);

-- ── Plan definitions (reference table) ───────────────────────
CREATE TABLE IF NOT EXISTS plans (
    id              serial PRIMARY KEY,
    name            text UNIQUE NOT NULL,   -- starter / pro / team / institution
    price_usd_month numeric(8,2) NOT NULL,
    tool_quota      integer NOT NULL,       -- -1 = unlimited
    token_quota     bigint NOT NULL,        -- monthly LLM tokens; -1 = unlimited
    max_lib_count   integer NOT NULL DEFAULT 1,
    max_seats       integer NOT NULL DEFAULT 1
);

INSERT INTO plans (name, price_usd_month, tool_quota, token_quota, max_lib_count, max_seats) VALUES
    ('free',        0,      100,    100000,  1, 1),
    ('starter',    19,     1000,    500000,  2, 1),
    ('pro',        49,     5000,   2000000,  5, 1),
    ('team',      129,    20000,   8000000, 20, 5),
    ('institution', -1, -1, -1, -1, -1)
ON CONFLICT (name) DO NOTHING;

-- ── Registration tokens (email verify + free trial) ──────────
CREATE TABLE IF NOT EXISTS reg_tokens (
    id          serial PRIMARY KEY,
    email       text NOT NULL,
    token       text UNIQUE NOT NULL,
    used        boolean NOT NULL DEFAULT false,
    expires_at  timestamptz NOT NULL DEFAULT now() + interval '24 hours',
    created_at  timestamptz NOT NULL DEFAULT now()
);

SELECT 'Schema v2 applied.' AS status;
