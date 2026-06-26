#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
compute_tnb_full_cmc.py
=======================
Full 15-metric CMC + continuous ADI (tent-function) for all Tnb04/Tnb164 variants.
Uses real sequences from Excel file — no estimates.

Also computes:
  - Fusion protein pI for all 8 bispecific combinations
  - Linker charge variants for pI engineering
  - Comparison vs VHH42 + scFv_52 references
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE_ROOT))

from Bio.SeqUtils.ProtParam import ProteinAnalysis
from core.cmc.adi_score import compute_adi_with_breakdown, adi_interpretation

# ─── VHH42 ref ───────────────────────────────────────────────────────────────
REF_PATH = SUITE_ROOT / "data" / "reference" / "VHH42_reference_stats_v1.json"
REF_STATS = json.loads(REF_PATH.read_text(encoding="utf-8"))
_TMP_REF = Path(tempfile.mktemp(suffix=".json"))
_TMP_REF.write_text(json.dumps(REF_STATS), encoding="utf-8")

# ─── Sequences (from Excel) ───────────────────────────────────────────────────
SEQUENCES = {
    # Tnb04 panel (SARS-CoV-2 arm, 116 aa)
    "Tnb04H9": "EVQLLESGGGLVQPGGSLRLSCAASGSISTLNVMGWYRQAPGKGRELVSRITLDGRPYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCKLENGGFFYYWGQGTMVTVSS",
    "Tnb04H4": "EVQLLESGGGLVQPGGSLRLSCAASGSISTLNVMSWYRQAPGKGRELVARITLDGRPYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCKLENGGFFYYWGQGTMVTVSS",
    "Tnb04H2": "EVQLLESGGGLVQPGGSLRLSCAASGSISTLNVMSWYRQAPGKGRELVSRITLDGRPYYADSVKGRFTISRDGSKNTLYLQMNSLRAEDTAVYYCKLENGGFFYYWGQGTMVTVSS",
    "Tnb04H3": "EVQLLESGGGLVQPGGSLRLSCAASGSISTLNVMSWYRQAPGKQRELVSRITLDGRPYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCKLENGGFFYYWGQGTMVTVSS",
    "Tnb04H7": "EVQLLESGGGLVQPGGSLRLSCAASGSISTLNVMSWYRQAPGKGRELVSRITLDGRPYYADSVKGRFTISRDNSKNTLYLQMNNLRAEDTAVYYCKLENGGFFYYWGQGTMVTVSS",
    "Tnb04H8": "EVQLLESGGGLVQPGGSLRLSCAASGSISTLNVMSWYRQAPGKGRELVSRITLDGRPYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYFCKLENGGFFYYWGQGTMVTVSS",
    # Tnb164 panel (MERS-CoV arm, 123 aa)
    "Tnb164H4": "EVQLLESGGGLVQPGGSLRLSCAASGRSFRDYTMSWFRQAPGKGREFVSAHGWIGGKEYYADSVKGRFTISRDKSKNTLYLQMNSLRAEDTAVYYCAAHWSGDYYDSAAYNYWGQGTMVTVSS",
    "Tnb164H5": "EVQLLESGGGLVQPGGSLRLSCAASGRSFRDYTMSWFRQAPGKGREFVAAHGWIGGKEYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAAHWSGDYYDSAAYNYWGQGTMVTVSS",
    "Tnb164H2": "EVQLLESGGGLVQPGGSLRLSCAASGRSFRDYTMSWFRQAPGKEREFVSAHGWIGGKEYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAAHWSGDYYDSAAYNYWGQGTMVTVSS",
    "Tnb164H6": "EVQLLESGGGLVQPGGSLRLSCAASGRSFRDYTMSWFRQAPGKGREFVSAHGWIGGKEYYADSVKGRFTVSRDNSKNTLYLQMNSLRAEDTAVYYCAAHWSGDYYDSAAYNYWGQGTMVTVSS",
    "Tnb164H7": "EVQLLESGGGLVQPGGSLRLSCAASGRSFRDYTMSWFRQAPGKGREFVSAHGWIGGKEYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYFCAAHWSGDYYDSAAYNYWGQGTMVTVSS",
    "Tnb164H8": "EVQLLESGGGLVQPGGSLRLSCAASGRSFRDYTMSWFRQAPGRGREFVSAHGWIGGKEYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAAHWSGDYYDSAAYNYWGQGTMVTVSS",
}

# ─── Linker options ───────────────────────────────────────────────────────────
LINKERS = {
    "(G4S)3":       "GGGGSGGGGSGGGGS",
    "(G4S)4":       "GGGGSGGGGSGGGGSGGGGS",
    "(G4S)3+2E":    "GGGGSGGGGSGGGGSEE",
    "(G4S)3+3E":    "GGGGSGGGGSGGGGSEEE",
    "(G4S)3+4E":    "GGGGSGGGGSGGGGSEEEE",
    "Whitlow":      "GSTSGSGKPGSGEGSTKG",
}

# ─── Bispecific combinations to evaluate ─────────────────────────────────────
COMBINATIONS = [
    ("Tnb04H9", "Tnb164H4"),   # current, low expression
    ("Tnb04H9", "Tnb164H6"),   # new P1-A recommendation
    ("Tnb04H9", "Tnb164H5"),   # P1-B
    ("Tnb04H9", "Tnb164H2"),   # P2
    ("Tnb04H2", "Tnb164H6"),   # P4 low-pI candidate
    ("Tnb04H2", "Tnb164H5"),   # P4
    ("Tnb04H2", "Tnb164H4"),   # P4
    ("Tnb04H2", "Tnb164H2"),   # P4 double-low
]

# ─── Neutralization activity (from pseudovirus assay) ────────────────────────
ACTIVITY = {
    # Tnb04: SARS-CoV-2 IC50 (μg/mL)
    "Tnb04H9": {"WT_IC50": 0.027, "JN1_IC50": 0.053, "KP_IC50": 0.011, "XDV_IC50": 0.037,
                "JN1_IC90": 0.316, "KP_IC90": 0.557, "XDV_IC90": 0.537},
    "Tnb04H4": {"WT_IC50": 0.001, "JN1_IC50": 0.150, "KP_IC50": 0.133, "XDV_IC50": 0.019,
                "JN1_IC90": 1.418, "KP_IC90": 2.629, "XDV_IC90": 1.251},
    "Tnb04H2": {"WT_IC50": 0.001, "JN1_IC50": 0.071, "KP_IC50": 0.093, "XDV_IC50": 0.106,
                "JN1_IC90": 0.697, "KP_IC90": 0.784, "XDV_IC90": 1.623},
    "Tnb04H3": {"WT_IC50": 0.001, "JN1_IC50": 0.205, "KP_IC50": 0.212, "XDV_IC50": 0.088,
                "JN1_IC90": 3.485, "KP_IC90": 1.744, "XDV_IC90": 3.184},
    "Tnb04H7": {"WT_IC50": None, "JN1_IC50": None,  "KP_IC50": None,  "XDV_IC50": None},
    "Tnb04H8": {"WT_IC50": 0.101, "JN1_IC50": 0.186, "KP_IC50": 0.024, "XDV_IC50": 0.577,
                "JN1_IC90": 5.731, "KP_IC90": 3.490, "XDV_IC90": 4.380},
    # Tnb164: MERS MjHKU4r IC90 (μg/mL) — key discriminator
    "Tnb164H4": {"MERS_WT_IC50": 0.001, "MjHKU4r_IC50": 0.001, "MjHKU4r_IC90": 0.119},
    "Tnb164H5": {"MERS_WT_IC50": 0.001, "MjHKU4r_IC50": 0.001, "MjHKU4r_IC90": 0.345},
    "Tnb164H2": {"MERS_WT_IC50": 0.001, "MjHKU4r_IC50": 0.000, "MjHKU4r_IC90": 0.489},
    "Tnb164H6": {"MERS_WT_IC50": 0.001, "MjHKU4r_IC50": 0.000, "MjHKU4r_IC90": 0.025},
    "Tnb164H7": {"MERS_WT_IC50": 0.001, "MjHKU4r_IC50": 0.001, "MjHKU4r_IC90": 0.754},
    "Tnb164H8": {"MERS_WT_IC50": 0.001, "MjHKU4r_IC50": 0.000, "MjHKU4r_IC90": 0.868},
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def compute_single_cmc(seq: str, vid: str) -> dict:
    """Compute CMC for single VHH and return full metrics + continuous ADI."""
    import re
    from core.cmc.cmc_metrics import (
        compute_pI, compute_GRAVY, compute_instability_index,
        compute_net_charge, compute_hydro_patch_max9, compute_charge_patch_max7,
        compute_aggregation_motifs, compute_hydro_cluster_count,
        compute_chemical_liabilities,
    )
    s = seq.upper()
    liab = compute_chemical_liabilities(s)
    # Free cys excluding canonical VHH disulfide (pos 22, 92 approx)
    _CONSERVED = {21, 91}
    free_cys_pos = [p for p in liab.get("free_cys", []) if all(abs(p - c) > 2 for c in _CONSERVED)]

    metrics = {
        "pI":                    compute_pI(s),
        "GRAVY":                 compute_GRAVY(s),
        "instability_index":     compute_instability_index(s),
        "net_charge_pH7":        compute_net_charge(s),
        "hydro_patch_max9":      compute_hydro_patch_max9(s),
        "charge_patch_max7":     compute_charge_patch_max7(s),
        "SAP_score":             max(sum(1 for a in s[i:i+7] if a in frozenset("AILMFWV"))/7.0 for i in range(max(1,len(s)-6))),
        "agg_motifs":            compute_aggregation_motifs(s),
        "hydro_cluster_count":   compute_hydro_cluster_count(s),
        "glycosylation_sites":   len(liab.get("glycosylation_sites", [])),
        "deamidation_sites":     len(liab.get("deamidation_sites", [])),
        "isomerization_sites":   len(liab.get("isomerization_sites", [])),
        "oxidation_sites":       len(liab.get("oxidation_sites", [])),
        "free_cys":              len(free_cys_pos),
        "_positions":            {k: v for k, v in liab.items()},
    }
    metrics["SAP_score"] = round(metrics["SAP_score"], 3)

    adi_r = compute_adi_with_breakdown(
        {k: v for k, v in metrics.items() if not k.startswith("_")},
        ref_stats_path=_TMP_REF
    )
    return {
        "vhh_id": vid,
        "sequence": seq,
        "seq_len": len(seq),
        "metrics": metrics,
        "adi_continuous": adi_r["ADI"],
        "adi_grade": adi_interpretation(adi_r["ADI"]),
        "metric_scores": adi_r["metric_scores"],
        "category_scores": adi_r["category_scores"],
    }


def compute_fusion_cmc(sars_seq: str, mers_seq: str, linker_seq: str) -> dict:
    """Compute CMC for full VHH-linker-VHH fusion."""
    fusion = sars_seq + linker_seq + mers_seq
    pa = ProteinAnalysis(fusion.upper())
    return {
        "pI":             round(pa.isoelectric_point(), 2),
        "GRAVY":          round(pa.gravy(), 3),
        "instability_index": round(pa.instability_index(), 1),
        "net_charge_pH7": round(pa.charge_at_pH(7.0), 2),
        "full_len":       len(fusion),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    out_dir = SUITE_ROOT / "projects" / "Tnb_bispecific" / "cmc_eval"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Single VHH CMC ────────────────────────────────────────────────────
    print("\n" + "="*105)
    print("  PART 1 — Single VHH CMC (15 metrics, real sequences, continuous ADI vs VHH42)")
    print("="*105)
    fmt = "{:12s} {:>5s} {:>5s} {:>7s} {:>7s} {:>6s} {:>5s} {:>4s} {:>5s} {:>5s} {:>5s} {:>4s} | {:>6s} {:>12s}"
    print(fmt.format("", "pI", "chg", "GRAVY", "instab", "SAP", "agg", "oxid", "deam", "isom", "cys", "hyd", "ADI", ""))
    print("-"*105)

    single_results = {}
    for vid, seq in SEQUENCES.items():
        r = compute_single_cmc(seq, vid)
        single_results[vid] = r
        m = r["metrics"]
        print(fmt.format(
            vid,
            f"{m['pI']:.2f}", f"{m['net_charge_pH7']:+.1f}",
            f"{m['GRAVY']:.3f}", f"{m['instability_index']:.1f}",
            f"{m['SAP_score']:.3f}", str(m['agg_motifs']),
            str(m['oxidation_sites']), str(m['deamidation_sites']),
            str(m['isomerization_sites']), str(m['free_cys']),
            str(m['hydro_cluster_count']),
            f"{r['adi_continuous']:.1f}", r['adi_grade'],
        ))

    # ── 2. Per-category ADI breakdown ────────────────────────────────────────
    print("\n" + "="*105)
    print("  PART 2 — ADI （）")
    print("="*105)
    fmt2 = "{:12s} {:>8s} {:>8s} {:>10s} {:>10s} | {:>8s} {:>8s} {:>8s} {:>8s} | {:>7s}"
    print(fmt2.format("", "pI_sc", "chg_sc", "GRAVY_sc", "instab_sc",
                      "_sc", "_sc", "", "", "ADI"))
    print("-"*105)
    for vid, r in single_results.items():
        ms = r["metric_scores"]
        cs = r["category_scores"]
        print(fmt2.format(
            vid,
            f"{ms.get('pI', 0):.1f}", f"{ms.get('net_charge_pH7', 0):.1f}",
            f"{ms.get('GRAVY', 0):.1f}", f"{ms.get('instability_index', 0):.1f}",
            f"{ms.get('oxidation_sites', 0):.1f}", f"{ms.get('deamidation_sites', 0):.1f}",
            f"{cs.get('hydrophobicity', 0):.1f}", f"{cs.get('charge', 0):.1f}",
            f"{r['adi_continuous']:.1f}",
        ))

    # ── 3. Fusion protein CMC ────────────────────────────────────────────────
    print("\n" + "="*105)
    print("  PART 3 —  CMC（VHH-linker-VHH ）")
    print("="*105)
    fmt3 = "{:22s} {:>10s} {:>6s} {:>5s} {:>5s} {:>7s} {:>8s} | {:>20s}"
    print(fmt3.format("", "Linker", "", "pI", "chg", "GRAVY", "instab", ""))
    print("-"*105)

    fusion_results = []
    for sars_id, mers_id in COMBINATIONS:
        sars_seq = SEQUENCES[sars_id]
        mers_seq = SEQUENCES[mers_id]
        for lk_name, lk_seq in LINKERS.items():
            fus = compute_fusion_cmc(sars_seq, mers_seq, lk_seq)
            combo_label = f"{sars_id}+{mers_id}"
            pi_flag = "⚠ " if fus["pI"] > 8.5 else ("✓ " if fus["pI"] <= 8.0 else "△ ")
            print(fmt3.format(
                combo_label if lk_name == "(G4S)3" else "",
                lk_name, str(fus["full_len"]),
                f"{fus['pI']:.2f}", f"{fus['net_charge_pH7']:+.1f}",
                f"{fus['GRAVY']:.3f}", f"{fus['instability_index']:.1f}",
                pi_flag,
            ))
            fusion_results.append({
                "combo": combo_label, "sars": sars_id, "mers": mers_id,
                "linker": lk_name, **fus,
            })
        print()

    # ── 4. pI vs old-report comparison ──────────────────────────────────────
    print("="*105)
    print("  PART 4 —  pI vs （）")
    print("="*105)
    OLD_PI = {
        "Tnb04H9": 9.0, "Tnb04H4": 9.0, "Tnb04H2": 9.0,
        "Tnb164H4": 8.59, "Tnb164H5": 8.03, "Tnb164H2": 7.0, "Tnb164H6": 8.03,
    }
    for vid, old_pi in OLD_PI.items():
        new_pi = single_results[vid]["metrics"]["pI"]
        delta = new_pi - old_pi
        status = "✓" if abs(delta) < 0.1 else f"Δ{delta:+.2f}"
        print(f"  {vid:12s}  ={old_pi:.2f}  ={new_pi:.2f}  {status}")

    # ── 5. Save JSON ─────────────────────────────────────────────────────────
    payload = {
        "_meta": {"run_time": datetime.now().isoformat(), "source": "real_sequences_from_excel"},
        "single_vhh": single_results,
        "fusion_proteins": fusion_results,
        "activity": ACTIVITY,
    }
    out_json = out_dir / "tnb_full_cmc_real.json"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {out_json}")

    _TMP_REF.unlink(missing_ok=True)
    print("\nDone.")


if __name__ == "__main__":
    main()
