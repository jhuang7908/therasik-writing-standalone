"""Map PubMed metadata + title → canonical article_type id."""

from __future__ import annotations

import re
from typing import Any

from ..article_type_context import canonical_article_type

# PubMed PublicationType → canonical (first match wins)
_PUBTYPE_MAP: list[tuple[str, str]] = [
    ("systematic review", "systematic_review"),
    ("meta-analysis", "systematic_review"),
    ("review", "review_narrative"),
    ("case reports", "case_report"),
    ("case report", "case_report"),
    ("clinical trial", "clinical_trial"),
    ("randomized controlled trial", "clinical_trial"),
    ("controlled clinical trial", "clinical_trial"),
    ("clinical study", "clinical_trial"),
    ("letter", "brief_communication"),
    ("comment", "perspective"),
    ("editorial", "perspective"),
    ("introductory journal article", "perspective"),
    ("published erratum", "negative_results"),
    ("evaluation study", "original_research"),
    ("validation study", "methods_protocols"),
    ("research support", "original_research"),
    ("journal article", "original_research"),
]

_TITLE_RULES: list[tuple[str, str]] = [
    (r"\bsystematic review\b", "systematic_review"),
    (r"\bmeta-?analysis\b", "systematic_review"),
    (r"\bprisma\b", "systematic_review"),
    (r"\bcase report\b", "case_report"),
    (r"\bprotocol\b", "methods_protocols"),
    (r"\bstandard operating\b", "methods_protocols"),
    (r"\bperspective\b", "perspective"),
    (r"\bcommentary\b", "perspective"),
    (r"\bhypothesis\b", "hypothesis"),
    (r"\bnegative result", "negative_results"),
    (r"\bresource\b", "resource_paper"),
    (r"\btranslational\b", "translational_drug_discovery"),
    (r"\breview\b", "review_narrative"),
]


def classify_article_type(
    *,
    title: str = "",
    pub_types: list[str] | None = None,
    seed_type: str | None = None,
) -> dict[str, Any]:
    """
    Return {canonical, source, confidence}.
    seed_type from SEED_FAMOUS overrides when provided.
    """
    if seed_type:
        return {
            "canonical": canonical_article_type(seed_type),
            "source": "seed_manifest",
            "confidence": "high",
        }

    title_l = (title or "").lower()
    for pat, ctype in _TITLE_RULES:
        if re.search(pat, title_l):
            return {
                "canonical": ctype,
                "source": "title_regex",
                "confidence": "medium",
            }

    for pt in pub_types or []:
        pl = pt.lower()
        for needle, ctype in _PUBTYPE_MAP:
            if needle in pl:
                return {
                    "canonical": ctype,
                    "source": "pubmed_publication_type",
                    "confidence": "high" if needle != "journal article" else "low",
                }

    return {
        "canonical": "original_research",
        "source": "default",
        "confidence": "low",
    }
