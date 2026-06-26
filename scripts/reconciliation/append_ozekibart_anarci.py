"""
Append Ozekibart ANARCII numbering to the 40-clinical reconciliation file.

Background:
    `data/vhh_clinical_40_anarci/anarci_results.json` was generated from
    `vhh_clinical_antibodies_complete_v2.json`, which omits Ozekibart.
    Ozekibart's sequence is curated from Thera-SAbDab (OPIG) and stored in
    `data/vhh_clinical_39_union/ozekibart_sequence.json`.

This script:
    1. Loads Ozekibart's curated sequence.
    2. Runs ANARCII (`anarcii` package) using the same Kabat scheme and the
       same serialization pattern as `scripts/vhh_clinical_40_anarci.py`.
    3. Appends the result to `data/vhh_clinical_40_anarci/anarci_results.json`,
       bumping `count` from 38 -> 39 if Ozekibart was missing.

The script is idempotent: if Ozekibart is already present, it does nothing.
It does not modify any LOCKED standard, config, or registry file.

Run (must be inside the `anarcii` conda env):
    conda run -n anarcii python scripts/reconciliation/append_ozekibart_anarci.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SEQ = (
    REPO_ROOT / "data" / "vhh_clinical_39_union" / "ozekibart_sequence.json"
)
TARGET = REPO_ROOT / "data" / "vhh_clinical_40_anarci" / "anarci_results.json"
SCHEME = "kabat"
ENTRY_ID = "Ozekibart"


def _load_sequence() -> str:
    with SOURCE_SEQ.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    seq = (data.get("Sequence") or "").strip().replace(" ", "")
    if not seq:
        raise SystemExit(f"[ozekibart-anarci] no Sequence field in {SOURCE_SEQ}")
    return seq


def _run_anarcii(sequence: str) -> list | None:
    try:
        from anarcii import Anarcii
    except ImportError as exc:
        raise SystemExit(
            "[ozekibart-anarci] anarcii package not importable. "
            "Activate the anarcii conda env. Original error: "
            f"{exc}"
        )
    engine = Anarcii()
    try:
        engine.number([(ENTRY_ID, sequence)])
        result = engine.to_scheme(SCHEME)
    except Exception as exc:
        raise SystemExit(f"[ozekibart-anarci] ANARCII run failed: {exc}")
    if not isinstance(result, dict):
        return None
    entry = result.get(ENTRY_ID, {})
    numbering = entry.get("numbering") if isinstance(entry, dict) else None
    return numbering


def _serialize_numbering(numbering: list | None) -> list | None:
    """Match the truncated preview format used by vhh_clinical_40_anarci.py."""
    if numbering is None:
        return None
    if not isinstance(numbering, list):
        return None
    head = []
    for item in numbering[:3]:
        try:
            head.append([list(item[0]), item[1]])
        except Exception:
            return None
    head.append(f"... {len(numbering)} total")
    return head


def main() -> int:
    if not TARGET.exists():
        raise SystemExit(f"[ozekibart-anarci] target not found: {TARGET}")

    with TARGET.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    results = payload.get("results", [])
    existing_ids = {r.get("id") for r in results}
    if ENTRY_ID in existing_ids:
        print(f"[ozekibart-anarci] {ENTRY_ID} already present; nothing to do.")
        return 0

    sequence = _load_sequence()
    print(f"[ozekibart-anarci] loaded sequence ({len(sequence)} aa) from {SOURCE_SEQ.name}")

    numbering = _run_anarcii(sequence)
    has_numbering = numbering is not None
    serialized = _serialize_numbering(numbering)

    new_entry = {
        "id": ENTRY_ID,
        "len": len(sequence),
        "has_numbering": has_numbering,
        "numbering": serialized,
    }

    results.append(new_entry)
    payload["results"] = results
    payload["count"] = len(results)

    with TARGET.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)

    print(
        f"[ozekibart-anarci] appended {ENTRY_ID}; "
        f"has_numbering={has_numbering}; new count={payload['count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
