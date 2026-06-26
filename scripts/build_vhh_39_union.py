#!/usr/bin/env python3
"""
Build the union of 39 clinical VHH: paper Table1 (19) + current 38 with ANARCII.
Output: sequence + formatted clinical info (Target, Phase, CDR3 length, etc.).

Clinical info sources (priority):
  1) Paper Table1 (19 entries, most detailed).
  2) vhh_clinical_data: FASTA header ">Name|Target|Phase|Year" and/or complete_v2.json per-record fields.

Usage:
  python scripts/build_vhh_39_union.py --out-dir data/vhh_clinical_39_union
  python scripts/build_vhh_39_union.py --source-dir "C:\\Users\\NextVivo\\.openclaw\\workspace\\vhh_clinical_data" --out-dir data/vhh_clinical_39_union

Uses source_path from data/design_rules/vhh_clinical_40_reference.json when --source-dir omitted.
"""
import argparse
import csv
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_JSON = PROJECT_ROOT / "data" / "design_rules" / "vhh_clinical_40_reference.json"
ANARCI_RESULTS = PROJECT_ROOT / "data" / "vhh_clinical_40_anarci" / "anarci_results.json"
TABLE1_CSV = PROJECT_ROOT / "paper" / "Submission_Package" / "data and figure" / "Tables" / "Table1_Clinical_Landscape.csv"


def load_38_ids():
    """38 VHH IDs from anarci_results.json."""
    with open(ANARCI_RESULTS, encoding="utf-8") as f:
        data = json.load(f)
    return [r["id"] for r in data["results"]]


def load_sequences_from_40_json(json_path: Path):
    """name -> sequence from vhh_clinical_antibodies_complete_v2.json."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    for rec in data:
        name = rec.get("therapeutic_name", "").strip()
        if not name:
            continue
        seqs = rec.get("sequences") or {}
        seq = (seqs.get("heavy") or {}).get("sequence") or (seqs.get("heavy_bispec") or {}).get("sequence")
        if seq and isinstance(seq, str):
            seq = seq.replace(" ", "").strip()
        if seq and len(seq) >= 90:
            out[name] = seq
    return out


def load_clinical_from_40_json(json_path: Path):
    """name -> {Target, Clinical_Phase, Year, ...} from vhh_clinical_antibodies_complete_v2.json (any top-level clinical-like keys)."""
    if not json_path or not json_path.exists():
        return {}
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    key_map = {"target": "Target", "phase": "Clinical_Phase", "clinical_phase": "Clinical_Phase", "year": "Year"}
    for rec in data:
        name = rec.get("therapeutic_name", "").strip()
        if not name:
            continue
        row = {}
        for k, v in rec.items():
            if k in ("sequences", "therapeutic_name"):
                continue
            if isinstance(v, (str, int, float)) and v not in (None, ""):
                row[k] = str(v).strip()
        # Normalize to our column names
        if "target" in row and "Target" not in row:
            row["Target"] = row["target"]
        if "phase" in row and "Clinical_Phase" not in row:
            row["Clinical_Phase"] = row["phase"]
        elif "clinical_phase" in row and "Clinical_Phase" not in row:
            row["Clinical_Phase"] = row["clinical_phase"]
        if row:
            out[name] = row
    return out


def load_clinical_from_fasta(fasta_path: Path):
    """name -> {Target, Clinical_Phase, Year} from FASTA headers: >Name|Target|Phase|Year."""
    if not fasta_path or not fasta_path.exists():
        return {}
    out = {}
    with open(fasta_path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            if not line.startswith(">"):
                continue
            parts = line[1:].split("|")
            name = (parts[0] or "").strip()
            if not name:
                continue
            # Target, Phase, Year
            target = (parts[1] or "").strip() if len(parts) > 1 else ""
            phase = (parts[2] or "").strip() if len(parts) > 2 else ""
            year = (parts[3] or "").strip() if len(parts) > 3 else ""
            out[name] = {"Target": target, "Clinical_Phase": phase, "Year": year}
    return out


def load_table1_clinical():
    """Paper Table1: name -> dict with Target, Clinical_Phase, CDR3_Length_aa, CDR2_Fold, Classification, Human_Identity."""
    if not TABLE1_CSV.exists():
        return {}
    with open(TABLE1_CSV, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return {
        (r["Antibody Name"].strip()): {
            "Target": r.get("Target", "").strip(),
            "Clinical_Phase": r.get("Clinical Phase", "").strip(),
            "CDR3_Length_aa": r.get("CDR3 Length (aa)", "").strip(),
            "CDR2_Fold": r.get("CDR2 Fold", "").strip(),
            "Classification": r.get("Classification", "").strip(),
            "Human_Identity_pct": r.get("Human Identity (%)", "").strip(),
        }
        for r in rows
        if r.get("Antibody Name", "").strip()
    }


def main():
    parser = argparse.ArgumentParser(description="Build 39 VHH union table: sequence + clinical")
    parser.add_argument("--source-dir", type=str, default=None, help="vhh_clinical_data folder (default: from vhh_clinical_40_reference.json)")
    parser.add_argument("--json", type=str, default=None, help="Override: path to vhh_clinical_antibodies_complete_v2.json")
    parser.add_argument("--out-dir", type=str, default="data/vhh_clinical_39_union")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Base path for 40 data (source_path)
    base = None
    ref = {}
    if REFERENCE_JSON.exists():
        with open(REFERENCE_JSON, encoding="utf-8") as f:
            ref = json.load(f)
    if args.source_dir:
        base = Path(args.source_dir)
    elif ref:
        base = Path(ref["meta"]["source_path"])
    json_path = Path(args.json) if args.json else None
    fasta_path = None
    if base:
        if not json_path and ref.get("files"):
            json_path = base / ref["files"].get("json_complete", "vhh_clinical_antibodies_complete_v2.json")
        fasta_path = base / ref["files"].get("fasta", "vhh_sequences_v2.fasta") if ref.get("files") else base / "vhh_sequences_v2.fasta"

    # 39 names: 38 from anarci + Ozekibart (only in paper)
    ids_38 = load_38_ids()
    paper_only = ["Ozekibart"]
    all_39 = sorted(set(ids_38) | set(paper_only))

    # Sequences: from 40 JSON if available
    seq_map = {}
    if json_path and json_path.exists():
        seq_map = load_sequences_from_40_json(json_path)
    else:
        print(f"Note: 40 JSON not found. Sequences will be empty. Tried: {json_path}")

    # Clinical: Table1 (19, highest priority) + vhh_clinical_data (JSON then FASTA)
    table1 = load_table1_clinical()
    clinical_40_json = load_clinical_from_40_json(json_path) if json_path else {}
    clinical_40_fasta = load_clinical_from_fasta(fasta_path) if base else {}
    # Merge: for each name, start from 40 (FASTA then JSON overlay), then Table1 overrides
    clinical = {}
    for name in all_39:
        row = {}
        if name in clinical_40_fasta:
            row.update(clinical_40_fasta[name])
        if name in clinical_40_json:
            for k, v in clinical_40_json[name].items():
                if v:
                    row[k] = v
        if name in table1:
            # Table1 has full columns; override
            row.update(table1[name])
        clinical[name] = row

    # Build rows: Name, Sequence, Target, Clinical_Phase, CDR3_Length_aa, CDR2_Fold, Classification, Human_Identity_pct, In_Paper_Table1
    rows = []
    for name in all_39:
        seq = seq_map.get(name, "")
        clin = clinical.get(name, {})
        in_paper = "Y" if name in table1 else "N"
        rows.append({
            "Name": name,
            "Sequence": seq,
            "Target": clin.get("Target", ""),
            "Clinical_Phase": clin.get("Clinical_Phase", ""),
            "CDR3_Length_aa": clin.get("CDR3_Length_aa", ""),
            "CDR2_Fold": clin.get("CDR2_Fold", ""),
            "Classification": clin.get("Classification", ""),
            "Human_Identity_pct": clin.get("Human_Identity_pct", ""),
            "In_Paper_Table1": in_paper,
        })

    # CSV
    csv_path = out_dir / "vhh_39_sequences_clinical.csv"
    fieldnames = ["Name", "Sequence", "Target", "Clinical_Phase", "CDR3_Length_aa", "CDR2_Fold", "Classification", "Human_Identity_pct", "In_Paper_Table1"]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {csv_path}")

    # JSON (same content, for programmatic use)
    json_path_out = out_dir / "vhh_39_sequences_clinical.json"
    with open(json_path_out, "w", encoding="utf-8") as f:
        json.dump({"count": len(rows), "vhh": rows}, f, ensure_ascii=False, indent=2)
    print(f"Wrote {json_path_out}")

    n_with_seq = sum(1 for r in rows if r["Sequence"])
    n_with_target = sum(1 for r in rows if r["Target"])
    n_table1 = sum(1 for r in rows if r["In_Paper_Table1"] == "Y")
    print(f"39 VHH: {n_with_seq} with sequence, {n_with_target} with Target/Phase (Table1: {n_table1}, vhh_clinical_data: FASTA/JSON merged).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
