"""
recompute_surface_hydrophilicity.py
====================================
Re-compute surface hydrophilicity for all 70 therapeutic antibodies,
filling the NaN n_hydrophilic_patches and updating the summary CSV.

For each antibody:
  1. Try freesasa (if PDB exists with chain H+L) → accurate SASA
  2. Always also compute Parker scale → consistent sequence-level metric
  3. Report both; primary = freesasa (when available), secondary = Parker

Updates:
  data/thera_sabdab/out/mhcii_immuno_70_summary.csv
  data/thera_sabdab/out/immuno70_full_matrix.csv
  data/thera_sabdab/out/immuno70_surface_detail.csv   (new, per-patch detail)
"""
from __future__ import annotations
import sys, time
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT      = ROOT / "data" / "thera_sabdab" / "out"
PDB_ROOT_NATURAL    = ROOT / "data" / "structures" / "natural"
PDB_ROOT_ENGINEERED = ROOT / "data" / "structures" / "engineered"

from core.immunogenicity.surface_immuno import (
    SurfaceImmunogenicity,
    _freesasa_per_residue_by_chain,
    _sasa_patches, _parker_patches,
    _chain_result_parker,
    SASA_THRESHOLD, MIN_PATCH_LEN,
)

# ── Load data ─────────────────────────────────────────────────────────────────
seq_df = pd.read_csv(OUT / "confirmed70_sequences_full.csv")
hla_df = pd.read_csv(OUT / "mhcii_immuno_70_summary.csv")

rows = []
detail_rows = []
total = len(seq_df)

print(f"Recomputing surface hydrophilicity for {total} antibodies …\n")

for ni, (_, row) in enumerate(seq_df.iterrows(), 1):
    name = str(row["antibody_name"])
    vh   = str(row.get("arm1_heavy_aa", "") or "").strip()
    vl   = str(row.get("arm1_light_aa", "") or "").strip()

    if not vh:
        print(f"[{ni:2d}/{total}] {name:30s}  SKIP (no VH)")
        rows.append({"antibody_name": name,
                     "surf_mode": "skipped", "surf_n_patches_parker": 0,
                     "surf_n_patches_sasa": None, "surf_frac_exposed_vh": None,
                     "surf_frac_exposed_vl": None, "surf_mean_sasa_vh": None,
                     "surf_mean_sasa_vl": None, "surf_pdb_used": False})
        continue

    # ── 1. Parker scale (always) ──────────────────────────────────────────────
    parker_si = SurfaceImmunogenicity(vh_seq=vh, vl_seq=vl)
    parker_r  = parker_si.run()
    n_parker  = parker_r.get("n_hydrophilic_patches", 0)
    vh_parker_patches = (parker_r.get("vh") or {}).get("patches", [])
    vl_parker_patches = (parker_r.get("vl") or {}).get("patches", [])

    # ── 2. Structural SASA (if PDB has H+L chains) ────────────────────────────
    pdb_path = PDB_ROOT_NATURAL / f"{name}.pdb"
    if not pdb_path.exists():
        pdb_path = PDB_ROOT_ENGINEERED / f"{name}.pdb"
        
    sasa_ok  = False
    n_sasa   = None
    frac_vh  = None
    frac_vl  = None
    msasa_vh = None
    msasa_vl = None
    sasa_patches_vh = []
    sasa_patches_vl = []

    if pdb_path.exists():
        sasa_chains = _freesasa_per_residue_by_chain(str(pdb_path))
        if sasa_chains:
            vh_chain = sasa_chains.get("H")
            vl_chain = sasa_chains.get("L")

            if vh_chain:
                seq_h, sasa_h = vh_chain
                sasa_patches_vh = _sasa_patches(seq_h, sasa_h)
                frac_vh  = float((sasa_h > SASA_THRESHOLD).mean())
                msasa_vh = float(sasa_h.mean())

            if vl_chain:
                seq_l, sasa_l = vl_chain
                sasa_patches_vl = _sasa_patches(seq_l, sasa_l)
                frac_vl  = float((sasa_l > SASA_THRESHOLD).mean())
                msasa_vl = float(sasa_l.mean())

            n_sasa   = len(sasa_patches_vh) + len(sasa_patches_vl)
            sasa_ok  = True

    # ── 3. Decide primary mode ────────────────────────────────────────────────
    if sasa_ok:
        surf_mode = "freesasa"
        n_primary = n_sasa
    else:
        surf_mode = "parker_scale"
        n_primary = n_parker

    # ── 4. Surface risk (primary count) ───────────────────────────────────────
    surf_risk = "HIGH" if n_primary >= 3 else ("MEDIUM" if n_primary >= 1 else "LOW")

    rows.append({
        "antibody_name":          name,
        "surf_mode":              surf_mode,
        "surf_n_patches_parker":  n_parker,
        "surf_n_patches_sasa":    n_sasa,
        "surf_n_patches_primary": n_primary,
        "surf_risk":              surf_risk,
        "surf_frac_exposed_vh":   frac_vh,
        "surf_frac_exposed_vl":   frac_vl,
        "surf_mean_sasa_vh":      msasa_vh,
        "surf_mean_sasa_vl":      msasa_vl,
        "surf_pdb_used":          sasa_ok,
    })

    # ── 5. Patch detail rows ──────────────────────────────────────────────────
    for p in vh_parker_patches:
        detail_rows.append({"antibody_name": name, "chain": "VH", "method": "parker",
                            "start": p["start"], "end": p["end"],
                            "seq": p["seq"], "score": p.get("mean_parker", 0)})
    for p in vl_parker_patches:
        detail_rows.append({"antibody_name": name, "chain": "VL", "method": "parker",
                            "start": p["start"], "end": p["end"],
                            "seq": p["seq"], "score": p.get("mean_parker", 0)})
    for p in sasa_patches_vh:
        detail_rows.append({"antibody_name": name, "chain": "VH", "method": "freesasa",
                            "start": p["start"], "end": p["end"],
                            "seq": p["seq"], "score": p.get("mean_sasa", 0)})
    for p in sasa_patches_vl:
        detail_rows.append({"antibody_name": name, "chain": "VL", "method": "freesasa",
                            "start": p["start"], "end": p["end"],
                            "seq": p["seq"], "score": p.get("mean_sasa", 0)})

    pdb_icon = "✓PDB" if sasa_ok else "seq"
    print(f"[{ni:2d}/{total}] {name:30s}  "
          f"Parker={n_parker:2d}  SASA={str(n_sasa) if n_sasa is not None else '—':>4s}  "
          f"frac_vh={f'{frac_vh:.3f}' if frac_vh else '—':>6s}  "
          f"mode={pdb_icon}")

surf_df     = pd.DataFrame(rows)
detail_df   = pd.DataFrame(detail_rows)

# ── 6. Update mhcii_immuno_70_summary.csv ─────────────────────────────────────
print("\n[Updating summary CSV …]")
surf_merge = surf_df.rename(columns={"antibody_name": "antibody"})

# Drop old surface columns that had NaN issues
old_cols = ["n_hydrophilic_patches","frac_exposed_vh","frac_exposed_vl",
            "mean_sasa_vh","mean_sasa_vl","surface_mode","pdb_used","surface_risk"]
hla_clean = hla_df.drop(columns=[c for c in old_cols if c in hla_df.columns])
hla_new = hla_clean.merge(
    surf_merge[["antibody","surf_mode","surf_n_patches_parker","surf_n_patches_sasa",
                "surf_n_patches_primary","surf_risk","surf_frac_exposed_vh",
                "surf_frac_exposed_vl","surf_mean_sasa_vh","surf_mean_sasa_vl",
                "surf_pdb_used"]].rename(columns={
        "surf_mode":              "surface_mode",
        "surf_n_patches_primary": "n_hydrophilic_patches",
        "surf_risk":              "surface_risk",
        "surf_frac_exposed_vh":   "frac_exposed_vh",
        "surf_frac_exposed_vl":   "frac_exposed_vl",
        "surf_mean_sasa_vh":      "mean_sasa_vh",
        "surf_mean_sasa_vl":      "mean_sasa_vl",
        "surf_pdb_used":          "pdb_used",
    }),
    on="antibody", how="left"
)
hla_new.to_csv(OUT / "mhcii_immuno_70_summary.csv", index=False)

# ── 7. Update immuno70_full_matrix.csv ────────────────────────────────────────
mat_df = pd.read_csv(OUT / "immuno70_full_matrix.csv")
mat_drop_cols = [c for c in mat_df.columns if c in
    ["n_hydrophilic_patches","frac_exposed_vh","frac_exposed_vl",
     "mean_sasa_vh","mean_sasa_vl","surface_mode","pdb_used"]]
mat_df.drop(columns=mat_drop_cols, inplace=True)
mat_df = mat_df.merge(surf_df, on="antibody_name", how="left")
mat_df.to_csv(OUT / "immuno70_full_matrix.csv", index=False)

# ── 8. Save detail ────────────────────────────────────────────────────────────
detail_df.to_csv(OUT / "immuno70_surface_detail.csv", index=False)

# ── 9. Print summary stats ────────────────────────────────────────────────────
print("\n=== Summary ===")
print(f"  PDB/freesasa used:  {surf_df['surf_pdb_used'].sum()} / {len(surf_df)}")
print(f"  Parker scale only:  {(~surf_df['surf_pdb_used']).sum()} / {len(surf_df)}")
print()
print("  n_patches (primary) distribution:")
print(f"    Parker mean: {surf_df['surf_n_patches_parker'].mean():.2f}")
pdb_sub = surf_df[surf_df["surf_pdb_used"]]
if len(pdb_sub):
    print(f"    SASA mean (PDB antibodies): {pdb_sub['surf_n_patches_sasa'].mean():.2f}")
print()
print("  Surface risk distribution:")
print(surf_df["surf_risk"].value_counts().to_string())
print()
print("Saved:")
print(f"  {OUT / 'mhcii_immuno_70_summary.csv'}")
print(f"  {OUT / 'immuno70_full_matrix.csv'}")
print(f"  {OUT / 'immuno70_surface_detail.csv'}")
print("\n[Done]")
