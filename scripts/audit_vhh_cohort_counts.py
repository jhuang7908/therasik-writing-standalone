#!/usr/bin/env python3
"""
audit_vhh_cohort_counts.py
==========================
Recompute VHH cohort sizes from frozen files only (no registry prose).

Writes canonical counts + definitions-friendly breakdown to stdout and optional JSON.

Canonical paths (suite-relative):
  data/vhh_structural_union/vhh68_special_cmc_results.json
  data/vhh_structural_union/vhh_structural_union_index.json
  data/vhh_clinical_39_union/vhh42_cmc_metrics.csv
  data/vhh_clinical_39_union/vhh42_sabdab_supplement.json
  data/vhh_39_clinical_atlas/master_table.csv
  data/vhh_clinical_39_union/vhh_39_sequences_clinical_validated.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

SUITE = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit VHH cohort counts from data files")
    ap.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write machine-readable snapshot (UTF-8 JSON)",
    )
    args = ap.parse_args()

    errors: List[str] = []

    p68 = SUITE / "data/vhh_structural_union/vhh68_special_cmc_results.json"
    p_idx = SUITE / "data/vhh_structural_union/vhh_structural_union_index.json"
    p_vhh42 = SUITE / "data/vhh_clinical_39_union/vhh42_cmc_metrics.csv"
    p_sup = SUITE / "data/vhh_clinical_39_union/vhh42_sabdab_supplement.json"
    p_mt = SUITE / "data/vhh_39_clinical_atlas/master_table.csv"
    p_val = SUITE / "data/vhh_clinical_39_union/vhh_39_sequences_clinical_validated.json"

    for p in (p68, p_idx, p_vhh42, p_sup, p_mt, p_val):
        if not p.is_file():
            errors.append(f"missing_file:{p.relative_to(SUITE)}")

    data68: List[Dict[str, Any]] = _read_json(p68) if p68.is_file() else []
    idx = _read_json(p_idx) if p_idx.is_file() else {}
    meta_idx = idx.get("_meta", {}) if isinstance(idx, dict) else {}

    ss_counts = Counter(str(r.get("source_set", "?")) for r in data68)
    ids_clinical_bucket = [r.get("id") for r in data68 if r.get("source_set") == "clinical_vhh_immunbuilder"]
    ids_db_bucket = [r.get("id") for r in data68 if r.get("source_set") == "database_b_humanized_camelid_nanobuilder"]

    supplement = _read_json(p_sup) if p_sup.is_file() else {}
    sup_entries = supplement.get("entries", []) if isinstance(supplement, dict) else []
    sup_ids = sorted({str(e.get("id")) for e in sup_entries if isinstance(e, dict)})

    rows42: List[Dict[str, str]] = []
    if p_vhh42.is_file():
        with p_vhh42.open(encoding="utf-8", newline="") as f:
            rows42 = list(csv.DictReader(f))
    names42 = [r.get("name", "") for r in rows42]
    vhh42_clinical_rows = [n for n in names42 if n and n not in sup_ids]
    vhh42_supplement_rows = [n for n in names42 if n in sup_ids]

    mt_rows: List[Dict[str, str]] = []
    if p_mt.is_file():
        with p_mt.open(encoding="utf-8", newline="", errors="replace") as f:
            mt_rows = list(csv.DictReader(f))
    mt_names = [r.get("Name", "").strip() for r in mt_rows if r.get("Name")]

    validated = _read_json(p_val) if p_val.is_file() else {}
    vhh_list = validated.get("vhh", []) if isinstance(validated, dict) else []
    val_names = [x.get("Name", "").strip() for x in vhh_list if isinstance(x, dict)]

    # Cross-checks
    if len(data68) != len(ids_clinical_bucket) + len(ids_db_bucket):
        errors.append("vhh68_split_sum_mismatch")
    if len(names42) != len(vhh42_clinical_rows) + len(vhh42_supplement_rows):
        errors.append("vhh42_row_split_mismatch")
    if set(sup_ids) != set(vhh42_supplement_rows):
        errors.append(f"vhh42_supplement_mismatch expected={sup_ids} got={sorted(vhh42_supplement_rows)}")

    porustobart_in_clinical = "Porustobart" in ids_clinical_bucket

    snapshot: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "suite_root": str(SUITE),
        "errors": errors,
        "terminology": {
            "clinical_sequence_cohort_39": (
                "39 therapeutic/clinical-style single-domain VHH sequences in "
                "vhh_39_sequences_clinical_validated.json — SSOT for ‘validated clinical’ counts."
            ),
            "master_table_rows_40": (
                "40 rows in vhh_39_clinical_atlas/master_table.csv — includes Lofacimig "
                "without a production single-chain sequence row (metadata-only)."
            ),
            "vhh42_per_sequence_cmc_42": (
                "42 rows in vhh42_cmc_metrics.csv = 39 clinical_sequence_cohort names "
                "+ 3 SAbDab-published humanized camelid chains (supplement PDB ids)."
            ),
            "vhh68_union_69": (
                "69 rows in vhh68_special_cmc_results.json — 40 clinical_vhh_immunbuilder "
                "+ 29 database_b_humanized_camelid_nanobuilder. Porustobart is inside the "
                "40-clinical bucket in JSON (no separate platform field)."
            ),
            "structural_union_index": (
                "vhh_structural_union_index.json _meta must match vhh68 row totals "
                "(clinical_n + database_b_n = total_n)."
            ),
        },
        "sources": {
            "vhh68_special_cmc_results": str(p68.relative_to(SUITE)),
            "vhh_structural_union_index": str(p_idx.relative_to(SUITE)),
            "vhh42_cmc_metrics": str(p_vhh42.relative_to(SUITE)),
            "vhh42_sabdab_supplement": str(p_sup.relative_to(SUITE)),
            "clinical_atlas_master_table": str(p_mt.relative_to(SUITE)),
            "clinical_validated_sequences": str(p_val.relative_to(SUITE)),
        },
        "counts": {
            "vhh68_total": len(data68),
            "vhh68_by_source_set": dict(sorted(ss_counts.items(), key=lambda x: (-x[1], x[0]))),
            "vhh68_clinical_bucket": len(ids_clinical_bucket),
            "vhh68_database_b_bucket": len(ids_db_bucket),
            "porustobart_in_clinical_bucket_json": porustobart_in_clinical,
            "structural_union_meta": {
                "clinical_n": meta_idx.get("clinical_n"),
                "database_b_n": meta_idx.get("database_b_n"),
                "total_n": meta_idx.get("total_n"),
            },
            "master_table_row_count": len(mt_rows),
            "master_table_distinct_name_count": len(set(mt_names)),
            "clinical_validated_sequence_count": len(vhh_list),
            "clinical_validated_distinct_name_count": len(set(val_names)),
            "vhh42_cmc_metrics_rows": len(rows42),
            "vhh42_clinical_side_rows": len(vhh42_clinical_rows),
            "vhh42_supplement_rows": len(vhh42_supplement_rows),
            "vhh42_supplement_ids_fixed": sup_ids,
        },
        "identity_notes": {
            "lofacimig": (
                "Present as a master_table row; absent from clinical_validated JSON and "
                "vhh42_cmc_metrics — see data/_reconciliation/LOFACIMIG_STATUS.md."
            ),
            "three_sabdab_in_database_b": (
                "1yzz_A, 3eak_A, 6rnk_B are both VHH42 supplement rows and members of "
                "Database-B / structural union (no extra identities beyond 69-union math)."
            ),
        },
    }

    # Consistency: index meta vs computed
    if meta_idx:
        if meta_idx.get("total_n") != snapshot["counts"]["vhh68_total"]:
            errors.append(
                f"structural_union_total_mismatch meta={meta_idx.get('total_n')} vhh68={len(data68)}"
            )
        snapshot["errors"] = errors

    text_report = [
        "=== VHH cohort audit (file-derived) ===",
        f"vhh68_special_cmc_results.json  total = {len(data68)}",
        f"  by source_set: {dict(sorted(ss_counts.items()))}",
        f"  Porustobart in clinical bucket: {porustobart_in_clinical}",
        f"vhh_structural_union_index _meta: {meta_idx}",
        f"master_table.csv rows: {len(mt_rows)}",
        f"clinical_validated.json sequences: {len(vhh_list)}",
        f"vhh42_cmc_metrics.csv rows: {len(rows42)} (clinical-side {len(vhh42_clinical_rows)} + supplement {len(vhh42_supplement_rows)})",
        f"supplement ids: {sup_ids}",
        f"errors: {errors or 'none'}",
    ]
    print("\n".join(text_report))

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote {args.json_out}")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
