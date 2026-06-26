-- =============================================================================
-- Writing Memory MVP -- PostgreSQL + pgvector schema (v0.1)
--
-- Scope:
--   - Stores 150 PMC-resolved papers across 3 journals
--   - Stores per-paper Claude-extracted article_profile (JSONB)
--   - Stores per-journal aggregated journal_profile + phrase_bank
--   - Supports semantic search over both paragraph chunks and phrases
--   - Logs every LLM call for audit (anti-hallucination policy)
--
-- Embeddings:
--   - Dimension fixed at 1536 (OpenAI text-embedding-3-small).
--     If you swap the embedding model, you MUST migrate the column type.
--
-- Anti-hallucination invariants baked into the schema:
--   - papers.text_provenance is a required enum, no nullable "abstract_only"
--     row may be embedded without sections_available being explicit.
--   - phrase_bank.evidence_paper_ids requires >= 2 (DB-level CHECK).
--   - reviewer_attack_patterns.verification_status is locked to 'inferred'.
--   - llm_calls captures input/output hashes for every model call.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- 1. Journals
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS journals (
    id              SERIAL PRIMARY KEY,
    key             TEXT UNIQUE NOT NULL CHECK (key IN ('pnas','elife','plos_med')),
    display_name    TEXT NOT NULL,
    publisher       TEXT,
    field           TEXT,
    issn_print      TEXT,
    issn_electronic TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 2. Papers
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS papers (
    id              SERIAL PRIMARY KEY,
    journal_id      INTEGER NOT NULL REFERENCES journals(id) ON DELETE RESTRICT,

    pmid            TEXT UNIQUE NOT NULL,
    pmcid           TEXT UNIQUE,
    doi             TEXT,
    openalex_id     TEXT,

    title           TEXT NOT NULL,
    year            INTEGER CHECK (year BETWEEN 1900 AND 2100),
    citation_count  INTEGER CHECK (citation_count IS NULL OR citation_count >= 0),
    paper_type      TEXT,  -- research-article | review-article | ...
    license         TEXT,

    abstract        TEXT,
    discussion      TEXT,
    conclusion      TEXT,
    figure_legends  JSONB,  -- array of strings; null if absent

    sections_available JSONB NOT NULL DEFAULT '{}'::jsonb,
    text_provenance    TEXT NOT NULL CHECK (text_provenance IN
                       ('pmc_jats','pmc_bioc','abstract_only','aam')),

    -- Embedding is over the canonical "writing-style" text we choose to embed:
    -- abstract + first 800 tokens of discussion (concatenated). The exact
    -- recipe is recorded in ingest scripts; if it changes, bump embed_version.
    embedding       vector(1536),
    embed_version   TEXT,

    -- Per-paper article_profile JSON produced by Claude.
    article_profile JSONB,
    profile_status  TEXT NOT NULL DEFAULT 'pending'
                    CHECK (profile_status IN ('pending','generated','validated','rejected')),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS papers_journal_year_idx ON papers (journal_id, year DESC);
CREATE INDEX IF NOT EXISTS papers_profile_status_idx ON papers (profile_status);
CREATE INDEX IF NOT EXISTS papers_embedding_hnsw_idx
    ON papers USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ---------------------------------------------------------------------------
-- 3. Paragraph-level chunks (better recall than whole-paper embeddings)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS paper_chunks (
    id              SERIAL PRIMARY KEY,
    paper_id        INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    section         TEXT NOT NULL CHECK (section IN
                    ('abstract','discussion','conclusion','figure_legend')),
    ordinal         INTEGER NOT NULL CHECK (ordinal >= 0),
    text            TEXT NOT NULL,
    char_len        INTEGER GENERATED ALWAYS AS (char_length(text)) STORED,
    embedding       vector(1536),
    embed_version   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (paper_id, section, ordinal)
);

CREATE INDEX IF NOT EXISTS paper_chunks_section_idx ON paper_chunks (section);
CREATE INDEX IF NOT EXISTS paper_chunks_embedding_hnsw_idx
    ON paper_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ---------------------------------------------------------------------------
-- 4. Journal profiles (aggregated by Claude over N article_profiles)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS journal_profiles (
    id                  SERIAL PRIMARY KEY,
    journal_id          INTEGER NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
    profile_version     TEXT NOT NULL,
    source_paper_count  INTEGER NOT NULL CHECK (source_paper_count >= 1),
    source_paper_ids    INTEGER[] NOT NULL,

    rhetoric_profile            JSONB NOT NULL,
    logic_profile               JSONB NOT NULL,
    sentence_style_profile      JSONB NOT NULL,
    paragraph_structure_profile JSONB NOT NULL,
    claim_strength_profile      JSONB NOT NULL,

    is_active           BOOLEAN NOT NULL DEFAULT FALSE,
    generated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (journal_id, profile_version)
);

CREATE UNIQUE INDEX IF NOT EXISTS journal_profiles_one_active
    ON journal_profiles (journal_id)
    WHERE is_active;

-- ---------------------------------------------------------------------------
-- 5. Phrase bank
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS phrase_bank (
    id                  SERIAL PRIMARY KEY,
    journal_id          INTEGER NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
    profile_id          INTEGER NOT NULL REFERENCES journal_profiles(id) ON DELETE CASCADE,
    phrase              TEXT NOT NULL,
    category            TEXT NOT NULL CHECK (category IN
                        ('opening','transition','hedge','claim',
                         'limitation','implication','figure_legend','other')),
    frequency           INTEGER NOT NULL CHECK (frequency >= 2),
    evidence_paper_ids  INTEGER[] NOT NULL,
    verification_status TEXT NOT NULL CHECK (verification_status IN ('verified','inferred')),

    embedding           vector(1536),
    embed_version       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT phrase_bank_evidence_min CHECK (array_length(evidence_paper_ids, 1) >= 2)
);

CREATE INDEX IF NOT EXISTS phrase_bank_journal_cat_idx ON phrase_bank (journal_id, category);
CREATE INDEX IF NOT EXISTS phrase_bank_phrase_trgm_idx ON phrase_bank USING gin (phrase gin_trgm_ops);
CREATE INDEX IF NOT EXISTS phrase_bank_embedding_hnsw_idx
    ON phrase_bank USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ---------------------------------------------------------------------------
-- 6. Reviewer-attack patterns (always inferred)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reviewer_attack_patterns (
    id                  SERIAL PRIMARY KEY,
    journal_id          INTEGER NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
    profile_id          INTEGER NOT NULL REFERENCES journal_profiles(id) ON DELETE CASCADE,
    pattern_id          TEXT NOT NULL,                -- stable id usable by the LLM (e.g. "plos_med.bias.selection")
    pattern             TEXT NOT NULL,
    suggested_fix       TEXT,
    frequency           INTEGER NOT NULL CHECK (frequency >= 1),
    evidence_paper_ids  INTEGER[] NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'inferred'
                        CHECK (verification_status = 'inferred'),
    embedding           vector(1536),
    embed_version       TEXT,

    UNIQUE (profile_id, pattern_id)
);

CREATE INDEX IF NOT EXISTS reviewer_attack_embedding_hnsw_idx
    ON reviewer_attack_patterns USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ---------------------------------------------------------------------------
-- 7. LLM call audit log
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS llm_calls (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint            TEXT NOT NULL,                -- 'article_profile' | 'rewrite' | 'self_check' | ...
    model               TEXT NOT NULL,
    system_prompt_hash  TEXT NOT NULL,
    user_input_hash     TEXT NOT NULL,
    output_hash         TEXT,
    paper_id            INTEGER REFERENCES papers(id) ON DELETE SET NULL,
    user_session        TEXT,
    latency_ms          INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    prompt_tokens       INTEGER,
    completion_tokens   INTEGER,
    verdict             TEXT CHECK (verdict IS NULL OR
                        verdict IN ('clean','suspect','reject','validated','schema_invalid')),
    error               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS llm_calls_endpoint_created_idx
    ON llm_calls (endpoint, created_at DESC);

-- ---------------------------------------------------------------------------
-- 8. updated_at trigger for papers
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS papers_set_updated_at ON papers;
CREATE TRIGGER papers_set_updated_at
    BEFORE UPDATE ON papers
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- 9. Seed journals
-- ---------------------------------------------------------------------------
INSERT INTO journals (key, display_name, publisher, field) VALUES
    ('pnas',     'Proceedings of the National Academy of Sciences', 'NAS',  'general biology + medicine'),
    ('elife',    'eLife',                                            'eLife','life sciences'),
    ('plos_med', 'PLOS Medicine',                                    'PLOS', 'clinical + public health')
ON CONFLICT (key) DO NOTHING;
