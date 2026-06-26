-- =============================================================================
-- Module 4 — Intelligence & IP Discovery — private library schema (v0.1)
--
-- Scope (Phase 1):
--   - Per-project (per-lab) private library of literature / patent / sequence
--     items saved from OpenAlex + patent search.
--   - Title + abstract embedding for semantic recall (RAG chat, hotspot digest).
--   - Stored hotspot / FTO / novelty reports.
--
-- Multi-tenancy:
--   - EVERY row carries project_id; EVERY query MUST filter on project_id.
--     This is the hard isolation boundary between labs (see intelligence_store.py).
--
-- Embeddings:
--   - Dimension fixed at 1536 (OpenAI text-embedding-3-small), matching the
--     corpus schema in db/schema.sql. If the embedding model changes, the
--     embedding column type MUST be migrated and a re-embed run scheduled.
--
-- Backend note:
--   - This file targets PostgreSQL + pgvector (production / WRITING_MEMORY_PG).
--   - When WRITING_MEMORY_PG is unset, intelligence_store.py falls back to a
--     local SQLite database with numpy cosine search (zero-dependency MVP).
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- 1. Saved documents (literature / patent / sequence / manual)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wm_documents (
    id                  BIGSERIAL PRIMARY KEY,
    project_id          TEXT NOT NULL,
    source              TEXT NOT NULL CHECK (source IN
                        ('openalex','patent','sequence','manual')),
    ext_id              TEXT,                 -- openalex_id or patent_id
    doi                 TEXT,
    patent_id           TEXT,
    title               TEXT NOT NULL,
    abstract            TEXT,
    year                INTEGER,
    url                 TEXT,
    authors             TEXT,
    verification_status TEXT NOT NULL DEFAULT 'verified'
                        CHECK (verification_status IN ('verified','inferred','unverified')),
    raw                 JSONB,
    subproject          TEXT,                 -- literature sub-topic / 亚项目 within project
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Idempotent save: same external item is not duplicated within a project.
    UNIQUE (project_id, source, ext_id)
);

CREATE INDEX IF NOT EXISTS wm_documents_project_idx
    ON wm_documents (project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS wm_documents_project_source_idx
    ON wm_documents (project_id, source);
CREATE INDEX IF NOT EXISTS wm_documents_project_subproject_idx
    ON wm_documents (project_id, subproject);

    -- Idempotent upgrade for databases created before subproject column existed.
    ALTER TABLE wm_documents ADD COLUMN IF NOT EXISTS subproject TEXT;
    ALTER TABLE wm_documents ADD COLUMN IF NOT EXISTS pdf_path TEXT;
    ALTER TABLE wm_documents ADD COLUMN IF NOT EXISTS ingested_at TIMESTAMPTZ;

    -- ---------------------------------------------------------------------------
    -- 2. Document chunks (Phase 1: one chunk = title + abstract; Phase 2: full text)
    -- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wm_doc_chunks (
    id                  BIGSERIAL PRIMARY KEY,
    document_id         BIGINT NOT NULL REFERENCES wm_documents(id) ON DELETE CASCADE,
    project_id          TEXT NOT NULL,
    ordinal             INTEGER NOT NULL DEFAULT 0,
    text                TEXT NOT NULL,
    embedding           vector(1536),
    embed_version       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS wm_doc_chunks_project_idx
    ON wm_doc_chunks (project_id);
CREATE INDEX IF NOT EXISTS wm_doc_chunks_document_idx
    ON wm_doc_chunks (document_id);
CREATE INDEX IF NOT EXISTS wm_doc_chunks_embedding_hnsw_idx
    ON wm_doc_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ---------------------------------------------------------------------------
-- 3. Generated reports (hotspot digest / FTO / novelty)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wm_reports (
    id                  BIGSERIAL PRIMARY KEY,
    project_id          TEXT NOT NULL,
    kind                TEXT NOT NULL CHECK (kind IN ('digest','fto','novelty','entity','radar')),
    query               TEXT,
    body_md             TEXT NOT NULL,
    meta                JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS wm_reports_project_idx
    ON wm_reports (project_id, kind, created_at DESC);

-- Idempotent upgrade for report kinds (add scheduled literature radar).
ALTER TABLE wm_reports DROP CONSTRAINT IF EXISTS wm_reports_kind_check;
ALTER TABLE wm_reports ADD CONSTRAINT wm_reports_kind_check
    CHECK (kind IN ('digest','fto','novelty','entity','radar'));

-- ---------------------------------------------------------------------------
-- 4. Scheduled literature radar watches (per project, multi-topic)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wm_radar_watches (
    id                  BIGSERIAL PRIMARY KEY,
    project_id          TEXT NOT NULL,
    label               TEXT,
    query               TEXT NOT NULL,
    cadence             TEXT NOT NULL DEFAULT 'weekly'
                        CHECK (cadence IN ('weekly','monthly')),
    notify_email        TEXT,
    enabled             BOOLEAN NOT NULL DEFAULT TRUE,
    auto_save_library   BOOLEAN NOT NULL DEFAULT FALSE,
    per_page            INTEGER NOT NULL DEFAULT 15,
    last_run_at         TIMESTAMPTZ,
    last_seen_ids       JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS wm_radar_watches_project_idx
    ON wm_radar_watches (project_id, enabled);
