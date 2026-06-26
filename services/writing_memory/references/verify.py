"""
Reference verification — the anti-hallucination layer.

What it does
------------
Given (1) a topic phrase Claude wrote and (2) a candidate PubMed record we
retrieved from eutils, this module produces a *verification verdict*:

  verified      — title + abstract clearly matches the topic
  partial       — moderate semantic overlap; show with caution
  unverified    — no evidence the record matches what Claude meant
  conflict      — PMID and DOI point to different records

The decision uses two signals, both rule-based:
  1. Embedding similarity (OpenAI `text-embedding-3-small`) between the
     topic phrase and `title + first 600 chars of abstract`.
  2. PMID ↔ DOI cross-check via CrossRef (when DOI is present).

No LLM is allowed to make the verification call.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import numpy as np

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]

from .crossref_client import lookup_doi
from .pubmed_client   import PubMedRecord

# ---------------------------------------------------------------------------
# Thresholds (frozen constants — calibrate against a golden set later)
# ---------------------------------------------------------------------------

VERIFY_THRESHOLD  = 0.55   # ≥ → verified
PARTIAL_THRESHOLD = 0.40   # ≥ but < verify → partial
# below partial → unverified

# Year-bound sanity: if Claude asks about 2024 and the record is 1985, downgrade.
# Set None to disable.
MAX_YEAR_DRIFT = None  # currently disabled; topic phrases rarely encode years


# ---------------------------------------------------------------------------
# OpenAI client (lazy, shared)
# ---------------------------------------------------------------------------

_oai = None


def _get_oai():
    global _oai
    if _oai is None:
        if OpenAI is None:
            raise RuntimeError("openai package not installed")
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set; reference verification disabled")
        _oai = OpenAI(api_key=key)
    return _oai


def _embed(texts: list[str]) -> np.ndarray:
    """Embed a list of strings; returns L2-normalised (N, 1536) array."""
    oai = _get_oai()
    resp = oai.embeddings.create(model="text-embedding-3-small", input=texts)
    vecs = np.array([d.embedding for d in resp.data], dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


# ---------------------------------------------------------------------------
# Public model
# ---------------------------------------------------------------------------

@dataclass
class VerificationResult:
    verdict:      str             # 'verified' | 'partial' | 'unverified' | 'conflict'
    similarity:   float
    reason:       str
    title_match:  bool = False
    doi_match:    bool | None = None
    crossref_record: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict":         self.verdict,
            "similarity":      round(float(self.similarity), 4),
            "reason":          self.reason,
            "title_match":     self.title_match,
            "doi_match":       self.doi_match,
            "crossref_record": self.crossref_record,
        }


# ---------------------------------------------------------------------------
# Embedding similarity
# ---------------------------------------------------------------------------

def _record_text(rec: PubMedRecord) -> str:
    """Concatenate the title + truncated abstract for embedding."""
    abstract = (rec.abstract or "")[:600]
    return f"{rec.title}\n\n{abstract}".strip()


def topic_record_similarity(topic: str, rec: PubMedRecord) -> float:
    """Cosine similarity between Claude's topic phrase and the article."""
    if not topic.strip() or not rec.title.strip():
        return 0.0
    vecs = _embed([topic, _record_text(rec)])
    return float(vecs[0] @ vecs[1])


def batch_score(topic: str, records: list[PubMedRecord]) -> list[float]:
    """Score many records in a single embedding call (cheaper)."""
    if not records:
        return []
    texts = [topic] + [_record_text(r) for r in records]
    vecs  = _embed(texts)
    q     = vecs[0]
    return [float(q @ v) for v in vecs[1:]]


# ---------------------------------------------------------------------------
# Title token Jaccard (heuristic fallback when embeddings unavailable)
# ---------------------------------------------------------------------------

_STOP = {"the","a","an","and","or","of","in","on","for","to","with","by","from",
         "is","are","was","were","be","been","being","this","that","these","those"}

def _tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[A-Za-z0-9]{3,}", s.lower()) if w not in _STOP}


def title_jaccard(topic: str, title: str) -> float:
    a, b = _tokens(topic), _tokens(title)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------------------
# Main verification entry point
# ---------------------------------------------------------------------------

def verify_record(
    topic:               str,
    record:              PubMedRecord,
    similarity_score:    float | None = None,
    cross_check_doi:     bool = True,
) -> VerificationResult:
    """
    Verify that `record` is a genuine match for the topic phrase Claude
    requested.  Combines:

      a) Embedding similarity (or computes one if not given)
      b) Optional DOI cross-check via CrossRef

    Returns one of: verified | partial | unverified | conflict.
    """
    # 1) Similarity
    if similarity_score is None:
        try:
            similarity_score = topic_record_similarity(topic, record)
        except RuntimeError:
            similarity_score = title_jaccard(topic, record.title)

    title_match = title_jaccard(topic, record.title) > 0.15

    # 2) DOI cross-check (only if we have a DOI and the caller wants it)
    doi_match: bool | None = None
    crossref_dict: dict[str, Any] | None = None
    if cross_check_doi and record.doi:
        cr = lookup_doi(record.doi)
        if cr is None:
            doi_match = False
        else:
            crossref_dict = cr.as_dict()
            j1 = title_jaccard(record.title, cr.title)
            doi_match = j1 >= 0.4

    # 3) Decide verdict
    if doi_match is False and record.doi:
        return VerificationResult(
            verdict="conflict",
            similarity=similarity_score,
            reason=f"PMID claims DOI {record.doi} but CrossRef record disagrees.",
            title_match=title_match,
            doi_match=False,
            crossref_record=crossref_dict,
        )

    if similarity_score >= VERIFY_THRESHOLD:
        return VerificationResult(
            verdict="verified",
            similarity=similarity_score,
            reason=f"Strong semantic match (cos={similarity_score:.2f}).",
            title_match=title_match,
            doi_match=doi_match,
            crossref_record=crossref_dict,
        )

    if similarity_score >= PARTIAL_THRESHOLD:
        return VerificationResult(
            verdict="partial",
            similarity=similarity_score,
            reason=f"Moderate match (cos={similarity_score:.2f}); show with caution.",
            title_match=title_match,
            doi_match=doi_match,
            crossref_record=crossref_dict,
        )

    return VerificationResult(
        verdict="unverified",
        similarity=similarity_score,
        reason=f"No strong evidence (cos={similarity_score:.2f}).",
        title_match=title_match,
        doi_match=doi_match,
        crossref_record=crossref_dict,
    )


# ---------------------------------------------------------------------------
# Citation placeholder extraction
# ---------------------------------------------------------------------------

# Claude is required to emit citations as [CITE: topic phrase here]
# This module extracts those — we never trust Claude to emit a PMID or DOI.

_CITE_RE = re.compile(r"\[CITE:\s*(.+?)\s*\]")


def extract_cite_placeholders(text: str) -> list[str]:
    """Return the topic phrase inside each [CITE: …] occurrence."""
    return [m.group(1).strip() for m in _CITE_RE.finditer(text)]


def replace_cite_with_marker(text: str, replacements: list[str]) -> str:
    """
    Replace each [CITE: …] in order with the strings in `replacements`
    (must be the same length).  Used by /insert_citations to substitute
    in the rendered in-text citation (e.g. "[1]" or "(Smith et al., 2024)").
    """
    iterator = iter(replacements)
    return _CITE_RE.sub(lambda _m: next(iterator, "[CITE]"), text)
