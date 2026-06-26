"""
Builtin sample rows for Module 4 literature / patent databases.

Loads ``data/intelligence_demo_samples.json`` (no OpenAlex/PubMed API calls).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from . import intelligence_store
except ImportError:
    import intelligence_store  # type: ignore[no-redef]

_SAMPLES_PATH = Path(__file__).resolve().parent / "data" / "intelligence_demo_samples.json"


def load_sample_manifest() -> dict[str, Any]:
    return json.loads(_SAMPLES_PATH.read_text(encoding="utf-8"))


def seed_builtin_samples(
    project_id: str | None,
    *,
    force: bool = False,
    min_existing: int = 3,
) -> dict[str, Any]:
    """
    Insert curated demo literature + patent rows for UI walkthrough.

    Skips when the project already has >= ``min_existing`` documents unless ``force``.
    """
    pid = intelligence_store._norm_project(project_id)
    existing = intelligence_store.count_documents(pid)
    if not force and existing >= min_existing:
        return {
            "ok": True,
            "skipped": True,
            "project_id": pid,
            "existing_count": existing,
            "reason": f"project already has {existing} record(s)",
        }

    manifest = load_sample_manifest()
    lit_saved = 0
    pat_saved = 0
    doc_ids: list[int] = []
    errors: list[str] = []
    subproject_by_id: dict[int, str] = {}

    for block_key, counter_name in (("literature", "lit_saved"), ("patents", "pat_saved")):
        for entry in manifest.get(block_key) or []:
            src = str(entry.get("source") or "manual").strip()
            item = dict(entry.get("item") or {})
            sp = (entry.get("subproject") or item.get("subproject") or "").strip()
            if sp:
                item["subproject"] = sp
            try:
                res = intelligence_store.save_document(pid, src, item)
                doc_id = res.get("id")
                if doc_id is not None:
                    doc_ids.append(int(doc_id))
                    if sp:
                        subproject_by_id[int(doc_id)] = sp
                if block_key == "literature":
                    lit_saved += 1
                else:
                    pat_saved += 1
            except Exception as exc:
                errors.append(f"{src} '{item.get('title', '')[:40]}': {exc}")

    tagged: dict[str, int] = {}
    by_sp: dict[str, list[int]] = {}
    for did, sp in subproject_by_id.items():
        by_sp.setdefault(sp, []).append(did)
    for sp, ids in by_sp.items():
        try:
            out = intelligence_store.tag_documents(pid, ids, sp)
            tagged[sp] = int(out.get("updated") or len(ids))
        except Exception as exc:
            errors.append(f"tag {sp}: {exc}")

    total = intelligence_store.count_documents(pid)
    return {
        "ok": True,
        "skipped": False,
        "project_id": pid,
        "literature_saved": lit_saved,
        "patents_saved": pat_saved,
        "total_in_project": total,
        "subprojects": intelligence_store.list_subprojects(pid),
        "tagged": tagged,
        "errors": errors,
    }
