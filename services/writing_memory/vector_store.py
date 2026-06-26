"""
Semantic search over the writing-memory corpus.

Priority:
  1. PostgreSQL + pgvector (``WRITING_MEMORY_PG``) — ``paper_chunks`` HNSW index
  2. In-memory ``embeddings/index.npz`` loaded at API startup (MVP vector index)

Hits always include chunk ``text`` — callers must not re-scan ``papers_raw`` JSON.
"""

from __future__ import annotations

import os
from typing import Any, Callable

import numpy as np

_EMBED_MODEL = "text-embedding-3-small"
_PG_DSN = os.environ.get("WRITING_MEMORY_PG", "").strip()

# Set by app startup: _load_index() assigns the numpy bundle
_NPZ_INDEX: dict[str, Any] | None = None
_OPENAI_FACTORY: Callable[[], Any] | None = None


def set_npz_index(index: dict[str, Any] | None) -> None:
    global _NPZ_INDEX
    _NPZ_INDEX = index


def set_openai_factory(factory: Callable[[], Any]) -> None:
    global _OPENAI_FACTORY
    _OPENAI_FACTORY = factory


def vector_backend_status() -> dict[str, Any]:
    pg = bool(_PG_DSN)
    npz = _NPZ_INDEX is not None and "vectors" in (_NPZ_INDEX or {})
    n = int(_NPZ_INDEX["vectors"].shape[0]) if npz else 0
    return {
        "pgvector_configured": pg,
        "npz_index_loaded": npz,
        "npz_chunk_count": n,
        "active_backend": "pgvector" if pg else ("npz" if npz else "none"),
    }


def _embed_query(query: str) -> np.ndarray | None:
    if not _OPENAI_FACTORY:
        return None
    try:
        oai = _OPENAI_FACTORY()
        resp = oai.embeddings.create(model=_EMBED_MODEL, input=[query])
        q = np.array(resp.data[0].embedding, dtype=np.float32)
        norm = float(np.linalg.norm(q))
        if norm > 0:
            q /= norm
        return q
    except Exception:
        return None


def _search_pgvector(
    q_vec: np.ndarray,
    journal: str | None,
    section: str | None,
    top_k: int,
) -> list[dict[str, Any]]:
    try:
        import psycopg
        from pgvector.psycopg import register_vector
    except ImportError:
        return []

    vec_list = q_vec.astype(np.float32).tolist()
    sql = """
        SELECT
            pc.text,
            pc.section,
            pc.ordinal,
            p.pmid,
            j.key AS journal_key,
            p.title,
            1 - (pc.embedding <=> %s::vector) AS similarity
        FROM paper_chunks pc
        JOIN papers p ON p.id = pc.paper_id
        JOIN journals j ON j.id = p.journal_id
        WHERE pc.embedding IS NOT NULL
    """
    params: list[Any] = [vec_list]
    if journal:
        sql += " AND j.key = %s"
        params.append(journal)
    if section:
        sql += " AND pc.section = %s"
        params.append(section)
    sql += " ORDER BY pc.embedding <=> %s::vector LIMIT %s"
    params.extend([vec_list, top_k])

    try:
        with psycopg.connect(_PG_DSN, connect_timeout=4) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
    except Exception:
        return []

    out: list[dict[str, Any]] = []
    for row in rows:
        text, sec, ordinal, pmid, jkey, title, sim = row
        if not text or not pmid:
            continue
        out.append({
            "text": str(text),
            "section": str(sec or ""),
            "ordinal": int(ordinal or 0),
            "pmid": str(pmid),
            "journal": str(jkey or ""),
            "title": str(title or ""),
            "similarity": round(float(sim), 4),
            "source": "pgvector",
        })
    return out


def _search_npz(
    q_vec: np.ndarray,
    journal: str | None,
    section: str | None,
    top_k: int,
) -> list[dict[str, Any]]:
    if _NPZ_INDEX is None:
        return []
    vecs: np.ndarray = _NPZ_INDEX["vectors"]
    scores: np.ndarray = vecs @ q_vec
    mask = np.ones(len(scores), dtype=bool)
    if journal:
        mask &= (_NPZ_INDEX["journals"] == journal)
    if section:
        mask &= (_NPZ_INDEX["sections"] == section)
    filtered = np.where(mask, scores, -2.0)
    top_idx = np.argsort(filtered)[::-1][:top_k]
    out: list[dict[str, Any]] = []
    for idx in top_idx:
        sim = float(filtered[idx])
        if sim < -1.0:
            break
        out.append({
            "text": str(_NPZ_INDEX["texts"][idx]),
            "section": str(_NPZ_INDEX["sections"][idx]),
            "ordinal": int(_NPZ_INDEX["ordinals"][idx]),
            "pmid": str(_NPZ_INDEX["pmids"][idx]),
            "journal": str(_NPZ_INDEX["journals"][idx]),
            "similarity": round(sim, 4),
            "source": "npz_index",
        })
    return out


def search_chunks(
    query: str,
    *,
    journal: str | None = None,
    section: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Cosine-similarity search over embedded paragraph chunks.
    Returns chunk text inline (no secondary file lookup required).
    """
    q_vec = _embed_query(query)
    if q_vec is None:
        return []

    if _PG_DSN:
        hits = _search_pgvector(q_vec, journal, section, top_k)
        if hits:
            return hits

    return _search_npz(q_vec, journal, section, top_k)


def aggregate_chunks_to_papers(
    hits: list[dict[str, Any]],
    *,
    kind: str,
    max_papers: int,
) -> list[dict[str, str]]:
    """
    Group vector hits by PMID into pseudo full-text papers for style learning.
    Uses chunk text from the vector store only.
    """
    by_pmid: dict[str, list[dict[str, Any]]] = {}
    for h in hits:
        pmid = h.get("pmid") or ""
        if not pmid:
            continue
        by_pmid.setdefault(pmid, []).append(h)

    papers: list[dict[str, str]] = []
    for pmid, chunks in list(by_pmid.items())[:max_papers]:
        chunks.sort(key=lambda c: (c.get("section", ""), c.get("ordinal", 0)))
        body = "\n\n".join(c["text"] for c in chunks if c.get("text"))
        if len(body) < 400:
            continue
        title = chunks[0].get("title") or f"Corpus PMID {pmid}"
        jkey = chunks[0].get("journal", "")
        papers.append({
            "title": str(title),
            "text": body[:120_000],
            "kind": kind,
            "source": chunks[0].get("source", "vector_index"),
            "pmid": pmid,
            "corpus_journal": str(jkey),
        })
    return papers
