#!/usr/bin/env python3
"""
Four-way VH/VL humanization comparison for the **rat** demo pair from api/static/demo.html
(Campath-1G / Alemtuzumab-class parental).

Methods:
  1) DEEP-FR      — AbEngineCore standard VH/VL pipeline (HumanizationEngine, rattus_norvegicus)
  2) 9AA-CTX      — ContextualSubstitutionEngine (FR-only), germlines from (1) or IGHV3-23/IGKV1-39
  3) CDR_graft+BM — CDR graft on IGHV3-23*01 / IGKV1-39*01 + Vernier back-mutations
  4) Surface      — surface_reshape_sequence (same scaffolds as mouse_cd20 script)

Outputs under projects/rat_campath_console_humanization/:
  humanized_sequences.json, FOURWAY_COMPARISON.md, fourway_metrics.json

Usage (anarcii env recommended):
  python scripts/compare_rat_console_humanization.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

# Same as api/static/demo.html — Rat demo
RAT_VH = (
    "EVKLLESGGGLVQPGGSMRLSCAGSGFTFTDFYMNWIRQPAGKAPEWLGFIRDKAKGYTTEYNPSVKGRFTISRDNTQNMLYLQMNTLRAEDTATYYCAREGHTAAPFDYWGQGVMVTVSS"
)
RAT_VL = (
    "DIKMTQSPSFLSASVGDRVTLNCKASQNIDKYLNWYQQKLGESPKLLIYNTNNLQTGIPSRFSGSGSGTDFTLTISSLQPEDVATYFCLQHISRPRTFGTGTKLELK"
)

HUMAN_IGHV = "IGHV3-23*01"
HUMAN_IGKV = "IGKV1-39*01"

OUT = SUITE / "projects" / "rat_campath_console_humanization"


def _load_human_v(seq_type: str, allele_id: str) -> str:
    path = SUITE / "data" / "germlines" / "human_ig_aa" / f"{seq_type}_aa.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for row in data.get("entries", data.get("rows", [])):
        if row.get("id") == allele_id:
            return row["sequence_aa"].strip().upper()
    raise SystemExit(f"Missing {allele_id} in {path}")


def _sid(a: str, b: str) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    return round(sum(x == y for x, y in zip(a, b)) / n * 100.0, 2)


def _kabat_segments_vh_vl(vh: str, vl: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    from core.humanization.kabat_utils import cdr_span, get_kabat_numbering, sorted_keys

    kd_h = get_kabat_numbering(vh)
    kd_l = get_kabat_numbering(vl)
    if not kd_h or not kd_l:
        raise RuntimeError("Kabat numbering failed for rat VH/VL (check ANARCI).")

    def fr4_h(kd: dict) -> str:
        return "".join(kd[k] for k in sorted_keys(kd) if k[0] > 102)

    def fr4_l(kd: dict) -> str:
        return "".join(kd[k] for k in sorted_keys(kd) if k[0] > 97)

    vh_seg = {
        "FR1": cdr_span(kd_h, 1, 25),
        "CDR1": cdr_span(kd_h, 26, 35),
        "FR2": cdr_span(kd_h, 36, 49),
        "CDR2": cdr_span(kd_h, 50, 65),
        "FR3": cdr_span(kd_h, 66, 94),
        "CDR3": cdr_span(kd_h, 95, 102),
        "FR4": fr4_h(kd_h),
    }
    vl_seg = {
        "FR1": cdr_span(kd_l, 1, 23),
        "CDR1": cdr_span(kd_l, 24, 34),
        "FR2": cdr_span(kd_l, 35, 49),
        "CDR2": cdr_span(kd_l, 50, 56),
        "FR3": cdr_span(kd_l, 57, 88),
        "CDR3": cdr_span(kd_l, 89, 97),
        "FR4": fr4_l(kd_l),
    }
    # sanity: reassemble
    vh_re = (
        vh_seg["FR1"] + vh_seg["CDR1"] + vh_seg["FR2"] + vh_seg["CDR2"]
        + vh_seg["FR3"] + vh_seg["CDR3"] + vh_seg["FR4"]
    )
    vl_re = (
        vl_seg["FR1"] + vl_seg["CDR1"] + vl_seg["FR2"] + vl_seg["CDR2"]
        + vl_seg["FR3"] + vl_seg["CDR3"] + vl_seg["FR4"]
    )
    if vh_re != vh.upper() or vl_re != vl.upper():
        raise RuntimeError(
            f"Segment reassembly mismatch VH {len(vh_re)} vs {len(vh)} / VL {len(vl_re)} vs {len(vl)}"
        )
    return vh_seg, vl_seg


def _fv_metrics(vh: str, vl: str) -> Dict[str, Any]:
    from core.cmc.adi_score import compute_adi
    from core.cmc.cmc_metrics import (
        compute_GRAVY,
        compute_aggregation_motifs,
        compute_instability_index,
        compute_net_charge,
        compute_pI,
    )

    fv = vh + vl
    rm: Dict[str, Any] = {
        "pI": round(compute_pI(fv), 2),
        "GRAVY": round(compute_GRAVY(fv), 3),
        "instability_index": round(compute_instability_index(fv), 2),
        "net_charge_pH7": round(compute_net_charge(fv, pH=7.0), 2),
        "agg_motifs": compute_aggregation_motifs(fv),
    }
    try:
        rm["ADI"] = round(compute_adi(rm), 2)
    except Exception as exc:  # noqa: BLE001
        rm["ADI"] = None
        rm["ADI_error"] = str(exc)
    return rm


def _run_deep_fr() -> Tuple[Dict[str, str], Dict[str, Any], Optional[str]]:
    from core.humanization.engine import HumanizationEngine

    engine = HumanizationEngine(workflow="vh_vl", donor_species="rattus_norvegicus")
    try:
        res = engine.run(
            mouse_vh=RAT_VH,
            mouse_vl=RAT_VL,
            project_name="rat_campath_console_deepfr",
            out_dir=str(OUT / "delivery_deepfr"),
            dry_run_structure=True,
            skip_iedb=True,
        )
    except Exception as exc:  # noqa: BLE001
        return {}, {}, f"{type(exc).__name__}: {exc}"

    seqs = res.sequences or {}
    qm = res.qc_metrics or {}
    vh_g = (qm.get("selected_vh_germline") or "IGHV3-23*01").strip()
    vl_g = (qm.get("selected_vl_germline") or "IGKV1-39*01").strip()
    # Short names for 9AA-CTX (family resolution)
    vh_g_short = vh_g.split("*")[0] if "*" in vh_g else vh_g
    vl_g_short = vl_g.split("*")[0] if "*" in vl_g else vl_g

    out = {
        "vh": (seqs.get("humanized_vh") or "").upper(),
        "vl": (seqs.get("humanized_vl") or "").upper(),
        "vh_germline": vh_g_short,
        "vl_germline": vl_g_short,
        "engine_status": res.overall_status,
    }
    return out, qm, None


def _run_9aa_ctx(vh_seg: Dict[str, str], vl_seg: Dict[str, str], vh_g: str, vl_g: str) -> Dict[str, Any]:
    from core.humanization.contextual_substitution_engine import ContextualSubstitutionEngine

    ctx = ContextualSubstitutionEngine()
    r_h = ctx.humanize_fr(
        fr1=vh_seg["FR1"],
        cdr1=vh_seg["CDR1"],
        fr2=vh_seg["FR2"],
        cdr2=vh_seg["CDR2"],
        fr3=vh_seg["FR3"],
        vh_germline=vh_g,
        chain="VH",
    )
    r_l = ctx.humanize_fr(
        fr1=vl_seg["FR1"],
        cdr1=vl_seg["CDR1"],
        fr2=vl_seg["FR2"],
        cdr2=vl_seg["CDR2"],
        fr3=vl_seg["FR3"],
        vh_germline=vl_g,
        chain="VK",
    )
    vh_out = r_h.output_seq + vh_seg["CDR3"] + vh_seg["FR4"]
    vl_out = r_l.output_seq + vl_seg["CDR3"] + vl_seg["FR4"]
    return {
        "vh": vh_out.upper(),
        "vl": vl_out.upper(),
        "vh_replacements": r_h.n_replacements,
        "vl_replacements": r_l.n_replacements,
    }


def _run_graft_surface() -> Dict[str, Any]:
    from scripts.run_petization_pipeline import (
        UNIVERSAL_PET_FR4,
        VERNIER_KABAT_VH,
        VERNIER_KABAT_VL,
        graft_sequence,
        surface_reshape_sequence,
    )

    vh_scaf = _load_human_v("IGHV", HUMAN_IGHV)
    vl_scaf = _load_human_v("IGKV", HUMAN_IGKV)
    fr4_vh = UNIVERSAL_PET_FR4["VH"]
    fr4_vl = UNIVERSAL_PET_FR4["VL_kappa"]

    vh_graft_v, bm_vh_v = graft_sequence(
        RAT_VH, vh_scaf, "VH", VERNIER_KABAT_VH, fr4_strategy="universal_clinical"
    )
    vl_graft_v, bm_vl_v = graft_sequence(
        RAT_VL,
        vl_scaf,
        "VL",
        VERNIER_KABAT_VL,
        fr4_strategy="universal_clinical",
        locus="IGKV",
    )
    vh_surf, mut_vh = surface_reshape_sequence(
        RAT_VH, vh_scaf, "VH", reshape_keys=None, fr4_strategy="universal_clinical"
    )
    vl_surf, mut_vl = surface_reshape_sequence(
        RAT_VL,
        vl_scaf,
        "VL",
        reshape_keys=None,
        fr4_strategy="universal_clinical",
        locus="IGKV",
    )
    return {
        "cdr_graft_vernier_bm": {"vh": vh_graft_v, "vl": vl_graft_v, "bm_vh": bm_vh_v, "bm_vl": bm_vl_v},
        "surface_reshaping": {"vh": vh_surf, "vl": vl_surf, "mut_vh": mut_vh, "mut_vl": mut_vl},
        "meta": {"scaffold_vh": HUMAN_IGHV, "scaffold_vl": HUMAN_IGKV, "fr4_vh": fr4_vh, "fr4_vl": fr4_vl},
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    vh_seg, vl_seg = _kabat_segments_vh_vl(RAT_VH, RAT_VL)
    (OUT / "annotation_kabat_segments.json").write_text(
        json.dumps({"VH": vh_seg, "VL": vl_seg}, indent=2),
        encoding="utf-8",
    )

    deep, qm, err = _run_deep_fr()
    if err:
        print(f"[WARN] DEEP-FR engine failed: {err}")
        vh_g = "IGHV3-23"
        vl_g = "IGKV1-39"
        deep_vh, deep_vl = "", ""
    else:
        vh_g = deep.get("vh_germline") or "IGHV3-23"
        vl_g = deep.get("vl_germline") or "IGKV1-39"
        deep_vh, deep_vl = deep.get("vh", ""), deep.get("vl", "")

    nine = _run_9aa_ctx(vh_seg, vl_seg, vh_g, vl_g)
    gs = _run_graft_surface()

    bundle: Dict[str, Any] = {
        "meta": {
            "source": "api/static/demo.html rat (Campath-1G class)",
            "donor_species": "rattus_norvegicus",
            "deep_fr_error": err,
        },
        "rat_parent": {"vh": RAT_VH, "vl": RAT_VL},
        "DEEP_FR": {"vh": deep_vh, "vl": deep_vl, "qc_note": (qm if not err else None)},
        "9AA_CTX": {
            "vh": nine["vh"],
            "vl": nine["vl"],
            "vh_germline": vh_g,
            "vl_germline": vl_g,
            "vh_replacements": nine.get("vh_replacements"),
            "vl_replacements": nine.get("vl_replacements"),
        },
        "CDR_graft_Vernier_BM": gs["cdr_graft_vernier_bm"],
        "Surface_reshape": gs["surface_reshaping"],
        "graft_surface_meta": gs["meta"],
    }
    (OUT / "humanized_sequences.json").write_text(json.dumps(bundle, indent=2, default=str), encoding="utf-8")

    rows: List[Dict[str, Any]] = []
    variants: List[Tuple[str, str, str]] = [
        ("Rat_parent", RAT_VH, RAT_VL),
        ("DEEP-FR", deep_vh, deep_vl),
        ("9AA-CTX", nine["vh"], nine["vl"]),
        ("CDR_graft+Vernier_BM", gs["cdr_graft_vernier_bm"]["vh"], gs["cdr_graft_vernier_bm"]["vl"]),
        ("Surface_reshape", gs["surface_reshaping"]["vh"], gs["surface_reshaping"]["vl"]),
    ]
    for name, vh, vl in variants:
        if not vh or not vl:
            rows.append({"Variant": name, "error": "missing_sequence"})
            continue
        m = _fv_metrics(vh, vl)
        rows.append(
            {
                "Variant": name,
                "vh_id_vs_rat": _sid(RAT_VH, vh),
                "vl_id_vs_rat": _sid(RAT_VL, vl),
                **m,
            }
        )

    (OUT / "fourway_metrics.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    lines = [
        "# Rat console demo — four-way humanization comparison",
        "",
        "**Input:** `demo.html` rat pair (Campath-1G class), `donor_species=rattus_norvegicus` for AbEngineCore.",
        "",
        "| Variant | VH id% | VL id% | pI | GRAVY | Instab | Agg | ADI |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['Variant']} | — | — | — | — | — | — | — |")
            continue
        lines.append(
            f"| {r['Variant']} | {r['vh_id_vs_rat']} | {r['vl_id_vs_rat']} | "
            f"{r['pI']} | {r['GRAVY']} | {r['instability_index']} | {r['agg_motifs']} | {r.get('ADI')} |"
        )
    lines += ["", f"Artifacts: `{OUT / 'humanized_sequences.json'}`", ""]
    if err:
        lines += [f"**DEEP-FR run:** failed — `{err}`", ""]
    (OUT / "FOURWAY_COMPARISON.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(rows, indent=2, default=str))
    print(f"\nWrote {OUT / 'FOURWAY_COMPARISON.md'}")


if __name__ == "__main__":
    main()
