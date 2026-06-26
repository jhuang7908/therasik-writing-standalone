"""
semantic_scholar.py — Semantic Scholar API client for citation verification.

Public API: https://api.semanticscholar.org/graph/v1
Rate limits:
  Without key : ~100 req / 5 min  (~1 req/3s to be safe)
  With key    : 100 req / s  (set S2_API_KEY env var or SEMANTIC_SCHOLAR_API_KEY)

DOI verification workflow:
  1. extract_dois(text)           → list of DOIs found in manuscript
  2. lookup_doi(doi)              → paper metadata from S2, or None if not found
  3. verify_references(text)      → batch verify all DOIs in text
  4. verify_references_report()   → structured finding list for multi_expert_review

Title search (for references without DOIs):
  search_by_title(title)          → top-N S2 paper matches

All results are in-process cached to avoid duplicate network calls within a run.
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

# ── API config ────────────────────────────────────────────────────────────────

_BASE  = "https://api.semanticscholar.org/graph/v1"
_KEY   = (os.environ.get("S2_API_KEY")
          or os.environ.get("SEMANTIC_SCHOLAR_API_KEY", ""))

# Conservative rate: 1 req / 1.2s  (stays under 100/5min limit comfortably)
_MIN_INTERVAL = 1.2

# ── In-process cache ──────────────────────────────────────────────────────────
_CACHE:     dict[str, Optional[dict]] = {}
_LAST_CALL: float = 0.0

# ── DOI patterns ─────────────────────────────────────────────────────────────
# Matches labelled DOIs:  doi: 10.xxx/yyy  |  https://doi.org/10.xxx/yyy
_DOI_LABELLED = re.compile(
    r"(?:doi\s*:\s*|https?://doi\.org/|https?://dx\.doi\.org/)"
    r"(10\.\d{4,9}/[^\s\]\[,;\"'<>\)]+)",
    re.IGNORECASE,
)
# Matches bare DOIs appearing in reference lists: 10.xxxx/xxx
_DOI_BARE = re.compile(
    r"(?<!\w)(10\.\d{4,9}/[^\s\]\[,;\"'<>\)]{5,})"
)

# DOI format validator — checks structural validity before calling the network
_DOI_FORMAT = re.compile(r"^10\.\d{4,9}/.{2,}$")


# ══════════════════════════════════════════════════════════════════════════════
# HTTP HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _wait():
    global _LAST_CALL
    elapsed = time.monotonic() - _LAST_CALL
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _LAST_CALL = time.monotonic()


def _get(url: str, timeout: int = 10) -> Optional[dict]:
    """GET JSON with rate-limiting, caching, and silent error handling."""
    if url in _CACHE:
        return _CACHE[url]

    _wait()

    headers = {"Accept": "application/json", "User-Agent": "TheraSIK-CitationAuditor/1.0"}
    if _KEY:
        headers["x-api-key"] = _KEY

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _CACHE[url] = data
            return data
    except urllib.error.HTTPError as exc:
        _CACHE[url] = None          # cache the 404 / 4xx result
        if exc.code not in (404, 429):
            pass  # silent for expected codes
        return None
    except Exception:
        return None                 # network timeout etc. — not cached


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def lookup_doi(doi: str) -> Optional[dict]:
    """
    Look up a paper by DOI on Semantic Scholar.

    Returns dict with keys: paperId, title, year, authors, publicationVenue
    Returns None if DOI not found or network error.
    """
    doi = doi.strip().rstrip(".,;")
    if not _DOI_FORMAT.match(doi):
        return None
    safe = urllib.parse.quote(doi, safe="")
    url  = (f"{_BASE}/paper/DOI:{safe}"
            f"?fields=title,year,authors,publicationVenue,externalIds")
    return _get(url)


def search_by_title(title: str, limit: int = 3) -> list[dict]:
    """
    Search Semantic Scholar by paper title. Returns up to `limit` matches.

    Each match: {paperId, title, year, authors, externalIds}
    """
    q   = urllib.parse.quote(title[:200].strip(), safe="")
    url = f"{_BASE}/paper/search?query={q}&limit={limit}&fields=title,year,authors,externalIds"
    data = _get(url)
    if data and "data" in data:
        return data["data"]
    return []


def extract_dois(text: str) -> list[str]:
    """
    Extract all DOI strings from manuscript text (labelled and bare patterns).
    Returns a deduplicated, sorted list.
    """
    found: set[str] = set()
    for m in _DOI_LABELLED.finditer(text):
        raw = m.group(1).strip().rstrip(".,;")
        if _DOI_FORMAT.match(raw):
            found.add(raw)
    for m in _DOI_BARE.finditer(text):
        raw = m.group(1).strip().rstrip(".,;")
        if _DOI_FORMAT.match(raw) and raw not in found:
            found.add(raw)
    return sorted(found)


def verify_references(
    text: str,
    max_verify: int = 25,
) -> list[dict]:
    """
    Extract DOIs from manuscript text and verify each against Semantic Scholar.

    Args:
        text:        Full manuscript text.
        max_verify:  Maximum number of DOIs to verify (default 25 to stay in quota).

    Returns list of dicts:
        [
          {
            "doi":    "10.1016/j.cell.2023.01.001",
            "status": "verified" | "not_found" | "invalid_format",
            "title":  "...",
            "year":   2023,
            "venue":  "Cell",
          },
          ...
        ]
    """
    dois = extract_dois(text)

    # Validate format first (free, no network)
    results: list[dict] = []
    invalid = [d for d in dois if not _DOI_FORMAT.match(d)]
    for doi in invalid:
        results.append({
            "doi":    doi,
            "status": "invalid_format",
            "title":  "",
            "year":   None,
            "venue":  "",
        })

    valid = [d for d in dois if _DOI_FORMAT.match(d)][:max_verify]
    for doi in valid:
        paper = lookup_doi(doi)
        if paper:
            results.append({
                "doi":    doi,
                "status": "verified",
                "title":  paper.get("title") or "",
                "year":   paper.get("year"),
                "venue":  (paper.get("publicationVenue") or {}).get("name", ""),
            })
        else:
            results.append({
                "doi":    doi,
                "status": "not_found",
                "title":  "",
                "year":   None,
                "venue":  "",
            })

    return results


def verify_references_report(text: str, max_verify: int = 25) -> dict:
    """
    High-level wrapper: verify references and return a structured report
    compatible with multi_expert_review finding format.

    Returns:
        {
          "total_dois":    int,
          "verified":      int,
          "not_found":     int,
          "invalid":       int,
          "hallucination_risk": [{"doi": ..., "status": ...}, ...],
          "verified_list": [...],
          "findings":      [finding dict, ...],   ← ready for review report
        }
    """
    results = verify_references(text, max_verify=max_verify)

    verified     = [r for r in results if r["status"] == "verified"]
    not_found    = [r for r in results if r["status"] == "not_found"]
    invalid_fmt  = [r for r in results if r["status"] == "invalid_format"]
    at_risk      = not_found + invalid_fmt

    findings = []

    if not_found:
        sev = "CRITICAL" if len(not_found) >= 3 else "MAJOR"
        findings.append({
            "category": "Citation verification",
            "severity":  sev,
            "issue": (
                f"{len(not_found)} DOI(s) not found on Semantic Scholar "
                f"(potential hallucination or transcription error)"
            ),
            "evidence": "; ".join(r["doi"] for r in not_found[:5]),
            "recommendation": (
                "Verify each flagged DOI manually. "
                "If the paper exists, check for typos in the DOI string. "
                "If the paper cannot be found in any database, it may be AI-hallucinated — "
                "remove or replace with a real, verifiable citation."
            ),
        })

    if invalid_fmt:
        findings.append({
            "category": "DOI format",
            "severity":  "MAJOR",
            "issue": (
                f"{len(invalid_fmt)} DOI(s) with invalid format "
                f"(does not match 10.xxxx/... pattern)"
            ),
            "evidence": "; ".join(r["doi"] for r in invalid_fmt[:5]),
            "recommendation": (
                "Correct malformed DOI strings. "
                "Valid DOI format: 10.XXXX/suffix — e.g. 10.1016/j.cell.2023.01.001."
            ),
        })

    if verified and len(verified) == len(results):
        findings.append({
            "category": "Citation verification",
            "severity":  "INFO",
            "issue":    f"All {len(verified)} DOI(s) verified on Semantic Scholar.",
            "evidence": "",
            "recommendation": "",
        })

    return {
        "total_dois":        len(results),
        "verified":          len(verified),
        "not_found":         len(not_found),
        "invalid":           len(invalid_fmt),
        "hallucination_risk": [{"doi": r["doi"], "status": r["status"]} for r in at_risk],
        "verified_list":     verified,
        "findings":          findings,
    }


# ══════════════════════════════════════════════════════════════════════════════
# AVAILABILITY CHECK
# ══════════════════════════════════════════════════════════════════════════════

def is_reachable(timeout: int = 5) -> bool:
    """Quick connectivity check — looks up a known DOI."""
    test = lookup_doi("10.1038/nature12345")
    # Nature paper 12345 may or may not exist; we just need a non-exception response
    return test is not None or "10.1038/nature12345" in _CACHE
