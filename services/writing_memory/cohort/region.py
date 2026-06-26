"""Prefer US/UK English-language journal sources for cohort exemplars."""

from __future__ import annotations

import re

# NLM journal abbrev / title fragments strongly associated with US/UK venues
_UK_US_MARKERS = (
    r"proc natl acad sci",
    r"\bpnas\b",
    r"elife",
    r"elifesciences",
    r"plos med",
    r"plos medicine",
    r"\bnature\b",
    r"n engl j med",
    r"\bnejm\b",
    r"\blancet\b",
    r"\bbmj\b",
    r"british medical",
    r"\bscience\b",
    r"\bcell\b",
    r"plos biol",
    r"plos one",
    r"genome res",
    r"nucl acids res",
    r"j immunol",
    r"blood",
    r"cancer cell",
    r"cancer discov",
    r"nat med",
    r"nat biotechnol",
    r"nat commun",
    r"sci transl med",
    r"sci immunol",
    r"immunity",
    r"mol cell",
    r"dev cell",
    r"curr biol",
    r"emboj",
    r"embo j",
)

_NON_UK_US_MARKERS = (
    r"\bchina\b",
    r"chinese",
    r"japan",
    r"japanese",
    r"korean",
    r"indian j",
    r"braz",
    r"revista",
)


def score_uk_us_source(journal: str = "", journal_abbrev: str = "") -> dict:
    """
    Return {pass: bool, score: 0-1, reason: str}.
    pass=True when journal looks US/UK English-medium.
    """
    blob = f"{journal} {journal_abbrev}".lower()
    if not blob.strip():
        return {"pass": False, "score": 0.0, "reason": "missing_journal"}

    for pat in _NON_UK_US_MARKERS:
        if re.search(pat, blob):
            return {"pass": False, "score": 0.2, "reason": f"non_uk_us_marker:{pat}"}

    hits = sum(1 for pat in _UK_US_MARKERS if re.search(pat, blob))
    if hits:
        sc = min(1.0, 0.55 + 0.15 * hits)
        return {"pass": True, "score": sc, "reason": f"uk_us_hits:{hits}"}

    if re.search(r"\b(j|journal)\s", blob) or len(blob) > 8:
        return {"pass": True, "score": 0.45, "reason": "english_journal_unlisted"}

    return {"pass": False, "score": 0.3, "reason": "unknown_journal"}
