"""
protocols.io API v3/v4 client — Module 2 (public search) + Module 3 (workspace SOP list).

Configure:
  PROTOCOLSIO_ACCESS_TOKEN   Client token from https://www.protocols.io/developers
  PROTOCOLSIO_WORKSPACE_URI  Lab workspace slug (default: insynbio)

Docs: https://apidocs.protocols.io/
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

_HERE = Path(__file__).resolve().parent
_QUEUE_DIR = Path(
    os.environ.get("PROTOCOLSIO_QUEUE_DIR", str(_HERE / "data" / "lab_sop_queue"))
)

# protocols.io indexes English protocol text; expand common CN lab terms for search.
_CN_TO_EN: dict[str, str] = {
    "小鼠": "mouse",
    "大鼠": "rat",
    "鼠": "mouse",
    "人源": "human",
    "人类": "human",
    "细胞": "cell",
    "流式": "flow cytometry",
    "免疫组化": "immunohistochemistry",
    "western": "western blot",
    "蛋白": "protein",
    "基因": "gene",
}

_API_V3 = "https://www.protocols.io/api/v3"
_API_V4 = "https://www.protocols.io/api/v4"
_TIMEOUT = 30


def default_workspace_uri() -> str:
    return (os.environ.get("PROTOCOLSIO_WORKSPACE_URI") or "insynbio").strip() or "insynbio"


def protocolsio_config() -> dict[str, Any]:
    token = (os.environ.get("PROTOCOLSIO_ACCESS_TOKEN") or "").strip()
    ws = default_workspace_uri()
    return {
        "configured": bool(token),
        "public_search": bool(token),
        "workspace_uri": ws,
        "workspace_url": f"https://www.protocols.io/workspace/{ws}",
    }


def _auth_headers() -> dict[str, str]:
    token = (os.environ.get("PROTOCOLSIO_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("PROTOCOLSIO_ACCESS_TOKEN is not set")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def search_public_protocols(
    query: str,
    *,
    page_size: int = 10,
    page_id: int = 1,
    order_field: str = "activity",
) -> dict[str, Any]:
    """Search public protocols on protocols.io by keyword.

    Note: ``order_field=relevance`` currently returns HTTP 400 from protocols.io
    (server-side SQL error). Use ``activity`` (API default) until fixed upstream.
    """
    q = (query or "").strip()
    if len(q) < 2:
        return {"items": [], "total": 0, "query": q}
    params = {
        "filter": "public",
        "key": q,
        "order_field": order_field,
        "order_dir": "desc",
        "page_size": max(1, min(page_size, 25)),
        "page_id": max(1, page_id),
    }
    r = requests.get(
        f"{_API_V3}/protocols",
        headers=_auth_headers(),
        params=params,
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    items = data.get("items") if isinstance(data, dict) else []
    if not isinstance(items, list):
        items = []
    normalized = [_normalize_protocol_row(x) for x in items if isinstance(x, dict)]
    return {
        "items": normalized,
        "total": data.get("total", len(normalized)) if isinstance(data, dict) else len(normalized),
        "total_pages": data.get("total_pages", 1) if isinstance(data, dict) else 1,
        "query": q,
        "page_id": page_id,
        "verification_status": "verified",
        "source": "protocols.io",
    }


def expand_search_queries(raw: str) -> list[str]:
    """Build alternate English queries (protocols.io is sparse for niche in vivo terms)."""
    q = (raw or "").strip()
    if len(q) < 2:
        return []
    seen: set[str] = set()
    out: list[str] = []

    def _add(s: str) -> None:
        s = " ".join((s or "").split())
        if len(s) >= 2 and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)

    _add(q)
    en = q
    for cn, eng in _CN_TO_EN.items():
        en = en.replace(cn, f" {eng} ")
    en = re.sub(r"[\u4e00-\u9fff\u3040-\u30ff]+", " ", en)
    en = " ".join(en.split())
    if en and en.lower() != q.lower():
        _add(en)
    blob = f"{q} {en}".lower()
    for gene in re.findall(r"(?i)cd\d+", blob):
        g = gene.upper()
        _add(g)
        _add(f"{g} positive cell isolation")
        _add(f"{g} hematopoietic stem cell")
        _add(f"{g} PBMC")
    if "pbmc" in blob:
        _add("PBMC isolation")
        _add("peripheral blood mononuclear cell isolation")
        _add("Ficoll PBMC")
    if "mouse" in blob or "mice" in blob:
        _add("mouse hematopoietic stem cell isolation")
        _add("murine PBMC isolation")
    if "cd34" in blob and ("mouse" in blob or "mice" in blob):
        _add("CD34 humanized mice")
        _add("human CD34 xenograft HSPC")
        _add("CD34 positive cell nucleofection")
    if "stem" in blob or "hspc" in blob or "cd34" in blob:
        _add("hematopoietic stem cell isolation")
    words = [w for w in re.findall(r"[a-z0-9]+", q.lower()) if len(w) >= 3 and w not in ("and", "the", "for")]
    if len(words) >= 2:
        _add(" ".join(words[:4]))
        for w in words[:5]:
            _add(w)
    return out[:10]


def _query_tokens(query: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (query or "").lower()) if len(t) >= 2}


def score_protocol_relevance(protocol: dict[str, Any], query: str) -> float:
    tokens = _query_tokens(query)
    if not tokens:
        return 0.0
    title = ((protocol.get("title") or "") + " " + (protocol.get("description") or "")).lower()
    score = 0.0
    for t in tokens:
        if t in title:
            score += 3.0 if title.find(t) < 40 else 1.5
    q_low = query.lower()
    if q_low and q_low in title:
        score += 5.0
    return score


def search_public_protocols_smart(
    query: str,
    *,
    page_size: int = 15,
    max_curated: int = 3,
    exhaust_variants: bool = False,
) -> dict[str, Any]:
    """Search with CN→EN fallbacks; rank and return curated subset for auto-import."""
    variants = expand_search_queries(query)
    if not variants:
        return {
            "items": [],
            "curated": [],
            "total": 0,
            "query": query,
            "search_attempts": [],
            "verification_status": "verified",
            "source": "protocols.io",
        }
    by_id: dict[int, dict[str, Any]] = {}
    attempts: list[dict[str, Any]] = []
    for i, sq in enumerate(variants):
        if i:
            time.sleep(0.35)
        try:
            batch = search_public_protocols(sq, page_size=page_size)
            n = len(batch.get("items") or [])
            attempts.append({"query": sq, "count": n})
            for it in batch.get("items") or []:
                pid = it.get("id")
                if pid is not None:
                    by_id[int(pid)] = it
            if not exhaust_variants and len(by_id) >= page_size:
                break
        except Exception as exc:
            attempts.append({"query": sq, "count": 0, "error": str(exc)[:120]})
    items = list(by_id.values())
    ranked = sorted(
        items,
        key=lambda p: score_protocol_relevance(p, query),
        reverse=True,
    )
    curated = [p for p in ranked if score_protocol_relevance(p, query) > 0][:max_curated]
    if not curated and ranked:
        curated = ranked[:max_curated]
    return {
        "items": ranked,
        "curated": curated,
        "total": len(ranked),
        "query": query,
        "search_attempts": attempts,
        "query_variants": variants,
        "verification_status": "verified",
        "source": "protocols.io",
    }


def curate_and_import_to_facts(
    query: str,
    *,
    max_curated: int = 3,
    fetch_steps_for_top: int = 1,
) -> dict[str, Any]:
    """Auto-pick top relevant public protocols and append to Facts."""
    found = search_public_protocols_smart(query, max_curated=max_curated)
    curated = found.get("curated") or []
    block = format_protocols_for_facts(
        curated,
        include_steps_for_first=min(fetch_steps_for_top, len(curated)),
        scope="public_reference",
    )
    if curated:
        header = (
            f"<!-- Curated for query: {query} | variants: "
            + ", ".join(found.get("query_variants") or [])[:200]
            + " -->"
        )
        block = header + "\n" + block
    return {
        "facts_block": block,
        "count": len(curated),
        "query": query,
        "protocols": curated,
        "search_attempts": found.get("search_attempts"),
        "query_variants": found.get("query_variants"),
        "verification_status": "verified",
        "source": "protocols.io",
        "scope": "public_search_curated",
    }


def _normalize_protocol_row(row: dict[str, Any]) -> dict[str, Any]:
    pid = row.get("id")
    uri = row.get("uri") or ""
    link = row.get("link") or (f"https://www.protocols.io/view/{uri}" if uri else None)
    if not link and pid:
        link = f"https://www.protocols.io/view/{pid}"
    authors = row.get("authors") or []
    author_names = []
    for a in authors[:5]:
        if isinstance(a, dict) and a.get("name"):
            author_names.append(str(a["name"]))
    desc = row.get("description") or ""
    if isinstance(desc, str) and len(desc) > 400:
        desc = desc[:400] + "…"
    return {
        "id": pid,
        "uri": uri,
        "title": (row.get("title") or "").strip() or f"protocol-{pid}",
        "description": desc,
        "authors": author_names,
        "url": link,
        "doi": row.get("doi"),
        "source": "protocols.io",
    }


def get_protocol_steps(protocol_id: int | str) -> list[dict[str, Any]]:
    """Fetch step list for one protocol (v4 API)."""
    r = requests.get(
        f"{_API_V4}/protocols/{protocol_id}/steps",
        headers=_auth_headers(),
        params={"content_format": "markdown"},
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    steps = data.get("steps") if isinstance(data, dict) else []
    if not isinstance(steps, list):
        return []
    out = []
    for i, s in enumerate(steps, 1):
        if not isinstance(s, dict):
            continue
        step = s.get("step") if isinstance(s.get("step"), dict) else s
        text = ""
        if isinstance(step, dict):
            text = (step.get("markdown") or step.get("html") or step.get("text") or "").strip()
        elif isinstance(step, str):
            text = step.strip()
        if len(text) > 500:
            text = text[:500] + "…"
        out.append({"index": i, "text": text})
    return out


_FACTS_MATERIAL_NOTICE = (
    "[inferred] Writing material only — do not paste verbatim into the manuscript. "
    "Rewrite for the target journal (concise Methods prose; cite source protocol/SOP)."
)


def format_protocols_for_facts(
    protocols: list[dict[str, Any]],
    *,
    include_steps_for_first: int = 0,
    scope: str = "public_reference",
) -> str:
    """Build Facts / Methods reference block from search hits (not manuscript text)."""
    if not protocols:
        return "## Public protocols (protocols.io)\n\n[No protocols found for this query.]"
    if scope == "lab_sop":
        heading = "## Lab SOP reference (protocols.io workspace)"
        provenance = "[verified] From InSynBio lab workspace on protocols.io — primary SOP source of record."
    else:
        heading = "## External protocol reference (protocols.io public)"
        provenance = (
            "[verified] Public protocols.io entries — use as background/reference; "
            "journal Methods are abbreviated vs. full SOP steps."
        )
    lines = [
        heading,
        provenance,
        _FACTS_MATERIAL_NOTICE,
        "",
    ]
    for i, p in enumerate(protocols[:15], 1):
        title = p.get("title") or "Untitled"
        url = p.get("url") or ""
        authors = ", ".join(p.get("authors") or []) or "unknown"
        line = f"- **{title}** (authors: {authors})"
        if url:
            line += f" — {url}"
        if p.get("doi"):
            line += f" DOI: {p['doi']}"
        desc = (p.get("description") or "").strip()
        if desc:
            line += f"\n  Summary: {desc}"
        lines.append(line)
        if include_steps_for_first > 0 and i <= include_steps_for_first and p.get("id"):
            try:
                steps = get_protocol_steps(p["id"])
                if steps:
                    lines.append("  Key steps (abbrev.):")
                    for st in steps[:8]:
                        if st.get("text"):
                            lines.append(f"    {st['index']}. {st['text']}")
            except Exception:
                lines.append("  (steps not fetched — open URL for full procedure)")
    return "\n".join(lines)


def import_search_to_facts(
    query: str,
    *,
    limit: int = 5,
    fetch_steps_for_top: int = 1,
) -> dict[str, Any]:
    found = search_public_protocols(query, page_size=limit)
    items = found.get("items") or []
    block = format_protocols_for_facts(
        items,
        include_steps_for_first=min(fetch_steps_for_top, len(items)),
        scope="public_reference",
    )
    return {
        "facts_block": block,
        "count": len(items),
        "query": query,
        "protocols": items,
        "verification_status": "verified",
        "source": "protocols.io",
        "scope": "public_search",
    }


def import_selected_protocols_to_facts(
    protocols: list[dict[str, Any]],
    *,
    scope: str = "public_reference",
    fetch_steps_for_top: int = 1,
) -> dict[str, Any]:
    """Import user-selected protocol rows into Facts (writing material, not draft text)."""
    items = [_normalize_protocol_row(p) for p in protocols if isinstance(p, dict) and p.get("id")]
    if not items:
        return {
            "facts_block": "",
            "count": 0,
            "protocols": [],
            "verification_status": "verified",
            "source": "protocols.io",
            "scope": scope,
        }
    block = format_protocols_for_facts(
        items,
        include_steps_for_first=min(fetch_steps_for_top, len(items)),
        scope=scope,
    )
    return {
        "facts_block": block,
        "count": len(items),
        "protocols": items,
        "verification_status": "verified",
        "source": "protocols.io",
        "scope": scope,
    }


def list_workspace_protocols(
    workspace_uri: str | None = None,
    *,
    key: str = "",
    page_size: int = 15,
    page_id: int = 1,
) -> dict[str, Any]:
    """List public protocols published in an protocols.io workspace (Module 3 SOP catalog)."""
    ws = (workspace_uri or default_workspace_uri()).strip()
    params: dict[str, Any] = {
        "page_size": max(1, min(page_size, 25)),
        "page_id": max(1, page_id),
    }
    q = (key or "").strip()
    if q:
        params["key"] = q
    r = requests.get(
        f"{_API_V3}/workspaces/{ws}/protocols",
        headers=_auth_headers(),
        params=params,
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    items = data.get("items") if isinstance(data, dict) else []
    if not isinstance(items, list):
        items = []
    normalized = [_normalize_protocol_row(x) for x in items if isinstance(x, dict)]
    pag = data.get("pagination") if isinstance(data, dict) else {}
    total = len(normalized)
    if isinstance(pag, dict) and pag.get("total_results") is not None:
        total = pag.get("total_results", total)
    return {
        "items": normalized,
        "total": total,
        "workspace_uri": ws,
        "workspace_url": f"https://www.protocols.io/workspace/{ws}",
        "query": q,
        "page_id": page_id,
        "verification_status": "verified",
        "source": "protocols.io",
        "scope": "workspace_public",
    }


def format_workspace_protocols_for_facts(
    protocols: list[dict[str, Any]],
    *,
    workspace_uri: str,
    include_steps_for_first: int = 0,
) -> str:
    if not protocols:
        return (
            f"## Lab SOPs (protocols.io workspace: {workspace_uri})\n\n"
            "[No public protocols in this workspace yet. Create or publish SOPs on protocols.io.]"
        )
    lines = [
        f"## Lab SOPs (protocols.io workspace: {workspace_uri})",
        "[verified] Listed from InSynBio lab workspace on protocols.io — cite URL/DOI in Methods.",
        _FACTS_MATERIAL_NOTICE,
        "",
    ]
    for i, p in enumerate(protocols[:15], 1):
        title = p.get("title") or "Untitled"
        url = p.get("url") or ""
        line = f"- **{title}**"
        if url:
            line += f" — {url}"
        if p.get("doi"):
            line += f" DOI: {p['doi']}"
        lines.append(line)
        if include_steps_for_first > 0 and i <= include_steps_for_first and p.get("id"):
            try:
                steps = get_protocol_steps(p["id"])
                if steps:
                    lines.append("  Steps (abbrev.):")
                    for st in steps[:8]:
                        if st.get("text"):
                            lines.append(f"    {st['index']}. {st['text']}")
            except Exception:
                lines.append("  (steps not fetched)")
    return "\n".join(lines)


def import_workspace_to_facts(
    workspace_uri: str | None = None,
    *,
    key: str = "",
    limit: int = 10,
    fetch_steps_for_top: int = 1,
) -> dict[str, Any]:
    ws = (workspace_uri or default_workspace_uri()).strip()
    found = list_workspace_protocols(ws, key=key, page_size=limit)
    items = found.get("items") or []
    block = format_workspace_protocols_for_facts(
        items,
        workspace_uri=ws,
        include_steps_for_first=min(fetch_steps_for_top, len(items)),
    )
    return {
        "facts_block": block,
        "count": len(items),
        "workspace_uri": ws,
        "workspace_url": found.get("workspace_url"),
        "query": key,
        "protocols": items,
        "verification_status": "verified",
        "source": "protocols.io",
        "scope": "workspace_public",
    }


def _queue_store_path(username: str, project_id: str | None) -> Path:
    safe_user = re.sub(r"[^\w.-]", "_", (username or "user").strip()) or "user"
    safe_proj = re.sub(r"[^\w.-]", "_", (project_id or "default").strip()) or "default"
    _QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    return _QUEUE_DIR / f"{safe_user}__{safe_proj}.json"


def list_workspace_sop_queue(
    username: str,
    project_id: str | None = None,
    *,
    workspace_uri: str | None = None,
) -> dict[str, Any]:
    """Pending public protocols queued for later fork into lab workspace (Module 3)."""
    ws = (workspace_uri or default_workspace_uri()).strip()
    path = _queue_store_path(username, project_id)
    if not path.is_file():
        return {
            "items": [],
            "count": 0,
            "workspace_uri": ws,
            "workspace_url": f"https://www.protocols.io/workspace/{ws}",
            "project_id": project_id,
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    items = data.get("items") if isinstance(data, dict) else []
    if not isinstance(items, list):
        items = []
    return {
        "items": items,
        "count": len(items),
        "workspace_uri": ws,
        "workspace_url": f"https://www.protocols.io/workspace/{ws}",
        "project_id": project_id,
        "updated_at": data.get("updated_at") if isinstance(data, dict) else None,
    }


def queue_protocols_for_workspace(
    username: str,
    protocols: list[dict[str, Any]],
    *,
    project_id: str | None = None,
    workspace_uri: str | None = None,
) -> dict[str, Any]:
    """
    Record customer-selected protocols for Module 3 SOP development.

    Full API fork is not available — each item stores view URL + status
    ``queued_for_fork`` until duplicated on protocols.io (UI Fork) or via
    future POST /workspaces/{id}/protocols automation.
    """
    ws = (workspace_uri or default_workspace_uri()).strip()
    ws_url = f"https://www.protocols.io/workspace/{ws}"
    existing = list_workspace_sop_queue(username, project_id, workspace_uri=ws)
    by_id: dict[int, dict[str, Any]] = {
        int(x["protocol_id"]): x
        for x in (existing.get("items") or [])
        if isinstance(x, dict) and x.get("protocol_id") is not None
    }
    added = 0
    now = datetime.now(timezone.utc).isoformat()
    for raw in protocols:
        row = _normalize_protocol_row(raw) if isinstance(raw, dict) else {}
        pid = row.get("id")
        if pid is None:
            continue
        pid = int(pid)
        view_url = row.get("url") or f"https://www.protocols.io/view/{row.get('uri') or pid}"
        by_id[pid] = {
            "protocol_id": pid,
            "title": row.get("title") or f"protocol-{pid}",
            "url": view_url,
            "doi": row.get("doi"),
            "authors": row.get("authors") or [],
            "workspace_uri": ws,
            "workspace_url": ws_url,
            "status": "queued_for_fork",
            "queued_at": now,
            "queued_by": username,
            "project_id": project_id,
            "next_step": (
                "Open URL on protocols.io → Fork into workspace "
                f"{ws} → edit → publish as lab SOP (future: auto-fork API)."
            ),
        }
        added += 1
    items = list(by_id.values())
    path = _queue_store_path(username, project_id)
    path.write_text(
        json.dumps(
            {
                "workspace_uri": ws,
                "project_id": project_id,
                "updated_at": now,
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "added": added,
        "count": len(items),
        "items": items,
        "workspace_uri": ws,
        "workspace_url": ws_url,
        "project_id": project_id,
        "verification_status": "user-provided",
        "source": "protocols.io",
        "scope": "workspace_queue",
    }


def format_workspace_queue_for_facts(
    queue: dict[str, Any],
) -> str:
    items = queue.get("items") or []
    ws = queue.get("workspace_uri") or default_workspace_uri()
    if not items:
        return ""
    lines = [
        f"## Lab SOP queue (workspace {ws})",
        "[user-provided] Selected for internal SOP development — fork/edit on protocols.io, then publish.",
        _FACTS_MATERIAL_NOTICE,
        "",
    ]
    for it in items[:15]:
        title = it.get("title") or "Untitled"
        url = it.get("url") or ""
        line = f"- **{title}** (status: {it.get('status', 'queued')})"
        if url:
            line += f" — {url}"
        lines.append(line)
    return "\n".join(lines)
