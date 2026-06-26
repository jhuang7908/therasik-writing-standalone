"""Quantitative QC metrics for cohort exemplars (partial full text from PMC JATS)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..upload_intake import quality_gate

_TYPES_DIR = Path(__file__).resolve().parent.parent / "schemas" / "article_types"
_SCHEMA_CACHE: dict[str, dict[str, Any]] = {}


def load_type_schema(canonical: str) -> dict[str, Any]:
    if canonical in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[canonical]
    path = _TYPES_DIR / f"{canonical}.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    _SCHEMA_CACHE[canonical] = data
    return data


def _word_count(text: str) -> int:
    return len(re.findall(r"[a-zA-Z]{2,}", text or ""))


def _count_reference_markers(text: str) -> int:
    """Conservative in-text citation marker count (not bibliography parsing)."""
    if not text:
        return 0
    numbered = len(re.findall(r"\(\s*\d{1,4}\s*[,\-\u2013]?\s*\d{0,4}\s*\)", text))
    numbered += len(re.findall(r"\[\s*\d{1,4}\s*\]", text))
    author_year = len(
        re.findall(
            r"\([A-Z][a-zA-Z\-']+(?:\s+et\s+al\.?)?,?\s+(?:19|20)\d{2}[a-z]?\)",
            text,
        )
    )
    return numbered + author_year


def compute_paper_metrics(
    paper: dict[str, Any],
    canonical_type: str,
) -> dict[str, Any]:
    """
    Metrics on available PMC fields (abstract, discussion, conclusion, legends).
    Full IMRAD body is not in papers_raw MVP — flags partial_coverage.
    """
    schema = load_type_schema(canonical_type)
    targets = schema.get("word_targets_default") or {}

    abstract_text = paper.get("abstract") or ""
    parts = [
        abstract_text,
        paper.get("discussion") or "",
        paper.get("conclusion") or "",
        " ".join(paper.get("figure_legends") or []),
    ]
    full_text = "\n\n".join(p for p in parts if p).strip()
    abstract_only = not (paper.get("discussion") or paper.get("conclusion"))

    qg = (
        quality_gate(abstract_text, title=paper.get("title") or "")
        if abstract_only
        else quality_gate(full_text, title=paper.get("title") or "")
    )

    abstract_wc = _word_count(paper.get("abstract") or "")
    discussion_wc = _word_count(paper.get("discussion") or "")
    conclusion_wc = _word_count(paper.get("conclusion") or "")
    total_wc = _word_count(full_text)

    ref_n = _count_reference_markers(full_text)
    density = (ref_n * 1000.0 / total_wc) if total_wc > 50 else 0.0

    sec_avail = paper.get("sections_available") or {}
    required = schema.get("sections_required") or []

    band_checks: dict[str, str] = {}
    for sec, target in targets.items():
        if sec == "abstract":
            wc = abstract_wc
        elif sec == "discussion":
            wc = discussion_wc
        else:
            wc = 0
        if not target or wc == 0:
            band_checks[sec] = "no_data"
            continue
        lo, hi = int(target * 0.35), int(target * 2.5)
        if lo <= wc <= hi:
            band_checks[sec] = "in_band"
        elif wc < lo:
            band_checks[sec] = "below_band"
        else:
            band_checks[sec] = "above_band"

    if abstract_only:
        qc_pass = qg.get("verdict") == "pass" and abstract_wc >= 80
    else:
        qc_pass = qg.get("verdict") == "pass" and total_wc >= 120
    if canonical_type in ("review_narrative", "systematic_review"):
        qc_pass = qc_pass and (discussion_wc >= 80 or abstract_wc >= 150)

    return {
        "partial_coverage": True,
        "quality_gate": qg,
        "qc_pass": qc_pass,
        "word_count": {
            "abstract": abstract_wc,
            "discussion": discussion_wc,
            "conclusion": conclusion_wc,
            "total_available": total_wc,
        },
        "word_targets_default": targets,
        "word_band_check": band_checks,
        "reference_markers_estimated": ref_n,
        "citations_per_1000_words": round(density, 2),
        "sections_available": sec_avail,
        "sections_required_schema": required,
    }
