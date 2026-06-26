#!/usr/bin/env python3
"""
Build unified VHH database classification tables from reconciliation output.

Inputs:
  data/_reconciliation/VHH_ID_RECONCILIATION.csv

Outputs:
  data/vhh_database/VHH_DATABASE_MASTER_v1.csv
  data/vhh_database/VHH_DATABASE_MASTER_v1.json
  data/vhh_database/VHH_DATABASE_NONREDUNDANT_SEQUENCES_v1.csv
  data/vhh_database/VHH_DATABASE_EXCLUDED_NON_SDVHH_v1.csv
  data/vhh_database/VHH_DATABASE_COUNTS_v1.md

This script classifies identities; it does not change frozen reference cohorts,
thresholds, standards, or registry entries.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List


SUITE = Path(__file__).resolve().parents[1]
INPUT = SUITE / "data" / "_reconciliation" / "VHH_ID_RECONCILIATION.csv"
OUT_DIR = SUITE / "data" / "vhh_database"


def _bool(value: str) -> bool:
    return str(value).strip().lower() == "true"


def _read_rows() -> List[Dict[str, str]]:
    with INPUT.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _hash_groups(rows: Iterable[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    groups: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        seq_hash = row.get("canonical_sequence_hash") or ""
        if seq_hash:
            groups[seq_hash].append(row)
    return groups


def _duplicate_reason(row: Dict[str, str], group: List[Dict[str, str]]) -> str:
    if not row.get("canonical_sequence_hash"):
        return "no_sequence"
    if len(group) <= 1:
        return "unique_sequence"
    names = [r.get("display_name", "") for r in group]
    ids = [r.get("canonical_id", "") for r in group]
    if all(name[:4].lower().isalnum() and "_" in cid for name, cid in zip(names, ids)):
        pdb_prefixes = {cid.split("_", 1)[0] for cid in ids}
        if len(pdb_prefixes) == 1 and all(len(cid.rsplit("_", 1)[-1]) == 1 for cid in ids):
            return "pdb_chain_copy"
    if all(_bool(r.get("in_database_b_29", "")) for r in group):
        return "database_b_chain_copy_or_structure_redundancy"
    return "alias_or_reused_construct"


def _entity_class(row: Dict[str, str]) -> str:
    platform = row.get("cohort_platform_tag") or ""
    if platform == "transgenic_mouse_nanobody":
        return "transgenic_mouse_nanobody_vhh"
    if platform == "humanized_camelid_tandem_vh_fc":
        return "humanized_camelid_tandem_vh_fc"
    if platform == "master_table_metadata_only_no_single_vhh_sequence":
        return "humanized_camelid_tandem_vh_fc"
    if _bool(row.get("in_clinical_39", "")):
        return "clinical_single_domain_vhh"
    if _bool(row.get("in_structural_union_69", "")) and not _bool(row.get("in_database_b_29", "")):
        return "clinical_single_domain_vhh"
    if _bool(row.get("in_database_b_29", "")):
        return "database_b_engineered_or_humanized_camelid_vhh"
    if _bool(row.get("in_master_table_40", "")):
        return "clinical_master_table_metadata_only"
    return "unclassified_review_required"


def _modality_class(row: Dict[str, str]) -> str:
    platform = row.get("cohort_platform_tag") or ""
    if platform in {
        "master_table_metadata_only_no_single_vhh_sequence",
        "humanized_camelid_tandem_vh_fc",
    }:
        return "tandem_vh_fc_not_single_domain"
    if (
        _bool(row.get("in_clinical_39", ""))
        or _bool(row.get("in_database_b_29", ""))
        or _bool(row.get("in_structural_union_69", ""))
    ):
        return "single_domain_vhh_or_vh_like"
    return "unknown_review_required"


def _statistical_inclusion(row: Dict[str, str]) -> str:
    entity = _entity_class(row)
    platform = row.get("cohort_platform_tag") or ""
    if entity == "humanized_camelid_tandem_vh_fc":
        return "exclude_sequence_stats_not_single_domain_vhh"
    if platform == "transgenic_mouse_nanobody":
        return "include_all69_exclude_camelid68_calibration"
    if _bool(row.get("in_clinical_39", "")):
        return "include_validated_clinical39_and_vhh42"
    if _bool(row.get("in_database_b_29", "")):
        return "include_database_b29_and_structural_union69"
    if _bool(row.get("in_structural_union_69", "")):
        return "include_structural_union69_not_validated39"
    return "review_required"


def _vhh42_role(row: Dict[str, str]) -> str:
    tags = row.get("origin_tags") or ""
    if _bool(row.get("in_clinical_39", "")) and _bool(row.get("in_vhh42_cmc", "")):
        return "vhh42_clinical_side"
    if "sabdab_humanized_vhh" in tags and _bool(row.get("in_vhh42_cmc", "")):
        return "vhh42_database_b_supplement"
    if _bool(row.get("in_vhh42_cmc", "")):
        return "vhh42_other_review_required"
    return ""


def build() -> List[Dict[str, str]]:
    rows = _read_rows()
    groups = _hash_groups(rows)
    out: List[Dict[str, str]] = []
    for row in rows:
        seq_hash = row.get("canonical_sequence_hash") or ""
        group = groups.get(seq_hash, [])
        aliases = sorted(r.get("display_name", "") for r in group if r.get("display_name")) if group else []
        out.append(
            {
                "canonical_id": row.get("canonical_id", ""),
                "display_name": row.get("display_name", ""),
                "entity_class": _entity_class(row),
                "modality_class": _modality_class(row),
                "statistical_inclusion": _statistical_inclusion(row),
                "vhh42_role": _vhh42_role(row),
                "origin_tags": row.get("origin_tags", ""),
                "cohort_platform_tag": row.get("cohort_platform_tag", ""),
                "canonical_sequence_hash": seq_hash,
                "sequence_status": (
                    "sequence_present"
                    if seq_hash
                    else (
                        "full_chain_sequence_collected_excluded_from_sdvhh_stats"
                        if _entity_class(row) == "humanized_camelid_tandem_vh_fc"
                        else "no_sequence_in_validated_sources"
                    )
                ),
                "duplicate_group_id": f"seqhash:{seq_hash}" if seq_hash and len(group) > 1 else "",
                "duplicate_group_size": str(len(group)) if seq_hash else "0",
                "duplicate_reason": _duplicate_reason(row, group),
                "aliases_same_sequence": ";".join(aliases),
                "in_clinical_39": row.get("in_clinical_39", ""),
                "in_master_table_40": row.get("in_master_table_40", ""),
                "in_vhh42_cmc": row.get("in_vhh42_cmc", ""),
                "in_database_b_29": row.get("in_database_b_29", ""),
                "in_structural_union_69": row.get("in_structural_union_69", ""),
                "germline_top_match": row.get("germline_top_match", ""),
                "ada_majority_risk": row.get("ada_majority_risk", ""),
                "structural_pdb_model": row.get("structural_pdb_model", ""),
            }
        )
    return out


def write_outputs(rows: List[Dict[str, str]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "VHH_DATABASE_MASTER_v1.csv"
    json_path = OUT_DIR / "VHH_DATABASE_MASTER_v1.json"
    nonredundant_path = OUT_DIR / "VHH_DATABASE_NONREDUNDANT_SEQUENCES_v1.csv"
    excluded_non_sdvhh_path = OUT_DIR / "VHH_DATABASE_EXCLUDED_NON_SDVHH_v1.csv"
    md_path = OUT_DIR / "VHH_DATABASE_COUNTS_v1.md"

    fieldnames = list(rows[0].keys()) if rows else []
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "_meta": {
                    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "source": str(INPUT.relative_to(SUITE)),
                    "n_rows": len(rows),
                    "note": "Unified classification table; counts by identity, not deduplicated sequence unless stated.",
                },
                "rows": rows,
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )

    groups_by_hash: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    excluded_non_sdvhh_rows: List[Dict[str, str]] = []
    for r in rows:
        if r["canonical_sequence_hash"]:
            groups_by_hash[r["canonical_sequence_hash"]].append(r)
        elif r["entity_class"] == "humanized_camelid_tandem_vh_fc":
            excluded_non_sdvhh_rows.append(r)

    nonredundant_rows: List[Dict[str, str]] = []
    for seq_hash, group in sorted(groups_by_hash.items()):
        entity_classes = sorted({r["entity_class"] for r in group})
        representative = sorted(group, key=lambda r: (r["entity_class"], r["display_name"]))[0]
        nonredundant_rows.append(
            {
                "canonical_sequence_hash": seq_hash,
                "representative_id": representative["canonical_id"],
                "representative_name": representative["display_name"],
                "sequence_entity_class": (
                    entity_classes[0] if len(entity_classes) == 1 else "mixed_entity_review_required"
                ),
                "identity_count": str(len(group)),
                "duplicate_excess_count": str(len(group) - 1),
                "aliases_same_sequence": ";".join(sorted(r["display_name"] for r in group)),
                "entity_classes_present": ";".join(entity_classes),
                "vhh42_roles_present": ";".join(sorted({r["vhh42_role"] for r in group if r["vhh42_role"]})),
                "statistical_inclusions_present": ";".join(sorted({r["statistical_inclusion"] for r in group})),
                "duplicate_reason": representative["duplicate_reason"],
            }
        )

    nr_fields = list(nonredundant_rows[0].keys()) if nonredundant_rows else []
    with nonredundant_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=nr_fields)
        writer.writeheader()
        writer.writerows(nonredundant_rows)

    with excluded_non_sdvhh_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(excluded_non_sdvhh_rows)

    entity_counts = Counter(r["entity_class"] for r in rows)
    modality_counts = Counter(r["modality_class"] for r in rows)
    stat_counts = Counter(r["statistical_inclusion"] for r in rows)
    vhh42_role_counts = Counter(r["vhh42_role"] or "not_in_vhh42" for r in rows)
    duplicate_counts = Counter(r["duplicate_reason"] for r in rows)
    sequence_hashes = {r["canonical_sequence_hash"] for r in rows if r["canonical_sequence_hash"]}
    nonredundant_entity_counts = Counter(r["sequence_entity_class"] for r in nonredundant_rows)
    duplicate_groups = {
        r["duplicate_group_id"]
        for r in rows
        if r["duplicate_group_id"]
    }

    def table(counter: Counter[str]) -> str:
        lines = ["| Class | Count |", "| --- | ---: |"]
        for key, value in sorted(counter.items()):
            lines.append(f"| `{key}` | {value} |")
        return "\n".join(lines)

    md = f"""# VHH Database Counts v1

Generated from `{INPUT.relative_to(SUITE)}`.

## Headline Counts

| Metric | Count |
| --- | ---: |
| identity rows | {len(rows)} |
| rows with sequence hash | {sum(1 for r in rows if r['canonical_sequence_hash'])} |
| unique sequence hashes | {len(sequence_hashes)} |
| duplicate sequence groups | {len(duplicate_groups)} |
| no-sequence rows | {sum(1 for r in rows if not r['canonical_sequence_hash'])} |
| duplicate excess identity rows | {sum(int(r['duplicate_excess_count']) for r in nonredundant_rows)} |

## Entity Classes

{table(entity_counts)}

## Nonredundant Sequence Classes

{table(nonredundant_entity_counts)}

## Modality Classes

{table(modality_counts)}

## Statistical Inclusion

{table(stat_counts)}

## VHH42 Roles

{table(vhh42_role_counts)}

## Duplicate Reasons

{table(duplicate_counts)}

## Interpretation Rules

- Use `entity_class` for cohort membership and reporting.
- Use `vhh42_role` for the mixed VHH42 reference role. VHH42 is not an entity class and must not be described as “42 clinical VHH” or “42 humanized VHH”.
- Use `statistical_inclusion` for whether a row can enter clinical39, VHH42, Database-B, structural-union, or camelid-only calibration statistics.
- Use `canonical_sequence_hash` and `duplicate_group_id` for sequence-level de-duplication. Identity counts and unique-sequence counts must be reported separately.
- Use `VHH_DATABASE_NONREDUNDANT_SEQUENCES_v1.csv` for sequence-level statistics. It has one row per unique sequence hash.
- Use `VHH_DATABASE_EXCLUDED_NON_SDVHH_v1.csv` for non-single-domain molecules such as Lofacimig.
- `clinical_single_domain_vhh` includes validated clinical39 rows except separately-tagged transgenic-mouse rows, plus clinical structural-union-only VHH rows such as Erfonrilimab-VHH2.
- `humanized_camelid_tandem_vh_fc` rows, currently Lofacimig, are clinical molecules with full-chain sequence provenance but excluded from single-domain VHH sequence statistics.
- `transgenic_mouse_nanobody_vhh` rows, currently Porustobart, remain in all-69 union statistics but should be excluded from camelid-only n=68 calibration.
"""
    md_path.write_text(md, encoding="utf-8")

    print(f"Wrote {csv_path.relative_to(SUITE)}")
    print(f"Wrote {json_path.relative_to(SUITE)}")
    print(f"Wrote {nonredundant_path.relative_to(SUITE)}")
    print(f"Wrote {excluded_non_sdvhh_path.relative_to(SUITE)}")
    print(f"Wrote {md_path.relative_to(SUITE)}")
    print(f"identity rows: {len(rows)}")
    print(f"unique sequence hashes: {len(sequence_hashes)}")
    print(f"duplicate sequence groups: {len(duplicate_groups)}")


def main() -> None:
    write_outputs(build())


if __name__ == "__main__":
    main()
