#!/usr/bin/env python3
"""
Predict Fv structures for 75 IgG-like multispecific antibodies using ImmuneBuilder (ABodyBuilder2).
Extracts sequences from thera_export.xlsx (handling both arms).

Usage:
  python scripts/predict_igg_like_75_immunebuilder.py
"""

import os
import sys
import site

# ImmuneBuilder needs the installed anarci package (with anarci.germlines). The repo root
# has anarci.py which shadows it. Prefer the actual site-packages directory (conda returns
# [env_root, env_root/lib/site-packages], so we need the one containing "site-packages").
_sp = [p for p in site.getsitepackages() if "site-packages" in p.lower()]
if _sp:
    _target = os.path.normpath(os.path.abspath(_sp[0]))
    _root = os.path.normpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # Remove repo root and any path that would shadow anarci (so installed anarci.germlines is used)
    sys.path = [p for p in sys.path if os.path.normpath(os.path.abspath(p or ".")) != _root]
    # Force conda/lib/site-packages to the front (ImmuneBuilder needs anarci.germlines from there)
    sys.path.insert(0, _target)
    sys.path.append(_root)

import json
import logging
import subprocess
import pandas as pd
from pathlib import Path

# ImmuneBuilder is loaded only in subprocess (predict_one_immunebuilder.py)

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data/design_rules"
THERA_XLSX = PROJECT_ROOT / "data/thera_sabdab/thera_export.xlsx"
OUT_DIR = DATA_DIR / "igg_like_75_immunebuilder_predictions"
OUT_DIR.mkdir(parents=True, exist_ok=True)
# Use a temp dir under our output to avoid WinError 32 (file in use) with system TEMP
_work_tmp = OUT_DIR / "_tmp"
_work_tmp.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = os.environ["TMP"] = str(_work_tmp)

# Logging (force flush so logs appear when run in background)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)

# Chain IDs: ArmA = H, L (ABodyBuilder2 default); ArmB = P, Q (to avoid clash in merged PDB)
ARM_B_CHAIN_MAP = {"H": "P", "L": "Q"}


def merge_fv_pdbs(arm_a_path: Path, arm_b_path: Path, out_path: Path) -> None:
    """
    Merge ArmA (H+L) and ArmB (H+L) PDBs into one file with 4 chains: H, L, P, Q.
    ArmB chains are relabeled from H,L to P,Q. Atom serials are renumbered contiguously.
    """
    lines_out = []
    atom_serial = 1

    for pdb_path, chain_map in [(arm_a_path, None), (arm_b_path, ARM_B_CHAIN_MAP)]:
        if not pdb_path.exists():
            continue
        for line in pdb_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.startswith(("ATOM  ", "HETATM")):
                continue
            # PDB: chain ID at col 21 (0-based); atom serial 6-11; resseq 22-26
            if len(line) < 26:
                continue
            if chain_map:
                ch = line[21]
                line = line[:21] + chain_map.get(ch, ch) + line[22:]
            # Renumber atom serial (columns 6-11, right-justified)
            line = f"{line[:6]}{atom_serial:5d}{line[11:]}"
            atom_serial += 1
            lines_out.append(line)

    if not lines_out:
        raise FileNotFoundError(f"No ATOM lines from {arm_a_path} / {arm_b_path}")
    header = (
        "REMARK  IgG-like bispecific: ArmA chains H,L + ArmB chains P,Q (one Fv per arm)\n"
        "REMARK  Merged from ImmuneBuilder ABodyBuilder2 ArmA + ArmB predictions\n"
    )
    out_path.write_text(header + "\n".join(lines_out) + "\n", encoding="utf-8")


def main(limit=None):
    print("predict_igg_like_75_immunebuilder: starting.", flush=True)
    # 1. Load target IDs
    json_path = DATA_DIR / "bispecific_125_igg_like.json"
    if not json_path.exists():
        logging.error(f"Target list not found: {json_path}")
        return
        
    with open(json_path, "r") as f:
        target_data = json.load(f)
    target_ids = set(target_data["antibody_ids"])
    logging.info(f"Loaded {len(target_ids)} target IDs.")

    # 2. Load Sequences
    if not THERA_XLSX.exists():
        logging.error(f"Sequence database not found: {THERA_XLSX}")
        return
        
    logging.info("Loading sequence database...")
    df = pd.read_excel(THERA_XLSX)
    
    # Filter for targets
    # Normalize IDs for matching (strip spaces)
    df['Therapeutic_Clean'] = df['Therapeutic'].astype(str).str.strip()
    df_targets = df[df['Therapeutic_Clean'].isin(target_ids)].copy()
    
    print(f"Found {len(df_targets)} matching records.", flush=True)
    logging.info(f"Found {len(df_targets)} matching records in database.")
    if len(df_targets) == 0:
        logging.error("No matching antibodies in thera_export.xlsx. Check Therapeutic column vs bispecific_125_igg_like.json.")
        return
    if limit is not None:
        df_targets = df_targets.head(limit)
        logging.info(f"Limited to first {limit} antibodies.")
    
    # 3. Path to one-shot script (subprocess per prediction to avoid WinError 32 on Windows)
    script_dir = Path(__file__).resolve().parent
    predict_one_script = script_dir / "predict_one_immunebuilder.py"
    
    # 4. Predict (one subprocess per arm to avoid temp file lock)
    success_count = 0
    
    for i, row in df_targets.iterrows():
        aid = row['Therapeutic_Clean']
        logging.info(f"Processing {aid}...")
        
        # Extract sequences
        h1 = row.get('HeavySequence')
        l1 = row.get('LightSequence')
        h2 = row.get('HeavySequence(ifbispec)')
        l2 = row.get('LightSequence(ifbispec)')
        
        # Clean NaNs
        def clean_seq(s):
            return s if pd.notna(s) and isinstance(s, str) and len(s.strip()) > 10 else None
            
        h1 = clean_seq(h1)
        l1 = clean_seq(l1)
        h2 = clean_seq(h2)
        l2 = clean_seq(l2)
        
        # Logic for arms
        arms = []
        
        # Arm A
        if h1 and l1:
            arms.append(("ArmA", h1, l1))
        elif h1:
            # Heavy only? Or maybe common light chain missing?
            # For now, skip if no light chain, ImmuneBuilder needs paired
            logging.warning(f"  {aid}: ArmA missing Light chain, skipping ArmA.")
            
        # Arm B
        if h2 and l2:
            arms.append(("ArmB", h2, l2))
        elif h2 and l1 and not l2:
             # Common light chain scenario?
             # If L2 is missing but H2 exists, and L1 exists, check if 'VD LC' implies common light
             # But safer to assume explicit columns. 
             # Let's try using L1 if L2 is missing but H2 is present?
             # Many bispecifics use common light chain.
             logging.info(f"  {aid}: ArmB has Heavy but no Light. Using L1 (Common LC assumption).")
             arms.append(("ArmB", h2, l1))
        elif h2:
             logging.warning(f"  {aid}: ArmB missing Light chain (and no L1 fallback), skipping ArmB.")

        if not arms:
            logging.warning(f"  {aid}: No valid VH/VL pairs found.")
            continue
            
        for arm_name, vh, vl in arms:
            out_name = f"{aid}_{arm_name}.pdb"
            out_path = OUT_DIR / out_name
            
            if out_path.exists():
                logging.info(f"  {out_name} exists, skipping.")
                success_count += 1
                continue

            # Run each prediction in a subprocess to avoid WinError 32 (file in use) on Windows
            payload_path = _work_tmp / f"payload_{aid}_{arm_name}.json".replace(" ", "_")
            payload_path.parent.mkdir(parents=True, exist_ok=True)
            with open(payload_path, "w", encoding="utf-8") as f:
                json.dump({"out_path": str(out_path), "H": vh, "L": vl}, f, indent=0)
            try:
                proc = subprocess.run(
                    [sys.executable, str(predict_one_script), "--json", str(payload_path)],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                if proc.returncode == 0:
                    logging.info(f"  Generated {out_name}")
                    success_count += 1
                else:
                    print(f"  FAILED {out_name}: {proc.stderr or proc.stdout or proc.returncode}", flush=True)
                    logging.error(f"  Failed to predict {out_name}: %s", proc.stderr or proc.stdout)
            except subprocess.TimeoutExpired:
                print(f"  FAILED {out_name}: timeout (600s)", flush=True)
                logging.error(f"  Timeout predicting {out_name}")
            except Exception as e:
                print(f"  FAILED {out_name}: {e}", flush=True)
                logging.error(f"  Failed to predict {out_name}: {e}")
            finally:
                try:
                    payload_path.unlink(missing_ok=True)
                except OSError:
                    pass

        # Merge both arms into one PDB (IgG-like = one structure with ArmA H,L + ArmB P,Q)
        arm_a_path = OUT_DIR / f"{aid}_ArmA.pdb"
        arm_b_path = OUT_DIR / f"{aid}_ArmB.pdb"
        merged_path = OUT_DIR / f"{aid}.pdb"
        if arm_a_path.exists() and arm_b_path.exists():
            try:
                merge_fv_pdbs(arm_a_path, arm_b_path, merged_path)
                logging.info(f"  Merged -> {aid}.pdb (H,L + P,Q)")
            except Exception as e:
                logging.warning(f"  Merge failed for {aid}: {e}")
        elif arm_a_path.exists():
            import shutil
            shutil.copy2(arm_a_path, merged_path)
            logging.info(f"  Single-arm -> {aid}.pdb (H,L only)")

    print(f"Done. Generated {success_count} new structures in {OUT_DIR}", flush=True)
    logging.info(f"Done. Generated {success_count} new structures in {OUT_DIR}")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="Max number of antibodies to process (default: all)")
    ap.add_argument(
        "--merge-only",
        action="store_true",
        help="Only merge existing ArmA/ArmB PDBs into <aid>.pdb (no prediction)",
    )
    args = ap.parse_args()
    if args.merge_only:
        # Merge existing arms into one PDB per antibody
        merged = 0
        for pdb in sorted(OUT_DIR.glob("*_ArmA.pdb")):
            aid = pdb.stem.replace("_ArmA", "")
            arm_a_path = OUT_DIR / f"{aid}_ArmA.pdb"
            arm_b_path = OUT_DIR / f"{aid}_ArmB.pdb"
            out_path = OUT_DIR / f"{aid}.pdb"
            if arm_a_path.exists() and arm_b_path.exists():
                merge_fv_pdbs(arm_a_path, arm_b_path, out_path)
                merged += 1
                print(f"Merged {aid}.pdb (H,L + P,Q)", flush=True)
            elif arm_a_path.exists():
                import shutil
                shutil.copy2(arm_a_path, out_path)
                merged += 1
                print(f"Single-arm {aid}.pdb (H,L only)", flush=True)
        print(f"Merge-only done: {merged} structures in {OUT_DIR}", flush=True)
    else:
        main(limit=args.limit)
