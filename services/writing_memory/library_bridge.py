"""
Bidirectional sync between Module 4 intelligence library and Write reference_library.

- intelligence_store: per-project wm_documents (OpenAlex, manual, patent, …)
- reference_library: per-account library.jsonl (Write module, Zotero-compatible)
"""
from __future__ import annotations

from typing import Any

try:
    from .intelligence_store import list_documents, save_document
    from .reference_library import (
        ReferenceEntry,
        add_or_update_reference,
        load_library,
        search_library,
    )
    from .unpaywall_client import enrich_work
except ImportError:
    from intelligence_store import list_documents, save_document  # type: ignore
    from reference_library import (  # type: ignore
        ReferenceEntry,
        add_or_update_reference,
        load_library,
        search_library,
    )
    from unpaywall_client import enrich_work  # type: ignore

_LIT_SOURCES = frozenset({"openalex", "manual"})


def _project_id(pid: str | None) -> str:
    return (pid or "").strip() or "_default"


def _entry_matches_project(entry: ReferenceEntry, project_id: str) -> bool:
    pids = entry.project_ids or []
    if not pids:
        return True
    return project_id in pids


def intel_doc_to_write_entry(doc: dict[str, Any], project_id: str) -> dict[str, Any]:
    raw = doc.get("raw") if isinstance(doc.get("raw"), dict) else {}
    doi = doc.get("doi") or raw.get("doi")
    pmid = raw.get("pmid")
    eid = doi or pmid or f"intel_{doc.get('id')}"
    return {
        "id": str(eid),
        "title": doc.get("title") or "Untitled",
        "authors": doc.get("authors") or raw.get("authors") or "",
        "year": doc.get("year") or raw.get("year"),
        "journal": raw.get("journal") or raw.get("venue") or doc.get("venue"),
        "volume": raw.get("volume"),
        "issue": raw.get("issue"),
        "pages": raw.get("pages"),
        "doi": doi,
        "pmid": pmid,
        "abstract": doc.get("abstract") or raw.get("abstract"),
        "source": "openalex" if doc.get("source") == "openalex" else "manual",
        "project_ids": [project_id],
        "tags": list(set((raw.get("tags") or []) + ["module4_sync"])),
        "notes": (raw.get("notes") or "") + f" [module4 doc_id={doc.get('id')}]".strip(),
    }


def write_entry_to_intel_item(entry: ReferenceEntry) -> tuple[str, dict[str, Any]]:
    item: dict[str, Any] = {
        "title": entry.title,
        "authors": entry.authors,
        "year": entry.year,
        "doi": entry.doi,
        "abstract": entry.abstract,
        "journal": entry.journal,
        "venue": entry.journal,
        "pmid": entry.pmid,
        "pmcid": entry.pmcid,
        "volume": entry.volume,
        "issue": entry.issue,
        "pages": entry.pages,
        "url": f"https://doi.org/{entry.doi}" if entry.doi else None,
        "openalex_id": entry.doi or entry.id,
        "verification_status": "user-provided",
        "tags": list(entry.tags or []),
        "write_library_id": entry.id,
    }
    if entry.doi:
        item = enrich_work(item)
    src = "openalex" if entry.source in ("openalex", "pubmed") and entry.doi else "manual"
    return src, item


def sync_to_write(username: str, project_id: str | None) -> dict[str, Any]:
    pid = _project_id(project_id)
    docs = list_documents(pid, limit=500)
    pushed = 0
    updated = 0
    skipped = 0
    existing = load_library(username)
    known_doi = {e.doi for e in existing if e.doi}
    known_id = {e.id for e in existing}
    for doc in docs:
        if (doc.get("source") or "") not in _LIT_SOURCES:
            skipped += 1
            continue
        data = intel_doc_to_write_entry(doc, pid)
        eid = str(data.get("id") or "")
        if eid in known_id or (data.get("doi") and data["doi"] in known_doi):
            updated += 1
        else:
            pushed += 1
            if data.get("doi"):
                known_doi.add(data["doi"])
            known_id.add(eid)
        add_or_update_reference(username, data)
    return {
        "direction": "to_write",
        "project_id": pid,
        "pushed": pushed,
        "updated": updated,
        "skipped_non_literature": skipped,
        "total_intel_literature": sum(1 for d in docs if d.get("source") in _LIT_SOURCES),
    }


def sync_from_write(username: str, project_id: str | None) -> dict[str, Any]:
    pid = _project_id(project_id)
    entries = search_library(username, "", project_id=None)
    saved = 0
    updated = 0
    skipped = 0
    for entry in entries:
        if not _entry_matches_project(entry, pid):
            skipped += 1
            continue
        src, item = write_entry_to_intel_item(entry)
        res = save_document(pid, src, item)
        if res.get("inserted"):
            saved += 1
        else:
            updated += 1
    return {
        "direction": "from_write",
        "project_id": pid,
        "saved": saved,
        "updated": updated,
        "skipped_other_project": skipped,
        "write_entries_seen": len(entries),
    }


def sync_both(username: str, project_id: str | None) -> dict[str, Any]:
    to_w = sync_to_write(username, project_id)
    from_w = sync_from_write(username, project_id)
    return {"ok": True, "to_write": to_w, "from_write": from_w}
