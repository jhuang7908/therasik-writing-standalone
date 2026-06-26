"""
Unpaywall API client — free OA metadata and PDF links by DOI.

https://unpaywall.org/products/api
Requires contact email on each request (UNPAYWALL_EMAIL or OPENALEX_EMAIL).
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

_TIMEOUT = 12
_BASE = "https://api.unpaywall.org/v2"


def unpaywall_config() -> dict[str, Any]:
    email = _email()
    disabled = (os.environ.get("WM_UNPAYWALL_DISABLE") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    return {
        "configured": bool(email),
        "email_set": bool(email),
        "disabled": disabled,
        "api": _BASE,
    }


def _email() -> str:
    return (
        os.environ.get("UNPAYWALL_EMAIL")
        or os.environ.get("OPENALEX_EMAIL")
        or os.environ.get("CROSSREF_EMAIL")
        or "oa@insynbio.com"
    ).strip()


def _norm_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    d = str(doi).strip().replace("https://doi.org/", "").replace("http://doi.org/", "")
    return d if d.startswith("10.") else None


def lookup_doi(doi: str) -> dict[str, Any] | None:
    """Return raw Unpaywall JSON for a DOI, or None."""
    d = _norm_doi(doi)
    if not d:
        return None
    try:
        r = requests.get(
            f"{_BASE}/{d}",
            params={"email": _email()},
            timeout=_TIMEOUT,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def oa_fields_from_payload(data: dict[str, Any]) -> dict[str, Any]:
    best = data.get("best_oa_location") if isinstance(data.get("best_oa_location"), dict) else {}
    pdf = best.get("url_for_pdf")
    landing = best.get("url") or best.get("url_for_landing_page")
    return {
        "is_oa": bool(data.get("is_oa")),
        "oa_status": data.get("oa_status"),
        "oa_url": pdf or landing,
        "oa_pdf_url": pdf,
        "oa_landing_url": landing,
        "oa_license": best.get("license"),
        "oa_host": best.get("host_type"),
        "unpaywall_genre": data.get("genre"),
        "verification_status": "verified",
    }


def enrich_work(work: dict[str, Any]) -> dict[str, Any]:
    """Merge Unpaywall OA fields into an OpenAlex-style work dict (in place)."""
    doi = _norm_doi(work.get("doi"))
    if not doi:
        return work
    data = lookup_doi(doi)
    if not data:
        return work
    fields = oa_fields_from_payload(data)
    if fields.get("oa_url") and not work.get("oa_url"):
        work["oa_url"] = fields["oa_url"]
    for k, v in fields.items():
        if v is not None and k != "verification_status":
            work[k] = v
    work["oa_source"] = "unpaywall"
    return work


def enrich_works(works: list[dict[str, Any]], *, max_workers: int = 5) -> list[dict[str, Any]]:
    if not works:
        return works
    if (os.environ.get("WM_UNPAYWALL_DISABLE") or "").strip().lower() in ("1", "true", "yes"):
        return works
    out = list(works)
    with ThreadPoolExecutor(max_workers=min(max_workers, len(out))) as pool:
        futs = {pool.submit(enrich_work, dict(w)): i for i, w in enumerate(out)}
        for fut in as_completed(futs):
            idx = futs[fut]
            try:
                out[idx] = fut.result()
            except Exception:
                pass
    return out
