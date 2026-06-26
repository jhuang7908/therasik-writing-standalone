"""Science illustration asset hub — local mirrors + API helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_HUB_ROOT = Path(__file__).resolve().parent / "data" / "science_assets"
_MANIFEST_PATH = _HUB_ROOT / "manifest.json"


def hub_root() -> Path:
    return _HUB_ROOT


def libraries_root() -> Path:
    return _HUB_ROOT / "libraries"


def load_manifest() -> dict[str, Any]:
    if not _MANIFEST_PATH.is_file():
        return {"hub_version": "0", "libraries": [], "tools": []}
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def _dir_stats(path: Path) -> dict[str, Any]:
    if not path.is_dir():
        return {"installed": False, "file_count": 0, "size_mb": 0.0}
    n = 0
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            n += 1
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return {
        "installed": n > 0,
        "file_count": n,
        "size_mb": round(total / (1024 * 1024), 2),
    }


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def _matches_query(query: str, haystack: str) -> bool:
    q = (query or "").strip().lower()
    if not q:
        return True
    h = haystack.lower()
    if q in h:
        return True
    raw_terms = [x for x in re.split(r"\s+", q) if x]
    term_norms = [_norm(x) for x in raw_terms if _norm(x)]
    hay_tokens = [_norm(x) for x in re.split(r"[^a-z0-9]+", h) if _norm(x)]
    if len(term_norms) > 1 and any(len(t) == 1 for t in term_norms):
        return all(t in hay_tokens for t in term_norms)
    q_norm = _norm(q)
    h_norm = _norm(h)
    if q_norm and q_norm in h_norm:
        return True
    terms = [x for x in term_norms if len(x) > 1]
    if len(term_norms) == 1 and terms:
        return terms[0] in hay_tokens or terms[0] in h_norm
    if len(terms) >= 2:
        return all(t in h_norm for t in terms)
    return False


def library_status() -> list[dict[str, Any]]:
    manifest = load_manifest()
    out: list[dict[str, Any]] = []
    for lib in manifest.get("libraries") or []:
        lid = lib.get("id") or ""
        rel = lib.get("install_dir") or f"libraries/{lid}"
        root = _HUB_ROOT / rel
        icon_root = root
        sub = (lib.get("subdir") or "").strip()
        if sub:
            icon_root = root / sub
        stats = _dir_stats(icon_root if icon_root.is_dir() else root)
        out.append({
            "id": lid,
            "name": lib.get("name") or lid,
            "license": lib.get("license"),
            "publication_ok": lib.get("publication_ok", True),
            "grant_ok": lib.get("grant_ok", True),
            "attribution": lib.get("attribution"),
            "drawio_url": lib.get("drawio_url"),
            "path": str(root.relative_to(_HUB_ROOT)).replace("\\", "/"),
            **stats,
        })
    return out


def search_icons(library_id: str, query: str = "", limit: int = 48) -> list[dict[str, Any]]:
    manifest = load_manifest()
    lib = next((x for x in (manifest.get("libraries") or []) if x.get("id") == library_id), None)
    if not lib:
        return []
    rel = lib.get("install_dir") or f"libraries/{library_id}"
    root = _HUB_ROOT / rel
    sub = (lib.get("subdir") or "").strip()
    if sub:
        root = root / sub
    if not root.is_dir():
        return []
    hits: list[dict[str, Any]] = []
    for svg in sorted(root.rglob("*.svg")):
        name = svg.stem
        rel_path = svg.relative_to(_HUB_ROOT).as_posix()
        if not _matches_query(query, f"{name} {rel_path}"):
            continue
        hits.append({
            "name": name,
            "path": rel_path,
            "url": f"/science-assets/files/{rel_path}",
        })
        if len(hits) >= limit:
            break
    return hits


def search_files(
    library_id: str,
    query: str = "",
    limit: int = 24,
    extensions: tuple[str, ...] = (".pptx", ".svg", ".png", ".pdf"),
) -> list[dict[str, Any]]:
    manifest = load_manifest()
    lib = next((x for x in (manifest.get("libraries") or []) if x.get("id") == library_id), None)
    if not lib:
        return []
    rel = lib.get("install_dir") or f"libraries/{library_id}"
    root = _HUB_ROOT / rel
    if not root.is_dir():
        return []
    hits: list[dict[str, Any]] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in extensions:
            continue
        name = p.stem
        rel_path = p.relative_to(_HUB_ROOT).as_posix()
        haystack = f"{name} {rel_path}"
        if not _matches_query(query, haystack):
            continue
        hits.append({
            "name": name,
            "path": rel_path,
            "url": f"/science-assets/files/{rel_path}",
            "kind": p.suffix.lower().lstrip("."),
        })
        if len(hits) >= limit:
            break
    return hits


def hub_status_payload() -> dict[str, Any]:
    manifest = load_manifest()
    libs = library_status()
    any_installed = any(x.get("installed") for x in libs)
    return {
        "ok": True,
        "hub_version": manifest.get("hub_version"),
        "any_installed": any_installed,
        "libraries": libs,
        "tools": manifest.get("tools") or [],
        "export_standards": manifest.get("export_standards") or {},
        "attribution_guide": manifest.get("attribution_guide"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
