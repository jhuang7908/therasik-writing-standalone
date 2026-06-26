"""
Supplement customer uploads via semantic search on the vector index.

Retrieval goes directly to pgvector (when WRITING_MEMORY_PG is set) or the
in-memory embeddings/index.npz — not a scan of papers_raw JSON files.
"""

from __future__ import annotations

from typing import Any

from .vector_store import aggregate_chunks_to_papers, search_chunks

IDEAL_TARGET_FILL = 5
IDEAL_SIMILAR_FILL = 5


def fetch_corpus_supplement(
    *,
    journal_display_name: str,
    linked_journal_key: str | None,
    target_need: int,
    similar_need: int,
    find_similar: Any | None = None,
    seed_query: str | None = None,
) -> list[dict[str, str]]:
    """
    Pull style exemplars from the vector corpus (pgvector or npz index).

    ``find_similar`` is ignored (legacy param); search uses ``vector_store``.
    """
    del find_similar  # unified vector_store path

    primary_journal = None
    if linked_journal_key in ("pnas", "elife", "plos_med"):
        primary_journal = linked_journal_key

    target_query = (
        f"{journal_display_name} scientific research article discussion writing style"
    )
    similar_query = seed_query or (
        f"{journal_display_name} related biomedical research narrative style"
    )

    out: list[dict[str, str]] = []

    if target_need > 0:
        hits = search_chunks(
            target_query,
            journal=primary_journal,
            section="discussion",
            top_k=target_need * 6,
        )
        if not hits:
            hits = search_chunks(target_query, journal=primary_journal, top_k=target_need * 6)
        out.extend(
            aggregate_chunks_to_papers(hits, kind="corpus_target", max_papers=target_need)
        )

    if similar_need > 0:
        hits = search_chunks(similar_query, journal=None, section="discussion", top_k=similar_need * 6)
        if not hits:
            hits = search_chunks(similar_query, top_k=similar_need * 6)
        out.extend(
            aggregate_chunks_to_papers(hits, kind="corpus_similar", max_papers=similar_need)
        )

    return out
