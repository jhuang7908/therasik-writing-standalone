#!/usr/bin/env python3
"""
ACTES component library integrity check.
- Counts all curated components across functional_domains.json and sequence_db to verify ~200.
- Samples entries and verifies: sequence present, source/QA when expected, no placeholders.
"""
from pathlib import Path
import json
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
FUNC_DOMAINS = REPO_ROOT / "ACTES_CART_Engine_v1.0" / "resources" / "functional_domains.json"
SEQ_DB = REPO_ROOT / "data" / "actes_sequences" / "sequence_db.json"
NEW_BINDERS = REPO_ROOT / "data" / "actes_sequences" / "new_binders.json"


def count_entries_in_dict(d: dict, prefix: str = "") -> list[tuple[str, dict]]:
    """Yield (key, value) for top-level named entries (not _note, not nested component keys)."""
    out = []
    for k, v in d.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict):
            if "seq" in v or "seq_ref" in v or "description" in v or "target" in v or "ECD" in v:
                out.append((f"{prefix}.{k}" if prefix else k, v))
            else:
                out.extend(count_entries_in_dict(v, f"{prefix}.{k}" if prefix else k))
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    out.append((f"{prefix}.{k}[{i}]" if prefix else f"{k}[{i}]", item))
    return out


def flatten_components(obj, path="", acc=None):
    """Flatten nested structure to list of (path, leaf_obj) where leaf has seq or seq_ref."""
    if acc is None:
        acc = []
    if isinstance(obj, dict):
        if "seq" in obj or "seq_ref" in obj:
            acc.append((path, obj))
        for k, v in obj.items():
            if k.startswith("_"):
                continue
            flatten_components(v, f"{path}.{k}" if path else k, acc)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            flatten_components(v, f"{path}[{i}]", acc)
    return acc


def main():
    print("=" * 60)
    print("ACTES Component Library — Completeness & Sampling Check")
    print("=" * 60)

    # --- functional_domains.json ---
    if not FUNC_DOMAINS.exists():
        print(f"Missing: {FUNC_DOMAINS}")
        return
    with open(FUNC_DOMAINS, "r", encoding="utf-8") as f:
        fd = json.load(f)

    category_counts = {}
    total_fd = 0
    for top_key, top_val in fd.items():
        if top_key.startswith("_"):
            continue
        if not isinstance(top_val, dict):
            continue
        # Count named entries in this category (e.g. each binder name, each hinge name)
        n = 0
        for k, v in top_val.items():
            if k.startswith("_"):
                continue
            if isinstance(v, dict):
                n += 1
        category_counts[top_key] = n
        total_fd += n

    print("\n1) functional_domains.json — entries per category")
    print("-" * 40)
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count}")
    print(f"   TOTAL (named entries): {total_fd}")

    # Count leaf components that have seq (to avoid double-counting sub-parts)
    flat = flatten_components(fd)
    with_seq = sum(1 for _, o in flat if o.get("seq") and not str(o.get("seq", "")).startswith("EVPED"))  # exclude placeholder
    with_ref = sum(1 for _, o in flat if o.get("seq_ref"))
    print(f"   Leaf components with 'seq': {with_seq}, with 'seq_ref': {with_ref}")

    # --- sequence_db.json ---
    seq_db_count = 0
    seq_db_ids = set()
    if SEQ_DB.exists():
        with open(SEQ_DB, "r", encoding="utf-8") as f:
            sd = json.load(f)
        entries = sd.get("entries", [])
        seq_db_count = len(entries)
        seq_db_ids = {e.get("entry_id") for e in entries if e.get("entry_id")}
        print(f"\n2) sequence_db.json — entries: {seq_db_count}")

    # --- new_binders.json ---
    new_binders_count = 0
    if NEW_BINDERS.exists():
        with open(NEW_BINDERS, "r", encoding="utf-8") as f:
            nb = json.load(f)
        new_binders_count = len(nb) if isinstance(nb, list) else 0
        print(f"3) new_binders.json — entries: {new_binders_count}")

    # Combined unique (sequence_db + new_binders may overlap by id; fd is different structure)
    # Conservative total: fd named entries + seq_db (many seq_db are referenced by fd)
    # So total "library size" often = fd entries + (seq_db entries that are not just refs from fd)
    # For "nearly 200" we need total_fd + something. If total_fd is e.g. 80, we need ~120 from elsewhere.
    total_library = total_fd + seq_db_count + new_binders_count
    print(f"\n   Raw sum (fd + sequence_db + new_binders): {total_library}")
    print("   (Overlap possible: sequence_db may contain sequences referenced by functional_domains)")

    # --- Sampling: pick a few from fd and check rigor ---
    print("\n4) Sampling — information completeness (rigor)")
    print("-" * 40)

    samples = []
    for top_key, top_val in fd.items():
        if top_key.startswith("_") or not isinstance(top_val, dict):
            continue
        for name, entry in list(top_val.items())[:2]:  # up to 2 per category
            if name.startswith("_"):
                continue
            samples.append((f"{top_key}.{name}", entry))

    issues = []
    for path, obj in samples[:16]:
        line = f"   {path}: "
        if isinstance(obj, dict):
            # Target rules (targets.*) don't have seq; short peptides (e.g. mimotope 9 aa) are valid
            has_seq = "seq" in obj and obj["seq"] and len(str(obj["seq"]).strip()) >= 5
            seq_ok = has_seq and "PARTIALLY_MAPPED" not in str(obj.get("seq", "")) and "awaiting" not in str(obj.get("seq", "")).lower()
            has_ref = "seq_ref" in obj
            def has_qa_any(o):
                if isinstance(o, dict):
                    if "qa" in o:
                        return True
                    return any(has_qa_any(v) for v in o.values())
                return False
            has_qa = has_qa_any(obj)
            has_source = "source" in obj or "uniprot" in obj or "target" in obj or "description" in obj
            if has_seq or has_ref:
                line += "seq/ref=OK "
            else:
                line += "seq/ref=MISSING "
            if has_qa or has_source:
                line += "source/qa=OK"
            else:
                line += "source/qa=check"
            if not seq_ok and has_seq:
                issues.append(f"{path}: possible placeholder in seq")
        else:
            line += "not-dict"
        print(line)

    if issues:
        print("\n   Potential issues:")
        for i in issues[:10]:
            print(f"   - {i}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary: Use total named entries in functional_domains + sequence_db + new_binders")
    print(f"         as library size. Current total_fd={total_fd}; sequence_db={seq_db_count}; new_binders={new_binders_count}.")
    print("         'Nearly 200' is accurate if combined unique component count is in 180–210 range.")
    print("=" * 60)


if __name__ == "__main__":
    main()
