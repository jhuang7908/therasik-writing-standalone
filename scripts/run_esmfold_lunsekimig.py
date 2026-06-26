#!/usr/bin/env python3
"""
Run ESMFold on Lunsekimig (VHH/nanobody) and write PDBs into the same directory
as the 84 scFv ESMFold predictions, so Lunsekimig models sit alongside other scFv.

Lunsekimig (SAR443765) is anti-TSLP/IL-13 NANOBODY® (VH-only, no light chain).
Input: CSV with columns antibody_id, sequence (e.g. Lunsekimig1, Lunsekimig2).

Usage:
  # 1. Fill sequences in data/design_rules/lunsekimig_esmfold_sequences.csv (from Thera-SAbDab or literature)
  # 2. Run:
  python scripts/run_esmfold_lunsekimig.py
  python scripts/run_esmfold_lunsekimig.py --csv path/to.csv --out-dir data/design_rules/multispecific_linker_pipeline/esmfold_predictions --method api
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = PROJECT_ROOT / "data" / "design_rules" / "lunsekimig_esmfold_sequences.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "design_rules" / "multispecific_linker_pipeline" / "esmfold_predictions"


def load_lunsekimig_csv(csv_path: Path):
    """Return list of (antibody_id, sequence) for rows that have non-empty sequence (len>=50)."""
    out = []
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            aid = (row.get("antibody_id") or "").strip()
            seq = (row.get("sequence") or row.get("heavy_sequence") or "").strip().replace(" ", "").replace("\n", "")
            if aid and seq and len(seq) >= 50:
                out.append((aid, seq))
    return out


def main():
    parser = argparse.ArgumentParser(description="ESMFold for Lunsekimig (VHH), output with 84 scFv PDBs")
    parser.add_argument("--csv", type=str, default=str(DEFAULT_CSV), help="CSV with antibody_id, sequence")
    parser.add_argument("--out-dir", type=str, default=str(DEFAULT_OUT_DIR), help="Output PDB directory (default: multispecific esmfold_predictions)")
    parser.add_argument("--method", choices=["api", "local"], default="api", help="ESMFold method")
    parser.add_argument("--dry-run", action="store_true", help="Only write FASTA, do not run ESMFold")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        print("Create it with columns: antibody_id, sequence", file=sys.stderr)
        print("Fill sequences for Lunsekimig1, Lunsekimig2 from Thera-SAbDab export or literature.", file=sys.stderr)
        sys.exit(1)

    records = load_lunsekimig_csv(csv_path)
    if not records:
        print("No rows with non-empty sequence (len>=50). Fill sequence column in CSV.", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fasta_path = csv_path.parent / "esmfold_input_lunsekimig.fasta"
    with open(fasta_path, "w", encoding="utf-8") as f:
        for aid, seq in records:
            f.write(f">{aid}\n{seq}\n")
    print(f"Wrote {len(records)} sequences to {fasta_path}")

    if args.dry_run:
        print("Dry-run: not calling ESMFold.")
        return 0

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "run_esmfold_batch_from_fasta.py"),
        "--fasta", str(fasta_path),
        "--out-dir", str(out_dir),
        "--method", args.method,
    ]
    sys.exit(subprocess.run(cmd, cwd=PROJECT_ROOT).returncode)


if __name__ == "__main__":
    main()
