#!/usr/bin/env python3
"""
Verify atlas PDB paths in confirmed70_structure_atlas_supplement.csv exist under the suite root.

Exit 0 if all 70 files exist; exit 1 otherwise. Prints missing rows.

Optional: --model-missing runs scripts/predict_one_immunebuilder.py for standard VH+VL drugs only
(arm1 from Thera via confirmed70_sequences_full.csv). Skips VHH-only / bispecific-only layouts
where a single H+L pair is not defined — document those in the report.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
SUPP = SUITE / "data/thera_sabdab/out/confirmed70_structure_atlas_supplement.csv"
SEQ_FULL = SUITE / "data/thera_sabdab/out/confirmed70_sequences_full.csv"
PRED_SCRIPT = SUITE / "scripts/predict_one_immunebuilder.py"
OUT_DIR_DEFAULT = SUITE / "data/thera_sabdab/out/immunebuilder_gapfill"


def load_seq_arm1() -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    if not SEQ_FULL.is_file():
        return out
    with SEQ_FULL.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            name = (row.get("antibody_name") or "").strip()
            h = (row.get("arm1_heavy_aa") or "").strip()
            l_ = (row.get("arm1_light_aa") or "").strip()
            if name and h and l_:
                out[name] = (h, l_)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--model-missing",
        action="store_true",
        help="Attempt ABodyBuilder2 for missing paths (VH+VL arm1 only; needs ImmuneBuilder env)",
    )
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR_DEFAULT, help="Output dir for gap-fill PDBs")
    args = ap.parse_args()

    missing: list[tuple[str, str]] = []
    with SUPP.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            name = row["antibody_name"]
            rel = row["atlas_structure_relpath"]
            p = SUITE / rel
            if not p.is_file():
                missing.append((name, rel))

    if not missing:
        print("confirmed70_structure_atlas_supplement: all 70 PDB paths exist.")
        return 0

    print(f"Missing {len(missing)} / 70:")
    for name, rel in missing:
        print(f"  {name}: {rel}")

    if not args.model_missing:
        return 1

    seqs = load_seq_arm1()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    python_exe = __import__("os").environ.get("IMMUNEBUILDER_PYTHON") or sys.executable
    skipped: list[str] = []
    for name, _rel in missing:
        pair = seqs.get(name)
        if not pair:
            skipped.append(f"{name} (no arm1 H+L in confirmed70_sequences_full.csv)")
            continue
        h, l_ = pair
        if len(h) < 30 or len(l_) < 30:
            skipped.append(f"{name} (arm1 sequences too short for ABodyBuilder2)")
            continue
        out_pdb = args.out_dir / f"{name.replace(' ', '_')}_arm1_gapfill.pdb"
        payload = {"out_path": str(out_pdb.resolve()), "H": h, "L": l_}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(payload, tf, ensure_ascii=False)
            tf_path = tf.name
        try:
            r = subprocess.run(
                [python_exe, str(PRED_SCRIPT), "--json", tf_path],
                cwd=str(SUITE),
                capture_output=True,
                text=True,
                timeout=600,
            )
        finally:
            Path(tf_path).unlink(missing_ok=True)
        if r.returncode != 0 or not out_pdb.is_file():
            err = (r.stderr or r.stdout or "").strip()[:400]
            skipped.append(f"{name} (predict failed: {err})")
        else:
            print(f"  modeled → {out_pdb}")

    if skipped:
        print("\nNot auto-modeled:")
        for s in skipped:
            print(f"  - {s}")
    print(
        "\nNote: supplement CSV paths were not rewritten; gap-fill PDBs are auxiliary.",
        file=sys.stderr,
    )

    return 1


if __name__ == "__main__":
    sys.exit(main())
