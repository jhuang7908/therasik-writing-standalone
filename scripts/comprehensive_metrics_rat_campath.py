#!/usr/bin/env python3
"""
Full humanness + CMC + structure metrics for rat Campath console variants.

Reads:  projects/rat_campath_console_humanization/humanized_sequences.json
Uses:   existing pdbs/*.pdb for RMSD (must exist)
Writes: projects/rat_campath_console_humanization/comprehensive_metrics.json
        projects/rat_campath_console_humanization/METRICS_FULL_TABLE.md

  conda activate anarcii
  python scripts/comprehensive_metrics_rat_campath.py

Requires: abnativ, promb (HPR), ablang2, BioPython
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE))
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import numpy as np
from Bio.PDB import PDBParser, Superimposer
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

PROJ = SUITE / "projects" / "rat_campath_console_humanization"
PDB_DIR = PROJ / "pdbs"


def _sid(a: str, b: str) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    return round(sum(x == y for x, y in zip(a.upper(), b.upper())) / n * 100.0, 2)


def main() -> None:
    data = json.loads((PROJ / "humanized_sequences.json").read_text(encoding="utf-8"))

    rat_vh = data["rat_parent"]["vh"]
    rat_vl = data["rat_parent"]["vl"]

    variants = {
        "Rat_parent": (rat_vh, rat_vl),
        "DEEP-FR": (data["DEEP_FR"]["vh"], data["DEEP_FR"]["vl"]),
        "9AA-CTX": (data["9AA_CTX"]["vh"], data["9AA_CTX"]["vl"]),
        "DeepFR-CTX": (data["DeepFR_CTX"]["vh"], data["DeepFR_CTX"]["vl"]),
        "DeepFR-CTX-CMC": (data["DeepFR_CTX_CMC"]["vh"], data["DeepFR_CTX_CMC"]["vl"]),
        "CDR_graft_Vernier_BM": (
            data["CDR_graft_Vernier_BM"]["vh"],
            data["CDR_graft_Vernier_BM"]["vl"],
        ),
        "Surface_reshape": (data["Surface_reshape"]["vh"], data["Surface_reshape"]["vl"]),
    }

    from abnativ.model.scoring_functions import abnativ_scoring
    from core.cmc.adi_score import compute_adi
    from core.cmc.cmc_metrics import CMCMetricEngine
    from core.humanization.hpr_index import compute_hpr_index

    print("Loading AbLang2 paired (once)…")
    import ablang2  # noqa: PLC0415

    ablang_model = ablang2.pretrained("ablang2-paired")

    # RMSD vs Rat_parent
    pdb_map = {
        "Rat_parent": "Rat_parent.pdb",
        "DEEP-FR": "DEEP-FR.pdb",
        "9AA-CTX": "9AA-CTX.pdb",
        "DeepFR-CTX": "DeepFR-CTX.pdb",
        "DeepFR-CTX-CMC": "DeepFR-CTX-CMC.pdb",
        "CDR_graft_Vernier_BM": "CDR_graft_Vernier_BM.pdb",
        "Surface_reshape": "Surface_reshape.pdb",
    }
    parser = PDBParser(QUIET=True)
    ref_path = PDB_DIR / pdb_map["Rat_parent"]
    rmsd_by: dict[str, float | None] = {}
    if ref_path.is_file():
        ref_struct = parser.get_structure("ref", str(ref_path))
        ref_ca = [a for a in ref_struct.get_atoms() if a.get_name() == "CA"]
        for name, pdb_fn in pdb_map.items():
            p = PDB_DIR / pdb_fn
            if not p.is_file():
                rmsd_by[name] = None
                continue
            if name == "Rat_parent":
                rmsd_by[name] = 0.0
                continue
            tgt = parser.get_structure(name, str(p))
            tgt_ca = [a for a in tgt.get_atoms() if a.get_name() == "CA"]
            n = min(len(ref_ca), len(tgt_ca))
            sup = Superimposer()
            sup.set_atoms(ref_ca[:n], tgt_ca[:n])
            rmsd_by[name] = round(sup.rms, 3)
    else:
        for name in variants:
            rmsd_by[name] = None

    rows: list[dict] = []
    for name, (vh, vl) in variants.items():
        print(f"Scoring {name}…")

        rec_h = [SeqRecord(Seq(vh), id=f"{name}_VH")]
        rec_l = [SeqRecord(Seq(vl), id=f"{name}_VL")]
        try:
            df_h, _ = abnativ_scoring(model_type="VH", seq_records=rec_h, verbose=False)
            df_l, _ = abnativ_scoring(model_type="VKappa", seq_records=rec_l, verbose=False)
            ab_h = round(float(df_h.filter(like="Score").iloc[0, 0]), 4)
            ab_l = round(float(df_l.filter(like="Score").iloc[0, 0]), 4)
        except Exception as exc:  # noqa: BLE001
            ab_h = ab_l = None
            ab_err = str(exc)
        else:
            ab_err = None

        hpr = compute_hpr_index(vh, vl)
        hpr_vh = hpr.get("vh", {}).get("score")
        hpr_vl = hpr.get("vl", {}).get("score")
        hpr_cb = (hpr.get("combined") or {}).get("score")

        try:
            pll = ablang_model([(vh.upper(), vl.upper())], mode="pseudo_log_likelihood")
            ablang = round(float(np.squeeze(pll)), 4)
        except Exception as exc:  # noqa: BLE001
            ablang = None
            ablang_err = str(exc)
        else:
            ablang_err = None

        m = CMCMetricEngine.compute_metrics(vh, vl)
        rm = {
            "pI": m.get("pI"),
            "GRAVY": m.get("GRAVY"),
            "instability_index": m.get("instability_index"),
            "net_charge_pH7": m.get("net_charge_pH7"),
            "hydro_patch_max9": m.get("hydro_patch_max9"),
            "charge_patch_max7": m.get("charge_patch_max7"),
            "SAP_score": m.get("SAP_score"),
            "Fv_charge_asymmetry": m.get("Fv_charge_asymmetry"),
            "agg_motifs": m.get("agg_motifs"),
            "hydro_cluster_count": m.get("hydro_cluster_count"),
            "n_deamidation": len(m.get("deamidation_sites") or []),
            "n_isomerization": len(m.get("isomerization_sites") or []),
            "n_glyc": len(m.get("glycosylation_sites") or []),
            "n_oxidation": len(m.get("oxidation_sites") or []),
            "n_free_cys": len(m.get("free_cys") or []),
        }
        try:
            adi = round(float(compute_adi(rm)), 2)
        except Exception:
            adi = None

        row = {
            "variant": name,
            "vh_identity_vs_rat_pct": _sid(rat_vh, vh),
            "vl_identity_vs_rat_pct": _sid(rat_vl, vl),
            "AbNatiV_VH": ab_h,
            "AbNatiV_VL": ab_l,
            "AbNatiV_error": ab_err,
            "HPR_VH": round(float(hpr_vh), 4) if hpr_vh is not None else None,
            "HPR_VL": round(float(hpr_vl), 4) if hpr_vl is not None else None,
            "HPR_combined": round(float(hpr_cb), 4) if hpr_cb is not None else None,
            "HPR_error": hpr.get("error"),
            "AbLang2_paired_PLL": ablang,
            "AbLang2_error": ablang_err,
            "RMSD_CA_vs_rat_parent_A": rmsd_by.get(name),
            "ADI": adi,
            **rm,
        }
        rows.append(row)

    (PROJ / "comprehensive_metrics.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )

    # Markdown — split tables for readability
    md: list[str] = [
        "# Rat Campath console — full metrics (identity, humanness, structure, CMC)",
        "",
        "**Reference sequences:** `rat_parent` (demo.html rat). **RMSD:** Cα vs `Rat_parent` PDB.",
        "",
        "## 1. Identity vs rat parent & humanness",
        "",
        "| Variant | VH id% | VL id% | AbNatiV VH | AbNatiV VL | HPR VH | HPR VL | HPR comb | AbLang2 PLL |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        md.append(
            f"| {r['variant']} | {r['vh_identity_vs_rat_pct']} | {r['vl_identity_vs_rat_pct']} | "
            f"{r['AbNatiV_VH']} | {r['AbNatiV_VL']} | {r['HPR_VH']} | {r['HPR_VL']} | "
            f"{r['HPR_combined']} | {r['AbLang2_paired_PLL']} |"
        )

    md += [
        "",
        "## 2. Structure (Fv model conservatism)",
        "",
        "| Variant | RMSD vs Rat_parent (Å) |",
        "|---|---:|",
    ]
    for r in rows:
        md.append(f"| {r['variant']} | {r['RMSD_CA_vs_rat_parent_A']} |")

    md += [
        "",
        "## 3. CMC / developability (Fv sequence)",
        "",
        "| Variant | pI | GRAVY | Instab | Net Q pH7 | Hydro patch9 | Chg patch7 | SAP | Fv asym | Agg | HydroClust | ADI |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        md.append(
            f"| {r['variant']} | {r['pI']} | {r['GRAVY']} | {r['instability_index']} | "
            f"{r['net_charge_pH7']} | {r['hydro_patch_max9']} | {r['charge_patch_max7']} | "
            f"{r['SAP_score']} | {r['Fv_charge_asymmetry']} | {r['agg_motifs']} | "
            f"{r['hydro_cluster_count']} | {r['ADI']} |"
        )

    md += [
        "",
        "## 4. Liability counts (positions)",
        "",
        "| Variant | Deamid | Isomer | N-glyc | Ox | Free Cys |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        md.append(
            f"| {r['variant']} | {r['n_deamidation']} | {r['n_isomerization']} | "
            f"{r['n_glyc']} | {r['n_oxidation']} | {r['n_free_cys']} |"
        )
    md.append("")

    (PROJ / "METRICS_FULL_TABLE.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {PROJ / 'METRICS_FULL_TABLE.md'}")
    print(f"Wrote {PROJ / 'comprehensive_metrics.json'}")


if __name__ == "__main__":
    main()
