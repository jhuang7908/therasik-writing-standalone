#!/usr/bin/env python3
"""
Extract / merge mBER (Manifold Bio) VHH framework sequences for comparison with our clinical VHH set.

Usage:
  # Print default mBER framework and our slice_3 VHH count
  python scripts/fetch_mber_vhh_frameworks.py

  # Merge frameworks from a Table S1 export (CSV/TSV with header; one column = sequence or 'masked_sequence')
  python scripts/fetch_mber_vhh_frameworks.py --table-s1 path/to/table_s1.csv

  # Export default framework as FASTA
  python scripts/fetch_mber_vhh_frameworks.py --fasta-out data/design_rules/mber_vhh_default.fasta
"""
import argparse
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MBER_JSON = PROJECT_ROOT / "data" / "design_rules" / "mber_vhh_frameworks.json"
REFERENCE_SLICES = PROJECT_ROOT / "data" / "thera_sabdab" / "out" / "reference_slices.json"


def load_mber_frameworks():
    if not MBER_JSON.exists():
        return {"frameworks": [], "meta": {}}
    with open(MBER_JSON, encoding="utf-8") as f:
        return json.load(f)


def load_slice3_vhh_ids():
    if not REFERENCE_SLICES.exists():
        return []
    with open(REFERENCE_SLICES, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("slice_3_vhh_design", {}).get("antibody_ids", [])


def parse_table_s1(path: str):
    """Parse CSV/TSV exported from Table S1. Expects header; looks for column 'sequence' or 'masked_sequence' or first column."""
    rows = []
    path = Path(path)
    if not path.exists():
        return rows
    sep = "\t" if path.suffix.lower() == ".tsv" else ","
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    if not lines:
        return rows
    header = [h.strip().strip('"') for h in lines[0].strip().split(sep)]
    key = None
    for k in ("masked_sequence", "sequence", "Sequence", "Framework"):
        if k in header:
            key = k
            break
    if key is None and header:
        key = header[0]
    for line in lines[1:]:
        parts = [p.strip().strip('"') for p in line.strip().split(sep)]
        if len(parts) >= len(header) and key:
            idx = header.index(key)
            seq = parts[idx] if idx < len(parts) else ""
            if seq and len(seq) > 50:
                rows.append({"sequence": seq, "source": path.name})
    return rows


def main():
    parser = argparse.ArgumentParser(description="Fetch/merge mBER VHH frameworks and compare with slice_3 VHH set")
    parser.add_argument("--table-s1", type=str, help="Path to Table S1 export (CSV/TSV)")
    parser.add_argument("--fasta-out", type=str, help="Write default framework(s) to FASTA")
    parser.add_argument("--write-json", type=str, help="Write merged frameworks to JSON (optional)")
    args = parser.parse_args()

    data = load_mber_frameworks()
    frameworks = data.get("frameworks", [])

    if args.table_s1:
        extra = parse_table_s1(args.table_s1)
        for i, row in enumerate(extra):
            frameworks.append({
                "id": f"table_s1_row_{i+1}",
                "sequence": row["sequence"],
                "source": row.get("source", args.table_s1),
            })
        print(f"Parsed {len(extra)} sequence(s) from {args.table_s1}")

    slice3_ids = load_slice3_vhh_ids()
    print(f"mBER frameworks in {MBER_JSON.name}: {len(frameworks)}")
    for fw in frameworks:
        seq = fw.get("masked_sequence") or fw.get("sequence", "")
        print(f"  - {fw.get('id', '?')}: len={len(seq)}")
    print(f"Our slice_3_vhh_design (clinical VHH reference): {len(slice3_ids)} antibodies")
    if slice3_ids:
        print(f"  IDs: {', '.join(slice3_ids[:8])}{'...' if len(slice3_ids) > 8 else ''}")

    if args.fasta_out:
        out = Path(args.fasta_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            for fw in frameworks:
                seq = (fw.get("masked_sequence") or fw.get("sequence", "")).replace("*", "X")
                if not seq:
                    continue
                fid = fw.get("id", "mber_framework")
                f.write(f">{fid}\n{seq}\n")
        print(f"Wrote {len(frameworks)} sequence(s) to {out}")

    if args.write_json:
        data["frameworks"] = frameworks
        with open(args.write_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Wrote merged JSON to {args.write_json}")


if __name__ == "__main__":
    main()
