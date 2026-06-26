"""
eLabFTW REST API v2 client (Module 3 — lab / reagents / experiments).

Configure via environment:
  ELABFTW_BASE_URL   e.g. https://lab.insynbio.com
  ELABFTW_API_TOKEN  API key from eLabFTW Settings (treat as secret)
  ELABFTW_PUBLIC_URL optional link shown in UI (defaults to BASE_URL)
  ELABFTW_TENANTS_FILE optional JSON file mapping project/customer IDs to Lab tenants

Docs: https://doc.elabftw.net/api.html
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

_TIMEOUT = 25
_ENTITY_TYPES = ("items", "experiments", "resources")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("date", "datetime", "iso", "start", "value", "timestamp"):
            if value.get(key):
                return str(value[key]).strip()
        return ""
    return str(value or "").strip()


def _default_tenants_path() -> Path:
    return Path(__file__).with_name("lab_tenants.json")


def _load_tenants_payload() -> dict[str, Any]:
    path_raw = _clean(os.environ.get("ELABFTW_TENANTS_FILE"))
    path = Path(path_raw) if path_raw else _default_tenants_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _tenant_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    tenants = payload.get("tenants")
    if isinstance(tenants, dict):
        rows = []
        for tenant_id, row in tenants.items():
            if isinstance(row, dict):
                rows.append({"tenant_id": str(tenant_id), **row})
        return rows
    if isinstance(tenants, list):
        return [row for row in tenants if isinstance(row, dict)]
    return []


def _as_set(row: dict[str, Any], *keys: str) -> set[str]:
    values: set[str] = set()
    for key in keys:
        raw = row.get(key)
        if isinstance(raw, list):
            values.update(_clean(v) for v in raw if _clean(v))
        elif _clean(raw):
            values.add(_clean(raw))
    return values


def _token_from_row(row: dict[str, Any]) -> str:
    token = _clean(row.get("api_token") or row.get("token"))
    if token:
        return token
    env_name = _clean(row.get("api_token_env") or row.get("token_env"))
    return _clean(os.environ.get(env_name)) if env_name else ""


def resolve_tenant_row(
    *,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any] | None:
    """Return the tenant row mapped to project/customer, or default tenant row."""
    project = _clean(project_id)
    customer = _clean(customer_id)
    payload = _load_tenants_payload()
    rows = _tenant_rows(payload)
    selected: dict[str, Any] | None = None

    for row in rows:
        projects = _as_set(row, "project_ids", "projects", "project_id")
        customers = _as_set(row, "customer_ids", "customers", "customer_id")
        if (project and project in projects) or (customer and customer in customers):
            selected = row
            break

    if selected is None and rows:
        default_tenant = _clean(payload.get("default_tenant"))
        for row in rows:
            if default_tenant and _clean(row.get("tenant_id")) == default_tenant:
                selected = row
                break
    return selected


def _tenant_context(
    *,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    selected = resolve_tenant_row(project_id=project_id, customer_id=customer_id)

    if selected is not None:
        base = _clean(selected.get("base_url")).rstrip("/")
        token = _token_from_row(selected)
        public = _clean(selected.get("public_url") or base).rstrip("/")
        tenant_id = _clean(selected.get("tenant_id") or selected.get("name")) or "tenant"
        lab_manager_email = _clean(
            selected.get("lab_manager_email") or selected.get("manager_email")
        )
        return {
            "configured": bool(base and token),
            "base_url": base or None,
            "public_url": public or None,
            "token": token,
            "tenant_id": tenant_id,
            "tenant_mode": "mapped",
            "lab_manager_email": lab_manager_email or None,
        }

    base = (os.environ.get("ELABFTW_BASE_URL") or "").strip().rstrip("/")
    token = (os.environ.get("ELABFTW_API_TOKEN") or "").strip()
    public = (os.environ.get("ELABFTW_PUBLIC_URL") or base).strip().rstrip("/")
    return {
        "configured": bool(base and token),
        "base_url": base or None,
        "public_url": public or None,
        "token": token,
        "tenant_id": "default",
        "tenant_mode": "env",
        "lab_manager_email": None,
    }


def lab_mail_config(
    *,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Per-tenant lab manager default + platform SMTP capability (SaaS)."""
    ctx = _tenant_context(project_id=project_id, customer_id=customer_id)
    tenant_email = _clean(ctx.get("lab_manager_email"))
    platform_default = (os.environ.get("LAB_MANAGER_EMAIL") or "").strip()
    host = (os.environ.get("LAB_SMTP_HOST") or "").strip()
    from_addr = (
        os.environ.get("LAB_SMTP_FROM")
        or os.environ.get("LAB_SMTP_USER")
        or platform_default
    ).strip()
    return {
        "tenant_id": ctx.get("tenant_id"),
        "tenant_lab_manager_email": tenant_email or None,
        "platform_lab_manager_email": platform_default or None,
        "smtp_configured": bool(host),
        "smtp_from": from_addr or None,
        "manager_email_required_in_form": True,
    }


def elabftw_config(
    *,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    ctx = _tenant_context(project_id=project_id, customer_id=customer_id)
    return {
        "configured": bool(ctx.get("configured")),
        "base_url": ctx.get("base_url"),
        "public_url": ctx.get("public_url"),
        "tenant_id": ctx.get("tenant_id"),
        "tenant_mode": ctx.get("tenant_mode"),
    }


def _headers(ctx: dict[str, Any], *, write: bool = False) -> dict[str, str]:
    token = _clean(ctx.get("token"))
    if not token:
        raise RuntimeError("ELABFTW_API_TOKEN is not set")
    headers = {
        "Authorization": token,
        "Accept": "application/json",
    }
    if write:
        headers["Content-Type"] = "application/json"
    return headers


def _base(ctx: dict[str, Any]) -> str:
    base = _clean(ctx.get("base_url")).rstrip("/")
    if not base:
        raise RuntimeError("ELABFTW_BASE_URL is not set")
    return base


def ping(
    *,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Lightweight connectivity check."""
    ctx = _tenant_context(project_id=project_id, customer_id=customer_id)
    cfg = elabftw_config(project_id=project_id, customer_id=customer_id)
    if not cfg["configured"]:
        return {"ok": False, "error": "not_configured", **cfg}
    try:
        url = f"{_base(ctx)}/api/v2/items"
        r = requests.get(
            url,
            headers=_headers(ctx),
            params={"limit": 1},
            timeout=_TIMEOUT,
            verify=True,
        )
        if r.status_code == 401:
            return {"ok": False, "error": "unauthorized", "status": 401, **cfg}
        if r.status_code >= 400:
            return {"ok": False, "error": "http_error", "status": r.status_code, **cfg}
        return {"ok": True, "status": r.status_code, **cfg}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc), **cfg}


def list_entries(
    entity: str = "items",
    *,
    limit: int = 25,
    offset: int = 0,
    search: str | None = None,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> list[dict[str, Any]]:
    """List eLabFTW database entries (items = reagents/resources inventory)."""
    ctx = _tenant_context(project_id=project_id, customer_id=customer_id)
    if entity not in _ENTITY_TYPES:
        entity = "items"
    url = f"{_base(ctx)}/api/v2/{entity}"
    params: dict[str, Any] = {"limit": max(1, min(limit, 100)), "offset": max(0, offset)}
    if search and search.strip():
        params["q"] = search.strip()
    r = requests.get(url, headers=_headers(ctx), params=params, timeout=_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("data", "results", entity, "items"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def get_entry(
    entity: str,
    entry_id: str | int,
    *,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Fetch a single eLabFTW entry with full body content."""
    ctx = _tenant_context(project_id=project_id, customer_id=customer_id)
    cfg = elabftw_config(project_id=project_id, customer_id=customer_id)
    path = _ENTITY_PATHS.get(entity, "items")
    url = f"{_base(ctx)}/api/v2/{path}/{entry_id}"
    r = requests.get(url, headers=_headers(ctx), timeout=_TIMEOUT)
    r.raise_for_status()
    e = r.json()

    public = _clean(cfg.get("public_url") or cfg.get("base_url"))
    view_seg = "experiments" if entity == "experiments" else "database"

    return {
        "id": e.get("id"),
        "title": _entry_title(e),
        "category": _clean(e.get("category_title") or e.get("category") or ""),
        "status": _clean(e.get("status_title") or e.get("status") or ""),
        "body": e.get("body") or e.get("content") or e.get("description") or "",
        "date": _clean(e.get("date") or e.get("created_at") or ""),
        "tags": e.get("tags", []),
        "url": f"{public}/{view_seg}.php?mode=view&id={e.get('id')}" if public and e.get("id") else "",
        "tenant_id": cfg.get("tenant_id"),
    }


_ENTITY_PATHS = {
    "items": "items",
    "resources": "items",  # eLabFTW v2 exposes resources via /items
    "experiments": "experiments",
}


_RESOURCE_TAGS = frozenset([
    "instrument", "equipment", "software", "resource", "resources",
    "protocol template", "reference sop", "machine", "device",
])
_REAGENT_TAGS = frozenset([
    "antibody", "chemical", "enzyme", "buffer", "kit", "consumable",
    "sample", "reagent", "reagents", "solution", "media", "culture media",
    "plasmid", "primer", "oligo",
])


def _item_tag_set(entry: dict[str, Any]) -> set[str]:
    """Return lowercase tag strings from an eLabFTW item entry."""
    raw = entry.get("tags") or ""
    if isinstance(raw, str):
        # eLabFTW returns tags as pipe-separated string e.g. "Antibody|HRP"
        parts = [t.strip().lower() for t in raw.replace(",", "|").split("|") if t.strip()]
    elif isinstance(raw, list):
        parts = []
        for t in raw:
            val = (t.get("tag") or t.get("value") or t) if isinstance(t, dict) else t
            parts.append(str(val).strip().lower())
    else:
        parts = []
    return set(parts)


def _classify_item(entry: dict[str, Any]) -> str:
    """Return 'resource' or 'reagent' based on tags and title heuristics."""
    tags = _item_tag_set(entry)
    if tags & _RESOURCE_TAGS:
        return "resource"
    if tags & _REAGENT_TAGS:
        return "reagent"
    # Fallback: title-based heuristic
    title = _clean(entry.get("title") or "").lower()
    for kw in ("system", "instrument", "machine", "centrifuge", "reader",
               "thermocycler", "microscope", "spectrometer", "fplc",
               "akta", "equipment", "device", "analyser", "analyzer"):
        if kw in title:
            return "resource"
    return "reagent"  # default to reagent


def browse_entries(
    entity: str = "items",
    *,
    limit: int = 50,
    offset: int = 0,
    search: str | None = None,
    tag_filter: str | None = None,   # "reagent" | "resource" | None
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Browse lab entries and return UI-friendly rows (id, title, category, snippet, url)."""
    ctx = _tenant_context(project_id=project_id, customer_id=customer_id)
    cfg = elabftw_config(project_id=project_id, customer_id=customer_id)
    entity = entity if entity in _ENTITY_PATHS else "items"

    # For resources/inventory split, fetch enough items to filter meaningfully
    fetch_limit = limit if not tag_filter else min(limit * 4, 200)
    rows = list_entries(
        _ENTITY_PATHS[entity],
        limit=fetch_limit,
        offset=offset,
        search=search,
        project_id=project_id,
        customer_id=customer_id,
    )

    # Apply tag_filter split for items (reagent vs resource)
    if tag_filter and entity in ("items", "resources"):
        want = "resource" if tag_filter == "resource" else "reagent"
        rows = [r for r in rows if _classify_item(r) == want]
        rows = rows[:limit]
    # Apply tag_filter for experiments (sop vs data results)
    elif tag_filter and entity == "experiments":
        tags = _item_tag_set
        if tag_filter == "sop":
            _sop_code_re = re.compile(r"\bSOP-\d{8}-\d{3}\b", re.I)
            rows = [
                r for r in rows
                if "sop" in tags(r)
                or _sop_code_re.search(_entry_title(r))
                or _sop_code_re.search(_clean(r.get("body") or ""))
            ]
        elif tag_filter in ("data", "results"):
            rows = [
                r for r in rows
                if tags(r) & {"data", "results"} and "sop" not in tags(r)
            ]
        rows = rows[:limit]

    public = _clean(cfg.get("public_url") or cfg.get("base_url"))
    view_seg = "experiments" if entity == "experiments" else "database"
    out: list[dict[str, Any]] = []
    for e in rows:
        eid = e.get("id", "")
        sop_code, sop_filename = _extract_sop_meta(e)
        # Use eLabFTW category if available; otherwise fall back to first meaningful tag
        category = _clean(e.get("category_title") or e.get("category") or "")
        if not category:
            raw_tags = e.get("tags") or ""
            if isinstance(raw_tags, str):
                tag_parts = [t.strip() for t in raw_tags.replace(",", "|").split("|") if t.strip()]
            elif isinstance(raw_tags, list):
                tag_parts = [str(t.get("tag") or t.get("value") or t).strip() for t in raw_tags if t]
            else:
                tag_parts = []
            category_tag = next(
                (
                    t.split(":", 1)[1].strip()
                    for t in tag_parts
                    if t.lower().startswith("category:") and ":" in t
                ),
                "",
            )
            # Pick the first tag that isn't a generic/system/test tag.
            # Without this guard, labels like "Smoke" can appear as category.
            skip = {
                "insynbio", "sop", "data", "results", "reagent", "resource",
                "smoke", "test", "demo", "tmp", "temp",
            }
            category = category_tag or next(
                (t for t in tag_parts if t.lower() not in skip and not t.lower().startswith(("status:", "lang:", "file:", "category:"))),
                tag_parts[0] if tag_parts else "",
            )
        # Normalize tags to a pipe-joined string so the UI can read storage/status badges.
        raw_tags_out = e.get("tags") or ""
        if isinstance(raw_tags_out, str):
            tags_str = "|".join(t.strip() for t in raw_tags_out.replace(",", "|").split("|") if t.strip())
        elif isinstance(raw_tags_out, list):
            tags_str = "|".join(str(t.get("tag") or t.get("value") or t).strip() for t in raw_tags_out if t)
        else:
            tags_str = ""
        out.append(
            {
                "id": eid,
                "title": _entry_title(e),
                "sop_code": sop_code,
                "sop_filename": sop_filename,
                "category": category,
                "status": _clean(e.get("status_title") or e.get("status") or ""),
                "tags": tags_str,
                "snippet": _entry_body_snippet(e, max_len=160),
                "date": _clean(e.get("date") or e.get("created_at") or ""),
                "url": f"{public}/{view_seg}.php?mode=view&id={eid}" if public and eid else "",
            }
        )
    return {
        "entity": entity,
        "count": len(out),
        "entries": out,
        "tenant_id": cfg.get("tenant_id"),
        "public_url": public or None,
    }
_SOP_SECTION_ORDER = (
    "Purpose & Scope",
    "Materials & Equipment",
    "Procedure",
    "QC & Acceptance Criteria",
    "Safety & Waste Disposal",
    "Revision Log",
)


def _sop_text_to_html(title: str, sections: dict[str, str]) -> str:
    """Render a structured SOP dict into simple HTML for the eLabFTW body."""
    parts: list[str] = []
    if title:
        parts.append(f"<h1>{_html_escape(title)}</h1>")
    labels = list(_SOP_SECTION_ORDER) + [
        k for k in sections if k not in _SOP_SECTION_ORDER
    ]
    for label in labels:
        value = _clean(sections.get(label) or "")
        if not value:
            continue
        body = _html_escape(value).replace("\n", "<br>")
        parts.append(f"<h2>{_html_escape(label)}</h2><p>{body}</p>")
    return "".join(parts) or "<p>(empty SOP)</p>"


def _build_sop_body_html(
    *,
    method_title: str,
    sop_code: str,
    sop_filename: str,
    status: str,
    sections: dict[str, str],
    i18n: dict[str, dict[str, str]] | None = None,
    primary_lang: str = "en",
) -> str:
    """Full eLabFTW SOP body: hidden meta, header, primary-language sections, optional i18n blob."""
    meta_html = (
        f'<p data-sop-meta="1" style="display:none">'
        f"SOP Code: {_html_escape(sop_code)} Filename: {_html_escape(sop_filename)}</p>"
    )
    header_html = (
        f"<h1>{_html_escape(method_title)}</h1>"
        f'<p style="color:#6b6b6b;font-size:13px;margin-top:-6px">'
        f"<strong>{_html_escape(sop_code)}</strong> · Document type: SOP · "
        f"Status: {_html_escape(status or 'Draft')} · Language: {_html_escape(primary_lang)}</p>"
    )
    body_html = meta_html + header_html + _sop_text_to_html("", sections)
    if i18n and len(i18n) > 1:
        packed = json.dumps(i18n, ensure_ascii=False)
        body_html += (
            f'<p data-sop-i18n="1" style="display:none">{_html_escape(packed)}</p>'
        )
    return body_html


def _html_escape(s: Any) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def create_entry(
    *,
    entity: str = "experiments",
    title: str,
    body_html: str,
    tags: list[str] | None = None,
    category: str | None = None,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Create a new eLabFTW experiment/resource and set its title + body.

    eLabFTW v2: POST creates an empty entry (201 + Location header),
    then PATCH sets title/body.

    Classification: for items/resources we tag the category name (robust across
    instances). The native items_types category id is intentionally NOT set via
    PATCH — some eLabFTW instances reject it with a DB foreign-key constraint,
    which would abort creation. The category badge in the UI is derived from tags.
    """
    ctx = _tenant_context(project_id=project_id, customer_id=customer_id)
    cfg = elabftw_config(project_id=project_id, customer_id=customer_id)
    entity = entity if entity in _ENTITY_PATHS else "experiments"
    path = _ENTITY_PATHS[entity]
    base = _base(ctx)

    # Ensure the category name is present as a tag so the UI can show/filter it.
    tags = list(tags or [])
    if _clean(category):
        if not any(_clean(t).lower() == _clean(category).lower() for t in tags):
            tags.insert(0, _clean(category))
        cat_tag = f"category:{_clean(category)}"
        if not any(_clean(t).lower() == cat_tag.lower() for t in tags):
            tags.insert(1, cat_tag)

    create = requests.post(
        f"{base}/api/v2/{path}",
        headers=_headers(ctx, write=True),
        json={},
        timeout=_TIMEOUT,
    )
    create.raise_for_status()
    location = create.headers.get("Location", "")
    new_id = location.rstrip("/").split("/")[-1] if location else ""
    if not new_id:
        data = create.json() if create.content else {}
        new_id = str(data.get("id", "")) if isinstance(data, dict) else ""
    if not new_id:
        raise RuntimeError("eLabFTW did not return a new entry id")

    # eLabFTW v2: title/body are PATCH-able; tags are NOT (separate endpoint).
    payload: dict[str, Any] = {"title": title or "Untitled SOP", "body": body_html}
    patch = requests.patch(
        f"{base}/api/v2/{path}/{new_id}",
        headers=_headers(ctx, write=True),
        json=payload,
        timeout=_TIMEOUT,
    )
    patch.raise_for_status()

    # Best-effort tag attachment (each tag via its own endpoint; ignore failures).
    for tag in tags or []:
        try:
            requests.post(
                f"{base}/api/v2/{path}/{new_id}/tags",
                headers=_headers(ctx, write=True),
                json={"tag": tag},
                timeout=_TIMEOUT,
            )
        except requests.RequestException:
            pass

    public = _clean(cfg.get("public_url") or cfg.get("base_url"))
    view_seg = "experiments" if entity == "experiments" else "database"
    return {
        "ok": True,
        "id": new_id,
        "entity": entity,
        "url": f"{public}/{view_seg}.php?mode=view&id={new_id}" if public else "",
        "tenant_id": cfg.get("tenant_id"),
    }


def update_entry(
    *,
    entity: str,
    entry_id: str | int,
    title: str | None = None,
    body_html: str | None = None,
    tags: list[str] | None = None,
    category: str | None = None,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Update an existing eLabFTW entry.

    Supports title/body patch and best-effort tag attachment.
    """
    ctx = _tenant_context(project_id=project_id, customer_id=customer_id)
    cfg = elabftw_config(project_id=project_id, customer_id=customer_id)
    path = _ENTITY_PATHS.get(entity, "items")
    payload: dict[str, Any] = {}
    if title is not None:
        payload["title"] = title
    if body_html is not None:
        payload["body"] = body_html
    if payload:
        patch = requests.patch(
            f"{_base(ctx)}/api/v2/{path}/{entry_id}",
            headers=_headers(ctx, write=True),
            json=payload,
            timeout=_TIMEOUT,
        )
        patch.raise_for_status()

    # Keep category searchable even if native category isn't API-settable.
    merged_tags = list(tags or [])
    if _clean(category) and _clean(category).lower() not in {str(t).strip().lower() for t in merged_tags}:
        merged_tags.insert(0, _clean(category))

    for tag in merged_tags:
        try:
            requests.post(
                f"{_base(ctx)}/api/v2/{path}/{entry_id}/tags",
                headers=_headers(ctx, write=True),
                json={"tag": tag},
                timeout=_TIMEOUT,
            )
        except requests.RequestException:
            pass

    public = _clean(cfg.get("public_url") or cfg.get("base_url"))
    view_seg = "experiments" if entity == "experiments" else "database"
    return {
        "ok": True,
        "id": str(entry_id),
        "entity": entity,
        "url": f"{public}/{view_seg}.php?mode=view&id={entry_id}" if public else "",
        "tenant_id": cfg.get("tenant_id"),
    }


def delete_entry(
    entity: str,
    entry_id: str | int,
    *,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Delete an eLabFTW entry (experiment, item, or resource)."""
    ctx = _tenant_context(project_id=project_id, customer_id=customer_id)
    cfg = elabftw_config(project_id=project_id, customer_id=customer_id)
    path = _ENTITY_PATHS.get(entity, "items")
    url = f"{_base(ctx)}/api/v2/{path}/{entry_id}"
    
    r = requests.delete(url, headers=_headers(ctx), timeout=_TIMEOUT)
    r.raise_for_status()
    
    return {
        "ok": True,
        "id": entry_id,
        "entity": entity,
        "tenant_id": cfg.get("tenant_id"),
    }


def set_item_bookable(
    item_id: str | int,
    *,
    is_bookable: bool = True,
    allow_overlap: bool | None = None,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Enable/disable booking for an item (resource/instrument)."""
    ctx = _tenant_context(project_id=project_id, customer_id=customer_id)
    payload: dict[str, Any] = {"is_bookable": 1 if is_bookable else 0}
    if allow_overlap is not None:
        payload["book_can_overlap"] = 1 if allow_overlap else 0
    r = requests.patch(
        f"{_base(ctx)}/api/v2/items/{item_id}",
        headers=_headers(ctx, write=True),
        json=payload,
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    data = r.json() if r.content else {}
    return {
        "ok": True,
        "item_id": str(item_id),
        "is_bookable": bool(data.get("is_bookable", payload["is_bookable"])),
        "book_can_overlap": bool(data.get("book_can_overlap", payload.get("book_can_overlap", 1))),
    }


def list_bookings(
    *,
    item_id: str | int | None = None,
    limit: int = 50,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """List scheduler events and optionally filter by item id."""
    ctx = _tenant_context(project_id=project_id, customer_id=customer_id)
    cfg = elabftw_config(project_id=project_id, customer_id=customer_id)
    r = requests.get(
        f"{_base(ctx)}/api/v2/events",
        headers=_headers(ctx),
        timeout=_TIMEOUT,
    )
    r.raise_for_status()
    data = r.json()
    rows = data if isinstance(data, list) else []
    if item_id is not None:
        item_str = str(item_id)
        rows = [
            ev for ev in rows
            if str(ev.get("items_id") or ev.get("item") or "") == item_str
        ]
    rows = rows[: max(1, min(limit, 200))]
    events = [
        {
            "id": str(ev.get("id", "")),
            "title": _clean(ev.get("title") or ev.get("comment") or "Booking"),
            "start": _clean(ev.get("start")),
            "end": _clean(ev.get("end")),
            "item_id": str(ev.get("items_id") or ev.get("item") or ""),
            "owner": _clean(ev.get("fullname") or ev.get("author") or ""),
        }
        for ev in rows
    ]
    return {
        "ok": True,
        "count": len(events),
        "events": events,
        "tenant_id": cfg.get("tenant_id"),
    }


def _elab_event_datetime(value: str) -> str:
    """Normalize browser ISO datetimes to eLabFTW scheduler format."""
    s = _clean(value)
    if not s:
        return s
    s = s.replace("Z", "").strip()
    if "T" in s:
        s = s.replace("T", " ", 1)
    if "." in s:
        s = s.split(".", 1)[0].strip()
    return s


def http_error_message(exc: requests.HTTPError) -> str:
    """Extract API error body for client-facing messages."""
    resp = exc.response
    if resp is None:
        return str(exc)
    try:
        data = resp.json()
        if isinstance(data, dict):
            for key in ("message", "description", "error", "detail"):
                if data.get(key):
                    return str(data[key])
        if isinstance(data, list) and data:
            return str(data[0])
    except (ValueError, json.JSONDecodeError):
        pass
    text = (resp.text or "").strip()
    if text and len(text) < 500:
        return text
    return f"{resp.status_code} {resp.reason or 'error'} for {resp.url}"


def create_booking(
    *,
    item_id: str | int,
    title: str,
    start: str,
    end: str,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Create a booking via POST /api/v2/events/{item_id} (eLabFTW scheduler)."""
    ctx = _tenant_context(project_id=project_id, customer_id=customer_id)
    start_fmt = _elab_event_datetime(start)
    end_fmt = _elab_event_datetime(end)
    if not start_fmt or not end_fmt:
        raise RuntimeError("Booking start and end times are required.")
    try:
        set_item_bookable(
            item_id,
            is_bookable=True,
            allow_overlap=False,
            project_id=project_id,
            customer_id=customer_id,
        )
    except requests.HTTPError:
        pass
    payload = {
        "title": title or "Instrument booking",
        "start": start_fmt,
        "end": end_fmt,
    }
    url = f"{_base(ctx)}/api/v2/events/{item_id}"
    r = requests.post(
        url,
        headers=_headers(ctx, write=True),
        json=payload,
        timeout=_TIMEOUT,
    )
    if not r.ok:
        msg = http_error_message(requests.HTTPError(response=r))
        raise requests.HTTPError(msg, response=r)
    loc = r.headers.get("Location", "")
    booking_id = loc.rstrip("/").split("/")[-1] if loc else ""
    return {
        "ok": True,
        "booking_id": booking_id or "",
        "item_id": str(item_id),
        "title": payload["title"],
        "start": start_fmt,
        "end": end_fmt,
    }


def delete_booking(
    booking_id: str | int,
    *,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Delete a booking event.

    eLabFTW 5.5.x accepts DELETE /api/v2/event/{id} (singular) while
    DELETE /api/v2/events/{id} may return 500 on some instances.
    """
    ctx = _tenant_context(project_id=project_id, customer_id=customer_id)
    base = _base(ctx)
    urls = [f"{base}/api/v2/event/{booking_id}", f"{base}/api/v2/events/{booking_id}"]
    last_exc: Exception | None = None
    for url in urls:
        try:
            r = requests.delete(url, headers=_headers(ctx), timeout=_TIMEOUT)
            r.raise_for_status()
            return {"ok": True, "booking_id": str(booking_id)}
        except requests.RequestException as exc:
            last_exc = exc
    if last_exc:
        raise last_exc
    return {"ok": False, "booking_id": str(booking_id)}


def save_sop_to_notebook(
    *,
    title: str,
    sections: dict[str, str],
    entity: str = "experiments",
    entry_id: str | int | None = None,
    sop_code: str | None = None,
    status: str = "Draft",
    category: str | None = None,
    language: str = "en",
    i18n: dict[str, dict[str, str]] | None = None,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Convert a structured SOP and store or update it in the lab notebook (eLabFTW)."""
    method_title = _clean(title) or "Untitled SOP"
    content_seed = _clean(
        sections.get("Procedure")
        or sections.get("Purpose & Scope")
        or sections.get("Materials & Equipment")
        or ""
    )
    lang = (_clean(language) or "en").lower()[:12]

    def _slug(v: str, max_len: int = 36) -> str:
        s = re.sub(r"[^a-zA-Z0-9]+", "_", _clean(v)).strip("_").lower()
        return s[:max_len] or "untitled"

    method_slug = _slug(method_title, max_len=40)
    content_slug = _slug(content_seed, max_len=28)
    st = _clean(status) or "Draft"
    cat = _clean(category) or "Assay"

    if entry_id is not None:
        existing = get_entry(
            entity=entity,
            entry_id=entry_id,
            project_id=project_id,
            customer_id=customer_id,
        )
        code, filename = _extract_sop_meta(existing)
        sop_code = _clean(sop_code) or code or f"SOP-{datetime.now().strftime('%Y%m%d')}-001"
        sop_filename = filename or f"{sop_code}_{method_slug}_{content_slug}.md"
        display_title = f"{sop_code} | {method_title}"
        body_html = _build_sop_body_html(
            method_title=method_title,
            sop_code=sop_code,
            sop_filename=sop_filename,
            status=st,
            sections=sections,
            i18n=i18n,
            primary_lang=lang,
        )
        prev_tags = existing.get("tags") or []
        if isinstance(prev_tags, str):
            tag_list = [t.strip() for t in prev_tags.replace(",", "|").split("|") if t.strip()]
        else:
            tag_list = [
                str(t.get("tag") or t.get("value") or t).strip()
                for t in (prev_tags if isinstance(prev_tags, list) else [])
                if t
            ]
        keep = [
            t for t in tag_list
            if t and not re.match(r"^(status:|lang:|category:)", t, re.I)
        ]
        tags = ["SOP", "InSynBio", cat, f"category:{cat}", sop_code, f"file:{sop_filename}", method_slug, f"lang:{lang}", f"status:{st}"] + keep
        tags = list(dict.fromkeys(tags))
        updated = update_entry(
            entity=entity,
            entry_id=entry_id,
            title=display_title,
            body_html=body_html,
            tags=tags,
            category=cat,
            project_id=project_id,
            customer_id=customer_id,
        )
        updated["sop_code"] = sop_code
        updated["sop_filename"] = sop_filename
        updated["method_name"] = method_title
        updated["updated"] = True
        updated["language"] = lang
        return updated

    # Deterministic SOP code: SOP-YYYYMMDD-XXX (per tenant/day).
    today = datetime.now().strftime("%Y%m%d")
    serial = 1
    try:
        rows = list_entries(
            "experiments",
            limit=300,
            search="SOP-",
            project_id=project_id,
            customer_id=customer_id,
        )
        pat = re.compile(rf"\bSOP-{today}-(\d{{3}})\b")
        nums = []
        for r in rows:
            m = pat.search(_entry_title(r))
            if m:
                nums.append(int(m.group(1)))
        if nums:
            serial = max(nums) + 1
    except Exception:
        serial = 1

    sop_code = _clean(sop_code) or f"SOP-{today}-{serial:03d}"
    sop_filename = f"{sop_code}_{method_slug}_{content_slug}.md"
    display_title = f"{sop_code} | {method_title}"
    body_html = _build_sop_body_html(
        method_title=method_title,
        sop_code=sop_code,
        sop_filename=sop_filename,
        status=st,
        sections=sections,
        i18n=i18n,
        primary_lang=lang,
    )
    created = create_entry(
        entity=entity,
        title=display_title,
        body_html=body_html,
        tags=["SOP", "InSynBio", cat, f"category:{cat}", sop_code, f"file:{sop_filename}", method_slug, f"lang:{lang}", f"status:{st}"],
        category=cat,
        project_id=project_id,
        customer_id=customer_id,
    )
    created["sop_code"] = sop_code
    created["sop_filename"] = sop_filename
    created["method_name"] = method_title
    created["language"] = lang
    return created


def build_data_record_html(
    *,
    title: str = "",
    experiment_ref: str | None = None,
    method: str = "",
    observations: str = "",
    raw_data: str = "",
    conclusion: str = "",
    qc_status: str = "Pending",
    attachments: list[dict[str, str]] | None = None,
) -> str:
    """HTML body for mini ELN data records (create or update)."""
    parts: list[str] = []
    if title:
        parts.append(f"<h1>{_html_escape(title)}</h1>")
    if experiment_ref:
        parts.append(
            f"<p><strong>Reference Experiment:</strong> {_html_escape(experiment_ref)}</p>"
        )
    if method:
        parts.append(
            f"<h2>Method / Procedure</h2>"
            f"<pre style='background:#f8f8f8;padding:8px;border-radius:4px;font-size:12px;"
            f"white-space:pre-wrap;'>{_html_escape(method.strip())}</pre>"
        )
    if observations:
        parts.append(
            f"<h2>Background / Context</h2>"
            f"<p>{_html_escape(observations).replace(chr(10), '<br>')}</p>"
        )

    if raw_data:
        blocks = re.split(r"\n\n(?=\[)", raw_data.strip())
        if len(blocks) > 1:
            for block in blocks:
                m = re.match(r"^\[(.+?)\]\n?([\s\S]*)", block.strip())
                label, content = (m.group(1), m.group(2)) if m else ("Result", block)
                parts.append(f"<h3>{_html_escape(label)}</h3>")
                parts.append(
                    "<pre style='background:#f5f5f5;padding:8px;border-radius:4px;"
                    f"font-size:12px;white-space:pre-wrap;'>{_html_escape(content.strip())}</pre>"
                )
        else:
            parts.append(
                "<h2>Results / Measurements</h2>"
                "<pre style='background:#f5f5f5;padding:8px;border-radius:4px;font-size:12px;"
                f"white-space:pre-wrap;'>{_html_escape(raw_data)}</pre>"
            )

    images = [a for a in (attachments or []) if a.get("type", "").startswith("image/")]
    other_files = [a for a in (attachments or []) if not a.get("type", "").startswith("image/")]

    if images:
        parts.append(
            "<h2>Figures</h2><div style='display:flex;flex-wrap:wrap;gap:12px;margin-bottom:8px;'>"
        )
        for att in images:
            name = att.get("name", "figure")
            data = att.get("data", "")
            parts.append(
                f"<figure style='border:1px solid #ddd;padding:6px;border-radius:6px;"
                f"text-align:center;max-width:320px;'>"
                f"<img src='{data}' style='max-width:300px;max-height:280px;display:block;border-radius:4px;' />"
                f"<figcaption style='font-size:11px;color:#666;margin-top:4px;'>"
                f"{_html_escape(name)}</figcaption></figure>"
            )
        parts.append("</div>")

    if other_files:
        parts.append("<h2>Attached Files</h2><ul>")
        for att in other_files:
            name = att.get("name", "file")
            data = att.get("data", "")
            parts.append(
                f"<li><a href='{data}' download='{_html_escape(name)}'>"
                f"{_html_escape(name)}</a></li>"
            )
        parts.append("</ul>")

    if conclusion:
        parts.append(
            f"<h2>Conclusion</h2><p>{_html_escape(conclusion).replace(chr(10), '<br>')}</p>"
        )

    status_color = {
        "Pass": "#27ae60",
        "Fail": "#e74c3c",
        "Requires Review": "#f39c12",
    }.get(qc_status, "#6b7280")
    parts.append(
        f"<p><strong>QC Status:</strong> "
        f"<span class='eln-qc-badge' style='padding:2px 8px;border-radius:4px;"
        f"background:{status_color};color:#ffffff;font-size:12px;font-weight:700;'>"
        f"{_html_escape(qc_status)}</span></p>"
    )
    return "".join(parts) or "<p>(empty data record)</p>"


def save_data_to_notebook(
    *,
    title: str,
    experiment_ref: str | None = None,
    method: str = "",
    observations: str = "",
    raw_data: str = "",
    conclusion: str = "",
    qc_status: str = "Pending",
    attachments: list[dict[str, str]] | None = None,
    entry_id: str | int | None = None,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    """Store or update experimental results in the lab notebook (mini ELN).

    raw_data may contain multi-block notation: [Result 1]\\ndata\\n\\n[Result 2]\\ndata
    attachments: list of {name, type, data (base64 data URL)}
    """
    body_html = build_data_record_html(
        title=title,
        experiment_ref=experiment_ref,
        method=method,
        observations=observations,
        raw_data=raw_data,
        conclusion=conclusion,
        qc_status=qc_status,
        attachments=attachments,
    )
    tags = ["Data", "Results", "InSynBio"]
    if entry_id:
        updated = update_entry(
            entity="experiments",
            entry_id=entry_id,
            title=title or "Experimental Data Record",
            body_html=body_html,
            tags=tags,
            project_id=project_id,
            customer_id=customer_id,
        )
        updated["updated"] = True
        return updated
    return create_entry(
        entity="experiments",
        title=title or "Experimental Data Record",
        body_html=body_html,
        tags=tags,
        project_id=project_id,
        customer_id=customer_id,
    )


def _entry_title(entry: dict[str, Any]) -> str:
    for key in ("title", "name", "content_title"):
        v = entry.get(key)
        if v:
            return str(v).strip()
    return f"entry-{entry.get('id', '?')}"


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    text = _HTML_TAG_RE.sub(" ", text)
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&nbsp;", " ")
        .replace("&quot;", '"')
    )
    return " ".join(text.split())


def _entry_body_snippet(entry: dict[str, Any], max_len: int = 200) -> str:
    # Remove SOP metadata lines (SOP Code / Filename) before extracting snippet
    _META_RE = re.compile(r"(SOP\s*Code|Filename)\s*:\s*\S+", re.I)
    for key in ("body", "content", "description", "maintext"):
        v = entry.get(key)
        if v and isinstance(v, str):
            t = _strip_html(v)
            t = _META_RE.sub("", t).strip()
            if not t:
                continue
            t = " ".join(t.split())  # collapse whitespace after removal
            return t[:max_len] + ("…" if len(t) > max_len else "")
    return ""


def _extract_sop_meta(entry: dict[str, Any]) -> tuple[str, str]:
    """Extract SOP code and filename from title, tags, or body metadata."""
    title = _entry_title(entry)
    body = _clean(entry.get("body") or entry.get("body_html") or "")
    raw_tags = entry.get("tags") or ""
    tag_str = raw_tags if isinstance(raw_tags, str) else "|".join(str(t) for t in raw_tags)
    code = ""
    filename = ""

    code_m = re.search(r"\b(SOP-\d{8}-\d{3})\b", title)
    if code_m:
        code = code_m.group(1)
    else:
        # Try tags first (faster than body parse)
        tag_code = re.search(r"\b(SOP-\d{8}-\d{3})\b", tag_str)
        if tag_code:
            code = tag_code.group(1)
        else:
            body_code = re.search(r"SOP\s*Code:\s*(SOP-\d{8}-\d{3})", body, flags=re.I)
            if body_code:
                code = body_code.group(1)

    # Filename from tag (format "file:<filename>") or body
    file_tag = re.search(r"(?:^|\|)\s*file:([A-Za-z0-9._-]+)", tag_str)
    if file_tag:
        filename = file_tag.group(1).strip()
    else:
        fn_m = re.search(r"Filename:\s*([A-Za-z0-9._-]+)", body, flags=re.I)
        if fn_m:
            filename = fn_m.group(1).strip()
    return code, filename


def format_reagents_for_facts(
    entries: list[dict[str, Any]],
    *,
    source_label: str = "eLabFTW",
) -> str:
    """Build a Facts Summary block from item/resource rows."""
    if not entries:
        return f"## Lab reagents ({source_label})\n\n[No items returned — check eLabFTW database or API scope.]"
    lines = [
        f"## Lab reagents & materials ({source_label})",
        "[user-provided via eLabFTW API — verify catalog numbers and lots before submission]",
        "",
    ]
    for i, e in enumerate(entries[:50], 1):
        title = _entry_title(e)
        eid = e.get("id", "")
        cat = e.get("category") or e.get("category_title") or ""
        snip = _entry_body_snippet(e)
        line = f"- {title}"
        if eid:
            line += f" (eLabFTW id {eid})"
        if cat:
            line += f" [{cat}]"
        if snip:
            line += f": {snip}"
        lines.append(line)
    return "\n".join(lines)


def import_reagents_facts_block(
    *,
    limit: int = 25,
    search: str | None = None,
    project_id: str | None = None,
    customer_id: str | None = None,
) -> dict[str, Any]:
    cfg = elabftw_config(project_id=project_id, customer_id=customer_id)
    entries = list_entries(
        "items",
        limit=limit,
        search=search,
        project_id=project_id,
        customer_id=customer_id,
    )
    block = format_reagents_for_facts(entries)
    return {
        "facts_block": block,
        "count": len(entries),
        "entity": "items",
        "verification_status": "user-provided",
        "tenant_id": cfg.get("tenant_id"),
        "tenant_mode": cfg.get("tenant_mode"),
    }
