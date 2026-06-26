"""
similar_search.py
=================
TheraSIK Similar Article Search

Finds papers in the local literature database that are semantically similar
to a query text (abstract, paragraph, or full manuscript section) using:

  1. TF-IDF cosine similarity (fast, always available)
  2. BM25 term-frequency ranking (better for short queries)
  3. Keyword overlap with title boosting

No external API calls required — works entirely against the local SQLite DB.

Usage (CLI):
  python scripts/similar_search.py "CAR-T therapy AML relapsed refractory"
  python scripts/similar_search.py --file path/to/abstract.txt --top 20
  python scripts/similar_search.py --project path/to/project_dir

Programmatic:
  from similar_search import find_similar_papers, find_by_abstract
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

SKILL_DIR = Path(os.environ.get("THERASIK_DIR", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(SKILL_DIR / "scripts"))

try:
    import literature_db as litdb
except ImportError:
    litdb = None  # type: ignore

DEFAULT_DB = SKILL_DIR / "assets" / "literature.db"


# ── Text processing ───────────────────────────────────────────────────────────

STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
    "has", "have", "had", "this", "that", "these", "those", "we", "our",
    "their", "it", "its", "as", "not", "no", "also", "although", "however",
    "thus", "therefore", "which", "who", "can", "may", "might", "should",
    "could", "would", "will", "than", "then", "when", "while", "since",
    "after", "before", "between", "during", "both", "each", "all", "only",
    "more", "most", "such", "into", "through", "over", "under", "et", "al",
    "study", "studies", "patients", "results", "methods", "conclusion",
    "background", "objective", "introduction", "discussion",
})


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", " ", text)
    tokens = re.findall(r"\b[a-z][a-z0-9-]{1,}\b", text)
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]


def _ngrams(tokens: list[str], n: int = 2) -> list[str]:
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]


def _term_freq(tokens: list[str]) -> dict[str, float]:
    if not tokens:
        return {}
    c = Counter(tokens)
    total = len(tokens)
    return {t: c[t] / total for t in c}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) & set(b)
    if not keys:
        return 0.0
    dot  = sum(a[k] * b[k] for k in keys)
    na   = math.sqrt(sum(v*v for v in a.values()))
    nb   = math.sqrt(sum(v*v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _bm25_score(query_terms: list[str], doc_tokens: list[str],
                avg_dl: float = 200.0, k1: float = 1.5, b: float = 0.75) -> float:
    tf_map = Counter(doc_tokens)
    dl     = len(doc_tokens)
    score  = 0.0
    for term in set(query_terms):
        tf = tf_map.get(term, 0)
        if tf == 0:
            continue
        numerator   = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * dl / max(1, avg_dl))
        score += numerator / denominator
    return score


# ── Database helpers ──────────────────────────────────────────────────────────

def _get_conn(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB
    if not path.exists():
        raise FileNotFoundError(f"Literature database not found: {path}\nRun add_paper_by_doi or add_paper_by_pmid first.")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _load_all_papers(conn: sqlite3.Connection) -> list[dict]:
    try:
        rows = conn.execute("""
            SELECT paper_id, title, abstract, year, journal, authors, doi, pmid,
                   keywords, full_text
            FROM papers
        """).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _load_tfidf_vectors(conn: sqlite3.Connection) -> dict[str, dict[str, float]]:
    """Load pre-computed TF-IDF vectors if available (stored as JSON blob)."""
    try:
        rows = conn.execute("SELECT paper_id, vector FROM tfidf_cache").fetchall()
        return {r["paper_id"]: json.loads(r["vector"]) for r in rows}
    except Exception:
        return {}


# ── Core search function ──────────────────────────────────────────────────────

def find_similar_papers(
    query: str,
    db_path: str | Path | None = None,
    top_k: int = 10,
    min_score: float = 0.05,
    boost_title: float = 2.0,
    use_ngrams: bool = True,
    year_from: int | None = None,
    year_to:   int | None = None,
    journal_filter: str | None = None,
) -> list[dict]:
    """
    Find papers similar to a query text using TF-IDF cosine similarity + BM25.

    Args:
        query:          Query text (abstract, paragraph, keywords, or full text).
        db_path:        Override default database path.
        top_k:          Number of top results to return (default 10).
        min_score:      Minimum similarity score threshold (0–1).
        boost_title:    Multiplier applied to title term matches (default 2.0).
        use_ngrams:     Include bigrams in similarity scoring (default True).
        year_from:      Filter to papers published from this year onward.
        year_to:        Filter to papers published up to this year.
        journal_filter: Case-insensitive substring filter on journal name.

    Returns:
        List of paper dicts with added 'similarity_score', 'match_terms',
        sorted by descending similarity.
    """
    conn = _get_conn(db_path)
    papers = _load_all_papers(conn)

    if not papers:
        return []

    # Tokenize query
    q_tokens = _tokenize(query)
    if use_ngrams:
        q_tokens = q_tokens + _ngrams(q_tokens, 2)
    q_tf = _term_freq(q_tokens)

    if not q_tf:
        return []

    # Average document length (for BM25)
    doc_lengths = []
    for p in papers:
        doc_text = " ".join(filter(None, [p.get("title",""), p.get("abstract",""),
                                           p.get("keywords",""), p.get("full_text","")]))
        doc_lengths.append(len(_tokenize(doc_text)))
    avg_dl = sum(doc_lengths) / max(1, len(doc_lengths))

    # Try pre-computed TF-IDF vectors
    cached_vecs = _load_tfidf_vectors(conn)

    results = []
    for i, paper in enumerate(papers):
        # Year filter
        year = paper.get("year")
        if year_from and year and int(year or 0) < year_from:
            continue
        if year_to and year and int(year or 0) > year_to:
            continue
        # Journal filter
        if journal_filter and journal_filter.lower() not in (paper.get("journal") or "").lower():
            continue

        pid = paper.get("paper_id", "")

        # Build document TF-IDF vector
        if pid in cached_vecs:
            doc_tf = cached_vecs[pid]
        else:
            title_tok    = _tokenize(paper.get("title",    "") or "")
            abstract_tok = _tokenize(paper.get("abstract", "") or "")
            kw_tok       = _tokenize(paper.get("keywords", "") or "")
            ft_tok       = _tokenize((paper.get("full_text", "") or "")[:3000])

            # Title tokens are boosted
            all_tokens = (
                title_tok * int(boost_title) +
                abstract_tok +
                kw_tok * 2 +
                ft_tok
            )
            if use_ngrams:
                all_tokens = all_tokens + _ngrams(title_tok, 2) * int(boost_title) + _ngrams(abstract_tok, 2)

            doc_tf = _term_freq(all_tokens)

        # TF-IDF cosine score
        cos_score = _cosine(q_tf, doc_tf)

        # BM25 score (on abstract + title)
        bm25_tokens = _tokenize(
            (paper.get("title", "") or "") + " " + (paper.get("abstract", "") or "")
        )
        bm25_score = _bm25_score(q_tokens, bm25_tokens, avg_dl=avg_dl)
        bm25_norm  = min(1.0, bm25_score / max(1.0, math.sqrt(len(q_tokens)) * 5))

        # Combined score: 60% cosine + 40% BM25
        combined = 0.6 * cos_score + 0.4 * bm25_norm

        if combined < min_score:
            continue

        # Identify matched terms
        match_terms = sorted(
            [t for t in q_tf if t in doc_tf and len(t) > 3],
            key=lambda t: q_tf[t] * doc_tf.get(t, 0),
            reverse=True
        )[:8]

        results.append({
            "paper_id":         pid,
            "title":            paper.get("title", ""),
            "authors":          paper.get("authors", ""),
            "year":             paper.get("year"),
            "journal":          paper.get("journal", ""),
            "doi":              paper.get("doi", ""),
            "pmid":             paper.get("pmid", ""),
            "abstract":         (paper.get("abstract", "") or "")[:300],
            "similarity_score": round(combined, 4),
            "cosine_score":     round(cos_score, 4),
            "bm25_score":       round(bm25_norm, 4),
            "match_terms":      match_terms,
        })

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    conn.close()
    return results[:top_k]


def find_by_abstract(
    abstract: str,
    db_path: str | Path | None = None,
    top_k: int = 10,
) -> list[dict]:
    """Convenience wrapper: find papers similar to an abstract text."""
    return find_similar_papers(abstract, db_path=db_path, top_k=top_k, use_ngrams=True)


def find_by_project(
    project_dir: str | Path,
    db_path: str | Path | None = None,
    top_k: int = 10,
) -> list[dict]:
    """
    Find similar papers using the project's manuscript abstract.

    Args:
        project_dir: Path to manuscript project directory.
        db_path:     Override database path.
        top_k:       Number of top results.

    Returns:
        Sorted list of similar papers.
    """
    proj = Path(project_dir).resolve()

    # Try to get abstract from manuscript
    ms_path = proj / "01_manuscript" / "manuscript.md"
    if not ms_path.exists():
        ms_path = next(proj.rglob("*.md"), None)

    query = ""
    if ms_path and ms_path.exists():
        text = ms_path.read_text(encoding="utf-8")
        # Extract abstract section
        m = re.search(
            r"^#{1,3}\s*Abstract\s*\n(.*?)(?=^#{1,3}\s|\Z)",
            text, re.IGNORECASE | re.MULTILINE | re.DOTALL
        )
        if m:
            query = m.group(1).strip()[:1500]
        else:
            query = text[:1500]

    if not query:
        # Try config title + keywords
        cfg_path = proj / "project_config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            query = cfg.get("title", "") + " " + " ".join(cfg.get("keywords", []))

    if not query:
        return []

    return find_similar_papers(query, db_path=db_path, top_k=top_k)


def keyword_coverage(
    paper_ids: list[str],
    topic: str,
    db_path: str | Path | None = None,
) -> dict:
    """
    Analyse keyword coverage: given a list of paper IDs in the DB and a topic,
    returns which key terms are well-covered and which are missing.

    Args:
        paper_ids: List of paper_ids already in the database.
        topic:     Research topic / query.
        db_path:   Override database path.

    Returns:
        dict with covered_terms, missing_terms, coverage_pct.
    """
    conn    = _get_conn(db_path)
    papers  = _load_all_papers(conn)
    conn.close()

    topic_tokens = set(_tokenize(topic))
    id_set       = set(paper_ids)
    covered      = set()

    for p in papers:
        if p.get("paper_id") not in id_set:
            continue
        doc_tokens = set(_tokenize(
            (p.get("title","") or "") + " " + (p.get("abstract","") or "")
        ))
        covered |= (topic_tokens & doc_tokens)

    missing     = topic_tokens - covered - STOPWORDS
    coverage    = len(covered) / max(1, len(topic_tokens)) * 100

    return {
        "total_topic_terms":    len(topic_tokens),
        "covered_terms":        sorted(covered),
        "missing_terms":        sorted(missing),
        "coverage_pct":         round(coverage, 1),
        "recommendation":       (
            "Coverage adequate." if coverage > 60
            else f"Add papers covering: {', '.join(sorted(missing)[:5])}"
        ),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TheraSIK Similar Article Search")
    parser.add_argument("query", nargs="?", default="", help="Query text")
    parser.add_argument("--file",    help="Read query from a text file")
    parser.add_argument("--project", help="Read query from project abstract")
    parser.add_argument("--db",      help="Override database path")
    parser.add_argument("--top",     type=int, default=10, help="Number of results")
    parser.add_argument("--min",     type=float, default=0.05, help="Min score threshold")
    parser.add_argument("--year-from", type=int, help="Filter papers from year")
    parser.add_argument("--year-to",   type=int, help="Filter papers up to year")
    parser.add_argument("--json",    action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    if args.project:
        results = find_by_project(args.project, db_path=args.db, top_k=args.top)
    else:
        query = args.query
        if args.file:
            query = Path(args.file).read_text(encoding="utf-8")
        if not query:
            parser.error("Provide a query text, --file, or --project")
        results = find_similar_papers(
            query, db_path=args.db, top_k=args.top, min_score=args.min,
            year_from=args.year_from, year_to=args.year_to,
        )

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    if not results:
        print("No similar papers found. Add papers first with add_paper_by_doi/pmid.")
        return

    print(f"\nTop {len(results)} similar papers:\n")
    for i, r in enumerate(results, 1):
        print(f"{i:2d}. [{r['similarity_score']:.3f}] {r['title']}")
        print(f"     {r.get('authors','')[:60]}  {r.get('year','')}  {r.get('journal','')}")
        if r.get("doi"):
            print(f"     DOI: {r['doi']}")
        if r.get("match_terms"):
            print(f"     Terms: {', '.join(r['match_terms'][:5])}")
        print()


if __name__ == "__main__":
    main()
