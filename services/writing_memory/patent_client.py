"""
Patent search MVP (Module 6).

Priority: USPTO Open Data Portal (USPTO_ODP_API_KEY) → PatentsView v2 → portal link fallback.

Legacy api.patentsview.org returns HTML (migrated to ODP, Mar 2026). Link fallback keeps MVP usable without keys.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.parse import quote_plus

import requests

_PV_LEGACY = "https://api.patentsview.org/patents/query"
_PV_V2 = "https://search.patentsview.org/api/v1/patent/"
_USPTO_ODP_SEARCH = "https://api.uspto.gov/api/v1/patent/applications/search"
_USPTO_ODP_APP = "https://api.uspto.gov/api/v1/patent/applications"
_TIMEOUT = 30
_FACTS_NOTICE = (
    "[inferred] Patent hits are prior-art references for writing — not legal or FTO advice. "
    "Verify with counsel before filing or product decisions."
)


def patent_config() -> dict[str, Any]:
    odp = bool((os.environ.get("USPTO_ODP_API_KEY") or "").strip())
    return {
        "configured": True,
        "patent_search": True,
        "sequence_search": False,
        "odp_configured": odp,
        "source": "uspto_odp" if odp else "portal_links",
        "link_fallback": not odp,
    }


def _is_json_response(r: requests.Response) -> bool:
    ct = (r.headers.get("content-type") or "").lower()
    return "json" in ct or (r.text or "").lstrip().startswith(("{", "["))


def _odp_headers() -> dict[str, str] | None:
    key = (os.environ.get("USPTO_ODP_API_KEY") or "").strip()
    if not key:
        return None
    return {
        "x-api-key": key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _normalize_app_no(patent_id: str) -> str:
    return re.sub(r"\D", "", (patent_id or "").strip())


def _first_mapping(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                return item
    return {}


def _dig(data: Any, *path: str) -> Any:
    cur = data
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _merge_odp_bibliographic(out: dict[str, Any], payload: dict[str, Any]) -> None:
    """Flatten common ODP wrapper / meta-data shapes into display fields."""
    meta = payload.get("applicationMetaData")
    if meta is None and "patentFileWrapperDataBag" in payload:
        bag = payload.get("patentFileWrapperDataBag")
        row = _first_mapping(bag)
        meta = row.get("applicationMetaData") if row else None
    meta = _first_mapping(meta) if meta is not None else payload

    title = (meta.get("inventionTitle") or meta.get("patentTitle") or "").strip()
    if title:
        out["title"] = title
    if meta.get("filingDate"):
        out["filing_date"] = meta.get("filingDate")
    if meta.get("patentNumber") or meta.get("patentNumberText"):
        out["patent_number"] = meta.get("patentNumber") or meta.get("patentNumberText")
    if meta.get("applicationStatusDescription") or meta.get("statusDescription"):
        out["status"] = meta.get("applicationStatusDescription") or meta.get("statusDescription")
    if meta.get("groupArtUnitNumber"):
        out["art_unit"] = meta.get("groupArtUnitNumber")
    if meta.get("examinerNameText"):
        out["examiner"] = meta.get("examinerNameText")

    abstract = (meta.get("patentAbstract") or meta.get("abstractText") or "").strip()
    if abstract:
        out["abstract"] = abstract[:4000]

    applicants = meta.get("applicantBag") or meta.get("applicants") or meta.get("assigneeBag")
    names: list[str] = []
    if isinstance(applicants, list):
        for a in applicants[:6]:
            if not isinstance(a, dict):
                continue
            n = (
                a.get("applicantNameText")
                or a.get("organizationStandardName")
                or a.get("assigneeNameText")
                or a.get("partyName")
            )
            if n:
                names.append(str(n).strip())
    elif isinstance(applicants, dict):
        n = applicants.get("applicantNameText") or applicants.get("organizationStandardName")
        if n:
            names.append(str(n).strip())
    if names:
        out["assignee"] = "; ".join(names)

    inventors = meta.get("inventorBag") or meta.get("inventors")
    inv_names: list[str] = []
    if isinstance(inventors, list):
        for inv in inventors[:8]:
            if not isinstance(inv, dict):
                continue
            n = inv.get("inventorNameText") or inv.get("partyName")
            if n:
                inv_names.append(str(n).strip())
    if inv_names:
        out["inventors"] = "; ".join(inv_names)


# Administrative file-wrapper codes — hide from default UI (not substantive prior art).
_ADMIN_DOC_CODES = frozenset({
    "WFEE", "WCLM", "M903", "APP.FILE.REC", "WELCOME.LET", "CRFE", "N417", "NTC.PUB",
    "PETDEC", "OA.EMAIL", "IFEE", "SCORE", "COMP", "IDS", "RCEX",
})
_SEQ_LISTING_CODES = frozenset({
    "SEQLST", "SEQL", "SEQ.LIST", "SEQ.XML", "WSEQ", "SEQDATA", "SLST",
})


def fetch_patent_detail(patent_id: str) -> dict[str, Any]:
    """
    Bibliographic patent/application record for in-app display (server-side ODP proxy).
    Does not download PDFs — document list is metadata only.
    """
    app_no = _normalize_app_no(patent_id)
    if len(app_no) < 4:
        return {"ok": False, "error": "Invalid application or patent number", "verification_status": "unverified"}
    headers = _odp_headers()
    if not headers:
        return {
            "ok": False,
            "error": "USPTO_ODP_API_KEY not configured on server",
            "verification_status": "unverified",
            "application_number": app_no,
        }

    out: dict[str, Any] = {
        "ok": False,
        "application_number": app_no,
        "source": "uspto_odp",
        "verification_status": "verified",
        "view_url": f"https://patents.google.com/patent/US{app_no}" if len(app_no) <= 8 else None,
    }
    warnings: list[str] = []

    for suffix in ("", "/meta-data"):
        url = f"{_USPTO_ODP_APP}/{app_no}{suffix}"
        try:
            r = requests.get(url, headers=headers, timeout=_TIMEOUT)
            if r.status_code == 404:
                continue
            r.raise_for_status()
            if not _is_json_response(r):
                warnings.append(f"Non-JSON from {suffix or 'wrapper'}")
                continue
            _merge_odp_bibliographic(out, r.json())
        except Exception as exc:
            warnings.append(str(exc))

    try:
        r = requests.get(f"{_USPTO_ODP_APP}/{app_no}/documents", headers=headers, timeout=_TIMEOUT)
        if r.ok and _is_json_response(r):
            data = r.json()
            bags = data.get("documentBag") or data.get("documents") or []
            if isinstance(bags, list):
                all_docs: list[dict[str, Any]] = []
                codes_seen: list[str] = []
                for d in bags:
                    if not isinstance(d, dict):
                        continue
                    code = (d.get("documentCode") or "").upper()
                    if code:
                        codes_seen.append(code)
                    all_docs.append({
                        "code": d.get("documentCode"),
                        "date": d.get("officialDate"),
                        "description": (
                            d.get("documentDescription")
                            or d.get("documentCodeDescription")
                            or d.get("documentCode")
                        ),
                        "administrative": code in _ADMIN_DOC_CODES,
                    })
                substantive = [x for x in all_docs if not x.get("administrative")]
                try:
                    from .patent_sequences import sequence_listing_status_from_bags

                    seq_st = sequence_listing_status_from_bags(bags)
                    out.update(seq_st)
                except Exception:
                    out["has_sequence_listing"] = any(c in _SEQ_LISTING_CODES for c in codes_seen)
                    out["sequence_listing_note"] = (
                        "Could not assess sequence listing availability from file wrapper."
                    )
                out["document_codes_seen"] = sorted(set(codes_seen))[:32]
                if substantive:
                    out["documents"] = substantive[:12]
                if len(all_docs) > len(substantive):
                    out["documents_admin_hidden"] = len(all_docs) - len(substantive)
    except Exception as exc:
        warnings.append(f"documents: {exc}")

    if out.get("patent_number"):
        pn = re.sub(r"\D", "", str(out["patent_number"]))
        if pn:
            out["view_url"] = f"https://patents.google.com/patent/US{pn}"

    out["ok"] = bool(
        out.get("title")
        or out.get("filing_date")
        or out.get("status")
        or out.get("documents")
    )
    if warnings:
        out["warnings"] = warnings
    if not out["ok"]:
        out["error"] = (
            "USPTO ODP returned no bibliographic fields for this number. "
            "Try a full application number from search results."
        )
        out["verification_status"] = "unverified"
    return out


def _odp_title_query(query: str) -> str:
    """ODP simple query string — see data.uspto.gov ODP-API-Query-Spec."""
    q = (query or "").strip().replace('"', " ")
    if len(q) < 2:
        return ""
    if " " in q:
        return f'applicationMetaData.inventionTitle:"{q}"'
    return f"applicationMetaData.inventionTitle:{q}"


def _parse_odp_row(row: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    app_no = row.get("applicationNumberText") or row.get("applicationNumber")
    meta = row.get("applicationMetaData")
    if isinstance(meta, list) and meta and isinstance(meta[0], dict):
        meta = meta[0]
    if not isinstance(meta, dict):
        meta = {}
    title = (meta.get("inventionTitle") or row.get("inventionTitle") or "").strip()
    if not title:
        title = f"Application {app_no}" if app_no else "USPTO application"
    filing = meta.get("filingDate") or row.get("filingDate")
    patent_no = meta.get("patentNumber") or meta.get("patentNumberText")
    if patent_no:
        pn = re.sub(r"\D", "", str(patent_no))
        url = f"https://patents.google.com/patent/US{pn}" if pn else None
    elif app_no:
        url = f"https://patents.google.com/?oq={app_no}"
    else:
        url = None
    return {
        "patent_id": patent_no or app_no,
        "title": title,
        "date": filing,
        "abstract": "",
        "assignee": "",
        "url": url,
        "source": "uspto_odp",
        "verification_status": "verified",
    }


def _search_uspto_odp(query: str, *, limit: int) -> list[dict[str, Any]]:
    key = (os.environ.get("USPTO_ODP_API_KEY") or "").strip()
    qdsl = _odp_title_query(query)
    if not key or not qdsl:
        return []
    headers = {
        "x-api-key": key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = {
        "q": qdsl,
        "pagination": {"offset": 0, "limit": limit},
        "fields": [
            "applicationNumberText",
            "applicationMetaData.inventionTitle",
            "applicationMetaData.filingDate",
            "applicationMetaData.patentNumber",
        ],
    }
    r = requests.post(_USPTO_ODP_SEARCH, json=body, headers=headers, timeout=_TIMEOUT)
    r.raise_for_status()
    if not _is_json_response(r):
        return []
    data = r.json()
    rows = data.get("patentFileWrapperDataBag") or data.get("results") or []
    if not isinstance(rows, list):
        return []
    patents: list[dict[str, Any]] = []
    for row in rows[:limit]:
        parsed = _parse_odp_row(row)
        if parsed:
            patents.append(parsed)
    return patents


def _search_patentsview_v2(query: str, *, limit: int) -> list[dict[str, Any]]:
    pv_q = {
        "_or": [
            {"_text_any": {"patent_title": query}},
            {"_text_any": {"patent_abstract": query}},
        ]
    }
    params = {
        "q": json.dumps(pv_q),
        "f": "patent_id,patent_title,patent_date,patent_abstract,assignee_organization",
        "o": json.dumps({"size": limit}),
    }
    r = requests.get(_PV_V2, params=params, timeout=_TIMEOUT)
    r.raise_for_status()
    if not _is_json_response(r):
        return []
    data = r.json()
    raw = []
    if isinstance(data, dict):
        raw = data.get("patents") or data.get("data") or []
    if not isinstance(raw, list):
        return []
    patents: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        pid = row.get("patent_id") or row.get("patent_number")
        title = (row.get("patent_title") or "").strip() or f"Patent {pid}"
        assignees = row.get("assignee_organization") or []
        if isinstance(assignees, list):
            org = ", ".join(str(a) for a in assignees[:3] if a)
        else:
            org = str(assignees) if assignees else ""
        patents.append({
            "patent_id": pid,
            "title": title,
            "date": row.get("patent_date"),
            "abstract": (row.get("patent_abstract") or "")[:400],
            "assignee": org,
            "url": f"https://patents.google.com/patent/US{pid}" if pid else None,
            "source": "patentsview_v2",
            "verification_status": "verified",
        })
    return patents


def _search_legacy_patentsview(query: str, *, limit: int) -> list[dict[str, Any]]:
    pv_q = {
        "_or": [
            {"_text_any": {"patent_title": query}},
            {"_text_any": {"patent_abstract": query}},
        ]
    }
    fields = ["patent_id", "patent_title", "patent_date", "patent_abstract", "assignee_organization"]
    params = {
        "q": json.dumps(pv_q),
        "f": json.dumps(fields),
        "o": json.dumps({"per_page": limit}),
    }
    r = requests.get(_PV_LEGACY, params=params, timeout=_TIMEOUT)
    r.raise_for_status()
    if not _is_json_response(r):
        return []
    data = r.json()
    raw = data.get("patents") if isinstance(data, dict) else []
    if not isinstance(raw, list):
        return []
    patents: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        pid = row.get("patent_id") or row.get("patent_number")
        title = (row.get("patent_title") or "").strip() or f"Patent {pid}"
        patents.append({
            "patent_id": pid,
            "title": title,
            "date": row.get("patent_date"),
            "abstract": (row.get("patent_abstract") or "")[:400],
            "assignee": "",
            "url": f"https://patents.google.com/patent/US{pid}" if pid else None,
            "source": "uspto_patentsview",
            "verification_status": "verified",
        })
    return patents


def _search_portal_links(query: str) -> list[dict[str, Any]]:
    q = quote_plus(query)
    portals = [
        ("Google Patents", f"https://patents.google.com/?q={q}"),
        ("USPTO Open Data Portal", f"https://data.uspto.gov/"),
        ("Lens.org", f"https://www.lens.org/lens/search/patent/list?q={q}"),
        ("Espacenet", f"https://worldwide.espacenet.com/patent/search?q={q}"),
    ]
    return [
        {
            "patent_id": None,
            "title": f"{name} — search: {query}",
            "date": None,
            "abstract": "Open this portal to review matching patent applications (external search).",
            "assignee": "",
            "url": url,
            "source": "portal_link",
            "verification_status": "unverified",
        }
        for name, url in portals
    ]


def search_patents(query: str, *, limit: int = 10) -> dict[str, Any]:
    q = (query or "").strip()
    if len(q) < 2:
        return {"patents": [], "count": 0, "query": q}
    limit = max(1, min(limit, 25))
    patents: list[dict[str, Any]] = []
    source = "portal_links"
    note = None
    for fn in (_search_uspto_odp, _search_patentsview_v2, _search_legacy_patentsview):
        try:
            batch = fn(q, limit=limit)
            if batch:
                patents = batch
                source = batch[0].get("source", "uspto")
                break
        except Exception:
            continue
    if not patents:
        patents = _search_portal_links(q)[: min(4, limit)]
        source = "portal_links"
        if (os.environ.get("USPTO_ODP_API_KEY") or "").strip():
            note = (
                "[unverified] USPTO ODP key is set but search returned no structured rows "
                "(check key permissions, rate limits, or query). Portal links below."
            )
        else:
            note = (
                "[unverified] Structured USPTO API unavailable — portal search links only. "
                "Configure USPTO_ODP_API_KEY (data.uspto.gov) for in-app patent rows."
            )
    return {
        "patents": patents,
        "count": len(patents),
        "query": q,
        "total_found": len(patents),
        "verification_status": "verified" if source != "portal_links" else "unverified",
        "source": source,
        "note": note,
    }


def search_patent_sequence_keywords(sequence: str, *, limit: int = 8) -> dict[str, Any]:
    """MVP: no sequence BLAST API — search patent text using motif/token keywords."""
    seq = re.sub(r"\s+", "", (sequence or "").upper())
    if len(seq) < 8:
        return {
            "patents": [],
            "count": 0,
            "query": sequence,
            "note": "Sequence too short; provide at least 8 residues.",
            "sequence_search": False,
        }
    keywords = []
    if len(seq) >= 12:
        keywords.append(seq[:12])
    if "CDR" in seq or len(seq) > 20:
        keywords.append("antibody CDR")
    keywords.append("antibody variable region")
    merged: dict[str, dict[str, Any]] = {}
    for kw in keywords[:3]:
        try:
            batch = search_patents(kw, limit=limit)
            for p in batch.get("patents") or []:
                key = str(p.get("patent_id") or p.get("title"))
                merged[key] = p
        except Exception:
            continue
    patents = list(merged.values())[:limit]
    return {
        "patents": patents,
        "count": len(patents),
        "query": sequence[:80] + ("…" if len(sequence) > 80 else ""),
        "keywords_tried": keywords,
        "note": (
            "MVP: keyword proxy only — full sequence homology search (WIPO/USPTO BLAST) planned. "
            "Use results as leads, not FTO clearance."
        ),
        "sequence_search": False,
        "verification_status": "inferred",
    }


def format_patents_for_facts(patents: list[dict[str, Any]], *, heading: str) -> str:
    if not patents:
        return ""
    lines = [heading, _FACTS_NOTICE, ""]
    for p in patents[:15]:
        line = f"- **{p.get('title', 'Untitled')}**"
        if p.get("patent_id"):
            line += f" (US {p['patent_id']})"
        if p.get("assignee"):
            line += f" — {p['assignee']}"
        if p.get("url"):
            line += f" — {p['url']}"
        lines.append(line)
        ab = (p.get("abstract") or "").strip()
        if ab:
            lines.append(f"  Abstract (excerpt): {ab[:280]}…" if len(ab) > 280 else f"  Abstract: {ab}")
    return "\n".join(lines)
