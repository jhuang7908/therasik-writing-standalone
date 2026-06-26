"""
VHH ID Reconciliation Builder (read-only).

Cross-walks VHH identifiers across the following datasets without modifying
any production logic, standards, or registry:

  - data/vhh_clinical_39_union/vhh_39_sequences_clinical_validated.csv
  - data/vhh_39_clinical_atlas/master_table.csv
  - data/vhh_clinical_40_anarci/anarci_results.json
  - data/vhh_clinical_39_union/vhh42_cmc_metrics.csv
  - data/vhh_clinical_39_union/vhh42_germline_assignments.json
  - data/vhh_database_b_union/database_b_manifest_29.json
  - data/vhh_database_b_union/database_b_sequences.json
  - data/vhh_structural_union/vhh_structural_union_index.json
  - data/sabdab_vhh_atlas/humanized_camelid_vhh_db.json (best-effort)

Outputs:
  - data/_reconciliation/VHH_ID_RECONCILIATION.csv
  - data/_reconciliation/VHH_ID_RECONCILIATION.json
  - data/_reconciliation/VHH_ID_RECONCILIATION_SUMMARY.json

This script is deliberately conservative:
  * It does not normalize names beyond a simple slug rule.
  * It does not invent identifiers; missing entries are reported as missing.
  * It is safe to rerun; it only writes into data/_reconciliation/.

Run:
    python scripts/reconciliation/build_vhh_id_reconciliation.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA = REPO_ROOT / "data"
OUT_DIR = DATA / "_reconciliation"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slug(name: str) -> str:
    """Create a normalized lookup key for fuzzy matching across files.

    Rules:
      * Lowercase
      * Replace non-alphanumerics with single underscore
      * Strip leading/trailing underscores

    Parenthetical groups are intentionally NOT stripped, because some sources
    embed disambiguators such as ``(cilta-cel)`` or ``(M1095)`` directly in
    the identifier without parentheses. Treating ``A (B)`` and ``A_B`` as the
    same key avoids false-positive duplicates while remaining conservative.
    """
    if not isinstance(name, str):
        return ""
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _hash_seq(seq: str | None) -> str | None:
    if not seq:
        return None
    cleaned = re.sub(r"\s+", "", seq).upper()
    if not cleaned:
        return None
    return hashlib.sha1(cleaned.encode("utf-8")).hexdigest()[:12]


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return [row for row in reader if any(v for v in row.values())]


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Source loaders
# ---------------------------------------------------------------------------


def load_clinical_39() -> dict[str, dict]:
    """Load validated 39 clinical VHH cohort."""
    rows = _read_csv(DATA / "vhh_clinical_39_union" / "vhh_39_sequences_clinical_validated.csv")
    out: dict[str, dict] = {}
    for r in rows:
        name = r.get("Name", "").strip()
        if not name:
            continue
        out[_slug(name)] = {
            "display_name": name,
            "sequence": r.get("Sequence", "").strip() or None,
            "target": r.get("Target", "").strip() or None,
            "clinical_phase": r.get("Clinical_Phase", "").strip() or None,
            "in_paper_table1": r.get("In_Paper_Table1", "").strip() or None,
        }
    return out


def load_master_table_40() -> dict[str, dict]:
    """Load master_table.csv (40 rows incl. Lofacimig without sequence)."""
    rows = _read_csv(DATA / "vhh_39_clinical_atlas" / "master_table.csv")
    out: dict[str, dict] = {}
    for r in rows:
        name = r.get("Name") or r.get("antibody_id") or ""
        name = name.strip()
        if not name:
            continue
        seq = (r.get("Sequence") or "").strip() or None
        has_seg = (r.get("has_segment") or "").strip().upper() == "Y"
        out[_slug(name)] = {
            "display_name": name,
            "sequence": seq,
            "has_segment": has_seg,
            "structure_path": (r.get("structure_path") or "").strip() or None,
            "format": (r.get("format") or "").strip() or None,
            "genetics": (r.get("genetics") or "").strip() or None,
        }
    return out


def load_anarci_38() -> dict[str, dict]:
    data = _read_json(DATA / "vhh_clinical_40_anarci" / "anarci_results.json")
    if not data:
        return {}
    out: dict[str, dict] = {}
    for r in data.get("results", []):
        rid = r.get("id", "").strip()
        if not rid:
            continue
        out[_slug(rid)] = {
            "display_name": rid,
            "has_numbering": bool(r.get("has_numbering")),
            "len": r.get("len"),
        }
    return out


def load_vhh42_cmc() -> dict[str, dict]:
    rows = _read_csv(DATA / "vhh_clinical_39_union" / "vhh42_cmc_metrics.csv")
    out: dict[str, dict] = {}
    for r in rows:
        name = (r.get("name") or "").strip()
        if not name:
            continue
        out[_slug(name)] = {
            "display_name": name,
            "origin": (r.get("origin") or "").strip() or None,
            "sequence": (r.get("sequence") or "").strip() or None,
            "pI": r.get("pI"),
            "GRAVY": r.get("GRAVY"),
            "instability_index": r.get("instability_index"),
            "net_charge_pH7": r.get("net_charge_pH7"),
        }
    return out


def load_vhh42_germline() -> dict[str, dict]:
    data = _read_json(DATA / "vhh_clinical_39_union" / "vhh42_germline_assignments.json")
    if not data:
        return {}
    out: dict[str, dict] = {}
    for g in data.get("germline_assignments", []):
        name = (g.get("name") or "").strip()
        if not name:
            continue
        out[_slug(name)] = {
            "display_name": name,
            "origin": g.get("origin"),
            "top_human_germline": g.get("top_human_germline"),
            "ada_majority_risk": g.get("ada_majority_risk"),
            "vhh_sequence": g.get("vhh_sequence"),
        }
    return out


def load_database_b_29() -> dict[str, dict]:
    manifest = _read_json(DATA / "vhh_database_b_union" / "database_b_manifest_29.json")
    sequences = _read_json(DATA / "vhh_database_b_union" / "database_b_sequences.json")
    seq_lookup: dict[str, dict] = {}
    if isinstance(sequences, dict):
        seq_entries = sequences.get("entries") or sequences.get("sequences") or []
    elif isinstance(sequences, list):
        seq_entries = sequences
    else:
        seq_entries = []
    for s in seq_entries or []:
        sid = s.get("safe_id") or s.get("id") or ""
        if sid:
            seq_lookup[_slug(sid)] = {
                "sequence": s.get("sequence"),
                "model_path": s.get("model_path") or s.get("pdb_model"),
            }

    out: dict[str, dict] = {}
    if isinstance(manifest, dict):
        entries = manifest.get("entries", [])
    else:
        entries = manifest or []
    for e in entries:
        sid = (e.get("safe_id") or "").strip()
        if not sid:
            continue
        slug = _slug(sid)
        seq_info = seq_lookup.get(slug, {})
        out[slug] = {
            "display_name": sid,
            "pdb": e.get("pdb"),
            "Hchain": e.get("Hchain"),
            "compound": e.get("compound"),
            "heavy_species": e.get("heavy_species"),
            "sequence": seq_info.get("sequence"),
            "model_path": seq_info.get("model_path"),
        }
    return out


def load_platform_labels() -> tuple[dict[str, str], dict[str, dict]]:
    """Optional sparse tags from data/vhh_structural_union/vhh_platform_labels_v1.json."""
    raw = _read_json(DATA / "vhh_structural_union" / "vhh_platform_labels_v1.json") or {}
    tags = dict(raw.get("platform_tag_by_canonical_slug") or {})
    seq_pol = dict(raw.get("sequence_policy_by_canonical_slug") or {})
    return tags, seq_pol


def load_structural_union_index() -> dict[str, dict]:
    data = _read_json(DATA / "vhh_structural_union" / "vhh_structural_union_index.json")
    if not data:
        return {}
    out: dict[str, dict] = {}
    for sub in ("clinical_vhh", "database_b"):
        for e in data.get(sub, []):
            sid = (e.get("id") or "").strip()
            if not sid:
                continue
            slug = _slug(sid)
            out[slug] = {
                "display_name": sid,
                "source_set": e.get("source_set") or sub,
                "pdb_model": e.get("pdb_model"),
                "sequence": e.get("sequence"),
                "seq_len": e.get("seq_len"),
            }
    return out


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------


SOURCE_ORDER = [
    "clinical_39",
    "master_table_40",
    "anarci_38",
    "vhh42_cmc",
    "vhh42_germline",
    "database_b_29",
    "structural_union_69",
]


def build_reconciliation() -> tuple[list[dict], dict]:
    platform_tags, _seq_pol = load_platform_labels()

    sources: dict[str, dict[str, dict]] = {
        "clinical_39": load_clinical_39(),
        "master_table_40": load_master_table_40(),
        "anarci_38": load_anarci_38(),
        "vhh42_cmc": load_vhh42_cmc(),
        "vhh42_germline": load_vhh42_germline(),
        "database_b_29": load_database_b_29(),
        "structural_union_69": load_structural_union_index(),
    }

    all_slugs: "OrderedDict[str, None]" = OrderedDict()
    for sname in SOURCE_ORDER:
        for slug in sources[sname].keys():
            all_slugs.setdefault(slug, None)

    rows: list[dict] = []
    for slug in all_slugs:
        display = ""
        seqs: list[str] = []
        for sname in SOURCE_ORDER:
            entry = sources[sname].get(slug)
            if not entry:
                continue
            if not display and entry.get("display_name"):
                display = entry["display_name"]
            for key in ("sequence", "vhh_sequence"):
                val = entry.get(key)
                if val:
                    seqs.append(val)

        seq_hashes = sorted({_hash_seq(s) for s in seqs if _hash_seq(s)})
        canonical_seq_hash = seq_hashes[0] if seq_hashes else None
        seq_consistent = len(seq_hashes) <= 1

        # Source membership flags
        in_clinical_39 = slug in sources["clinical_39"]
        in_master_40 = slug in sources["master_table_40"]
        in_anarci = slug in sources["anarci_38"]
        in_vhh42_cmc = slug in sources["vhh42_cmc"]
        in_vhh42_germline = slug in sources["vhh42_germline"]
        in_db_b = slug in sources["database_b_29"]
        in_struct_union = slug in sources["structural_union_69"]

        origin_tags: list[str] = []
        if in_clinical_39:
            origin_tags.append("clinical_vhh")
        if in_db_b:
            origin_tags.append("database_b_humanized_camelid")
        cmc_origin = sources["vhh42_cmc"].get(slug, {}).get("origin")
        if cmc_origin == "SAbDab_humanized":
            origin_tags.append("sabdab_humanized_vhh")
        elif cmc_origin == "clinical":
            origin_tags.append("clinical_vhh")

        # Master-table-only Lofacimig case (no sequence)
        master_entry = sources["master_table_40"].get(slug, {})
        if (
            in_master_40
            and not in_clinical_39
            and not master_entry.get("sequence")
        ):
            origin_tags.append("master_table_only_no_seq")

        anomalies: list[str] = []
        if not seq_consistent:
            anomalies.append("sequence_hash_mismatch_across_sources")
        if in_clinical_39 and not in_anarci:
            anomalies.append("missing_in_anarci")
        if in_clinical_39 and not in_vhh42_cmc:
            anomalies.append("clinical_missing_in_vhh42_cmc")
        if in_vhh42_cmc and not (in_clinical_39 or in_db_b):
            anomalies.append("vhh42_cmc_only_no_source_cohort")
        if in_db_b and not in_struct_union:
            anomalies.append("db_b_missing_in_structural_union")

        rows.append(
            {
                "canonical_id": slug,
                "display_name": display or slug,
                "origin_tags": ";".join(sorted(set(origin_tags))) or None,
                "in_clinical_39": in_clinical_39,
                "in_master_table_40": in_master_40,
                "in_anarci_38": in_anarci,
                "in_vhh42_cmc": in_vhh42_cmc,
                "in_vhh42_germline": in_vhh42_germline,
                "in_database_b_29": in_db_b,
                "in_structural_union_69": in_struct_union,
                "canonical_sequence_hash": canonical_seq_hash,
                "sequence_consistent_across_sources": seq_consistent,
                "anomalies": ";".join(anomalies) or None,
                "vhh42_cmc_origin": cmc_origin,
                "germline_top_match": sources["vhh42_germline"].get(slug, {}).get(
                    "top_human_germline"
                ),
                "ada_majority_risk": sources["vhh42_germline"].get(slug, {}).get(
                    "ada_majority_risk"
                ),
                "structural_pdb_model": sources["structural_union_69"]
                .get(slug, {})
                .get("pdb_model"),
                "cohort_platform_tag": platform_tags.get(slug, ""),
            }
        )

    summary = {
        "n_total_unique_ids": len(rows),
        "counts": {sname: len(s) for sname, s in sources.items()},
        "expected": {
            "clinical_39": 39,
            "master_table_40": 40,
            "anarci_38": 39,
            "vhh42_cmc": 42,
            "vhh42_germline": 42,
            "database_b_29": 29,
            "structural_union_69": 69,
        },
        "in_clinical_39": sum(1 for r in rows if r["in_clinical_39"]),
        "in_master_table_40": sum(1 for r in rows if r["in_master_table_40"]),
        "in_anarci_38": sum(1 for r in rows if r["in_anarci_38"]),
        "in_vhh42_cmc": sum(1 for r in rows if r["in_vhh42_cmc"]),
        "in_database_b_29": sum(1 for r in rows if r["in_database_b_29"]),
        "in_structural_union_69": sum(1 for r in rows if r["in_structural_union_69"]),
        "rows_with_anomalies": sum(1 for r in rows if r["anomalies"]),
    }

    return rows, summary


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


CSV_COLUMNS = [
    "canonical_id",
    "display_name",
    "origin_tags",
    "in_clinical_39",
    "in_master_table_40",
    "in_anarci_38",
    "in_vhh42_cmc",
    "in_vhh42_germline",
    "in_database_b_29",
    "in_structural_union_69",
    "canonical_sequence_hash",
    "sequence_consistent_across_sources",
    "anomalies",
    "vhh42_cmc_origin",
    "germline_top_match",
    "ada_majority_risk",
    "structural_pdb_model",
    "cohort_platform_tag",
]


def write_outputs(rows: list[dict], summary: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = OUT_DIR / "VHH_ID_RECONCILIATION.csv"
    json_path = OUT_DIR / "VHH_ID_RECONCILIATION.json"
    summary_path = OUT_DIR / "VHH_ID_RECONCILIATION_SUMMARY.json"

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k) for k in CSV_COLUMNS})

    with json_path.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "_meta": {
                    "purpose": "VHH ID reconciliation across clinical, ANARCI, VHH42, Database B, and structural union datasets",
                    "generator": "scripts/reconciliation/build_vhh_id_reconciliation.py",
                    "read_only_governance_artifact": True,
                    "n_rows": len(rows),
                },
                "rows": rows,
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )

    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)


def main() -> None:
    rows, summary = build_reconciliation()
    write_outputs(rows, summary)
    print("[reconciliation] rows:", len(rows))
    for k, v in summary["counts"].items():
        expected = summary["expected"].get(k)
        marker = "" if expected is None or v == expected else f"  (expected {expected})"
        print(f"[reconciliation]   {k}: {v}{marker}")
    print("[reconciliation] anomalies:", summary["rows_with_anomalies"])
    print("[reconciliation] outputs in:", OUT_DIR)


if __name__ == "__main__":
    main()
