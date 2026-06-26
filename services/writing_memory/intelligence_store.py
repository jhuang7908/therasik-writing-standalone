"""
Module 4 — Intelligence & IP Discovery — private library store.

Dual backend (auto-detected at runtime):
  1. PostgreSQL + pgvector  — when ``WRITING_MEMORY_PG`` is set. Production /
     multi-tenant; HNSW cosine search over ``wm_doc_chunks.embedding``.
  2. SQLite + numpy cosine  — fallback when ``WRITING_MEMORY_PG`` is unset.
     Zero external dependency; embeddings stored as JSON float arrays and
     scored in-process. Good enough for MVP / dev integration.

Hard rules:
  * EVERY read/write is scoped by ``project_id``. There is no cross-project
    query path. This is the lab-to-lab isolation boundary.
  * Embeddings reuse ``text-embedding-3-small`` (1536 dims) via an injected
    OpenAI factory, matching ``vector_store.py``. If no embedding is available
    (no OPENAI_API_KEY / offline), documents are still saved and search
    degrades to case-insensitive substring scoring — never raises.

Schema: see ``db/intelligence_schema.sql`` (Postgres) — the SQLite DDL below
mirrors it minus the pgvector column type.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

_EMBED_MODEL = "text-embedding-3-small"
_EMBED_DIM = 1536
_EMBED_VERSION = "te3s-1536-v1"

_PG_DSN = os.environ.get("WRITING_MEMORY_PG", "").strip()
_SQLITE_PATH = (
    os.environ.get("INTELLIGENCE_DB_PATH", "").strip()
    or str(Path(__file__).resolve().parent / "data" / "library" / "db" / "intelligence.db")
)

_OPENAI_FACTORY: Callable[[], Any] | None = None
_VALID_SOURCES = {"openalex", "pubmed", "patent", "sequence", "manual"}
_VALID_KINDS = {"digest", "fto", "novelty", "entity", "radar"}
_VALID_CADENCE = {"weekly", "monthly"}

_sqlite_lock = threading.Lock()
_sqlite_ready = False
_pg_ready = False


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def set_openai_factory(factory: Callable[[], Any]) -> None:
    """Inject the app's OpenAI client factory (same one used by vector_store)."""
    global _OPENAI_FACTORY
    _OPENAI_FACTORY = factory


def backend() -> str:
    return "pgvector" if _PG_DSN else "sqlite"


def backend_status(project_id: str | None = None) -> dict[str, Any]:
    pid = _norm_project(project_id) if project_id is not None else None
    return {
        "active_backend": backend(),
        "pg_configured": bool(_PG_DSN),
        "sqlite_path": None if _PG_DSN else _SQLITE_PATH,
        "embedding_model": _EMBED_MODEL,
        "embedding_dim": _EMBED_DIM,
        "embeddings_available": _OPENAI_FACTORY is not None,
        "project_id": pid,
        "document_count": count_documents(project_id) if pid else None,
    }


def _norm_project(project_id: str | None) -> str:
    p = (project_id or "").strip()
    return p or "_default"


def _openalex_ext_id(item: dict[str, Any]) -> str | None:
    oid = item.get("openalex_id") or item.get("id")
    if not oid:
        return None
    s = str(oid).strip()
    if "openalex.org/" in s:
        s = s.rstrip("/").split("/")[-1]
    return s or None


def doc_subproject(doc: dict[str, Any]) -> str:
    """亚项目 / sub-topic label for literature grouping within a project."""
    sp = doc.get("subproject")
    if sp:
        return str(sp).strip()
    raw = doc.get("raw")
    if raw:
        try:
            obj = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(obj, dict) and obj.get("subproject"):
                return str(obj["subproject"]).strip()
        except Exception:
            pass
    return ""


def _apply_subproject(doc: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    sp = (item.get("subproject") or doc_subproject(item) or "").strip()[:120] or None
    doc["subproject"] = sp
    raw = doc.get("raw")
    if isinstance(raw, dict):
        doc["raw"] = {**raw, "subproject": sp}
    elif isinstance(raw, str):
        try:
            obj = json.loads(raw)
            doc["raw"] = {**obj, "subproject": sp} if isinstance(obj, dict) else {"subproject": sp}
        except Exception:
            doc["raw"] = {"subproject": sp} if sp else {}
    else:
        base = item if isinstance(item, dict) else {}
        doc["raw"] = {**base, "subproject": sp} if sp else base
    return doc


_M2_TYPE_ALIASES: dict[str, str] = {
    "literature": "research",
    "original_research": "research",
    "research": "research",
    "review_narrative": "review",
    "review": "review",
    "narrative_review": "review",
    "systematic_review": "systematic_review",
    "meta_analysis": "systematic_review",
    "case_report": "case_report",
    "brief_communication": "letter",
    "letter": "letter",
    "editorial": "letter",
    "methods_protocols": "protocol",
    "protocol": "protocol",
}


def pubmed_pub_types_to_m2_type(pub_types: list[Any]) -> str:
    """Map PubMed PublicationType list → M2 UI article type id."""
    labels = [str(x).strip().lower() for x in pub_types if str(x).strip()]
    if not labels:
        return "research"
    for pl in labels:
        if pl in {"systematic review", "meta-analysis"} or "systematic review" in pl:
            return "systematic_review"
    for pl in labels:
        if pl in {"review", "narrative review", "scoping review"} or pl.endswith(" review"):
            return "review"
    for pl in labels:
        if "case report" in pl:
            return "case_report"
    for pl in labels:
        if pl in {"clinical trial protocol", "study protocol"} or (
            "protocol" in pl and "clinical trial" in pl
        ):
            return "protocol"
    for pl in labels:
        if pl in {"letter", "comment", "editorial", "brief report", "news"}:
            return "letter"
    return "research"


def literature_article_type(raw_obj: dict[str, Any] | None) -> str:
    """Normalize stored metadata → M2-aligned article type id."""
    if not isinstance(raw_obj, dict):
        return "research"

    explicit = (raw_obj.get("article_type") or "").strip().lower()
    if explicit in _M2_TYPE_ALIASES:
        return _M2_TYPE_ALIASES[explicit]
    if explicit in set(_M2_TYPE_ALIASES.values()):
        return explicit

    oa_type = (raw_obj.get("type") or "").strip().lower()
    if oa_type == "review":
        return "review"
    if oa_type in {"letter", "editorial"}:
        return "letter"

    pub_types = raw_obj.get("pub_types") or []
    if isinstance(pub_types, list) and pub_types:
        return pubmed_pub_types_to_m2_type(pub_types)

    return "research"


def _raw_obj(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("raw")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
    return {}


def _row_needs_type_enrich(row: dict[str, Any]) -> bool:
    if (row.get("source") or "") not in {"openalex", "pubmed", "manual"}:
        return False
    obj = _raw_obj(row)
    if obj.get("article_type_resolved"):
        return False
    doi = (row.get("doi") or obj.get("doi") or "").strip()
    pmid = str(obj.get("pmid") or row.get("ext_id") or "").strip()
    oa_id = (obj.get("openalex_id") or "").strip()
    return bool(doi or pmid or oa_id)


def _patch_document_raw(project_id: str, doc_id: int, obj: dict[str, Any]) -> None:
    payload = json.dumps(obj)
    if _PG_DSN:
        _pg_init()
        with _pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE wm_documents SET raw=%s WHERE project_id=%s AND id=%s",
                    (payload, project_id, doc_id),
                )
            conn.commit()
        return
    _sqlite_init()
    with _sqlite_lock:
        with _sqlite_conn() as conn:
            conn.execute(
                "UPDATE wm_documents SET raw=? WHERE project_id=? AND id=?",
                (payload, project_id, doc_id),
            )
            conn.commit()


def _enrich_list_article_types(rows: list[dict[str, Any]], project_id: str) -> None:
    """Backfill missing article_type for legacy library rows (OpenAlex/PubMed lookup)."""
    from . import openalex_client

    pending = [r for r in rows if _row_needs_type_enrich(r)]
    if not pending:
        return
    for row in pending[:20]:
        obj = _raw_obj(row)
        meta = openalex_client.lookup_article_type(
            doi=row.get("doi") or obj.get("doi"),
            openalex_id=obj.get("openalex_id"),
            pmid=obj.get("pmid") or row.get("ext_id"),
        )
        at = "research"
        if meta:
            at = (meta.get("article_type") or "research").strip().lower()
            obj.update({k: v for k, v in meta.items() if v is not None})
        obj["article_type"] = at
        obj["article_type_resolved"] = True
        _patch_document_raw(project_id, int(row["id"]), obj)
        row["raw"] = obj
        row["article_type"] = at


def _public_doc_row(row: dict[str, Any]) -> dict[str, Any]:
    """Attach venue from stored raw JSON for UI tables."""
    if not row.get("subproject"):
        row["subproject"] = doc_subproject(row) or None
    
    # Ensure pdf_path is absolute for UI if it exists
    if row.get("pdf_path"):
        row["has_pdf"] = True
    else:
        row["has_pdf"] = False

    raw = row.get("raw")
    if raw:
        try:
            obj = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(obj, dict):
                if obj.get("venue"):
                    row["venue"] = obj.get("venue")
                else:
                    primary_source = (
                        (obj.get("primary_location") or {}).get("source") or {}
                    )
                    best_oa_source = (
                        (obj.get("best_oa_location") or {}).get("source") or {}
                    )
                    host_venue = obj.get("host_venue") or {}
                    row["venue"] = (
                        obj.get("journal")
                        or obj.get("journal_title")
                        or obj.get("container_title")
                        or obj.get("source_display_name")
                        or primary_source.get("display_name")
                        or best_oa_source.get("display_name")
                        or host_venue.get("display_name")
                        or row.get("venue")
                    )
                if obj.get("oa_url"):
                    row["oa_url"] = obj.get("oa_url")
                if obj.get("oa_status"):
                    row["oa_status"] = obj.get("oa_status")
                if obj.get("is_oa") is not None:
                    row["is_oa"] = obj.get("is_oa")
                if not row.get("subproject") and obj.get("subproject"):
                    row["subproject"] = obj.get("subproject")
                if row.get("source") in {"openalex", "pubmed", "manual"}:
                    row["article_type"] = literature_article_type(obj)
        except Exception:
            pass
    return row


# ---------------------------------------------------------------------------
# Embeddings (shared by both backends)
# ---------------------------------------------------------------------------
def _embed(texts: list[str]) -> list[list[float]] | None:
    if not texts or _OPENAI_FACTORY is None:
        return None
    try:
        oai = _OPENAI_FACTORY()
        resp = oai.embeddings.create(model=_EMBED_MODEL, input=texts)
        return [list(d.embedding) for d in resp.data]
    except Exception:
        return None


def _embed_one(text: str) -> list[float] | None:
    out = _embed([text])
    return out[0] if out else None


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ---------------------------------------------------------------------------
# Document normalization
# ---------------------------------------------------------------------------
def normalize_item(source: str, item: dict[str, Any]) -> dict[str, Any]:
    """Map a raw OpenAlex/patent search result into the wm_documents shape."""
    src = source if source in _VALID_SOURCES else "manual"
    title = (item.get("title") or "Untitled").strip()
    if src == "openalex":
        ext_id = _openalex_ext_id(item)
        doi = item.get("doi")
        doc = {
            "source": "openalex",
            "ext_id": str(ext_id) if ext_id else None,
            "doi": doi,
            "patent_id": None,
            "title": title,
            "abstract": (item.get("abstract") or "").strip() or None,
            "year": item.get("year") or item.get("publication_year"),
            "url": (f"https://doi.org/{doi}" if doi else item.get("url")),
            "authors": item.get("authors") or None,
            "verification_status": item.get("verification_status") or "verified",
            "raw": item,
        }
        return _apply_subproject(doc, item)
    if src == "pubmed":
        pmid = str(item.get("pmid") or item.get("ext_id") or "").strip()
        doi = item.get("doi")
        doc = {
            "source": "pubmed",
            "ext_id": pmid or None,
            "doi": doi,
            "patent_id": None,
            "title": title,
            "abstract": (item.get("abstract") or "").strip() or None,
            "year": item.get("year"),
            "url": item.get("url") or (f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None),
            "authors": item.get("authors") or None,
            "verification_status": item.get("verification_status") or "verified",
            "raw": item,
        }
        return _apply_subproject(doc, item)
    if src == "manual":
        doi = item.get("doi")
        ext_id = item.get("ext_id") or doi or item.get("url") or title[:200]
        doc = {
            "source": "manual",
            "ext_id": str(ext_id) if ext_id else None,
            "doi": doi,
            "patent_id": None,
            "title": title,
            "abstract": (item.get("abstract") or "").strip() or None,
            "year": item.get("year"),
            "url": (f"https://doi.org/{doi}" if doi else item.get("url")),
            "authors": item.get("authors") or None,
            "verification_status": item.get("verification_status") or "user-provided",
            "raw": item,
        }
        return _apply_subproject(doc, item)
    # patent / sequence
    pid = item.get("patent_id")
    doc = {
        "source": src,
        "ext_id": str(pid) if pid else (item.get("ext_id") or item.get("url")),
        "doi": None,
        "patent_id": str(pid) if pid else None,
        "title": title,
        "abstract": (item.get("abstract") or "").strip() or None,
        "year": item.get("year"),
        "url": item.get("url"),
        "authors": item.get("assignee") or None,
        "verification_status": item.get("verification_status") or "verified",
        "raw": item,
    }
    return _apply_subproject(doc, item)


def _chunk_text(doc: dict[str, Any]) -> str:
    parts = [doc.get("title") or ""]
    # Phase 2: prioritize full-text if available
    if doc.get("full_text"):
        parts.append(doc["full_text"])
    elif doc.get("abstract"):
        parts.append(doc["abstract"])
    if doc.get("authors"):
        parts.append(str(doc["authors"]))
    return "\n".join(p for p in parts if p).strip()


def _get_doc_full_text(doc_id: int, project_id: str) -> str | None:
    """Read full text from local PDF if available."""
    _sqlite_init()
    with _sqlite_conn() as conn:
        row = conn.execute(
            "SELECT pdf_path FROM wm_documents WHERE id=? AND project_id=?",
            (doc_id, project_id),
        ).fetchone()
        if not row or not row["pdf_path"]:
            return None
        
        path = Path(row["pdf_path"])
        if not path.is_file():
            return None
        
        try:
            from .pdf_text import extract_text_from_pdf_bytes
            return extract_text_from_pdf_bytes(path.read_bytes())
        except Exception:
            return None


def ingest_document(project_id: str | None, doc_id: int) -> dict[str, Any]:
    """Extract full-text (if PDF exists) or abstract, chunk, and embed."""
    pid = _norm_project(project_id)
    _sqlite_init()
    
    with _sqlite_lock:
        with _sqlite_conn() as conn:
            doc_row = conn.execute(
                "SELECT * FROM wm_documents WHERE id=? AND project_id=?",
                (doc_id, pid),
            ).fetchone()
            if not doc_row:
                raise ValueError("Document not found")
            
            doc = dict(doc_row)
            full_text = _get_doc_full_text(doc_id, pid)
            if full_text:
                doc["full_text"] = full_text
            
            # Create chunks (Phase 2: simple chunking for full text)
            text_to_chunk = _chunk_text(doc)
            # For now, we still use one big chunk for title+abstract or title+fulltext
            # In a real RAG, we'd split full_text into ~1000 token chunks.
            # Let's do a simple split if it's long.
            chunks = []
            if len(text_to_chunk) > 3000:
                # Simple paragraph-based chunking
                paragraphs = text_to_chunk.split("\n\n")
                current_chunk = ""
                for p in paragraphs:
                    if len(current_chunk) + len(p) < 2500:
                        current_chunk += p + "\n\n"
                    else:
                        if current_chunk: chunks.append(current_chunk.strip())
                        current_chunk = p + "\n\n"
                if current_chunk: chunks.append(current_chunk.strip())
            else:
                chunks = [text_to_chunk]

            # Embed and save
            conn.execute("DELETE FROM wm_doc_chunks WHERE document_id=?", (doc_id,))
            for i, c in enumerate(chunks):
                emb = _embed_one(c)
                emb_json = json.dumps(emb) if (emb and len(emb) == _EMBED_DIM) else None
                conn.execute(
                    """
                    INSERT INTO wm_doc_chunks
                      (document_id, project_id, ordinal, text, embedding, embed_version)
                    VALUES (?,?,?,?,?,?)
                    """,
                    (doc_id, pid, i, c, emb_json, _EMBED_VERSION if emb_json else None),
                )
            
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            conn.execute(
                "UPDATE wm_documents SET ingested_at=? WHERE id=?",
                (now, doc_id),
            )
            conn.commit()
            
    return {"ok": True, "chunks": len(chunks), "full_text": full_text is not None}


# ===========================================================================
# PostgreSQL + pgvector backend
# ===========================================================================
def _pg_connect():
    import psycopg  # psycopg3

    return psycopg.connect(_PG_DSN)


def _pg_init() -> None:
    global _pg_ready
    if _pg_ready:
        return
    ddl = (Path(__file__).resolve().parent / "db" / "intelligence_schema.sql").read_text(
        encoding="utf-8"
    )
    with _pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
    _pg_ready = True


def _pg_vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.7g}" for x in vec) + "]"


def _pg_save(project_id: str, doc: dict[str, Any]) -> dict[str, Any]:
    _pg_init()
    with _pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO wm_documents
                  (project_id, source, ext_id, doi, patent_id, title, abstract,
                   year, url, authors, verification_status, raw, subproject)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (project_id, source, ext_id)
                DO UPDATE SET title = EXCLUDED.title,
                              abstract = EXCLUDED.abstract,
                              url = EXCLUDED.url,
                              raw = EXCLUDED.raw,
                              subproject = EXCLUDED.subproject
                RETURNING id, (xmax = 0) AS inserted
                """,
                (
                    project_id, doc["source"], doc.get("ext_id"), doc.get("doi"),
                    doc.get("patent_id"), doc["title"], doc.get("abstract"),
                    doc.get("year"), doc.get("url"), doc.get("authors"),
                    doc.get("verification_status", "verified"),
                    json.dumps(doc.get("raw") or {}),
                    doc.get("subproject"),
                ),
            )
            row = cur.fetchone()
            doc_id, inserted = int(row[0]), bool(row[1])
            # Refresh chunk + embedding.
            cur.execute("DELETE FROM wm_doc_chunks WHERE document_id = %s", (doc_id,))
            chunk = _chunk_text(doc)
            emb = _embed_one(chunk) if chunk else None
            if emb is not None and len(emb) == _EMBED_DIM:
                cur.execute(
                    """
                    INSERT INTO wm_doc_chunks
                      (document_id, project_id, ordinal, text, embedding, embed_version)
                    VALUES (%s,%s,0,%s,%s::vector,%s)
                    """,
                    (doc_id, project_id, chunk, _pg_vec_literal(emb), _EMBED_VERSION),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO wm_doc_chunks
                      (document_id, project_id, ordinal, text, embedding, embed_version)
                    VALUES (%s,%s,0,%s,NULL,%s)
                    """,
                    (doc_id, project_id, chunk, None),
                )
        conn.commit()
    return {"id": doc_id, "inserted": inserted, "embedded": emb is not None}


def _pg_list(project_id: str, source: str | None, limit: int) -> list[dict[str, Any]]:
    _pg_init()
    sql = (
        "SELECT id, source, ext_id, doi, patent_id, title, abstract, year, url, "
        "authors, verification_status, raw, subproject, pdf_path, ingested_at, created_at FROM wm_documents "
        "WHERE project_id = %s"
    )
    params: list[Any] = [project_id]
    if source:
        sql += " AND source = %s"
        params.append(source)
    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    with _pg_connect() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(sql, params)
            except Exception:
                sql = sql.replace(", subproject", "")
                cur.execute(sql, params)
            cols = [c.name for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    for r in rows:
        if r.get("created_at") is not None:
            r["created_at"] = str(r["created_at"])
        _public_doc_row(r)
    _enrich_list_article_types(rows, project_id)
    return rows


def _pg_search(project_id: str, query: str, top_k: int) -> list[dict[str, Any]]:
    _pg_init()
    qemb = _embed_one(query)
    with _pg_connect() as conn:
        with conn.cursor() as cur:
            if qemb is not None and len(qemb) == _EMBED_DIM:
                cur.execute(
                    """
                    SELECT d.id, d.source, d.title, d.abstract, d.year, d.url,
                           d.doi, d.patent_id, d.verification_status,
                           1 - (c.embedding <=> %s::vector) AS score
                    FROM wm_doc_chunks c
                    JOIN wm_documents d ON d.id = c.document_id
                    WHERE c.project_id = %s AND c.embedding IS NOT NULL
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (_pg_vec_literal(qemb), project_id, _pg_vec_literal(qemb), top_k),
                )
            else:
                like = f"%{query.lower()}%"
                cur.execute(
                    """
                    SELECT id, source, title, abstract, year, url, doi, patent_id,
                           verification_status, 0.0 AS score
                    FROM wm_documents
                    WHERE project_id = %s
                      AND (lower(title) LIKE %s OR lower(coalesce(abstract,'')) LIKE %s)
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (project_id, like, like, top_k),
                )
            cols = [c.name for c in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]


def _pg_save_report(project_id: str, kind: str, query: str | None, body_md: str,
                    meta: dict | None) -> dict[str, Any]:
    _pg_init()
    with _pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO wm_reports (project_id, kind, query, body_md, meta)
                VALUES (%s,%s,%s,%s,%s) RETURNING id, created_at
                """,
                (project_id, kind, query, body_md, json.dumps(meta or {})),
            )
            rid, created = cur.fetchone()
        conn.commit()
    return {"id": int(rid), "created_at": str(created)}


def _pg_list_reports(project_id: str, kind: str | None, limit: int) -> list[dict[str, Any]]:
    _pg_init()
    sql = "SELECT id, kind, query, body_md, created_at FROM wm_reports WHERE project_id = %s"
    params: list[Any] = [project_id]
    if kind:
        sql += " AND kind = %s"
        params.append(kind)
    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    with _pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [c.name for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    for r in rows:
        r["created_at"] = str(r.get("created_at"))
    return rows


# ===========================================================================
# SQLite + numpy fallback backend
# ===========================================================================
def _sqlite_conn() -> sqlite3.Connection:
    Path(_SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _sqlite_init() -> None:
    global _sqlite_ready
    if _sqlite_ready:
        return
    with _sqlite_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS wm_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                source TEXT NOT NULL,
                ext_id TEXT,
                doi TEXT,
                patent_id TEXT,
                title TEXT NOT NULL,
                abstract TEXT,
                year INTEGER,
                url TEXT,
                authors TEXT,
                verification_status TEXT NOT NULL DEFAULT 'verified',
                raw TEXT,
                subproject TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (project_id, source, ext_id)
            );
            CREATE INDEX IF NOT EXISTS wm_documents_project_idx
                ON wm_documents (project_id, created_at DESC);
            CREATE TABLE IF NOT EXISTS wm_doc_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL REFERENCES wm_documents(id) ON DELETE CASCADE,
                project_id TEXT NOT NULL,
                ordinal INTEGER NOT NULL DEFAULT 0,
                text TEXT NOT NULL,
                embedding TEXT,
                embed_version TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS wm_doc_chunks_project_idx
                ON wm_doc_chunks (project_id);
            CREATE TABLE IF NOT EXISTS wm_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                query TEXT,
                body_md TEXT NOT NULL,
                meta TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS wm_reports_project_idx
                ON wm_reports (project_id, kind, created_at DESC);
            CREATE TABLE IF NOT EXISTS wm_radar_watches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                label TEXT,
                query TEXT NOT NULL,
                cadence TEXT NOT NULL DEFAULT 'weekly',
                notify_email TEXT,
                enabled INTEGER NOT NULL DEFAULT 1,
                auto_save_library INTEGER NOT NULL DEFAULT 0,
                per_page INTEGER NOT NULL DEFAULT 15,
                last_run_at TEXT,
                last_seen_ids TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS wm_radar_watches_project_idx
                ON wm_radar_watches (project_id, enabled);
            """
        )
        conn.commit()
        with _sqlite_conn() as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(wm_documents)").fetchall()]
            if "subproject" not in cols:
                conn.execute("ALTER TABLE wm_documents ADD COLUMN subproject TEXT")
                conn.commit()
            if "pdf_path" not in cols:
                conn.execute("ALTER TABLE wm_documents ADD COLUMN pdf_path TEXT")
                conn.commit()
            if "ingested_at" not in cols:
                conn.execute("ALTER TABLE wm_documents ADD COLUMN ingested_at TEXT")
                conn.commit()
            wcols = [r[1] for r in conn.execute("PRAGMA table_info(wm_radar_watches)").fetchall()]
            if not wcols:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS wm_radar_watches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id TEXT NOT NULL,
                        label TEXT,
                        query TEXT NOT NULL,
                        cadence TEXT NOT NULL DEFAULT 'weekly',
                        notify_email TEXT,
                        enabled INTEGER NOT NULL DEFAULT 1,
                        auto_save_library INTEGER NOT NULL DEFAULT 0,
                        per_page INTEGER NOT NULL DEFAULT 15,
                        last_run_at TEXT,
                        last_seen_ids TEXT NOT NULL DEFAULT '[]',
                        created_at TEXT NOT NULL DEFAULT (datetime('now')),
                        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                    );
                    CREATE INDEX IF NOT EXISTS wm_radar_watches_project_idx
                        ON wm_radar_watches (project_id, enabled);
                    """
                )
                conn.commit()
    _sqlite_ready = True


def _sqlite_save(project_id: str, doc: dict[str, Any]) -> dict[str, Any]:
    with _sqlite_lock:
        _sqlite_init()
        chunk = _chunk_text(doc)
        emb = _embed_one(chunk) if chunk else None
        with _sqlite_conn() as conn:
            cur = conn.cursor()
            if doc.get("ext_id") is None:
                cur.execute(
                    "SELECT id FROM wm_documents WHERE project_id=? AND source=? AND ext_id IS NULL",
                    (project_id, doc["source"]),
                )
            else:
                cur.execute(
                    "SELECT id FROM wm_documents WHERE project_id=? AND source=? AND ext_id=?",
                    (project_id, doc["source"], doc.get("ext_id")),
                )
            existing = cur.fetchone()
            if existing:
                doc_id = int(existing["id"])
                inserted = False
                sp = doc.get("subproject")
                cur.execute(
                    "UPDATE wm_documents SET title=?, abstract=?, url=?, raw=?, subproject=? WHERE id=?",
                    (doc["title"], doc.get("abstract"), doc.get("url"),
                     json.dumps(doc.get("raw") or {}), sp, doc_id),
                )
                cur.execute("DELETE FROM wm_doc_chunks WHERE document_id=?", (doc_id,))
            else:
                cur.execute(
                    """
                    INSERT INTO wm_documents
                      (project_id, source, ext_id, doi, patent_id, title, abstract,
                       year, url, authors, verification_status, raw, subproject)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (project_id, doc["source"], doc.get("ext_id"), doc.get("doi"),
                     doc.get("patent_id"), doc["title"], doc.get("abstract"),
                     doc.get("year"), doc.get("url"), doc.get("authors"),
                     doc.get("verification_status", "verified"),
                     json.dumps(doc.get("raw") or {}), doc.get("subproject")),
                )
                doc_id = int(cur.lastrowid)
                inserted = True
            emb_json = json.dumps(emb) if (emb and len(emb) == _EMBED_DIM) else None
            cur.execute(
                """
                INSERT INTO wm_doc_chunks
                  (document_id, project_id, ordinal, text, embedding, embed_version)
                VALUES (?,?,0,?,?,?)
                """,
                (doc_id, project_id, chunk, emb_json, _EMBED_VERSION if emb_json else None),
            )
            conn.commit()
        return {"id": doc_id, "inserted": inserted, "embedded": emb is not None}


def _sqlite_list(project_id: str, source: str | None, limit: int) -> list[dict[str, Any]]:
    _sqlite_init()
    sql = (
        "SELECT id, source, ext_id, doi, patent_id, title, abstract, year, url, "
        "authors, verification_status, raw, subproject, pdf_path, ingested_at, created_at "
        "FROM wm_documents WHERE project_id=?"
    )
    params: list[Any] = [project_id]
    if source:
        sql += " AND source=?"
        params.append(source)
    sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
    params.append(limit)
    with _sqlite_conn() as conn:
        try:
            rows = [_public_doc_row(dict(r)) for r in conn.execute(sql, params).fetchall()]
        except Exception:
            sql = sql.replace(", subproject", "")
            rows = [_public_doc_row(dict(r)) for r in conn.execute(sql, params).fetchall()]
    _enrich_list_article_types(rows, project_id)
    return rows


def _sqlite_search(project_id: str, query: str, top_k: int) -> list[dict[str, Any]]:
    _sqlite_init()
    qemb = _embed_one(query)
    with _sqlite_conn() as conn:
        rows = conn.execute(
            """
            SELECT d.id, d.source, d.title, d.abstract, d.year, d.url, d.doi,
                   d.patent_id, d.verification_status, c.text AS chunk_text,
                   c.embedding AS emb
            FROM wm_doc_chunks c
            JOIN wm_documents d ON d.id = c.document_id
            WHERE c.project_id=?
            """,
            (project_id,),
        ).fetchall()
    if qemb is not None:
        qv = np.array(qemb, dtype=np.float32)
        scored: list[tuple[float, dict]] = []
        for r in rows:
            if not r["emb"]:
                continue
            try:
                v = np.array(json.loads(r["emb"]), dtype=np.float32)
            except Exception:
                continue
            scored.append((_cosine(qv, v), _row_to_hit(r)))
        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            out = []
            for score, hit in scored[:top_k]:
                hit["score"] = round(score, 4)
                out.append(hit)
            return out
    # Fallback: substring scoring.
    ql = query.lower()
    hits = []
    for r in rows:
        hay = (r["title"] or "") + " " + (r["abstract"] or "") + " " + (r["chunk_text"] or "")
        if ql in hay.lower():
            hit = _row_to_hit(r)
            hit["score"] = 0.0
            hits.append(hit)
    return hits[:top_k]


def _row_to_hit(r: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": r["id"], "source": r["source"], "title": r["title"],
        "abstract": r["abstract"], "year": r["year"], "url": r["url"],
        "doi": r["doi"], "patent_id": r["patent_id"],
        "verification_status": r["verification_status"],
        "chunk_text": r.get("chunk_text"),
    }


def _sqlite_save_report(project_id: str, kind: str, query: str | None, body_md: str,
                        meta: dict | None) -> dict[str, Any]:
    with _sqlite_lock:
        _sqlite_init()
        with _sqlite_conn() as conn:
            cur = conn.execute(
                "INSERT INTO wm_reports (project_id, kind, query, body_md, meta) VALUES (?,?,?,?,?)",
                (project_id, kind, query, body_md, json.dumps(meta or {})),
            )
            rid = int(cur.lastrowid)
            conn.commit()
    return {"id": rid, "created_at": None}


def _sqlite_list_reports(project_id: str, kind: str | None, limit: int) -> list[dict[str, Any]]:
    _sqlite_init()
    sql = "SELECT id, kind, query, body_md, created_at FROM wm_reports WHERE project_id=?"
    params: list[Any] = [project_id]
    if kind:
        sql += " AND kind=?"
        params.append(kind)
    sql += " ORDER BY created_at DESC, id DESC LIMIT ?"
    params.append(limit)
    with _sqlite_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


# ===========================================================================
# Public API (backend-agnostic, project_id enforced)
# ===========================================================================
def save_document(project_id: str | None, source: str, item: dict[str, Any]) -> dict[str, Any]:
    pid = _norm_project(project_id)
    doc = normalize_item(source, item)
    # Ensure subproject is explicitly passed if present in item
    if "subproject" in item and not doc.get("subproject"):
        doc["subproject"] = item["subproject"]
    
    if _PG_DSN:
        return _pg_save(pid, doc)
    return _sqlite_save(pid, doc)


def count_documents(project_id: str | None, source: str | None = None) -> int:
    pid = _norm_project(project_id)
    if _PG_DSN:
        _pg_init()
        sql = "SELECT COUNT(*) FROM wm_documents WHERE project_id = %s"
        params: list[Any] = [pid]
        if source and source in _VALID_SOURCES:
            sql += " AND source = %s"
            params.append(source)
        with _pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return int(cur.fetchone()[0])
    _sqlite_init()
    sql = "SELECT COUNT(*) FROM wm_documents WHERE project_id=?"
    params = [pid]
    if source and source in _VALID_SOURCES:
        sql += " AND source=?"
        params.append(source)
    with _sqlite_conn() as conn:
        return int(conn.execute(sql, params).fetchone()[0])


def list_documents(
    project_id: str | None,
    source: str | None = None,
    limit: int = 100,
    subproject: str | None = None,
) -> list[dict[str, Any]]:
    pid = _norm_project(project_id)
    limit = max(1, min(limit, 500))
    if source and source not in _VALID_SOURCES:
        source = None
    if _PG_DSN:
        rows = _pg_list(pid, source, limit)
    else:
        rows = _sqlite_list(pid, source, limit)
    if subproject == "__none__":
        return [r for r in rows if not doc_subproject(r)]
    if subproject:
        return [r for r in rows if doc_subproject(r) == subproject]
    return rows


def list_subprojects(project_id: str | None) -> list[str]:
    """Distinct sub-database labels for literature rows in this project."""
    pid = _norm_project(project_id)
    labels: set[str] = set()
    for doc in list_documents(pid, limit=500):
        if (doc.get("source") or "") in ("openalex", "pubmed", "manual", "patent", "sequence"):
            sp = doc_subproject(doc)
            if sp:
                labels.add(sp)
    return sorted(labels)


def update_document_pdf(project_id: str | None, doc_id: int, pdf_path: str) -> None:
    pid = _norm_project(project_id)
    if _PG_DSN:
        _pg_init()
        with _pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE wm_documents SET pdf_path=%s WHERE id=%s AND project_id=%s",
                    (pdf_path, doc_id, pid),
                )
                if cur.rowcount < 1:
                    raise ValueError(f"document {doc_id} not found in project {pid}")
            conn.commit()
        return
    _sqlite_init()
    with _sqlite_lock:
        with _sqlite_conn() as conn:
            cur = conn.execute(
                "UPDATE wm_documents SET pdf_path=? WHERE id=? AND project_id=?",
                (pdf_path, doc_id, pid),
            )
            if cur.rowcount < 1:
                raise ValueError(f"document {doc_id} not found in project {pid}")
            conn.commit()


def tag_documents(
    project_id: str | None,
    document_ids: list[int],
    subproject: str | None,
) -> dict[str, Any]:
    """Assign or clear亚项目 on saved library rows."""
    pid = _norm_project(project_id)
    sp = (subproject or "").strip()[:120] or None
    ids = [int(i) for i in document_ids if int(i) > 0]
    if not ids:
        return {"updated": 0, "subproject": sp}
    updated = 0
    if _PG_DSN:
        _pg_init()
        with _pg_connect() as conn:
            with conn.cursor() as cur:
                for doc_id in ids:
                    cur.execute(
                        "SELECT raw FROM wm_documents WHERE project_id=%s AND id=%s",
                        (pid, doc_id),
                    )
                    row = cur.fetchone()
                    if not row:
                        continue
                    raw = row[0]
                    if isinstance(raw, dict):
                        obj = raw
                    else:
                        obj = json.loads(raw) if raw else {}
                    if not isinstance(obj, dict):
                        obj = {}
                    obj["subproject"] = sp
                    cur.execute(
                        "UPDATE wm_documents SET subproject=%s, raw=%s WHERE project_id=%s AND id=%s",
                        (sp, json.dumps(obj), pid, doc_id),
                    )
                    updated += cur.rowcount
            conn.commit()
    else:
        _sqlite_init()
        with _sqlite_lock:
            with _sqlite_conn() as conn:
                for doc_id in ids:
                    row = conn.execute(
                        "SELECT raw FROM wm_documents WHERE project_id=? AND id=?",
                        (pid, doc_id),
                    ).fetchone()
                    if not row:
                        continue
                    try:
                        obj = json.loads(row["raw"] or "{}")
                    except Exception:
                        obj = {}
                    if not isinstance(obj, dict):
                        obj = {}
                    obj["subproject"] = sp
                    conn.execute(
                        "UPDATE wm_documents SET subproject=?, raw=? WHERE project_id=? AND id=?",
                        (sp, json.dumps(obj), pid, doc_id),
                    )
                    updated += 1
                conn.commit()
    return {"updated": updated, "subproject": sp, "document_ids": ids}


def rename_subproject(project_id: str | None, old_subproject: str, new_subproject: str | None) -> dict[str, Any]:
    # ... (existing code) ...
    return {"updated": updated, "old_subproject": old_sp, "new_subproject": new_sp}


def update_document_abstract(project_id: str | None, doc_id: int, abstract: str) -> bool:
    # ... (existing code) ...
    return True


def update_document_oa_url(project_id: str | None, doc_id: int, url: str) -> bool:
    """Update the OA URL of a specific document."""
    pid = _norm_project(project_id)
    if _PG_DSN:
        _pg_init()
        with _pg_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw FROM wm_documents WHERE project_id=%s AND id=%s", (pid, doc_id))
                row = cur.fetchone()
                if not row: return False
                raw = row[0]
                try:
                    obj = json.loads(raw) if raw else {}
                except Exception: obj = {}
                obj["oa_url"] = url
                cur.execute(
                    "UPDATE wm_documents SET raw=%s WHERE project_id=%s AND id=%s",
                    (json.dumps(obj), pid, doc_id)
                )
            conn.commit()
            return True
    else:
        _sqlite_init()
        with _sqlite_lock:
            with _sqlite_conn() as conn:
                row = conn.execute("SELECT raw FROM wm_documents WHERE project_id=? AND id=?", (pid, doc_id)).fetchone()
                if not row: return False
                raw = row["raw"]
                try:
                    obj = json.loads(raw) if raw else {}
                except Exception: obj = {}
                obj["oa_url"] = url
                conn.execute(
                    "UPDATE wm_documents SET raw=? WHERE project_id=? AND id=?",
                    (json.dumps(obj), pid, doc_id)
                )
                conn.commit()
                return True


def search_library(project_id: str | None, query: str, top_k: int = 8) -> list[dict[str, Any]]:
    pid = _norm_project(project_id)
    q = (query or "").strip()
    if len(q) < 2:
        return []
    top_k = max(1, min(top_k, 25))
    if _PG_DSN:
        return _pg_search(pid, q, top_k)
    return _sqlite_search(pid, q, top_k)


def save_report(project_id: str | None, kind: str, query: str | None,
                body_md: str, meta: dict | None = None) -> dict[str, Any]:
    pid = _norm_project(project_id)
    if kind not in _VALID_KINDS:
        kind = "digest"
    if _PG_DSN:
        return _pg_save_report(pid, kind, query, body_md, meta)
    return _sqlite_save_report(pid, kind, query, body_md, meta)


def list_reports(project_id: str | None, kind: str | None = None,
                 limit: int = 20) -> list[dict[str, Any]]:
    pid = _norm_project(project_id)
    limit = max(1, min(limit, 100))
    if kind and kind not in _VALID_KINDS:
        kind = None
    if _PG_DSN:
        return _pg_list_reports(pid, kind, limit)
    return _sqlite_list_reports(pid, kind, limit)


# ---------------------------------------------------------------------------
# Scheduled literature radar watches
# ---------------------------------------------------------------------------
def _public_watch_row(row: dict[str, Any]) -> dict[str, Any]:
    ids = row.get("last_seen_ids")
    if isinstance(ids, str):
        try:
            ids = json.loads(ids)
        except Exception:
            ids = []
    if not isinstance(ids, list):
        ids = []
    cadence = (row.get("cadence") or "weekly").strip().lower()
    if cadence not in _VALID_CADENCE:
        cadence = "weekly"
    days = 7 if cadence == "weekly" else 30
    due = _watch_is_due(row.get("last_run_at"), days, bool(row.get("enabled", 1)))
    return {
        "id": int(row["id"]),
        "project_id": row["project_id"],
        "label": row.get("label") or "",
        "query": row["query"],
        "cadence": cadence,
        "notify_email": row.get("notify_email") or "",
        "enabled": bool(row.get("enabled", 1)),
        "auto_save_library": bool(row.get("auto_save_library", 0)),
        "per_page": int(row.get("per_page") or 15),
        "last_run_at": row.get("last_run_at"),
        "last_seen_count": len(ids),
        "due": due,
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _watch_is_due(last_run_at: Any, interval_days: int, enabled: bool) -> bool:
    if not enabled:
        return False
    if not last_run_at:
        return True
    try:
        s = str(last_run_at).replace("Z", "+00:00")
        if "T" not in s and " " in s:
            s = s.replace(" ", "T") + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        elapsed = datetime.now(timezone.utc) - dt
        return elapsed >= timedelta(days=interval_days)
    except Exception:
        return True


def _sqlite_upsert_radar_watch(project_id: str, data: dict[str, Any]) -> dict[str, Any]:
    _sqlite_init()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cadence = (data.get("cadence") or "weekly").strip().lower()
    if cadence not in _VALID_CADENCE:
        cadence = "weekly"
    per_page = max(5, min(int(data.get("per_page") or 15), 25))
    enabled = 1 if data.get("enabled", True) else 0
    auto_save = 1 if data.get("auto_save_library") else 0
    label = (data.get("label") or "").strip()[:120] or None
    notify = (data.get("notify_email") or "").strip()[:200] or None
    query = (data.get("query") or "").strip()
    if len(query) < 2:
        raise ValueError("query must be at least 2 characters")
    with _sqlite_lock:
        with _sqlite_conn() as conn:
            wid = data.get("id")
            if wid:
                conn.execute(
                    """
                    UPDATE wm_radar_watches SET label=?, query=?, cadence=?, notify_email=?,
                      enabled=?, auto_save_library=?, per_page=?, updated_at=?
                    WHERE id=? AND project_id=?
                    """,
                    (label, query, cadence, notify, enabled, auto_save, per_page, now, int(wid), project_id),
                )
                if conn.total_changes == 0:
                    raise ValueError("watch not found")
                row_id = int(wid)
            else:
                cur = conn.execute(
                    """
                    INSERT INTO wm_radar_watches
                      (project_id, label, query, cadence, notify_email, enabled,
                       auto_save_library, per_page, last_seen_ids, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,'[]',?,?)
                    """,
                    (project_id, label, query, cadence, notify, enabled, auto_save, per_page, now, now),
                )
                row_id = int(cur.lastrowid)
            conn.commit()
            row = conn.execute(
                "SELECT * FROM wm_radar_watches WHERE id=? AND project_id=?",
                (row_id, project_id),
            ).fetchone()
    return _public_watch_row(dict(row))


def _sqlite_list_radar_watches(project_id: str) -> list[dict[str, Any]]:
    _sqlite_init()
    with _sqlite_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM wm_radar_watches WHERE project_id=? ORDER BY id ASC",
            (project_id,),
        ).fetchall()
    return [_public_watch_row(dict(r)) for r in rows]


def _sqlite_get_radar_watch(watch_id: int, project_id: str) -> dict[str, Any] | None:
    _sqlite_init()
    with _sqlite_conn() as conn:
        row = conn.execute(
            "SELECT * FROM wm_radar_watches WHERE id=? AND project_id=?",
            (watch_id, project_id),
        ).fetchone()
    return _public_watch_row(dict(row)) if row else None


def _sqlite_delete_radar_watch(watch_id: int, project_id: str) -> bool:
    _sqlite_init()
    with _sqlite_lock:
        with _sqlite_conn() as conn:
            conn.execute(
                "DELETE FROM wm_radar_watches WHERE id=? AND project_id=?",
                (watch_id, project_id),
            )
            ok = conn.total_changes > 0
            conn.commit()
    return ok


def _sqlite_mark_radar_watch_run(watch_id: int, project_id: str, seen_ids: list[str]) -> None:
    _sqlite_init()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _sqlite_lock:
        with _sqlite_conn() as conn:
            conn.execute(
                "UPDATE wm_radar_watches SET last_run_at=?, last_seen_ids=?, updated_at=? "
                "WHERE id=? AND project_id=?",
                (now, json.dumps(seen_ids[:500]), now, watch_id, project_id),
            )
            conn.commit()


def _sqlite_list_due_radar_watches(project_id: str | None) -> list[dict[str, Any]]:
    watches = []
    if project_id:
        watches = _sqlite_list_radar_watches(_norm_project(project_id))
    else:
        _sqlite_init()
        with _sqlite_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM wm_radar_watches WHERE enabled=1 ORDER BY project_id, id"
            ).fetchall()
        watches = [_public_watch_row(dict(r)) for r in rows]
    return [w for w in watches if w.get("due")]


def _pg_upsert_radar_watch(project_id: str, data: dict[str, Any]) -> dict[str, Any]:
    _pg_init()
    now = datetime.now(timezone.utc)
    cadence = (data.get("cadence") or "weekly").strip().lower()
    if cadence not in _VALID_CADENCE:
        cadence = "weekly"
    per_page = max(5, min(int(data.get("per_page") or 15), 25))
    enabled = bool(data.get("enabled", True))
    auto_save = bool(data.get("auto_save_library"))
    label = (data.get("label") or "").strip()[:120] or None
    notify = (data.get("notify_email") or "").strip()[:200] or None
    query = (data.get("query") or "").strip()
    if len(query) < 2:
        raise ValueError("query must be at least 2 characters")
    with _pg_connect() as conn:
        with conn.cursor() as cur:
            wid = data.get("id")
            if wid:
                cur.execute(
                    """
                    UPDATE wm_radar_watches SET label=%s, query=%s, cadence=%s, notify_email=%s,
                      enabled=%s, auto_save_library=%s, per_page=%s, updated_at=%s
                    WHERE id=%s AND project_id=%s
                    RETURNING *
                    """,
                    (label, query, cadence, notify, enabled, auto_save, per_page, now,
                     int(wid), project_id),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("watch not found")
            else:
                cur.execute(
                    """
                    INSERT INTO wm_radar_watches
                      (project_id, label, query, cadence, notify_email, enabled,
                       auto_save_library, per_page, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING *
                    """,
                    (project_id, label, query, cadence, notify, enabled, auto_save, per_page, now),
                )
                row = cur.fetchone()
            cols = [c.name for c in cur.description]
            out = dict(zip(cols, row))
        conn.commit()
    for k in ("created_at", "updated_at", "last_run_at"):
        if out.get(k) is not None:
            out[k] = str(out[k])
    return _public_watch_row(out)


def _pg_list_radar_watches(project_id: str) -> list[dict[str, Any]]:
    _pg_init()
    with _pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM wm_radar_watches WHERE project_id=%s ORDER BY id",
                (project_id,),
            )
            cols = [c.name for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    for r in rows:
        for k in ("created_at", "updated_at", "last_run_at"):
            if r.get(k) is not None:
                r[k] = str(r[k])
    return [_public_watch_row(r) for r in rows]


def _pg_get_radar_watch(watch_id: int, project_id: str) -> dict[str, Any] | None:
    _pg_init()
    with _pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM wm_radar_watches WHERE id=%s AND project_id=%s",
                (watch_id, project_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [c.name for c in cur.description]
            r = dict(zip(cols, row))
    for k in ("created_at", "updated_at", "last_run_at"):
        if r.get(k) is not None:
            r[k] = str(r[k])
    return _public_watch_row(r)


def _pg_delete_radar_watch(watch_id: int, project_id: str) -> bool:
    _pg_init()
    with _pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM wm_radar_watches WHERE id=%s AND project_id=%s",
                (watch_id, project_id),
            )
            ok = cur.rowcount > 0
        conn.commit()
    return ok


def _pg_mark_radar_watch_run(watch_id: int, project_id: str, seen_ids: list[str]) -> None:
    _pg_init()
    now = datetime.now(timezone.utc)
    with _pg_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE wm_radar_watches SET last_run_at=%s, last_seen_ids=%s, updated_at=%s
                WHERE id=%s AND project_id=%s
                """,
                (now, json.dumps(seen_ids[:500]), now, watch_id, project_id),
            )
        conn.commit()


def _pg_list_due_radar_watches(project_id: str | None) -> list[dict[str, Any]]:
    if project_id:
        watches = _pg_list_radar_watches(_norm_project(project_id))
    else:
        _pg_init()
        with _pg_connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM wm_radar_watches WHERE enabled=TRUE ORDER BY project_id, id"
                )
                cols = [c.name for c in cur.description]
                rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        watches = []
        for r in rows:
            for k in ("created_at", "updated_at", "last_run_at"):
                if r.get(k) is not None:
                    r[k] = str(r[k])
            watches.append(_public_watch_row(r))
    return [w for w in watches if w.get("due")]


def upsert_radar_watch(project_id: str | None, data: dict[str, Any]) -> dict[str, Any]:
    pid = _norm_project(project_id)
    if _PG_DSN:
        return _pg_upsert_radar_watch(pid, data)
    return _sqlite_upsert_radar_watch(pid, data)


def list_radar_watches(project_id: str | None) -> list[dict[str, Any]]:
    pid = _norm_project(project_id)
    if _PG_DSN:
        return _pg_list_radar_watches(pid)
    return _sqlite_list_radar_watches(pid)


def get_radar_watch(watch_id: int, project_id: str | None = None) -> dict[str, Any] | None:
    pid = _norm_project(project_id) if project_id else None
    if _PG_DSN:
        if not pid:
            _pg_init()
            with _pg_connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT project_id FROM wm_radar_watches WHERE id=%s", (watch_id,))
                    row = cur.fetchone()
            if not row:
                return None
            pid = row[0]
        return _pg_get_radar_watch(watch_id, pid)
    if not pid:
        _sqlite_init()
        with _sqlite_conn() as conn:
            row = conn.execute(
                "SELECT project_id FROM wm_radar_watches WHERE id=?", (watch_id,),
            ).fetchone()
        if not row:
            return None
        pid = row["project_id"]
    return _sqlite_get_radar_watch(watch_id, pid)


def delete_radar_watch(watch_id: int, project_id: str | None) -> bool:
    pid = _norm_project(project_id)
    if _PG_DSN:
        return _pg_delete_radar_watch(watch_id, pid)
    return _sqlite_delete_radar_watch(watch_id, pid)


def mark_radar_watch_run(watch_id: int, project_id: str, seen_ids: list[str]) -> None:
    if _PG_DSN:
        _pg_mark_radar_watch_run(watch_id, project_id, seen_ids)
    else:
        _sqlite_mark_radar_watch_run(watch_id, project_id, seen_ids)


def list_due_radar_watches(project_id: str | None = None) -> list[dict[str, Any]]:
    if _PG_DSN:
        return _pg_list_due_radar_watches(project_id)
    return _sqlite_list_due_radar_watches(project_id)
