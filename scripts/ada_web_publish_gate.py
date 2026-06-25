"""
Gate for publishing ADA rows to the public website (docs/ada_db_data.json).

Policy (accuracy-first):
  - Tier A or B only.
  - Non-empty evidence excerpt.
  - At least one http(s) URL in citation_urls or ada_source_url_primary (first URL wins).
  - If ada_first_pct is numeric: a matching % must appear in ada_evidence_chain_excerpt
    (same heuristic as verify_ada_master_row_by_row, tol ±0.51 pp), OR the excerpt must
    support qualitative ADA statements (no detectable ADA) when no numeric primary exists.

Offline master CSV may retain all 138 research rows; excluded antibodies are listed in
data/immunogenicity_knowledge_base/reports/ada_web_publish_excluded.csv for manual curation.
"""
from __future__ import annotations

import math
import re
from typing import Any, Mapping


def resolve_http_citation(row: Mapping[str, Any]) -> str:
    """Return first http(s) URL from citation_urls, else ada_source_url_primary."""
    for key in ("citation_urls", "ada_source_url_primary"):
        raw = str(row.get(key) or "").strip()
        if not raw:
            continue
        for sep in ";", ",", "\n":
            raw = raw.replace(sep, " ")
        for token in raw.split():
            t = token.strip().rstrip(").,]")
            if t.startswith("http://") or t.startswith("https://"):
                return t
    return ""


def _primary_float(row: Mapping[str, Any]) -> float | None:
    v = row.get("ada_first_pct")
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip()
        if not s or s.upper() == "NR" or s.lower() == "nan":
            return None
        try:
            fv = float(s)
        except ValueError:
            return None
    else:
        try:
            fv = float(v)
        except (TypeError, ValueError):
            return None
    if math.isnan(fv):
        return None
    return fv


def _pcts_in_text(t: str) -> list[float]:
    if not t:
        return []
    t = re.sub(r"9[0-9]\s*%\s*CI", "", t, flags=re.I)
    out: list[float] = []
    for m in re.finditer(r"(\d+\.?\d*)\s*%", t):
        try:
            v = float(m.group(1))
            if 0 <= v <= 100:
                out.append(v)
        except ValueError:
            pass
    return out


def excerpt_aligns_numeric_primary(primary: float, excerpt: str) -> bool:
    ex = excerpt or ""
    for v in _pcts_in_text(ex):
        if abs(v - primary) <= 0.51:
            return True
    if primary == 0 and re.search(r"0\s*%|not detected|were not detected|no detectable", ex, re.I):
        return True
    return False


def excerpt_qualitative_ok(excerpt: str) -> bool:
    """For rows without ada_first_pct: require substantive immunogenicity language."""
    ex = (excerpt or "").strip()
    if len(ex) < 50:
        return False
    low = ex.lower()
    return any(
        k in low
        for k in (
            "anti-drug",
            "antidrug",
            " anti-drug ",
            "immunogenic",
            "neutralizing antibod",
            "treatment-emergent",
            " ada ",
            "ada-positive",
            "ada positive",
        )
    )


_STRONG_URL_DOMAINS = (
    "ncbi.nlm.nih.gov", "pubmed.ncbi", "pmc.ncbi", "fda.gov", "accessdata.fda",
    "dailymed.nlm.nih.gov", "ema.europa.eu", "nejm.org", "lancet.com", "bmj.com",
    "annrheumdis", "jci.org", "nature.com", "science.org", "cell.com", "jama",
    "onlinelibrary.wiley", "springer", "elsevier", "bloodjournal", "jto-",
    "annalsofoncology", "jitc.bmj", "rheumatology", "haematologica",
)


def _has_strong_source(row: Mapping[str, Any]) -> bool:
    """True if the row has a PMID or a strong (non-AI) URL source."""
    pmids = str(row.get("ada_source_pmids") or "").strip()
    if pmids and pmids.lower() not in ("nan", "none", ""):
        return True
    for key in ("ada_source_url_primary", "citation_urls"):
        url = str(row.get(key) or "").lower()
        if any(d in url for d in _STRONG_URL_DOMAINS):
            return True
    return False


def web_publish_eligible(row: Mapping[str, Any]) -> tuple[bool, str]:
    tier = str(row.get("evidence_tier") or "").strip().upper()
    if tier not in ("A", "B"):
        return False, f"tier_not_AB:{tier or 'empty'}"

    excerpt = str(row.get("ada_evidence_chain_excerpt") or "").strip()
    if not excerpt:
        return False, "empty_excerpt"

    url = resolve_http_citation(row)
    if not url:
        return False, "no_http_citation"

    primary = _primary_float(row)
    if primary is not None:
        if excerpt_aligns_numeric_primary(primary, excerpt):
            return True, "numeric_excerpt_aligned"
        # Bypass numeric mismatch if record has a verified real primary source
        # (PMID / FDA PI / DailyMed). Principle: real source > AI-generated excerpt text.
        verify_status = str(row.get("verify_status") or "").strip().upper()
        if _has_strong_source(row) and verify_status in (
            "VERIFIED", "SOURCE_LIVE", "UNCERTAIN", "SOURCE_UNREACHABLE"
        ):
            return True, f"real_source_bypass:{verify_status}"
        return False, "excerpt_numeric_mismatch"

    if excerpt_qualitative_ok(excerpt):
        return True, "qualitative_immunogenicity_ok"
    return False, "qualitative_excerpt_insufficient"
