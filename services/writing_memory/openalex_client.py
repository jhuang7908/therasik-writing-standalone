"""
OpenAlex API client (Module 5 — literature radar, Phase 2).

Free API: https://openalex.org/docs
Set OPENALEX_EMAIL for polite pool (recommended).
"""
from __future__ import annotations

import html
import os
import re
from typing import Any

import requests

_OPENALEX = "https://api.openalex.org"
_TIMEOUT = 25
_HEADERS = {
    "User-Agent": "InSynBio-WritingMemory/1.0 (+https://insynbio.com; metadata lookup)",
}


def openalex_config() -> dict[str, Any]:
    email = (os.environ.get("OPENALEX_EMAIL") or os.environ.get("CROSSREF_EMAIL") or "").strip()
    return {"configured": True, "polite_email_set": bool(email)}


def _params(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    p: dict[str, Any] = {}
    email = (os.environ.get("OPENALEX_EMAIL") or os.environ.get("CROSSREF_EMAIL") or "").strip()
    if email:
        p["mailto"] = email
    if extra:
        p.update(extra)
    return p


def _reconstruct_abstract(inv: dict[str, Any] | None, max_chars: int = 1500) -> str | None:
    """Rebuild an abstract from OpenAlex' abstract_inverted_index."""
    if not isinstance(inv, dict) or not inv:
        return None
    positions: list[tuple[int, str]] = []
    for word, idxs in inv.items():
        if isinstance(idxs, list):
            for i in idxs:
                if isinstance(i, int):
                    positions.append((i, word))
    if not positions:
        return None
    positions.sort(key=lambda x: x[0])
    text = " ".join(w for _, w in positions).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "…"
    return text or None


def _authors_str(authorships: Any, limit: int = 3) -> str | None:
    if not isinstance(authorships, list) or not authorships:
        return None
    names = []
    for a in authorships:
        if isinstance(a, dict):
            nm = (a.get("author") or {}).get("display_name")
            if nm:
                names.append(nm)
    if not names:
        return None
    head = ", ".join(names[:limit])
    if len(names) > limit:
        head += " et al."
    return head


def _clean_doi(doi: str | None) -> str:
    return (doi or "").strip().replace("https://doi.org/", "").replace("http://dx.doi.org/", "")


_ARTICLE_TYPE_CACHE: dict[str, str] = {}


def oa_type_to_article_type(oa_type: str | None) -> str:
    t = (oa_type or "").strip().lower()
    if t == "review":
        return "review"
    if t in {"letter", "editorial"}:
        return "letter"
    return "research"


def _pub_types_to_article_type(pub_types: list[Any]) -> str:
    from .intelligence_store import pubmed_pub_types_to_m2_type

    return pubmed_pub_types_to_m2_type(pub_types)


def lookup_article_type(
    *,
    doi: str | None = None,
    openalex_id: str | None = None,
    pmid: str | None = None,
) -> dict[str, Any] | None:
    """Resolve article type from OpenAlex and/or PubMed publication types."""
    clean = _clean_doi(doi)
    pm = str(pmid or "").strip()
    oa_id = (openalex_id or "").strip() or None
    cache_key = (
        f"doi:{clean}" if clean else f"oa:{oa_id}" if oa_id else f"pmid:{pm}" if pm else None
    )
    if cache_key and cache_key in _ARTICLE_TYPE_CACHE:
        cached = _ARTICLE_TYPE_CACHE[cache_key]
        return {"article_type": cached} if cached else None

    result: dict[str, Any] | None = None
    candidates: list[str] = []
    if oa_id:
        candidates.append(oa_id)
    if clean:
        candidates.append(f"https://doi.org/{clean}")

    for ident in candidates:
        try:
            r = requests.get(
                f"{_OPENALEX}/works/{ident}",
                params=_params(),
                headers=_HEADERS,
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            work = r.json()
            oa_type = (work.get("type") or "").strip().lower()
            at = oa_type_to_article_type(oa_type)
            result = {
                "article_type": at,
                "type": oa_type or None,
                "openalex_id": work.get("id"),
            }
            ids = work.get("ids") or {}
            pmid_url = ids.get("pmid")
            if pmid_url and not pm:
                pm = str(pmid_url).replace("https://pubmed.ncbi.nlm.nih.gov/", "").strip()
            if at != "research":
                break
        except Exception:
            continue

    if pm:
        try:
            from .references import pubmed_client

            rec = pubmed_client.fetch_by_pmid(pm)
            if rec and rec.pub_types:
                pts = list(rec.pub_types)
                pt_at = _pub_types_to_article_type(pts)
                result = result or {}
                result["pub_types"] = pts
                oa_at = (result.get("article_type") or "research").strip().lower()
                if pt_at != "research" or oa_at == "research":
                    result["article_type"] = pt_at if pt_at != "research" else oa_at
        except Exception:
            pass

    if cache_key and result and result.get("article_type"):
        _ARTICLE_TYPE_CACHE[cache_key] = str(result["article_type"])
    return result


def _strip_html_text(text: str, max_chars: int = 2500) -> str | None:
    s = html.unescape(text or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_chars:
        s = s[:max_chars].rsplit(" ", 1)[0] + "…"
    return s or None


def _work_to_ui(w: dict[str, Any]) -> dict[str, Any] | None:
    title = (w.get("title") or "").strip()
    if not title:
        return None
    doi = _clean_doi(w.get("doi"))
    loc = w.get("primary_location") or {}
    venue = ((loc.get("source") or {}).get("display_name")) if isinstance(loc, dict) else None
    oa = w.get("open_access") or {}
    oa_url = oa.get("oa_url") if isinstance(oa, dict) else None
    oa_type = (w.get("type") or "").strip().lower()
    article_type = oa_type_to_article_type(oa_type)
    return {
        "openalex_id": w.get("id"),
        "title": title,
        "year": w.get("publication_year"),
        "doi": doi or None,
        "authors": _authors_str(w.get("authorships")),
        "venue": venue,
        "oa_url": oa_url,
        "abstract": _reconstruct_abstract(w.get("abstract_inverted_index")),
        "cited_by_count": w.get("cited_by_count"),
        "type": oa_type or None,
        "article_type": article_type,
        "verification_status": "verified",
        "source": "openalex",
    }


def _abstract_from_doi_page(doi: str, timeout: int = 20) -> tuple[str | None, str | None]:
    if not doi:
        return None, None
    url = f"https://doi.org/{doi}"
    try:
        r = requests.get(url, headers=_HEADERS, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
    except Exception:
        return None, None
    text = r.text or ""
    
    # 1. Look for meta tags
    for pat in (
        r'<meta\s+name=["\']citation_abstract["\']\s+content=["\'](.*?)["\']',
        r'<meta\s+content=["\'](.*?)["\']\s+name=["\']citation_abstract["\']',
        r'<meta\s+name=["\']dc\.description["\']\s+content=["\'](.*?)["\']',
        r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
        r'<meta\s+property=["\']og:description["\']\s+content=["\'](.*?)["\']',
        r'<meta\s+name=["\']abstract["\']\s+content=["\'](.*?)["\']',
        r'<meta\s+name=["\']eprints\.abstract["\']\s+content=["\'](.*?)["\']',
    ):
        m = re.search(pat, text, flags=re.I | re.S)
        if m:
            abs_text = _strip_html_text(m.group(1))
            if abs_text and len(abs_text) > 80:
                return abs_text, r.url
    
    # 2. Look for common abstract containers (aggressive fallback)
    # ScienceDirect, Wiley, Springer, etc. often use these
    for pat in (
        r'<div[^>]+class=["\'][^"\']*(?:abstract|abs-content|article-abstract|abstract-text)[^"\']*["\'][^>]*>(.*?)</div>',
        r'<section[^>]+class=["\'][^"\']*(?:abstract|abs-content)[^"\']*["\'][^>]*>(.*?)</section>',
        r'<div[^>]+id=["\'][^"\']*(?:abstract|abs-content)[^"\']*["\'][^>]*>(.*?)</div>',
        r'<div[^>]+class=["\'][^"\']*(?:AbstractSection)[^"\']*["\'][^>]*>(.*?)</div>',
    ):
        m = re.search(pat, text, flags=re.I | re.S)
        if m:
            inner = m.group(1)
            # Remove nested tags like <h3>Abstract</h3>
            inner = re.sub(r'<h[1-6][^>]*>.*?</h[1-6]>', '', inner, flags=re.I | re.S)
            abs_text = _strip_html_text(inner)
            if abs_text and len(abs_text) > 100:
                return abs_text, r.url

    return None, r.url


def _eager_fill_missing_abstracts(works: list[dict[str, Any]], limit: int = 5) -> int:
    """Best-effort DOI page metadata fill so details render abstracts immediately."""
    filled = 0
    for item in works:
        if filled >= limit:
            break
        if item.get("abstract") or not item.get("doi"):
            continue
        abs_text, landing = _abstract_from_doi_page(str(item.get("doi") or ""), timeout=5)
        if abs_text:
            item["abstract"] = abs_text
            item["abstract_source"] = "doi_landing_page"
            item["abstract_url"] = landing
            filled += 1
    return filled


def resolve_abstract(doi: str | None = None, openalex_id: str | None = None) -> dict[str, Any]:
    """Resolve a missing abstract from OpenAlex, PubMed, or DOI landing page."""
    clean_doi = _clean_doi(doi)
    
    # 1. Try PubMed first if we can find a PMID (often most reliable)
    pmid = None
    if clean_doi:
        try:
            from .references import pubmed_client
            pmids = pubmed_client.esearch(f'"{clean_doi}"[DOI]', max_results=1)
            if pmids:
                pmid = pmids[0]
        except Exception:
            pass
    
    if pmid:
        try:
            from .references import pubmed_client
            rec = pubmed_client.fetch_by_pmid(pmid)
            if rec and rec.abstract:
                return {"ok": True, "abstract": rec.abstract, "source": "pubmed", "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"}
        except Exception:
            pass

    # 2. Try OpenAlex
    candidates = []
    if openalex_id:
        candidates.append(str(openalex_id))
    if clean_doi:
        candidates.append(f"https://doi.org/{clean_doi}")
    for ident in candidates:
        try:
            r = requests.get(f"{_OPENALEX}/works/{ident}", params=_params(), headers=_HEADERS, timeout=_TIMEOUT)
            r.raise_for_status()
            work = r.json()
            if not pmid:
                for key, val in work.get("ids", {}).items():
                    if key == "pmid":
                        pmid = val.replace("https://pubmed.ncbi.nlm.nih.gov/", "")
                        break
            
            abs_text = _reconstruct_abstract(work.get("abstract_inverted_index"), max_chars=2500)
            if abs_text:
                return {"ok": True, "abstract": abs_text, "source": "openalex", "url": work.get("id")}
        except Exception:
            continue
            
    # 3. If OpenAlex gave us a PMID but no abstract, try PubMed now
    if pmid:
        try:
            from .references import pubmed_client
            rec = pubmed_client.fetch_by_pmid(pmid)
            if rec and rec.abstract:
                return {"ok": True, "abstract": rec.abstract, "source": "pubmed", "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"}
        except Exception:
            pass

    # 4. Scrape from DOI landing page
    abs_text, landing = _abstract_from_doi_page(clean_doi)
    if abs_text:
        return {"ok": True, "abstract": abs_text, "source": "doi_landing_page", "url": landing}
    return {"ok": False, "abstract": None, "source": None, "url": landing if clean_doi else None}


def search_works(
    query: str,
    *,
    per_page: int = 10,
    from_publication_date: str | None = None,
    work_type: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    sort: str = "relevance_score:desc",
) -> dict[str, Any]:
    """
    Search works by keyword (OpenAlex ``search`` filter).

    Default sort is **relevance** (``relevance_score:desc``) so keyword queries
    return on-topic papers rather than merely the newest ones. Callers wanting a
    recency feed (literature radar) can pass ``sort="publication_date:desc"``.
    Returns an enriched, de-duplicated, normalized list for the UI.
    """
    q = (query or "").strip()
    if len(q) < 2:
        return {"works": [], "count": 0, "query": q}
    # Relevance sort is only valid alongside a search term (always true here).
    params = _params({
        "search": q,
        "per-page": max(1, min(per_page, 25)),
        "sort": sort or "relevance_score:desc",
    })
    
    filters = []
    if from_publication_date:
        filters.append(f"from_publication_date:{from_publication_date}")
    if work_type:
        filters.append(f"type:{work_type}")
    if year_min or year_max:
        y_min = year_min or 1900
        y_max = year_max or 2100
        filters.append(f"publication_year:{y_min}-{y_max}")
    
    if filters:
        params["filter"] = ",".join(filters)
        
    r = requests.get(f"{_OPENALEX}/works", params=params, timeout=_TIMEOUT)
    r.raise_for_status()
    payload = r.json()
    results = payload.get("results") or []
    works = []
    seen: set[str] = set()
    for w in results:
        if not isinstance(w, dict):
            continue
        title = (w.get("title") or "").strip()
        if not title:
            continue
        # Dedup on normalized title (same title ≈ same paper, incl. repo copies).
        dedup_key = " ".join(title.lower().split())
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        item = _work_to_ui(w)
        if item:
            works.append(item)
    eager_abstracts = _eager_fill_missing_abstracts(works, limit=5)
    up_meta: dict[str, Any] = {}
    try:
        from . import unpaywall_client

        works = unpaywall_client.enrich_works(works)
        up_meta = unpaywall_client.unpaywall_config()
    except Exception:
        pass

    return {
        "works": works,
        "count": len(works),
        "query": q,
        "meta": {
            "count_in_response": payload.get("meta", {}).get("count"),
            "unpaywall": up_meta,
            "eager_abstracts_filled": eager_abstracts,
        },
    }
