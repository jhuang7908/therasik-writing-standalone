#!/usr/bin/env python3
"""
384 ： +  + 。

：384  CSV（ab_id / Name, vh_seq / VH, vl_seq / VL）， Thera-SAbDab 。
：
  1. ：data/humanization_assay/384_natural_segmentation.csv（FR/CDR ）
  2. ：data/humanization_assay/384_antibody_germline_assignment.csv（ 842 ）
  3. ：data/structures/natural/*.pdb + data/humanization_assay/384_natural_structure_metrics_summary.json

：
  python scripts/run_384_natural_pipeline.py <384_sequences.csv> [--skip-structure] [--skip-segmentation] [--merge-842]
  python scripts/run_384_natural_pipeline.py data/humanization_assay/384_natural_sequences.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DATA_ASSAY = PROJECT_ROOT / "data" / "humanization_assay"
STRUCTURES_NATURAL = PROJECT_ROOT / "data" / "structures" / "natural"
OUT_GERMLINE_384 = DATA_ASSAY / "384_antibody_germline_assignment.csv"
OUT_SEGMENTATION = DATA_ASSAY / "384_natural_segmentation.csv"
OUT_STRUCTURE_METRICS = DATA_ASSAY / "384_natural_structure_metrics_summary.json"
OUT_842 = DATA_ASSAY / "842_antibody_germline_assignment.csv"

# Kabat FR/CDR boundaries (same as kabat_utils); used for segmentation
VH_FR1, VH_CDR1, VH_FR2, VH_CDR2, VH_FR3, VH_CDR3 = (1, 25), (26, 35), (36, 49), (50, 65), (66, 94), (95, 102)
VL_FR1, VL_CDR1, VL_FR2, VL_CDR2, VL_FR3, VL_CDR3 = (1, 23), (24, 34), (35, 49), (50, 56), (57, 88), (89, 97)




def _norm_row(row: Dict[str, Any]) -> Dict[str, Any]:
    if not row:
        return row
    return {k.lstrip("\ufeff"): v for k, v in row.items()}


def run_germline_assignment(csv_path: Path) -> List[Dict[str, Any]]:
    """Reuse build_842 logic: CSV -> germline assignment rows."""
    from scripts.build_842_antibody_germline_assignment import _load_germline_cache, run_from_csv
    IGHV = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "_cache" / "IGHV_kabat_cache.json"
    IGKV = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "_cache" / "IGKV_kabat_cache.json"
    IGLV = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "_cache" / "IGLV_kabat_cache.json"
    vh_cache = _load_germline_cache(IGHV)
    kv_cache = _load_germline_cache(IGKV)
    lv_cache = _load_germline_cache(IGLV) if IGLV.exists() else {}
    return run_from_csv(csv_path, vh_cache, kv_cache, lv_cache, include_sequences=True)


def run_segmentation(csv_path: Path) -> List[Dict[str, Any]]:
    """ABARCII + Kabat: for each row get FR/CDR segments, write segmentation table."""
    try:
        from core.humanization.kabat_utils import kabat_from_anarcii, cdr_span
    except ImportError:
        from humanization.kabat_utils import kabat_from_anarcii, cdr_span
    try:
        from anarcii import Anarcii
    except ImportError:
        print("[Segmentation] ABARCII not available; skipping segmentation.", flush=True)
        return []

    anarcii = Anarcii()
    rows_out: List[Dict[str, Any]] = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            row = _norm_row(row)
            ab_id = (row.get("ab_id") or row.get("Name") or row.get("INN") or row.get("antibody_id") or "").strip()
            vh = (row.get("vh_seq") or row.get("VH") or row.get("Heavy_V_Sequence") or "").strip().upper()
            vl = (row.get("vl_seq") or row.get("VL") or row.get("Light_V_Sequence") or "").strip().upper()
            vh = "".join(c for c in vh if c in set("ACDEFGHIKLMNPQRSTVWY"))
            vl = "".join(c for c in vl if c in set("ACDEFGHIKLMNPQRSTVWY"))
            if not ab_id or (not vh and not vl):
                continue
            out_row: Dict[str, Any] = {"ab_id": ab_id}
            for chain, seq, fr_cdr_ranges in [
                ("vh", vh, [(VH_FR1, "vh_fr1"), (VH_CDR1, "vh_cdr1"), (VH_FR2, "vh_fr2"), (VH_CDR2, "vh_cdr2"), (VH_FR3, "vh_fr3"), (VH_CDR3, "vh_cdr3")]),
                ("vl", vl, [(VL_FR1, "vl_fr1"), (VL_CDR1, "vl_cdr1"), (VL_FR2, "vl_fr2"), (VL_CDR2, "vl_cdr2"), (VL_FR3, "vl_fr3"), (VL_CDR3, "vl_cdr3")]),
            ]:
                if not seq:
                    for _, col in fr_cdr_ranges:
                        out_row[col] = ""
                    continue
                try:
                    res = anarcii.number([("s", seq)])
                    res = anarcii.to_scheme("kabat")
                    entry = res.get("s", {})
                    num = (entry or {}).get("numbering")
                    if not num:
                        for _, col in fr_cdr_ranges:
                            out_row[col] = ""
                        continue
                    kd = kabat_from_anarcii(num)
                    for (lo, hi), col in fr_cdr_ranges:
                        out_row[col] = cdr_span(kd, lo, hi) if kd else ""
                except Exception as e:
                    for _, col in fr_cdr_ranges:
                        out_row[col] = ""
                    out_row.setdefault("segmentation_errors", []).append(f"{chain}: {e}")
            if "segmentation_errors" in out_row:
                out_row["segmentation_errors"] = "; ".join(out_row["segmentation_errors"])
            rows_out.append(out_row)
            if (idx + 1) % 50 == 0:
                print(f"  Segmentation {idx + 1}...", flush=True)
    return rows_out


def run_structure_predict_and_metrics(
    csv_path: Path,
    out_pdb_dir: Path,
    out_metrics_json: Path,
    predictor_script: Path,
) -> bool:
    """For each row: run ImmuneBuilder -> save PDB; then run structure_metrics --dir."""
    rows: List[Dict[str, Any]] = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = _norm_row(row)
            ab_id = (row.get("ab_id") or row.get("Name") or row.get("antibody_id") or "").strip()
            vh = (row.get("vh_seq") or row.get("VH") or "").strip().upper()
            vl = (row.get("vl_seq") or row.get("VL") or "").strip().upper()
            vh = "".join(c for c in vh if c in set("ACDEFGHIKLMNPQRSTVWY"))
            vl = "".join(c for c in vl if c in set("ACDEFGHIKLMNPQRSTVWY"))
            if ab_id and vh and vl:
                rows.append({"ab_id": ab_id, "vh": vh, "vl": vl})
    if not rows:
        print("[Structure] No rows with vh+vl; skip.", flush=True)
        return False
    out_pdb_dir.mkdir(parents=True, exist_ok=True)
    python_exe = os.environ.get("IMMUNEBUILDER_PYTHON") or sys.executable
    for i, r in enumerate(rows):
        pdb_path = out_pdb_dir / f"{r['ab_id']}.pdb"
        if (i + 1) % 20 == 0 or i == 0:
            print(f"  Predict {i + 1}/{len(rows)}: {r['ab_id']}", flush=True)
        payload = {"out_path": str(pdb_path.resolve()), "H": r["vh"], "L": r["vl"]}
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
                json.dump(payload, tf, ensure_ascii=False)
                tf_path = tf.name
            ret = subprocess.run(
                [python_exe, str(predictor_script), "--json", tf_path],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=600,
            )
            try:
                Path(tf_path).unlink(missing_ok=True)
            except Exception:
                pass
            if ret.returncode != 0 or not pdb_path.exists():
                print(f"  [WARN] {r['ab_id']} prediction failed: {ret.stderr[:200] if ret.stderr else ret.returncode}")
        except Exception as e:
            print(f"  [WARN] {r['ab_id']}: {e}")
    pdbs = list(out_pdb_dir.glob("*.pdb"))
    if not pdbs:
        print("[Structure] No PDBs generated; skip structure_metrics.", flush=True)
        return False
    sm_script = PROJECT_ROOT / "scripts" / "structure_metrics_humanization.py"
    ret = subprocess.run(
        [sys.executable, str(sm_script), "--dir", str(out_pdb_dir), "--out", str(out_metrics_json), "--skip-sasa"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=3600,
    )
    if ret.returncode != 0:
        print(f"[Structure] structure_metrics failed: {ret.stderr[:500]}", flush=True)
        return False
    print(f"  Wrote {out_metrics_json} ({len(pdbs)} entries)", flush=True)
    return True


def merge_384_into_842(germline_384_path: Path) -> None:
    """Append 384 rows to 842_antibody_germline_assignment.csv with origin=natural."""
    if not germline_384_path.exists():
        return
    rows_384: List[Dict[str, Any]] = []
    with open(germline_384_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["origin"] = "natural_384"
            rows_384.append(r)
    if not rows_384:
        return
    fieldnames = list(rows_384[0].keys())
    existing: List[Dict[str, Any]] = []
    if OUT_842.exists():
        with open(OUT_842, newline="", encoding="utf-8") as f:
            existing = list(csv.DictReader(f))
        if existing and "origin" not in existing[0]:
            for r in existing:
                r["origin"] = "engineered_458"
    all_rows = existing + rows_384
    out_fieldnames = list(all_rows[0].keys()) if all_rows else fieldnames
    with open(OUT_842, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)
    print(f"  Merged 384 into {OUT_842} (total {len(all_rows)} rows)", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="384 ： +  + ")
    ap.add_argument("input_csv", type=Path, help="384  CSV: ab_id/Name, vh_seq/VH, vl_seq/VL")
    ap.add_argument("--skip-structure", action="store_true", help=" structure_metrics")
    ap.add_argument("--skip-segmentation", action="store_true", help=" FR/CDR ")
    ap.add_argument("--merge-842", action="store_true", help=" 384  842_antibody_germline_assignment.csv")
    args = ap.parse_args()
    csv_path = args.input_csv.resolve()
    if not csv_path.exists():
        print(f"Input not found: {csv_path}", file=sys.stderr)
        return 1
    DATA_ASSAY.mkdir(parents=True, exist_ok=True)

    # 1) Germline assignment (always: needed for merge and for structure CSV if --skip-segmentation)
    print("[1/4] Germline assignment (384)...", flush=True)
    germline_rows = run_germline_assignment(csv_path)
    if not germline_rows:
        print("  No rows from CSV.", file=sys.stderr)
        return 1
    g_fieldnames = ["ab_id", "vh_germline", "vl_germline", "vh_identity", "vl_identity", "vh_seq", "vl_seq"]
    with open(OUT_GERMLINE_384, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=g_fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(germline_rows)
    print(f"  Wrote {OUT_GERMLINE_384} ({len(germline_rows)} rows)", flush=True)
    if args.merge_842:
        merge_384_into_842(OUT_GERMLINE_384)

    # 2) Segmentation
    if not args.skip_segmentation:
        print("[2/4] Segmentation (FR/CDR)...", flush=True)
        seg_rows = run_segmentation(csv_path)
        if seg_rows:
            seg_fields = ["ab_id", "vh_fr1", "vh_cdr1", "vh_fr2", "vh_cdr2", "vh_fr3", "vh_cdr3",
                          "vl_fr1", "vl_cdr1", "vl_fr2", "vl_cdr2", "vl_fr3", "vl_cdr3", "segmentation_errors"]
            with open(OUT_SEGMENTATION, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=seg_fields, extrasaction="ignore")
                w.writeheader()
                w.writerows(seg_rows)
            print(f"  Wrote {OUT_SEGMENTATION} ({len(seg_rows)} rows)", flush=True)
        else:
            print("  No segmentation output (ABARCII required).", flush=True)
    else:
        print("[2/4] Segmentation skipped.", flush=True)

    # 3) Structure prediction + metrics
    if not args.skip_structure:
        print("[3/4] Structure prediction (ImmuneBuilder)...", flush=True)
        pred_script = PROJECT_ROOT / "scripts" / "predict_one_immunebuilder.py"
        run_structure_predict_and_metrics(csv_path, STRUCTURES_NATURAL, OUT_STRUCTURE_METRICS, pred_script)
        print("[4/4] Structure metrics done.", flush=True)
    else:
        print("[3/4] Structure skipped.", flush=True)
        print("[4/4] Done.", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
