"""
citation_verifier.py — Unified citation verification via 3 free public APIs.

Verification chain (in priority order):
  1. Semantic Scholar  https://api.semanticscholar.org/graph/v1
  2. CrossRef          https://api.crossref.org/works/{doi}
  3. PubMed E-utils    https://eutils.ncbi.nlm.nih.gov/entrez/eutils/

Strategy per identifier type:
  DOI   → S2 first → CrossRef fallback
  PMID  → PubMed directly (most authoritative for PMIDs)
  Title → S2 title search (no DOI/PMID)

All APIs are free with no mandatory API key.
Optional env vars for higher rate limits:
  S2_API_KEY              / SEMANTIC_SCHOLAR_API_KEY
  NCBI_API_KEY            (PubMed: 3 req/s without key, 10 req/s with key)
  CROSSREF_MAILTO         (CrossRef polite pool: add email for better service)

In-process cache shared across all three backends.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

# ── Rate limits ───────────────────────────────────────────────────────────────
_S2_INTERVAL    = 1.2   # Semantic Scholar: ~100 req/5min without key
_CR_INTERVAL    = 0.2   # CrossRef: polite pool has no strict limit
_PM_INTERVAL    = 0.34  # PubMed: 3 req/s without key

# ── Optional credentials ──────────────────────────────────────────────────────
_S2_KEY    = os.environ.get("S2_API_KEY") or os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
_NCBI_KEY  = os.environ.get("NCBI_API_KEY", "")
_CR_MAILTO = os.environ.get("CROSSREF_MAILTO", "therasik-citationbot@insynbio.com")

# ── In-process cache ──────────────────────────────────────────────────────────
_CACHE: dict[str, Optional[dict]] = {}

# ── Per-service last-call tracker ─────────────────────────────────────────────
_LAST: dict[str, float] = {"s2": 0.0, "cr": 0.0, "pm": 0.0}

# ── Regex patterns ────────────────────────────────────────────────────────────
DOI_FORMAT    = re.compile(r"^10\.\d{4,9}/.{2,}$")
DOI_LABELLED  = re.compile(
    r"(?:doi\s*:\s*|https?://doi\.org/|https?://dx\.doi\.org/)"
    r"(10\.\d{4,9}/[^\s\]\[,;\"'<>\)]+)",
    re.IGNORECASE,
)
DOI_BARE      = re.compile(r"(?<!\w)(10\.\d{4,9}/[^\s\]\[,;\"'<>\)]{5,})")
PMID_RE       = re.compile(r"\bPMID\s*:?\s*(\d{5,9})\b", re.IGNORECASE)


# ══════════════════════════════════════════════════════════════════════════════
# HTTP PRIMITIVE
# ══════════════════════════════════════════════════════════════════════════════

def _get(url: str, headers: dict, service: str, timeout: int = 10) -> Optional[dict]:
    if url in _CACHE:
        return _CACHE[url]

    interval = {"s2": _S2_INTERVAL, "cr": _CR_INTERVAL, "pm": _PM_INTERVAL}.get(service, 1.0)
    elapsed  = time.monotonic() - _LAST.get(service, 0.0)
    if elapsed < interval:
        time.sleep(interval - elapsed)

    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "TheraSIK-CitationVerifier/2.0",
        **headers,
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _CACHE[url] = data
            _LAST[service] = time.monotonic()
            return data
    except urllib.error.HTTPError as exc:
        _CACHE[url] = None
        _LAST[service] = time.monotonic()
        return None
    except Exception:
        _LAST[service] = time.monotonic()
        return None


# ══════════════════════════════════════════════════════════════════════════════
# BACKEND 1 — SEMANTIC SCHOLAR
# ══════════════════════════════════════════════════════════════════════════════

def _s2_lookup_doi(doi: str) -> Optional[dict]:
    doi  = doi.strip().rstrip(".,;")
    safe = urllib.parse.quote(doi, safe="")
    url  = (f"https://api.semanticscholar.org/graph/v1/paper/DOI:{safe}"
            f"?fields=title,year,authors,publicationVenue,externalIds")
    hdrs = {"x-api-key": _S2_KEY} if _S2_KEY else {}
    data = _get(url, hdrs, "s2")
    if not data:
        return None
    return {
        "source":  "semantic_scholar",
        "title":   data.get("title") or "",
        "year":    data.get("year"),
        "venue":   (data.get("publicationVenue") or {}).get("name", ""),
        "doi":     doi,
        "pmid":    ((data.get("externalIds") or {}).get("PubMed", "")),
    }


def _s2_search_title(title: str) -> list[dict]:
    q   = urllib.parse.quote(title[:200].strip(), safe="")
    url = (f"https://api.semanticscholar.org/graph/v1/paper/search"
           f"?query={q}&limit=3&fields=title,year,authors,externalIds")
    hdrs = {"x-api-key": _S2_KEY} if _S2_KEY else {}
    data = _get(url, hdrs, "s2")
    if data and "data" in data:
        return data["data"]
    return []


# ══════════════════════════════════════════════════════════════════════════════
# BACKEND 2 — CROSSREF
# ══════════════════════════════════════════════════════════════════════════════

def _cr_lookup_doi(doi: str) -> Optional[dict]:
    doi  = doi.strip().rstrip(".,;")
    safe = urllib.parse.quote(doi, safe="")
    url  = f"https://api.crossref.org/works/{safe}"
    hdrs = {"mailto": _CR_MAILTO} if _CR_MAILTO else {}
    data = _get(url, hdrs, "cr")
    if not data or data.get("status") != "ok":
        return None
    msg = data.get("message", {})
    # Extract first author family name
    authors = msg.get("author", [])
    first_author = authors[0].get("family", "") if authors else ""
    # Title is a list in CrossRef
    title_list = msg.get("title", [])
    title = title_list[0] if title_list else ""
    # Published year
    pub_date = msg.get("published-print") or msg.get("published-online") or {}
    parts = pub_date.get("date-parts", [[]])
    year  = parts[0][0] if parts and parts[0] else None
    # Journal name
    container = msg.get("container-title", [])
    venue = container[0] if container else ""

    return {
        "source":  "crossref",
        "title":   title,
        "year":    year,
        "venue":   venue,
        "doi":     doi,
        "pmid":    "",
        "publisher": msg.get("publisher", ""),
        "type":    msg.get("type", ""),
    }


# ══════════════════════════════════════════════════════════════════════════════
# BACKEND 3 — PUBMED E-UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def _pm_lookup_pmid(pmid: str) -> Optional[dict]:
    pmid = str(pmid).strip()
    key_param = f"&api_key={_NCBI_KEY}" if _NCBI_KEY else ""
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
           f"?db=pubmed&id={pmid}&retmode=json{key_param}")
    data = _get(url, {}, "pm")
    if not data:
        return None
    result = data.get("result", {})
    entry  = result.get(pmid)
    if not entry or entry.get("error"):
        return None
    return {
        "source":  "pubmed",
        "title":   entry.get("title", ""),
        "year":    int(entry.get("pubdate", "")[:4]) if entry.get("pubdate") else None,
        "venue":   entry.get("source", ""),
        "doi":     next((id_["value"] for id_ in entry.get("articleids", [])
                         if id_.get("idtype") == "doi"), ""),
        "pmid":    pmid,
    }


def _pm_doi_to_pmid(doi: str) -> Optional[str]:
    """Use PubMed esearch to resolve a DOI to a PMID."""
    doi  = doi.strip().rstrip(".,;")
    safe = urllib.parse.quote(doi, safe="")
    key_param = f"&api_key={_NCBI_KEY}" if _NCBI_KEY else ""
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
           f"?db=pubmed&term={safe}[doi]&retmode=json{key_param}")
    data = _get(url, {}, "pm")
    if not data:
        return None
    ids = data.get("esearchresult", {}).get("idlist", [])
    return ids[0] if ids else None


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED VERIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def verify_doi(doi: str) -> dict:
    """
    Verify a single DOI using S2 → CrossRef → PubMed cascade.

    Returns:
        {
          "doi":    str,
          "status": "verified" | "not_found" | "invalid_format",
          "source": "semantic_scholar" | "crossref" | "pubmed" | "",
          "title":  str,
          "year":   int | None,
          "venue":  str,
        }
    """
    doi = doi.strip().rstrip(".,;")
    if not DOI_FORMAT.match(doi):
        return {"doi": doi, "status": "invalid_format",
                "source": "", "title": "", "year": None, "venue": ""}

    # Try S2
    paper = _s2_lookup_doi(doi)
    if paper:
        return {**paper, "status": "verified"}

    # Try CrossRef
    paper = _cr_lookup_doi(doi)
    if paper:
        return {**paper, "status": "verified"}

    # Try PubMed (DOI → PMID → metadata)
    pmid = _pm_doi_to_pmid(doi)
    if pmid:
        paper = _pm_lookup_pmid(pmid)
        if paper:
            return {**paper, "doi": doi, "status": "verified"}

    return {"doi": doi, "status": "not_found",
            "source": "", "title": "", "year": None, "venue": ""}


def verify_pmid(pmid: str) -> dict:
    """Verify a PMID directly via PubMed E-utilities."""
    paper = _pm_lookup_pmid(str(pmid))
    if paper:
        return {**paper, "status": "verified"}
    return {"pmid": pmid, "doi": "", "status": "not_found",
            "source": "", "title": "", "year": None, "venue": ""}


# ══════════════════════════════════════════════════════════════════════════════
# EXTRACTION HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def extract_dois(text: str) -> list[str]:
    found: set[str] = set()
    for m in DOI_LABELLED.finditer(text):
        raw = m.group(1).strip().rstrip(".,;")
        if DOI_FORMAT.match(raw):
            found.add(raw)
    for m in DOI_BARE.finditer(text):
        raw = m.group(1).strip().rstrip(".,;")
        if DOI_FORMAT.match(raw):
            found.add(raw)
    return sorted(found)


def extract_pmids(text: str) -> list[str]:
    return sorted({m.group(1) for m in PMID_RE.finditer(text)})


# ══════════════════════════════════════════════════════════════════════════════
# BATCH VERIFICATION + REPORT
# ══════════════════════════════════════════════════════════════════════════════

def verify_all(
    text: str,
    max_dois:  int = 25,
    max_pmids: int = 10,
) -> dict:
    """
    Extract and verify all DOIs and PMIDs in manuscript text.

    DOI verification: S2 → CrossRef → PubMed cascade (3 free APIs).
    PMID verification: PubMed E-utilities directly.

    Returns unified report:
    {
      "dois":  {"total": N, "verified": N, "not_found": [...], "invalid": [...]},
      "pmids": {"total": N, "verified": N, "not_found": [...]},
      "findings": [ finding-compatible dicts ],
      "details":  [ per-identifier result dicts ],
    }
    """
    dois  = extract_dois(text)[:max_dois]
    pmids = extract_pmids(text)[:max_pmids]

    doi_results  = [verify_doi(d)  for d in dois]
    pmid_results = [verify_pmid(p) for p in pmids]

    doi_verified    = [r for r in doi_results  if r["status"] == "verified"]
    doi_not_found   = [r for r in doi_results  if r["status"] == "not_found"]
    doi_invalid     = [r for r in doi_results  if r["status"] == "invalid_format"]
    pmid_verified   = [r for r in pmid_results if r["status"] == "verified"]
    pmid_not_found  = [r for r in pmid_results if r["status"] == "not_found"]

    findings: list[dict] = []

    # DOI not found
    if doi_not_found:
        sev = "CRITICAL" if len(doi_not_found) >= 3 else "MAJOR"
        findings.append({
            "category": "Citation verification (DOI)",
            "severity":  sev,
            "issue": (f"{len(doi_not_found)} DOI(s) not found across Semantic Scholar, "
                      f"CrossRef, and PubMed — potential hallucination or transcription error"),
            "evidence": "; ".join(r["doi"] for r in doi_not_found[:5]),
            "recommendation": (
                "Manually verify each flagged DOI in the journal's website or PubMed. "
                "If the paper cannot be found in any database, it is likely AI-hallucinated. "
                "Remove or replace with a real, verifiable citation."
            ),
        })

    # DOI invalid format
    if doi_invalid:
        findings.append({
            "category": "DOI format",
            "severity":  "MAJOR",
            "issue": f"{len(doi_invalid)} DOI(s) with invalid format",
            "evidence": "; ".join(r["doi"] for r in doi_invalid[:4]),
            "recommendation": "Correct malformed DOIs. Valid format: 10.XXXX/suffix.",
        })

    # PMID not found
    if pmid_not_found:
        findings.append({
            "category": "Citation verification (PMID)",
            "severity":  "MAJOR",
            "issue": f"{len(pmid_not_found)} PMID(s) not found on PubMed",
            "evidence": "; ".join(r["pmid"] for r in pmid_not_found[:4]),
            "recommendation": (
                "Verify PMIDs on https://pubmed.ncbi.nlm.nih.gov/. "
                "An unresolvable PMID may indicate a transcription error or hallucinated reference."
            ),
        })

    # All clear
    total_checked = len(doi_results) + len(pmid_results)
    total_ok      = len(doi_verified) + len(pmid_verified)
    if total_checked > 0 and total_ok == total_checked:
        findings.append({
            "category": "Citation verification",
            "severity":  "INFO",
            "issue": f"All {total_checked} identifier(s) verified (S2 / CrossRef / PubMed).",
            "evidence": "",
            "recommendation": "",
        })

    return {
        "dois": {
            "total":     len(doi_results),
            "verified":  len(doi_verified),
            "not_found": [r["doi"] for r in doi_not_found],
            "invalid":   [r["doi"] for r in doi_invalid],
        },
        "pmids": {
            "total":     len(pmid_results),
            "verified":  len(pmid_verified),
            "not_found": [r["pmid"] for r in pmid_not_found],
        },
        "findings": findings,
        "details":  doi_results + pmid_results,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CONNECTIVITY CHECK
# ══════════════════════════════════════════════════════════════════════════════

def check_connectivity() -> dict[str, bool]:
    """Quick probe of all three backends. Returns {service: reachable}."""
    results: dict[str, bool] = {}

    # S2 — probe with known real paper
    r = _s2_lookup_doi("10.1016/j.cell.2022.09.028")
    results["semantic_scholar"] = r is not None

    # CrossRef — probe with same DOI
    r = _cr_lookup_doi("10.1016/j.cell.2022.09.028")
    results["crossref"] = r is not None

    # PubMed — probe with known PMID
    r = _pm_lookup_pmid("36208648")
    results["pubmed"] = r is not None

    return results
