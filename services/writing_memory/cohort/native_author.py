"""Heuristic: corresponding / senior author likely native English speaker (name + affiliation)."""

from __future__ import annotations

import re
from typing import Any

# Surnames common in East/South Asia — conservative flag (not definitive)
_SURNAME_NON_NATIVE_RE = re.compile(
    r"^(zhang|wang|li|liu|chen|yang|huang|zhao|wu|xu|sun|ma|zhou|zhu|"
    r"lin|tan|gao|luo|he|song|deng|xie|pan|yu|yuan|tang|wei|"
    r"singh|kumar|patel|sharma|gupta|reddy|nguyen|tran|pham|"
    r"tanaka|sato|suzuki|yamamoto|watanabe|ito|nakamura|kobayashi|kim|park|choi|lee)$",
    re.I,
)

_ANGLO_SURNAME_RE = re.compile(
    r"^(smith|jones|williams|brown|taylor|davies|evans|wilson|johnson|"
    r"robinson|thompson|wright|walker|white|hall|green|wood|clark|"
    r"robertson|anderson|murray|scott|watson|harris|lewis|young|"
    r"miller|moore|jackson|martin|lee|king|wright|clarke|harrison|"
    r"mitchell|roberts|cooper|bennett|graham|stewart|foster|butler|"
    r"hamilton|morgan|bell|bailey|cox|ward|turner|hill|adams|"
    r"campbell|kelly|palmer|holmes|marshall|richards|collins|"
    r"baker|nelson|carter|mitchell|parker|edwards|collins|stevens|"
    r"watson|morrison|fraser|mackenzie|mcdonald|macleod|thomson)$",
    re.I,
)

_UK_US_AFFIL_RE = re.compile(
    r"\b(usa|u\.s\.a|united states|uk|u\.k\.|united kingdom|england|"
    r"scotland|wales|cambridge|oxford|london|boston|harvard|stanford|"
    r"mit\b|nih|yale|california|texas|michigan|pennsylvania)\b",
    re.I,
)


def _last_author(authors: list[tuple[str, str]]) -> tuple[str, str] | None:
    if not authors:
        return None
    return authors[-1]


def score_corresponding_author_native(
    authors: list[tuple[str, str]],
    affiliations: list[str] | None = None,
) -> dict[str, Any]:
    """
    Biomedical convention: use **last author** as corresponding-author proxy when
    PubMed does not mark Corresponding=Y.

    Returns:
      pass: True if likely native English-speaking correspondent
      confidence: low | medium | high
      correspondent: {last, initials}
      reason: audit string
    """
    affils = " ; ".join(affiliations or [])
    corr = _last_author(authors)
    if not corr:
        return {
            "pass": False,
            "confidence": "low",
            "correspondent": None,
            "reason": "no_authors",
        }

    last, ini = corr
    last_l = last.lower().strip()

    if _SURNAME_NON_NATIVE_RE.match(last_l):
        if _UK_US_AFFIL_RE.search(affils):
            return {
                "pass": True,
                "confidence": "medium",
                "correspondent": {"last": last, "initials": ini},
                "reason": "non_anglo_surname_but_uk_us_affiliation",
            }
        return {
            "pass": False,
            "confidence": "medium",
            "correspondent": {"last": last, "initials": ini},
            "reason": "surname_heuristic_non_native",
        }

    if _ANGLO_SURNAME_RE.match(last_l):
        return {
            "pass": True,
            "confidence": "high",
            "correspondent": {"last": last, "initials": ini},
            "reason": "anglo_surname_common",
        }

    if _UK_US_AFFIL_RE.search(affils):
        return {
            "pass": True,
            "confidence": "medium",
            "correspondent": {"last": last, "initials": ini},
            "reason": "uk_us_affiliation",
        }

    if re.search(r"(son|sen|ski|ez|ez|mann|berg|stein|strom)$", last_l):
        return {
            "pass": True,
            "confidence": "medium",
            "correspondent": {"last": last, "initials": ini},
            "reason": "european_surname_suffix",
        }

    return {
        "pass": False,
        "confidence": "low",
        "correspondent": {"last": last, "initials": ini},
        "reason": "unclassified_surname",
    }
