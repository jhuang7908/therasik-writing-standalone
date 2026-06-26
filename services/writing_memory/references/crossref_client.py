"""
CrossRef API client — DOI lookup + title search.

Used as:
  1. Cross-check: confirm that a PMID's DOI resolves to a real record with
     the same title and year (catches PMID typos and OCR errors).
  2. Fallback: when a topic isn't indexed in PubMed yet (preprints,
     non-biomedical journals, very recent papers).

CrossRef Public API has no auth requirement and a "polite pool" if you
send a User-Agent with your email — we do that automatically.
Rate limit: 50 req/s burst, much higher than NCBI.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any

import requests

CROSSREF = "https://api.crossref.org/works"

_EMAIL   = os.environ.get("CROSSREF_EMAIL", os.environ.get("NCBI_EMAIL", "support@insynbio.com"))
_TOOL    = os.environ.get("NCBI_TOOL", "insynbio_writing_memory")
_TIMEOUT = float(os.environ.get("CROSSREF_TIMEOUT", "20"))
_UA      = f"{_TOOL} (mailto:{_EMAIL})"

# CrossRef allows ~50 req/s but we stay polite at 5 req/s
_MIN_INTERVAL = 0.2
_last_call    = 0.0
_lock         = Lock()


def _throttle() -> None:
    global _last_call
    with _lock:
        now = time.monotonic()
        wait = _MIN_INTERVAL - (now - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


@dataclass
class CrossRefRecord:
    doi:     str
    title:   str = ""
    authors: list[tuple[str, str]] = None  # type: ignore[assignment]
    year:    int | None = None
    journal: str = ""
    volume:  str | None = None
    issue:   str | None = None
    pages:   str | None = None
    pub_type: str = ""
    retrieved_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "doi":          self.doi,
            "title":        self.title,
            "authors":      [{"last": a, "initials": i} for a, i in (self.authors or [])],
            "year":         self.year,
            "journal":      self.journal,
            "volume":       self.volume,
            "issue":        self.issue,
            "pages":        self.pages,
            "pub_type":     self.pub_type,
            "retrieved_at": self.retrieved_at,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_message(msg: dict[str, Any]) -> CrossRefRecord:
    title_list = msg.get("title") or []
    title = title_list[0] if title_list else ""

    authors_out: list[tuple[str, str]] = []
    for au in msg.get("author") or []:
        last = au.get("family") or ""
        given = au.get("given") or ""
        ini = "".join(part[0] for part in given.split() if part)
        if last:
            authors_out.append((last, ini))

    year: int | None = None
    for key in ("published-print", "published-online", "issued", "created"):
        d = msg.get(key)
        if d and d.get("date-parts"):
            try:
                year = int(d["date-parts"][0][0])
                break
            except (IndexError, TypeError, ValueError):
                continue

    journal_list = msg.get("container-title") or []
    journal = journal_list[0] if journal_list else ""

    return CrossRefRecord(
        doi=msg.get("DOI", "").lower(),
        title=title.strip(),
        authors=authors_out,
        year=year,
        journal=journal,
        volume=msg.get("volume") or None,
        issue=msg.get("issue") or None,
        pages=msg.get("page") or None,
        pub_type=msg.get("type") or "",
        retrieved_at=_now(),
    )


def lookup_doi(doi: str) -> CrossRefRecord | None:
    """Resolve a DOI to its canonical CrossRef record. Returns None if not found."""
    if not doi or not doi.strip():
        return None
    doi_clean = doi.strip().lstrip("doi:").lstrip("https://doi.org/").lstrip("http://doi.org/")

    _throttle()
    try:
        r = requests.get(
            f"{CROSSREF}/{doi_clean}",
            headers={"User-Agent": _UA},
            timeout=_TIMEOUT,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
    except requests.HTTPError:
        return None
    except requests.RequestException:
        return None

    msg = r.json().get("message") or {}
    if not msg:
        return None
    return _parse_message(msg)


def search_title(query: str, rows: int = 5) -> list[CrossRefRecord]:
    """Title/keyword search; returns up to `rows` candidate records."""
    if not query.strip():
        return []

    _throttle()
    try:
        r = requests.get(
            CROSSREF,
            params={"query.bibliographic": query, "rows": rows},
            headers={"User-Agent": _UA},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
    except requests.RequestException:
        return []

    items = (r.json().get("message") or {}).get("items") or []
    return [_parse_message(m) for m in items]
