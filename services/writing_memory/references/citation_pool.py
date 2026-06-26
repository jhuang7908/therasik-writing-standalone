"""
SmartCitationPool — multi-pass citation building strategy.

Three-pass design:
  P1  Seed Search     : author-context keywords → PubMed → seed papers
                        + related-article expansion (elink snowball)
  P2  Scoring Matrix  : relevance × recency × authority → keep top (target×1.5)
  P3  Claim Match     : assign pool candidates to [CITE:…] placeholders;
                        targeted deep-search for unmatched claims (~20-30%)

Reference target counts are derived from JOURNAL_CONSTRAINTS (app.py) by article
type and journal.  Pool is built to 1.5× that ceiling, then culled by total score.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

import datetime

# ---------------------------------------------------------------------------
# Journal authority lookup  (name fragment → 0–5 tier)
# ---------------------------------------------------------------------------
_JOURNAL_AUTHORITY: dict[str, float] = {
    "nature":           5.0,
    "science":          5.0,
    "cell":             5.0,
    "nat med":          4.8,
    "nat commun":       4.5,
    "nat methods":      4.7,
    "nat biotechnol":   4.7,
    "nat immunol":      4.8,
    "nejm":             5.0,
    "n engl j med":     5.0,
    "lancet":           4.9,
    "jama":             4.8,
    "bmj":              4.6,
    "pnas":             4.2,
    "proc natl acad":   4.2,
    "elife":            4.0,
    "plos med":         3.8,
    "plos one":         3.5,
    "j clin invest":    4.3,
    "immunity":         4.5,
    "j immunol":        3.8,
    "nucleic acids":    4.2,
    "genome biol":      4.3,
    "bioinformatics":   3.7,
    "cancer res":       4.0,
    "blood":            4.3,
    "gut":              4.5,
    "hepatology":       4.4,
    "brain":            4.2,
}

# Reference target ceiling by journal × article_type (mirrors JOURNAL_CONSTRAINTS in app.py)
_REFERENCE_CEILINGS: dict[str, dict[str, int]] = {
    "generic":  {"research": 60, "review": 100, "case_report": 30, "letter": 15},
    "pnas":     {"research": 50, "review": 100, "case_report": 30, "letter": 10},
    "elife":    {"research": 80, "review": 150, "case_report": 40, "letter": 15},
    "plos_med": {"research": 60, "review":  80, "case_report": 20, "letter": 12},
}

# Current year for recency calculation
_BASE_YEAR = datetime.date.today().year


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CitationCandidate:
    pmid:             str
    title:            str
    abstract:         str
    year:             int | None
    journal:          str
    authors:          list[tuple[str, str]]   # (last_name, initials)
    doi:              str | None
    pmcid:            str | None
    relevance_score:  float = 0.0
    recency_score:    float = 0.0
    authority_score:  float = 0.0
    total_score:      float = 0.0

    def compute_total(
        self,
        w_rel: float = 0.50,
        w_rec: float = 0.25,
        w_aut: float = 0.25,
    ) -> None:
        self.total_score = (
            w_rel * self.relevance_score
            + w_rec * self.recency_score
            + w_aut * self.authority_score
        )


@dataclass
class CitationAssignment:
    claim_text: str
    candidate:  CitationCandidate | None
    similarity: float
    source:     str   # "pool" | "targeted_search" | "unresolved"


@dataclass
class CitationPool:
    candidates:        list[CitationCandidate]     # top-scored candidates (≤ pool_target)
    claim_assignments: list[CitationAssignment]    # one per [CITE:] placeholder
    pool_size:         int
    target_count:      int
    stats:             dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_citation_pool(
    claims:          list[str],
    author_context:  str,
    journal:         str = "generic",
    article_type:    str = "research",
    target_count:    int | None = None,
    excluded_pmids:  set[str] | None = None,
) -> CitationPool:
    """
    Build a scored citation pool and assign claims to candidates.

    Parameters
    ----------
    claims          : list of [CITE: …] topic strings extracted from draft prose
    author_context  : free-text blending of the plan's research_statement,
                      background, key_findings, and significance fields
    journal         : journal key (e.g. "pnas", "elife")
    article_type    : "research" | "review" | "case_report" | "letter"
    target_count    : max references allowed (defaults to journal ceiling)
    excluded_pmids  : set of PMIDs to unconditionally exclude (blind benchmark)
    """
    from .pubmed_client import search_and_fetch
    from .verify import batch_score

    _excl: set[str] = excluded_pmids or set()

    # ── ceiling & pool target ───────────────────────────────────────────────
    ceil_map  = _REFERENCE_CEILINGS.get(journal, _REFERENCE_CEILINGS["generic"])
    ceiling   = target_count or ceil_map.get(article_type, 60)
    pool_target = max(int(ceiling * 1.5), 20)   # build 50 % more than needed

    seen_pmids: set[str] = set()
    all_candidates: list[CitationCandidate] = []

    # ── Pass 1a: seed search on author context ──────────────────────────────
    seed_query = _build_seed_query(author_context, article_type)
    try:
        seed_recs = search_and_fetch(query=seed_query, max_results=15)
    except Exception:
        seed_recs = []

    for rec in seed_recs:
        if rec.pmid and rec.pmid not in seen_pmids and rec.pmid not in _excl:
            seen_pmids.add(rec.pmid)
            all_candidates.append(_rec_to_candidate(rec))

    # ── Pass 1b: claim-level mini-searches (diversify topics) ───────────────
    for claim in claims[:8]:   # first 8 claims only to bound API cost
        try:
            recs = search_and_fetch(query=claim[:250], max_results=5)
            for rec in recs:
                if rec.pmid and rec.pmid not in seen_pmids and rec.pmid not in _excl:
                    seen_pmids.add(rec.pmid)
                    all_candidates.append(_rec_to_candidate(rec))
        except Exception:
            pass

    # ── Pass 1c: related-article snowball from top seed PMIDs ──────────────
    seed_pmids = [c.pmid for c in all_candidates[:5] if c.pmid]
    related_recs = _fetch_related_articles(seed_pmids)
    for rec in related_recs:
        if rec.pmid and rec.pmid not in seen_pmids and rec.pmid not in _excl:
            seen_pmids.add(rec.pmid)
            all_candidates.append(_rec_to_candidate(rec))

    # ── Pass 2: score the full candidate pool ──────────────────────────────
    context_blob = (author_context + " " + " ".join(claims)).strip()
    try:
        _FakeRec = _make_fake_rec_class()
        fake_recs = [_FakeRec(c.title, c.abstract, c.pmid) for c in all_candidates]
        rel_scores = batch_score(context_blob, fake_recs)
    except Exception:
        rel_scores = [0.4] * len(all_candidates)

    for cand, rel in zip(all_candidates, rel_scores):
        cand.relevance_score  = float(rel)
        cand.recency_score    = _recency_score(cand.year)
        cand.authority_score  = _authority_score(cand.journal)
        cand.compute_total()

    # Keep top pool_target by total score
    all_candidates.sort(key=lambda c: c.total_score, reverse=True)
    pool = all_candidates[:pool_target]

    # ── Pass 3: match claims to pool candidates ──────────────────────────────
    assignments: list[CitationAssignment] = []
    for claim in claims:
        assignment = _match_claim_to_pool(claim, pool, batch_score)
        if assignment.source == "unresolved":
            # Targeted deep search for differentiated / novel content
            assignment = _targeted_deep_search(claim)
        assignments.append(assignment)

    resolved_pool      = sum(1 for a in assignments if a.source == "pool")
    resolved_targeted  = sum(1 for a in assignments if a.source == "targeted_search")
    unresolved         = sum(1 for a in assignments if a.source == "unresolved")

    return CitationPool(
        candidates=pool,
        claim_assignments=assignments,
        pool_size=len(pool),
        target_count=ceiling,
        stats={
            "seed_records":        len(seed_recs),
            "claim_mini_searches": min(len(claims), 8),
            "related_expanded":    len(related_recs),
            "total_candidates":    len(all_candidates),
            "pool_size":           len(pool),
            "pool_target":         pool_target,
            "ceiling":             ceiling,
            "claims_total":        len(claims),
            "resolved_from_pool":  resolved_pool,
            "resolved_targeted":   resolved_targeted,
            "unresolved":          unresolved,
            "differentiated_pct":  round(100 * resolved_targeted / max(len(claims), 1), 1),
        },
    )


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _recency_score(year: int | None, half_life: int = 5) -> float:
    """Exponential decay: current year = 1.0, halves every `half_life` years."""
    if not year:
        return 0.3
    age = max(0, _BASE_YEAR - year)
    return math.exp(-math.log(2) * age / half_life)


def _authority_score(journal_name: str) -> float:
    """0.0–1.0 authority based on journal tier table."""
    jl = (journal_name or "").lower().strip()
    for fragment, tier in _JOURNAL_AUTHORITY.items():
        if fragment in jl:
            return tier / 5.0
    return 0.40   # unknown journal → modest default


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_seed_query(context: str, article_type: str) -> str:
    """
    Build a PubMed query from the author context.
    For review articles, append Review[pt] filter.
    """
    stopwords = {
        "the", "a", "an", "of", "in", "and", "or", "to", "for", "with", "by",
        "this", "that", "we", "our", "is", "are", "was", "were", "from", "at",
        "on", "as", "be", "have", "has", "it", "its", "not", "but", "also",
        "which", "their", "these", "those", "study", "studies", "paper", "show",
        "showed", "found", "result", "results", "using", "used", "between",
    }
    words = re.findall(r"[a-zA-Z]{4,}", context)
    keywords = [w.lower() for w in words if w.lower() not in stopwords]
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for w in keywords:
        if w not in seen:
            seen.add(w)
            unique.append(w)
        if len(unique) >= 10:
            break

    query = " AND ".join(f'"{kw}"' for kw in unique[:6])
    if article_type == "review":
        query += " AND Review[pt]"
    return query or context[:200]


def _rec_to_candidate(rec: Any) -> CitationCandidate:
    return CitationCandidate(
        pmid=rec.pmid or "",
        title=rec.title or "",
        abstract=getattr(rec, "abstract", "") or "",
        year=rec.year,
        journal=getattr(rec, "journal_abbrev", None) or rec.journal or "",
        authors=rec.authors or [],
        doi=rec.doi,
        pmcid=getattr(rec, "pmcid", None),
    )


def _make_fake_rec_class():
    """Return a lightweight object compatible with batch_score's expected interface."""
    class FakeRec:
        def __init__(self, title: str, abstract: str, pmid: str):
            self.title    = title
            self.abstract = abstract
            self.pmid     = pmid
    return FakeRec


def _fetch_related_articles(pmids: list[str], max_per_seed: int = 8) -> list[Any]:
    """
    Use PubMed elink (pubmed_pubmed) to find similar articles from seed PMIDs.
    Returns PubMedRecord objects (same type as search_and_fetch returns).
    """
    if not pmids:
        return []
    try:
        import urllib.request
        import xml.etree.ElementTree as ET

        ids = ",".join(pmids)
        url = (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
            f"?dbfrom=pubmed&db=pubmed&linkname=pubmed_pubmed&id={ids}"
            "&retmode=xml&tool=insynbio_wm&email=api@insynbio.com"
        )
        with urllib.request.urlopen(url, timeout=12) as r:
            xml_bytes = r.read()
        root = ET.fromstring(xml_bytes)

        linked_ids: list[str] = []
        for link_set_db in root.findall(".//LinkSetDb"):
            for link in link_set_db.findall("Link/Id"):
                if link.text and link.text not in pmids:
                    linked_ids.append(link.text)

        linked_ids = list(dict.fromkeys(linked_ids))[:max_per_seed * len(pmids)]
        if not linked_ids:
            return []

        from .pubmed_client import search_and_fetch
        pmid_query = " OR ".join(f"{pid}[pmid]" for pid in linked_ids[:20])
        return search_and_fetch(query=pmid_query, max_results=min(len(linked_ids), 20))
    except Exception:
        return []


def _match_claim_to_pool(
    claim: str,
    pool: list[CitationCandidate],
    batch_score_fn: Any,
    threshold: float = 0.55,
) -> CitationAssignment:
    """
    Score the claim against every pool candidate and return the best match,
    or an 'unresolved' assignment if no candidate clears the threshold.
    """
    if not pool:
        return CitationAssignment(claim_text=claim, candidate=None, similarity=0.0, source="unresolved")
    try:
        FakeRec = _make_fake_rec_class()
        fake_recs = [FakeRec(c.title, c.abstract, c.pmid) for c in pool]
        scores = batch_score_fn(claim, fake_recs)
        if not scores:
            return CitationAssignment(claim_text=claim, candidate=None, similarity=0.0, source="unresolved")
        best_idx = max(range(len(scores)), key=lambda i: scores[i])
        best_sim = float(scores[best_idx])
        if best_sim >= threshold:
            return CitationAssignment(
                claim_text=claim,
                candidate=pool[best_idx],
                similarity=best_sim,
                source="pool",
            )
    except Exception:
        pass
    return CitationAssignment(claim_text=claim, candidate=None, similarity=0.0, source="unresolved")


def _targeted_deep_search(claim: str) -> CitationAssignment:
    """
    Targeted deep search for differentiated / novel claims that have no pool match.
    Uses a lower threshold (0.45) since the claim is already specific.
    This handles the ~20–30% of novel content citations.
    """
    try:
        from .pubmed_client import search_and_fetch
        from .verify import batch_score

        recs = search_and_fetch(query=claim[:300], max_results=10)
        if not recs:
            return CitationAssignment(claim_text=claim, candidate=None, similarity=0.0, source="unresolved")

        FakeRec = _make_fake_rec_class()
        scores = batch_score(claim, [FakeRec(r.title, getattr(r, "abstract", "") or "", r.pmid) for r in recs])
        if not scores:
            return CitationAssignment(claim_text=claim, candidate=None, similarity=0.0, source="unresolved")

        best_idx = max(range(len(scores)), key=lambda i: scores[i])
        best_sim = float(scores[best_idx])
        if best_sim >= 0.45:
            cand = _rec_to_candidate(recs[best_idx])
            cand.relevance_score = best_sim
            return CitationAssignment(
                claim_text=claim,
                candidate=cand,
                similarity=best_sim,
                source="targeted_search",
            )
    except Exception:
        pass
    return CitationAssignment(claim_text=claim, candidate=None, similarity=0.0, source="unresolved")


# ---------------------------------------------------------------------------
# Integration helper: pool → marker map for _insert_citations_pipeline
# ---------------------------------------------------------------------------

def pool_to_marker_map(
    pool: CitationPool,
    style: Any,
    format_in_text_fn: Any,
) -> tuple[dict[str, Any], list[Any]]:
    """
    Convert a CitationPool into the (seen_pmids, chosen_papers) structures
    expected by _insert_citations_pipeline so the pool can hot-swap in.

    Returns
    -------
    assignment_map : dict claim_text → in_text_marker str (or None)
    chosen_papers  : ordered list of Paper objects for reference list
    """
    from .citation_pool import CitationCandidate

    chosen_papers: list[Any] = []
    seen_pmids: dict[str, int] = {}   # pmid → 1-based index
    assignment_map: dict[str, str | None] = {}

    for asn in pool.claim_assignments:
        cand: CitationCandidate | None = asn.candidate
        if cand is None:
            assignment_map[asn.claim_text] = None
            continue
        if cand.pmid in seen_pmids:
            idx = seen_pmids[cand.pmid]
        else:
            from ..journal_specs.format_reference import Author, Paper
            authors = [Author(last=last, initials=init) for last, init in (cand.authors or [])]
            paper = Paper(
                authors=authors,
                title=cand.title,
                journal=cand.journal,
                year=cand.year,
                doi=cand.doi,
                pmid=cand.pmid,
                pmcid=cand.pmcid,
            )
            chosen_papers.append(paper)
            idx = len(chosen_papers)
            seen_pmids[cand.pmid] = idx

        marker = format_in_text_fn(chosen_papers[idx - 1], style, index=idx)
        assignment_map[asn.claim_text] = marker

    return assignment_map, chosen_papers
