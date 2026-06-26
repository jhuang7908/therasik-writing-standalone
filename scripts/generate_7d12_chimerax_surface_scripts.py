#!/usr/bin/env python3
"""
Generate ChimeraX scripts to render 7D12 Native+SR surface PNGs
with SR mutation sites highlighted and labeled by IMGT position.
ENHANCED for client reports: blue surface patches + larger markers/labels.

Inputs:
  - output/7D12/7d12_native_af2.pdb
  - output/7D12/7d12_sr_af2.pdb
  - output/7D12/7d12_4krl_per_residue_surface_metrics.csv  (for IMGT->resseq mapping)

Outputs:
  - output/7D12/chimerax_7d12_native_sr_surface.cxc
  - output/7D12/7d12_native_surface_sr_sites.png
  - output/7D12/7d12_sr_surface_sr_sites.png
  - output/7D12/7d12_4krl_surface_sr_sites_viewA.png (CLIENT MAIN FIGURE)
  - output/7D12/7d12_4krl_surface_sr_sites_viewB.png (CLIENT MAIN FIGURE)
"""

from __future__ import annotations

from pathlib import Path
import csv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "output" / "7D12"

NATIVE_PDB = OUT_DIR / "7d12_native_af2.pdb"
SR_PDB = OUT_DIR / "7d12_sr_af2.pdb"

MAP_CSV = OUT_DIR / "7d12_4krl_per_residue_surface_metrics.csv"

OUT_CXC = OUT_DIR / "chimerax_7d12_native_sr_surface.cxc"
OUT_PNG_NATIVE = OUT_DIR / "7d12_native_surface_sr_sites.png"
OUT_PNG_SR = OUT_DIR / "7d12_sr_surface_sr_sites.png"
OUT_PNG_4KRL_VIEWA = OUT_DIR / "7d12_4krl_surface_sr_sites_viewA.png"
OUT_PNG_4KRL_VIEWB = OUT_DIR / "7d12_4krl_surface_sr_sites_viewB.png"

# Predicted PDBs are single-chain; ColabFold typically uses chain A.
PRED_CHAIN_ID = "A"

# Experimental structure (PDB 4KRL) for evidence
PDB_4KRL = OUT_DIR / "4KRL.pdb"
PDB_4KRL_CHAIN_ID = "B"

# SR mutation positions in IMGT numbering (as used in the paper)
SR_IMGT_POS = [12, 40, 42, 83, 96, 101]

# IMGT CDR ranges (paper convention)
CDR_RANGES = [
    ("CDR1", 27, 38),
    ("CDR2", 56, 65),
    ("CDR3", 105, 117),
]


def _load_imgt_to_resseq_map(csv_path: Path) -> dict[int, int]:
    """
    Map IMGT position -> PDB residue number (resseq) for 7D12 chain B in 4KRL.

    We use this as a stable IMGT->sequence-index mapping so we can label predicted
    structures (which usually have resseq=1..N).
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing mapping CSV: {csv_path}")

    out: dict[int, int] = {}
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            imgt = row.get("imgt_pos")
            resseq = row.get("resseq")
            if not imgt or imgt == "None":
                continue
            if not resseq or resseq == "None":
                continue
            try:
                imgt_i = int(float(imgt))
                resseq_i = int(float(resseq))
            except ValueError:
                continue
            # Keep the first mapping if duplicates appear (shouldn't for this CSV)
            out.setdefault(imgt_i, resseq_i)
    return out


def _resseq_list_for_imgt_range(imgt_to_resseq: dict[int, int], start: int, end: int) -> list[int]:
    return [imgt_to_resseq[p] for p in range(start, end + 1) if p in imgt_to_resseq]


def _fmt_res_list(nums: list[int]) -> str:
    # ChimeraX residue spec: :1,2,3
    return ",".join(str(n) for n in sorted(set(nums)))


def main() -> None:
    if not NATIVE_PDB.exists():
        raise FileNotFoundError(f"Missing Native PDB: {NATIVE_PDB}")
    if not SR_PDB.exists():
        raise FileNotFoundError(f"Missing SR PDB: {SR_PDB}")
    if not PDB_4KRL.exists():
        raise FileNotFoundError(f"Missing experimental PDB: {PDB_4KRL}")

    imgt_to_resseq = _load_imgt_to_resseq_map(MAP_CSV)

    # Mutation site residue numbers (for selection in ChimeraX)
    mut_resseq = []
    missing = []
    for p in SR_IMGT_POS:
        if p not in imgt_to_resseq:
            missing.append(p)
        else:
            mut_resseq.append(imgt_to_resseq[p])
    if missing:
        raise RuntimeError(f"Missing IMGT->resseq mapping for positions: {missing}")

    # CDR residue numbers (for coloring; optional but helpful)
    cdr_resseq: list[int] = []
    for _, a, b in CDR_RANGES:
        cdr_resseq.extend(_resseq_list_for_imgt_range(imgt_to_resseq, a, b))

    mut_sel = _fmt_res_list(mut_resseq)
    cdr_sel = _fmt_res_list(cdr_resseq)
    mut_ca_sel = f"{mut_sel}@CA"

    # CLIENT-FRIENDLY STYLE: blue surface patches + large markers/labels
    lines: list[str] = []
    lines += [
        "set bgColor white",
        "graphics silhouettes true",
        "lighting soft",
        "",
        "# --- Model 1: Native (AF2/ColabFold) ---",
        f"open \"{NATIVE_PDB.as_posix()}\"",
        "hide",
        "surface",
        "transparency 40 target s",
        "color gray",
    ]
    if cdr_sel:
        lines += [f"color #1/{PRED_CHAIN_ID}:{cdr_sel} green"]
    lines += [
        # COLOR MUTATION SITES AS BLUE SURFACE PATCHES (most visible)
        f"color #1/{PRED_CHAIN_ID}:{mut_sel} dodgerblue target s",
        # Also show large spheres at CA for emphasis
        f"color #1/{PRED_CHAIN_ID}:{mut_ca_sel} dodgerblue",
        f"show #1/{PRED_CHAIN_ID}:{mut_ca_sel}",
        f"style #1/{PRED_CHAIN_ID}:{mut_ca_sel} sphere",
        f"size #1/{PRED_CHAIN_ID}:{mut_ca_sel} atomRadius 2.5",
        "",
        "# Label SR sites with IMGT position numbers",
    ]
    for imgt in SR_IMGT_POS:
        resseq = imgt_to_resseq[imgt]
        lines += [f"label #1/{PRED_CHAIN_ID}:{resseq}@CA text \"{imgt}\""]
    lines += [
        f"label #1/{PRED_CHAIN_ID}:{mut_ca_sel} color black",
        f"label #1/{PRED_CHAIN_ID}:{mut_ca_sel} height 2.8",
        f"label #1/{PRED_CHAIN_ID}:{mut_ca_sel} bgColor white",
    ]

    lines += [
        "view",
        "turn y 20",
        "turn x -10",
        f"save \"{OUT_PNG_NATIVE.as_posix()}\" supersample 3",
        "",
        "# --- Model 2: SR (AF2/ColabFold) ---",
        "close session",
        f"open \"{SR_PDB.as_posix()}\"",
        "hide",
        "surface",
        "transparency 40 target s",
        "color gray",
    ]
    if cdr_sel:
        lines += [f"color #1/{PRED_CHAIN_ID}:{cdr_sel} green"]
    lines += [
        f"color #1/{PRED_CHAIN_ID}:{mut_sel} dodgerblue target s",
        f"color #1/{PRED_CHAIN_ID}:{mut_ca_sel} dodgerblue",
        f"show #1/{PRED_CHAIN_ID}:{mut_ca_sel}",
        f"style #1/{PRED_CHAIN_ID}:{mut_ca_sel} sphere",
        f"size #1/{PRED_CHAIN_ID}:{mut_ca_sel} atomRadius 2.5",
        "",
        "# Label SR sites with IMGT position numbers",
    ]
    for imgt in SR_IMGT_POS:
        resseq = imgt_to_resseq[imgt]
        lines += [f"label #1/{PRED_CHAIN_ID}:{resseq}@CA text \"{imgt}\""]
    lines += [
        f"label #1/{PRED_CHAIN_ID}:{mut_ca_sel} color black",
        f"label #1/{PRED_CHAIN_ID}:{mut_ca_sel} height 2.8",
        f"label #1/{PRED_CHAIN_ID}:{mut_ca_sel} bgColor white",
    ]
    lines += [
        "view",
        "turn y 20",
        "turn x -10",
        f"save \"{OUT_PNG_SR.as_posix()}\" supersample 3",
        "",
        "# ======================================================================",
        "# CLIENT REPORT MAIN FIGURES: 4KRL experimental structure (chain B)",
        "# ======================================================================",
        "close session",
        f"open \"{PDB_4KRL.as_posix()}\"",
        "# Keep only VHH chain B for clean client figure",
        f"select /{PDB_4KRL_CHAIN_ID}",
        "delete ~sel",
        "hide",
        "surface",
        "# View A: Lower transparency so blue patches are prominent",
        "transparency 35 target s",
        "color gray",
    ]
    if cdr_sel:
        lines += [f"color #1/{PDB_4KRL_CHAIN_ID}:{cdr_sel} green"]
    lines += [
        # KEY: Blue surface patches make mutation sites obvious to clients
        f"color #1/{PDB_4KRL_CHAIN_ID}:{mut_sel} dodgerblue target s",
        # Large spheres for print visibility
        f"color #1/{PDB_4KRL_CHAIN_ID}:{mut_ca_sel} dodgerblue",
        f"show #1/{PDB_4KRL_CHAIN_ID}:{mut_ca_sel}",
        f"style #1/{PDB_4KRL_CHAIN_ID}:{mut_ca_sel} sphere",
        f"size #1/{PDB_4KRL_CHAIN_ID}:{mut_ca_sel} atomRadius 2.5",
        "",
        "# Label SR sites with IMGT position numbers (large for readability)",
    ]
    for imgt in SR_IMGT_POS:
        resseq = imgt_to_resseq[imgt]
        lines += [f"label #1/{PDB_4KRL_CHAIN_ID}:{resseq}@CA text \"{imgt}\""]
    lines += [
        f"label #1/{PDB_4KRL_CHAIN_ID}:{mut_ca_sel} color black",
        f"label #1/{PDB_4KRL_CHAIN_ID}:{mut_ca_sel} height 2.8",
        f"label #1/{PDB_4KRL_CHAIN_ID}:{mut_ca_sel} bgColor white",
    ]
    lines += [
        "view",
        "turn y 20",
        "turn x -10",
        "# View A: emphasize the 4 surface-exposed SR sites",
        f"save \"{OUT_PNG_4KRL_VIEWA.as_posix()}\" supersample 3 width 2400 height 2400",
        "",
        "# View B: rotate and increase transparency to reveal buried sites (40/42)",
        "turn y 140",
        "turn x 10",
        "transparency 75 target s",
        f"save \"{OUT_PNG_4KRL_VIEWB.as_posix()}\" supersample 3 width 2400 height 2400",
        "",
        "exit",
        "",
    ]

    OUT_CXC.write_text("\n".join(lines), encoding="utf-8")

    print("✓ Wrote ChimeraX script:", OUT_CXC)
    print("✓ Will render PNGs to:")
    print("  -", OUT_PNG_NATIVE)
    print("  -", OUT_PNG_SR)
    print("  -", OUT_PNG_4KRL_VIEWA, "(CLIENT MAIN FIGURE)")
    print("  -", OUT_PNG_4KRL_VIEWB, "(CLIENT MAIN FIGURE)")
    print("")
    print("Run in ChimeraX:")
    print(f"  chimerax --script \"{OUT_CXC}\"")


if __name__ == "__main__":
    main()
