#!/usr/bin/env python3
"""
cmc_optimize_pipeline.py — InSynBio AbEngineCore CMC  CLI
=====================================================================

: AbEvaluator.run()  ← 
:    optimization_pipeline  ←  + 

:
  [AbEvaluator] （15  + QA ）
       ↓
  [optimization_pipeline] FR-only  →  → ABodyBuilder2  → 
       ↓
  [AbEvaluator] （15  + QA ）
       ↓
  （FAIL=0, WARN≤1, ADI≥60, ）+ before/after 


-----------
，：
  mumab4d5        → projects/mumab4d5_spliced_Redesign/
  muMAb4D5        → （）
  "mab4d5 v2"     → 
  pdl1            → projects/pdl1_Redesign/（）


--------
#  — （）
python scripts/cmc_optimize_pipeline.py mumab4d5

# （）
python scripts/cmc_optimize_pipeline.py mumab4d5 \\
    --vh EVQLLESGGGLVQPGGSLRLSCAASGFNIKDTYIH... \\
    --vl DIQMTQSPSSLSASVGDRVTITCRASQDVNTAVA...

# ，
python scripts/cmc_optimize_pipeline.py mumab4d5 --mode evaluate

#  + （）
python scripts/cmc_optimize_pipeline.py mumab4d5 --mode full

# 
python scripts/cmc_optimize_pipeline.py mumab4d5 --out ./cmc_output
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple  # noqa: F401

# ──  ──────────────────────────────────────────────────────────────────
_SUITE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SUITE_ROOT))
sys.path.insert(0, str(_SUITE_ROOT / "scripts"))

# ── （） ────────────────────────────────────────────────────
_IS_TTY = sys.stdout.isatty()

def _c(text: str, code: str) -> str:
    if not _IS_TTY:
        return text
    codes = {"green": "32", "red": "31", "yellow": "33", "cyan": "36", "bold": "1", "reset": "0"}
    c = codes.get(code, "0")
    return f"\033[{c}m{text}\033[0m"

def ok(s):  return _c(s, "green")
def err(s): return _c(s, "red")
def warn(s): return _c(s, "yellow")
def info(s): return _c(s, "cyan")
def bold(s): return _c(s, "bold")


# ─────────────────────────────────────────────────────────────────────────────
# 1. （）
# ─────────────────────────────────────────────────────────────────────────────

def _discover_project(name: str) -> Optional[Path]:
    """
    。
    :  name （、、）。
    """
    projects_dir = _SUITE_ROOT / "projects"
    if not projects_dir.exists():
        return None

    # （ tokens）
    tokens = [t.lower() for t in name.replace("-", " ").replace("_", " ").split() if t]
    if not tokens:
        return None

    candidates = []
    for p in projects_dir.iterdir():
        if not p.is_dir():
            continue
        dir_lower = p.name.lower()
        if all(tok in dir_lower for tok in tokens):
            candidates.append(p)

    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        # ：
        # 1.  v2/spliced PDB （）
        # 2. （）
        def _priority(p: Path) -> Tuple[int, int, float]:
            struct = p / "structures"
            has_v2_pdb = 1 if struct.exists() and any("v2" in f.name.lower() for f in struct.glob("*.pdb")) else 0
            has_results = 1 if any(p.glob("*results*.json")) else 0
            mtime = p.stat().st_mtime
            return (-(has_v2_pdb + has_results), -mtime, 0)
        return sorted(candidates, key=_priority)[0]
    return None


def _discover_sequences(project_dir: Path) -> Tuple[Optional[str], Optional[str]]:
    """
     VH/VL 。
    : results JSON (v2_VH/v2_VL ) → run reports
    """
    def _is_seq(s: Any) -> bool:
        return isinstance(s, str) and len(s) > 50 and all(
            c in "ACDEFGHIKLMNPQRSTVWY" for c in s.strip().upper()
        )

    # 1.  results JSON 
    results_files = sorted(project_dir.glob("*results*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    for rf in results_files:
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))

            # : data["sequences"]["v2_VH"] / ["v2_VL"]
            seqs = data.get("sequences", {})
            for suffix in ("v2", "v3", "v1", ""):
                key_vh = f"{suffix}_VH" if suffix else "VH"
                key_vl = f"{suffix}_VL" if suffix else "VL"
                vh = seqs.get(key_vh) or seqs.get(key_vh.lower())
                vl = seqs.get(key_vl) or seqs.get(key_vl.lower())
                if _is_seq(vh) and _is_seq(vl):
                    return vh.strip().upper(), vl.strip().upper()

            # : data["humanized_vh"] / data["vh_seq"] / ...
            for vh_key in ("humanized_vh", "vh_seq", "vh", "VH"):
                for vl_key in ("humanized_vl", "vl_seq", "vl", "VL"):
                    vh = data.get(vh_key)
                    vl = data.get(vl_key)
                    if _is_seq(vh) and _is_seq(vl):
                        return vh.strip().upper(), vl.strip().upper()
        except Exception:
            continue

    # 2.  run reports JSON 
    report_dir = project_dir / "reports"
    if report_dir.exists():
        for rf in sorted(report_dir.glob("*/abenginecore_checklist_report.json"),
                         key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                data = json.loads(rf.read_text(encoding="utf-8"))
                ph5 = data.get("phases", {}).get("phase5", {})
                vh = ph5.get("humanized_vh_seq") or ph5.get("vh_seq")
                vl = ph5.get("humanized_vl_seq") or ph5.get("vl_seq")
                if _is_seq(vh) and _is_seq(vl):
                    return vh.strip().upper(), vl.strip().upper()
            except Exception:
                continue

    return None, None


def _discover_pdbs(project_dir: Path) -> Dict[str, Optional[Path]]:
    """
    、 V2、 PDB 。
    """
    struct_dir = project_dir / "structures"
    pdbs: Dict[str, Optional[Path]] = {"mouse": None, "humanized_v2": None, "clinical": None}

    if struct_dir.exists():
        for pdb in struct_dir.glob("*.pdb"):
            n = pdb.name.lower()
            if "mouse" in n and pdbs["mouse"] is None:
                pdbs["mouse"] = pdb
            elif "v2" in n and ("humanized" in n or "human" in n):
                pdbs["humanized_v2"] = pdb
            elif "clinical" in n and pdbs["clinical"] is None:
                pdbs["clinical"] = pdb

    # fallback:  run report 
    if pdbs["humanized_v2"] is None:
        for rf in sorted((project_dir / "reports").glob("*/humanized_vh_vl_structure.pdb"),
                         key=lambda x: x.stat().st_mtime, reverse=True):
            pdbs["humanized_v2"] = rf
            break

    return pdbs


# ─────────────────────────────────────────────────────────────────────────────
# 2. 15 
# ─────────────────────────────────────────────────────────────────────────────

_METRIC_LABELS = {
    "pI":                  "pI ()",
    "GRAVY":               "GRAVY ()",
    "instability_index":   "",
    "net_charge_pH7":      " pH7",
    "hydro_patch_max9":    " 9mer",
    "charge_patch_max7":   " 7mer",
    "SAP_score":           "SAP score",
    "Fv_charge_asymmetry": "Fv ",
    "agg_motifs":          " motif ",
    "hydro_cluster_count": "",
    "glycosylation_sites": "",
    "deamidation_sites":   "",
    "isomerization_sites": "",
    "oxidation_sites":     "",
    "free_cys":            " Cys",
}


def _fmt_val(v: Any) -> str:
    if isinstance(v, list):
        return f"{len(v)} "
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v) if v is not None else "N/A"


def _print_metrics_table(annotated: Dict[str, Any], title: str, ref_stats: Dict) -> None:
    """
    annotated :
      A. optimization_pipeline: { mkey: {"value": .., "band": .., "gate": ..} }
      B. cmc_advisor_module:    { mkey: {"value": .., "percentile_band": .., "gate": ..} }
    """
    ref_m = ref_stats.get("metrics", ref_stats)
    print(f"\n{bold(title)}")
    print(f"{'#':<3} {'':<22} {'':<10} {'p50':<8} {'':<22} {''}")
    print("─" * 82)
    for i, (k, a) in enumerate(annotated.items(), 1):
        if not isinstance(a, dict):
            continue
        v    = a.get("value")
        gate = a.get("gate", "?")
        # support both "band" and "percentile_band" keys
        band = a.get("band") or a.get("percentile_band", "?")
        p50  = ref_m.get(k, {}).get("p50", a.get("ref_p50", "N/A"))
        lbl  = _METRIC_LABELS.get(k, k)
        flag = ok("✅ PASS") if gate == "PASS" else (warn("⚠️ WARN") if gate == "WARN" else err("❌ FAIL"))
        print(f"{i:<3} {lbl:<22} {_fmt_val(v):<10} {str(p50):<8} {str(band):<22} {flag}")


def _print_structural_fidelity(sf: Dict[str, Any]) -> None:
    if not sf:
        print(warn("  : （ PDB）"))
        return
    if sf.get("error"):
        print(err(f"  : {sf['error']}"))
        return
    print(f"\n{bold('')}")
    checks = {
        "VH/VL ":       (sf.get("vhvl_angle_delta"),   5.0,  "°"),
        "Fv RMSD":            (sf.get("fv_rmsd"),             1.5,  " Å"),
        "CDR-H1 RMSD":        (sf.get("cdr_rmsd", {}).get("H1"), 1.0, " Å"),
        "CDR-H2 RMSD":        (sf.get("cdr_rmsd", {}).get("H2"), 1.0, " Å"),
        "CDR-H3 RMSD (WARN)": (sf.get("cdr_rmsd", {}).get("H3"), None, " Å"),
        "CDR-L1 RMSD (WARN)": (sf.get("cdr_rmsd", {}).get("L1"), None, " Å"),
        "CDR-L2 RMSD":        (sf.get("cdr_rmsd", {}).get("L2"), 1.0, " Å"),
        "CDR-L3 RMSD":        (sf.get("cdr_rmsd", {}).get("L3"), 1.0, " Å"),
        "Canonical ":     (sf.get("canonical_unchanged"), None, ""),
    }
    for label, (val, threshold, unit) in checks.items():
        if val is None:
            continue
        if isinstance(val, bool):
            flag = ok("✅") if val else err("❌")
            print(f"  {label:<28}: {flag}")
        elif threshold:
            flag = ok("✅ PASS") if float(val) <= threshold else err("❌ FAIL")
            print(f"  {label:<28}: {val:.3f}{unit}  {flag}")
        else:
            print(f"  {label:<28}: {val:.3f}{unit}  (WARN only)")


def _print_comparison(orig_ann: Dict, best_ann: Dict, adi_orig: float, adi_best: float,
                      ref_stats: Dict) -> None:
    ref_m = ref_stats.get("metrics", ref_stats)
    print(f"\n{bold('Before / After ')}")
    print(f"{'':<22} {'':<12} {'':<12} {'':<12} {''}")
    print("─" * 72)
    for k in _METRIC_LABELS:
        ao = orig_ann.get(k)
        ab = best_ann.get(k)
        if not (isinstance(ao, dict) and isinstance(ab, dict)):
            continue
        vo   = _fmt_val(ao.get("value"))
        vb   = _fmt_val(ab.get("value"))
        go   = ao.get("gate", "?")
        gb   = ab.get("gate", "?")
        lbl  = _METRIC_LABELS[k]
        go_c = ok(go) if go == "PASS" else (warn(go) if go == "WARN" else err(go))
        gb_c = ok(gb) if gb == "PASS" else (warn(gb) if gb == "WARN" else err(gb))
        chg  = "→" if vo == vb else ok("↑ ") if gb == "PASS" and go != "PASS" else warn("→ ")
        print(f"{lbl:<22} {vo:<12} {vb:<12} {go_c:<12} {gb_c}  {chg}")
    print()
    adi_delta = adi_best - adi_orig
    sign      = ok(f"+{adi_delta:.1f}") if adi_delta > 0 else warn(f"{adi_delta:.1f}")
    print(f"  ADI: {adi_orig:.1f} → {bold(f'{adi_best:.1f}')}  ({sign})")


# ─────────────────────────────────────────────────────────────────────────────
# 3.  CLI 
# ─────────────────────────────────────────────────────────────────────────────

def _make_evaluator(
    antibody_id: str,
    vh_seq: str,
    vl_seq: str,
    pdb_path: Optional[Path] = None,
    ref_pdb_path: Optional[Path] = None,
    strict_qa: bool = False,
) -> "AbEvaluator":
    """
     AbEvaluator 。strict_qa=False  FAIL （CMC 
    optimization_pipeline ， AbEvaluator  abort）。
    """
    from core.evaluation.evaluator import AbEvaluator, AntibodyType
    return AbEvaluator(
        project_name = antibody_id,
        ab_type      = AntibodyType.HUMANIZED,
        vh_seq       = vh_seq,
        vl_seq       = vl_seq,
        pdb_path     = str(pdb_path) if pdb_path and pdb_path.exists() else None,
        ref_pdb_path = str(ref_pdb_path) if ref_pdb_path and ref_pdb_path.exists() else None,
        strict_qa    = strict_qa,
    )


# ─────────────────────────────────────────────────────────────────────────────
# （ / ）
# ─────────────────────────────────────────────────────────────────────────────

# （ PDB，）
SEQ_MODULES = ["cmc_advisor", "cdr_scan", "developability", "germline", "immunogenicity"]

# （ PDB）
STRUCT_MODULES_BASE     = ["structure_13param", "tap"]
STRUCT_MODULES_VS_MOUSE = ["delta_vs_mouse"]          #  ref_pdb（）


def _build_eval_modules(has_pdb: bool, has_ref_pdb: bool) -> List[str]:
    """。"""
    modules = list(SEQ_MODULES)
    if has_pdb:
        modules.extend(STRUCT_MODULES_BASE)
        if has_ref_pdb:
            modules.extend(STRUCT_MODULES_VS_MOUSE)
    return modules


# ─────────────────────────────────────────────────────────────────────────────
# 
# ─────────────────────────────────────────────────────────────────────────────

def _print_cdr_scan(result: Dict) -> None:
    """ cdr_scan （ CDR ）。"""
    if result.get("status") in ("SKIPPED", "ERROR", "PLANNED"):
        print(warn(f"  cdr_scan: {result.get('status')} — {result.get('reason', result.get('note', ''))}"))
        return
    liabilities = result.get("liabilities", [])
    total = result.get("total_liabilities", len(liabilities))
    flag = ok("✅ ") if total == 0 else warn(f"⚠️ {total} ")

    print(f"\n{bold('CDR （cdr_scan）')} {flag}")
    if not liabilities:
        print("  ")
        return

    by_type: Dict[str, List] = {}
    for lb in liabilities:
        t = lb.get("type", "unknown")
        by_type.setdefault(t, []).append(lb)

    for t, items in by_type.items():
        sev = items[0].get("severity", "?")
        flag_sev = err("HIGH") if sev == "HIGH" else warn("MEDIUM")
        print(f"  {t:<22}: {len(items):>2}   [{flag_sev}]")
        for it in items[:3]:
            pos = it.get("pos", "?")
            pat = it.get("pattern", "")
            print(f"    pos {pos}: {pat}")
        if len(items) > 3:
            print(f"    ...  {len(items)-3} ")


def _print_developability(result: Dict) -> None:
    """ developability （）。"""
    if result.get("status") in ("SKIPPED", "ERROR", "PLANNED"):
        print(warn(f"  developability: {result.get('status')} — {result.get('reason', result.get('note', ''))}"))
        return
    # developability （ "metrics" ）
    ranks = result.get("clinical_percentile_ranks", {})
    print(f"\n{bold('（developability）')}")
    rows = [
        ("pI",            result.get("pI_fab_estimate")),
        ("GRAVY",         result.get("GRAVY")),
        ("",     result.get("instability_index")),
        (" pH7",    result.get("net_charge_pH7")),
        (" 9mer", result.get("hydro_patch_max9")),
        (" 7mer", result.get("charge_patch_max7")),
    ]
    for label, val in rows:
        if val is None:
            continue
        val_s = f"{val:.3f}" if isinstance(val, float) else str(val)
        rank = ranks.get(label.split("(")[0].strip(), {})
        gate = rank.get("gate", "") if isinstance(rank, dict) else ""
        gate_s = ok("PASS") if gate == "PASS" else (warn("WARN") if gate == "WARN"
                  else (err("FAIL") if gate == "FAIL" else ""))
        print(f"  {label:<18}: {val_s:<10}  {gate_s}")
    cs = result.get("clinical_score")
    if cs is not None:
        pop = result.get("clinical_population", "AbRef")
        print(f"   ({pop}): {ok(f'{cs:.0f}/100') if cs >= 80 else warn(f'{cs:.0f}/100')}")


def _print_germline(result: Dict) -> None:
    """ germline （）。"""
    if result.get("status") in ("SKIPPED", "ERROR", "PLANNED"):
        print(warn(f"  germline: {result.get('status')} — {result.get('reason', result.get('note', ''))}"))
        return
    print(f"\n{bold('（germline）')}")
    # （ vs ）
    for k, label in [
        ("closest_vh_germline",    "VH "),
        ("vh_germline",            "VH "),
        ("closest_vl_germline",    "VL "),
        ("vl_germline",            "VL "),
        ("vh_germline_identity_pct","VH "),
        ("vl_germline_identity_pct","VL "),
        ("vh_identity_pct",        "VH "),
        ("vl_identity_pct",        "VL "),
        ("shm_count",              "（SHM）"),
        ("canonical_h1",           "Canonical H1"),
        ("canonical_h2",           "Canonical H2"),
        ("canonical_l1",           "Canonical L1"),
    ]:
        v = result.get(k)
        if v is None:
            continue
        val_s = f"{v:.1f}%" if "pct" in k and isinstance(v, float) else str(v)
        print(f"  {label:<24}: {val_s}")
    if result.get("note"):
        print(f"  {warn('')}: {result['note'][:100]}")


def _print_immunogenicity(result: Dict) -> None:
    """ immunogenicity （）。"""
    if result.get("status") in ("SKIPPED", "ERROR", "PLANNED"):
        print(warn(f"  immunogenicity: {result.get('status')} — {result.get('reason', result.get('note', ''))}"))
        return
    print(f"\n{bold('（immunogenicity）')}")
    # : mhcii_risk ( risk_level)
    risk = (result.get("mhcii_risk") or result.get("risk_level") or
            result.get("mhcii_risk_level") or "unknown")
    flag = ok("✅ LOW") if "low" in str(risk).lower() else (
           warn("⚠️ MEDIUM") if "medium" in str(risk).lower() else err("❌ HIGH"))
    print(f"  MHC-II : {flag}")

    # TCIA 
    tcia = result.get("tcia_score")
    if tcia is not None:
        tcia_flag = ok(f"{tcia:.3f}") if tcia < 0.1 else (warn(f"{tcia:.3f}") if tcia < 0.3 else err(f"{tcia:.3f}"))
        print(f"  TCIA :       {tcia_flag}  (< 0.1 = )")
    n_ep    = result.get("n_epitopes")
    n_clust = result.get("n_clusters")
    if n_ep is not None:
        print(f"  :        {n_ep}  (: {n_clust})")

    # funnel （， stages ）
    fs = result.get("funnel_stats", {})
    stages = fs.get("stages", []) if isinstance(fs, dict) else []
    if stages and isinstance(stages, list):
        print(f"  :")
        for st in stages:
            if isinstance(st, dict):
                name  = st.get("stage", "?")
                total = st.get("total", "?")
                print(f"    {name:<40}: {total} ")

    #  Top 3
    tops = result.get("top_epitopes", [])
    high = [e for e in tops if str(e.get("risk","")).upper() == "HIGH"][:3]
    if high:
        print(f"   (Top {len(high)}):")
        for e in high:
            print(f"    {e.get('peptide','?'):<18} chain={e.get('chain','?')} "
                  f"region={e.get('region','?')} alleles={e.get('n_alleles','?')}")

    # 
    surf_risk = result.get("surface_risk")
    if surf_risk:
        sf = ok("✅ LOW") if "low" in str(surf_risk).lower() else warn(f"⚠️ {surf_risk}")
        print(f"  :    {sf}")
        print(f"  :      {result.get('n_hydrophilic_patches', 0)}  "
              f": {result.get('n_hydrophobic_patches', 0)}")


def _print_structure_13param(result: Dict) -> None:
    """ structure_13param 。"""
    if result.get("status") in ("SKIPPED", "ERROR", "PLANNED"):
        reason = result.get("reason") or result.get("error") or result.get("note", "")
        print(warn(f"  structure_13param: {result.get('status')} — {reason}"))
        return
    print(f"\n{bold('13 （structure_13param）')}")
    #  result["metrics"] ，（ tap、vernier_dual_numbering ）
    params = result.get("metrics") or {}
    for k, label, threshold in [
        ("vhvl_angle",              "VH/VL  (°)",      5.0),
        ("packing_angle",           " (°)",         None),
        ("fv_rmsd",                 "Fv RMSD (Å)",        1.5),
        ("plddt_mean",              " pLDDT",          None),
        ("plddt_cdr_mean",          "CDR pLDDT",           None),
        ("sasa_total",              " SASA (Å²)",        None),
        ("vhvl_interface_contacts", "VH-VL ",      None),
        ("vh_cdr_contacts",         "VH CDR ",       None),
        ("vl_cdr_contacts",         "VL CDR ",       None),
        ("vernier_dual_numbering_n","Vernier ",      None),
    ]:
        v = params.get(k)
        if v is None and k == "vernier_dual_numbering_n":
            vdn = params.get("vernier_dual_numbering")
            v = len(vdn) if isinstance(vdn, list) else None
        if v is None:
            continue
        val_s = f"{v:.2f}" if isinstance(v, float) else str(v)
        if threshold and isinstance(v, float):
            flag = ok("✅") if v <= threshold else err("❌")
            print(f"  {label:<26}: {val_s}  {flag}")
        else:
            print(f"  {label:<26}: {val_s}")


def _print_tap(result: Dict) -> None:
    """ TAP （）。"""
    if result.get("status") in ("SKIPPED", "ERROR", "PLANNED"):
        print(warn(f"  tap: {result.get('status')} — {result.get('reason', result.get('note', ''))}"))
        return
    print(f"\n{bold('TAP （Therapeutic Antibody Profiler）')}")
    for k, label in [("PSH","PSH — "), ("PPC","PPC — "),
                     ("PNC","PNC — "), ("SFvCSP","SFvCSP — Fv "),
                     ("tap_score","TAP "), ("tap_flag","TAP ")]:
        v = result.get(k)
        if v is not None:
            flag = ok("✅ PASS") if v == "PASS" else (warn("⚠️ WARN") if v == "WARN" else
                   err("❌ FAIL") if v == "FAIL" else "")
            val_s = f"{v:.3f}" if isinstance(v, float) else str(v)
            suffix = f"  {flag}" if k == "tap_flag" else ""
            print(f"  {label:<28}: {val_s}{suffix}")


def _print_delta_vs_mouse(result: Dict) -> None:
    """ delta_vs_mouse （）。"""
    if result.get("status") in ("SKIPPED", "ERROR", "PLANNED"):
        print(warn(f"  delta_vs_mouse: {result.get('status')} — {result.get('reason', result.get('note', ''))}"))
        return
    print(f"\n{bold('（delta_vs_mouse）')}")
    for k, label, threshold in [
        ("vhvl_angle_delta", "VH/VL  (°)", 5.0),
        ("fv_rmsd",          "Fv RMSD (Å)",       1.5),
    ]:
        v = result.get(k)
        if v is not None and isinstance(v, (int, float)):
            flag = ok("✅ PASS") if float(v) <= threshold else err("❌ FAIL")
            print(f"  {label:<26}: {v:.3f}  {flag}")
    cdrs = result.get("cdr_rmsd", {})
    if cdrs:
        print(f"  CDR RMSD:")
        for cdr, rmsd in cdrs.items():
            if isinstance(rmsd, (int, float)):
                f = ok("✅") if float(rmsd) <= 1.0 else err("❌")
                print(f"    {cdr}: {rmsd:.3f} Å  {f}")


def _print_all_seq_struct_modules(results: Dict, has_pdb: bool) -> None:
    """
     /  AbEvaluator 。
    """
    print(bold("\n───  ───────────────────────────────────────────"))
    _print_cdr_scan(results.get("cdr_scan", {"status": "SKIPPED"}))
    _print_developability(results.get("developability", {"status": "SKIPPED"}))
    _print_germline(results.get("germline", {"status": "SKIPPED"}))
    _print_immunogenicity(results.get("immunogenicity", {"status": "SKIPPED"}))

    if has_pdb:
        print(bold("\n───  ───────────────────────────────────────────"))
        _print_structure_13param(results.get("structure_13param", {"status": "SKIPPED"}))
        _print_tap(results.get("tap", {"status": "SKIPPED"}))
        _print_delta_vs_mouse(results.get("delta_vs_mouse", {"status": "SKIPPED"}))


def _run_abevaluator(
    evaluator: "AbEvaluator",
    modules: List[str],
    label: str,
) -> "EvaluationResult":
    """ AbEvaluator  QA 。strict_qa  False。"""
    print(info(f"[AbEvaluator] : {label}"))
    print(info(f"  : {[m for m in modules if m in SEQ_MODULES]}"))
    if any(m in STRUCT_MODULES_BASE + STRUCT_MODULES_VS_MOUSE for m in modules):
        print(info(f"  : {[m for m in modules if m in STRUCT_MODULES_BASE + STRUCT_MODULES_VS_MOUSE]}"))
    result = evaluator.run(modules=modules)
    qa = result.results.get("_qa", {})
    qa_status = qa.get("status", "N/A")
    qa_flag = ok(qa_status) if qa_status in ("PASS", "WARN") else warn(qa_status)
    print(ok(f"  ✅ AbEvaluator  | QA : {qa_flag} "
             f"(n_pass={qa.get('n_pass',0)}, n_warn={qa.get('n_warn',0)}, n_fail={qa.get('n_fail',0)})"))
    return result


def run(args: argparse.Namespace) -> int:
    """
    。 0=, 1=, 2=。

    :
      AbEvaluator.run()   ← （ QA ）
      optimization_pipeline  ←  +  + 
    """
    print(bold("\n╔══════════════════════════════════════════════════════════════╗"))
    print(bold("║   AbEngineCore CMC                            ║"))
    print(bold("║   : AbEvaluator.run()                             ║"))
    print(bold("║   : optimization_pipeline._run_optimization_pipeline  ║"))
    print(bold("╚══════════════════════════════════════════════════════════════╝\n"))

    # Evidence Gate — pre-flight knowledge check
    _evidence_ctx = None
    try:
        from core.resources.evidence_gate import EvidenceGate, print_evidence_banner
        _gate = EvidenceGate(enable_network=False)
        ab_label = args.antibody_id or args.project or ""
        _evidence_ctx = _gate.check(antibody_name=ab_label)
        print_evidence_banner(_evidence_ctx)
    except Exception as e:
        print(f"[CMC-Opt] Evidence gate skipped: {e}", flush=True)

    # ──  A:  /  ──────────────────────────────────────────────
    vh_seq: Optional[str] = args.vh
    vl_seq: Optional[str] = args.vl
    project_dir: Optional[Path] = None
    pdbs: Dict[str, Optional[Path]] = {}

    if args.project:
        print(info(f"[] : '{args.project}'"))
        project_dir = _discover_project(args.project)
        if project_dir:
            # （）
            all_candidates = [
                p for p in (_SUITE_ROOT / "projects").iterdir()
                if p.is_dir() and all(t in p.name.lower() for t in
                    [tok.lower() for tok in args.project.replace("-","_").replace(" ","_").split("_") if tok])
            ]
            if len(all_candidates) > 1:
                print(warn(f"  (: {[c.name for c in all_candidates]})"))
                print(warn(f"  (: ， 'mumab4d5 spliced')"))
            print(ok(f"  ✅ : {project_dir.name}"))
        else:
            print(err(f"  ❌  '{args.project}'"))
            print(f"  : {[p.name for p in (_SUITE_ROOT / 'projects').iterdir() if p.is_dir()]}")
            return 1

        # 
        if not (vh_seq and vl_seq):
            print(info("[] ..."))
            vh_seq, vl_seq = _discover_sequences(project_dir)
            if vh_seq and vl_seq:
                print(ok(f"  ✅ VH: {len(vh_seq)} aa, VL: {len(vl_seq)} aa"))
            else:
                print(err("  ❌ ， --vh / --vl "))
                return 1

        #  PDB
        print(info("[]  PDB ..."))
        pdbs = _discover_pdbs(project_dir)
        for k, v in pdbs.items():
            status = ok(f"✅ {v.name}") if v else warn("")
            print(f"  {k:<16}: {status}")

    elif not (vh_seq and vl_seq):
        print(err(":  (--project)  (--vh --vl)"))
        return 1

    antibody_id = args.antibody_id or (project_dir.name if project_dir else "antibody")

    # 
    if args.out:
        out_dir = Path(args.out)
    elif project_dir:
        out_dir = project_dir / "cmc_optimization"
    else:
        out_dir = _SUITE_ROOT / "cmc_optimization_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(info(f"\n[] : {out_dir}"))

    import json as _json
    ref_stats = _json.loads((_SUITE_ROOT / "data" / "reference" / "AbRef458_stats_v1.json").read_text())

    # ──  B:  — AbEvaluator () ────────────────────────
    has_pdb     = bool(pdbs.get("humanized_v2"))
    has_ref_pdb = bool(pdbs.get("mouse"))
    eval_modules = _build_eval_modules(has_pdb, has_ref_pdb)

    print(info(f"\n[ 1/4] AbEvaluator —  ()"))
    print(info(f"   ({len([m for m in eval_modules if m in SEQ_MODULES])}): "
               f"{[m for m in eval_modules if m in SEQ_MODULES]}"))
    if has_pdb:
        struct_mods = [m for m in eval_modules if m in STRUCT_MODULES_BASE + STRUCT_MODULES_VS_MOUSE]
        print(info(f"   ({len(struct_mods)}): {struct_mods}"))
    orig_evaluator = _make_evaluator(
        antibody_id, vh_seq, vl_seq,
        pdb_path     = pdbs.get("humanized_v2"),
        ref_pdb_path = pdbs.get("mouse"),
    )
    orig_eval_result = _run_abevaluator(orig_evaluator, eval_modules, "")

    orig_cmc = orig_eval_result.results.get("cmc_advisor", {})

    # 
    print(bold("\n══════════════════════  (via AbEvaluator) ══════════════════════"))

    # 1. 15  CMC
    _print_metrics_table(orig_cmc.get("metrics", {}), f"■ CMC  — {antibody_id} ", ref_stats)
    orig_adi = float(orig_cmc.get("ADI") or orig_cmc.get("adi") or 0.0)
    orig_fail = len([m for m in orig_cmc.get("metrics", {}).values()
                     if isinstance(m, dict) and m.get("gate") == "FAIL"])
    orig_warn = len([m for m in orig_cmc.get("metrics", {}).values()
                     if isinstance(m, dict) and m.get("gate") == "WARN"])
    orig_adi_str = bold(f"{orig_adi:.1f}")
    print(f"\n  ADI: {orig_adi_str}  FAIL={orig_fail}  WARN={orig_warn}")

    # 2.  + 
    _print_all_seq_struct_modules(orig_eval_result.results, has_pdb)

    if orig_cmc.get("mutation_suggestions"):
        sug = orig_cmc["mutation_suggestions"]
        print(f"\n{bold('■ FR ')} ({len(sug)} ):")
        for s in sug[:5]:
            print(f"  • {s.get('chain','?')}{s.get('kabat_pos') or s.get('position','?')} "
                  f"{s.get('original','?')}→{s.get('suggested','?')}: {s.get('reason','')}")

    if args.mode == "evaluate":
        return 0

    # ──  C:  — mutation generation + structural fidelity ─────────
    print(info(f"\n[ 2/4] : optimization_pipeline._run_optimization_pipeline()"))
    print(info(f"  (； +  + )"))

    #  AbEvaluator  CMC （）
    stored_cache_key = f"{vh_seq}|{vl_seq}"
    # optimization_pipeline  metric ， band/gate 
    raw_metrics_for_cache = {}
    for k, v in orig_cmc.get("metrics", {}).items():
        if isinstance(v, dict) and "value" in v:
            raw_metrics_for_cache[k] = v["value"]
        elif not isinstance(v, dict):
            raw_metrics_for_cache[k] = v
    metrics_cache = {stored_cache_key: raw_metrics_for_cache}

    from core.cmc.optimization_pipeline import _run_optimization_pipeline
    opt_result = _run_optimization_pipeline(
        vh_seq       = vh_seq,
        vl_seq       = vl_seq,
        mouse_pdb    = pdbs.get("mouse"),
        initial_pdb  = pdbs.get("humanized_v2"),
        metrics_cache= metrics_cache,
        output_dir   = out_dir,
        antibody_id  = antibody_id,
    )

    all_variants = opt_result.get("variants", [])
    best_raw = opt_result.get("best_variant")

    # ：， AbEvaluator  FR 
    if best_raw is None and args.relaxed:
        suggestions = orig_cmc.get("mutation_suggestions", [])
        if all_variants:
            best_raw = max(all_variants, key=lambda v: v.get("adi", 0))
            print(warn(f"\n⚠️  ，（ opt_pipeline）"))
        elif suggestions:
            #  AbEvaluator 
            best_sug = suggestions[0]
            chain = best_sug.get("chain", "")
            seq_pos = best_sug.get("seq_pos")
            new_aa  = best_sug.get("suggested", "")
            if seq_pos is not None and new_aa and chain in ("VH", "H", "VL", "L"):
                seq_pos = int(seq_pos)
                if chain in ("VH", "H"):
                    opt_vh = vh_seq[:seq_pos] + new_aa + vh_seq[seq_pos + 1:]
                    opt_vl = vl_seq
                else:
                    opt_vh = vh_seq
                    opt_vl = vl_seq[:seq_pos] + new_aa + vl_seq[seq_pos + 1:]
                best_raw = {
                    "vh": opt_vh, "vl": opt_vl,
                    "mutations": [best_sug],
                    "adi": None,
                    "structural_fidelity": {},
                }
                print(warn(f"\n⚠️  ，:"))
                print(warn(f"  {chain}{best_sug.get('kabat_pos') or seq_pos} "
                           f"{best_sug.get('original','?')}→{new_aa}"))

    # ──  D:  — AbEvaluator () ──────────────────────
    if best_raw:
        opt_vh = best_raw["vh"]
        opt_vl = best_raw["vl"]
        opt_pdb_path = best_raw.get("optimized_pdb_path")

        print(info(f"\n[ 3/4] AbEvaluator —  ()"))
        muts = best_raw.get("mutations", [])
        print(f"  : " + (", ".join(
            f"{m.get('chain','?')}{m.get('kabat_pos') or m.get('position','?')} "
            f"{m.get('original','?')}→{m.get('suggested','?')}"
            for m in muts
        ) or ""))

        opt_evaluator = _make_evaluator(
            f"{antibody_id}_optimized",
            opt_vh, opt_vl,
            pdb_path     = Path(opt_pdb_path) if opt_pdb_path else pdbs.get("humanized_v2"),
            ref_pdb_path = pdbs.get("mouse"),
        )
        opt_eval_result = _run_abevaluator(
            opt_evaluator, ["cmc_advisor"], ""
        )
        opt_cmc = opt_eval_result.results.get("cmc_advisor", {})

        print(bold("\n══════════════════════  (via AbEvaluator) ══════════════════════"))
        _print_metrics_table(opt_cmc.get("metrics", {}), f"■ CMC  — {antibody_id} ", ref_stats)
        opt_adi = float(opt_cmc.get("ADI") or opt_cmc.get("adi") or best_raw.get("adi") or 0.0)
        opt_fail = len([m for m in opt_cmc.get("metrics", {}).values()
                        if isinstance(m, dict) and m.get("gate") == "FAIL"])
        opt_warn = len([m for m in opt_cmc.get("metrics", {}).values()
                        if isinstance(m, dict) and m.get("gate") == "WARN"])
        best_adi_str = bold(f"{opt_adi:.1f}")
        print(f"\n  ADI: {best_adi_str}  FAIL={opt_fail}  WARN={opt_warn}")

        #  + 
        opt_has_pdb = bool(opt_pdb_path)
        _print_all_seq_struct_modules(opt_eval_result.results, opt_has_pdb)

        # Before / After CMC 
        _print_comparison(
            orig_cmc.get("metrics", {}), opt_cmc.get("metrics", {}),
            orig_adi, opt_adi, ref_stats
        )

        # QA 
        orig_qa = orig_eval_result.results.get("_qa", {})
        opt_qa  = opt_eval_result.results.get("_qa", {})
        print(f"\n{bold('QA  (AbEvaluator._qa)')}:")
        print(f"  : status={orig_qa.get('status','?')}, "
              f"pass={orig_qa.get('n_pass',0)}, warn={orig_qa.get('n_warn',0)}, fail={orig_qa.get('n_fail',0)}")
        print(f"  : status={opt_qa.get('status','?')}, "
              f"pass={opt_qa.get('n_pass',0)}, warn={opt_qa.get('n_warn',0)}, fail={opt_qa.get('n_fail',0)}")

        # ──  E:  ────────────────────────────────────────────────
        print(info(f"\n[ 4/4] "))
        sf = best_raw.get("structural_fidelity") or opt_result.get("structural_fidelity") or {}
        print(bold("\n══════════════════════  (via optimization_pipeline) ══════════════════════"))
        _print_structural_fidelity(sf)

        #  JSON
        opt_json_out = out_dir / f"{antibody_id}_optimized_abevaluator_result.json"
        with open(opt_json_out, "w", encoding="utf-8") as f:
            json.dump(opt_eval_result.results, f, indent=2, default=str, ensure_ascii=False)
        print(info(f"\n  💾  AbEvaluator : {opt_json_out}"))

        deliverable = (
            opt_fail == 0 and opt_warn <= 1 and opt_adi >= 60
            and not sf.get("structural_warning", False)
            and not sf.get("error")
        )
    else:
        deliverable = False
        n_suggested = opt_result.get("suggestions_filtered", 0)
        print(warn(f"\n⚠️   ({n_suggested} )"))
        if n_suggested == 0:
            print(warn("  :  CDR/Vernier "))
        else:
            print(warn("  :  --relaxed "))
        print(info("  : SAP/Fv_charge_asymmetry （，）"))
        print(info("        agg_motifs  SASA ，"))

    # ──  ─────────────────────────────────────────────────────────────
    print(bold("\n══════════════════════  ══════════════════════"))
    print(f"  : AbEvaluator() → optimization_pipeline → AbEvaluator()")
    if deliverable:
        print(ok("  ✅  (DELIVERABLE)"))
        print(ok("     FAIL=0, WARN≤1, ADI≥60, "))
    else:
        print(warn("  ⚠️   (CONDITIONAL)"))
        reasons = []
        if best_raw:
            if opt_fail > 0:
                reasons.append(f"FAIL={opt_fail} ()")
            if opt_warn > 1:
                reasons.append(f"WARN={opt_warn}")
            if opt_adi < 60:
                reasons.append(f"ADI={opt_adi:.1f} < 60")
            sf = best_raw.get("structural_fidelity") or {}
            if sf.get("structural_warning") or sf.get("error"):
                reasons.append("")
        else:
            reasons.append("")
        for r in reasons:
            print(warn(f"     • {r}"))
        print(warn("  :  SEC-HPLC "))

    # ──  Phase 4: （ --ref-vh/--ref-vl）─────────────────
    ref_eval_result = None
    ref_vh = getattr(args, "ref_vh", None)
    ref_vl = getattr(args, "ref_vl", None)
    ref_name = getattr(args, "ref_name", None) or ""
    ref_pdb_arg = getattr(args, "ref_pdb", None)

    if ref_vh and ref_vl:
        print(bold(f"\n══════════════════════ Phase 4 — : {ref_name} ══════════════════════"))
        ref_pdb_path = Path(ref_pdb_arg) if ref_pdb_arg and Path(ref_pdb_arg).exists() else None
        ref_evaluator = _make_evaluator(
            f"{antibody_id}_reference",
            ref_vh.strip().upper(), ref_vl.strip().upper(),
            pdb_path=ref_pdb_path,
        )
        ref_modules = list(SEQ_MODULES) + (list(STRUCT_MODULES_BASE) if ref_pdb_path else [])
        ref_modules.append("cmc_advisor")
        ref_eval_result = _run_abevaluator(ref_evaluator, ref_modules, f": {ref_name}")
        ref_cmc = ref_eval_result.results.get("cmc_advisor", {})
        _print_metrics_table(ref_cmc.get("metrics", {}), f"■ CMC — {ref_name}", ref_stats)
        ref_adi = float(ref_cmc.get("ADI") or ref_cmc.get("adi") or 0.0)
        print(f"  {ref_name} ADI: {bold(f'{ref_adi:.1f}')}")

        # EvaluationComparison 
        if best_raw:
            print(bold(f"\n── 4  ──"))
            from core.evaluation.evaluator import EvaluationComparison
            comp = EvaluationComparison(
                original=orig_eval_result,
                optimized=opt_eval_result,
                reference=ref_eval_result,
                original_label=f"{antibody_id} ()",
                optimized_label=f"{antibody_id} ()",
                reference_label=ref_name,
            )
            print(comp.summary_text())

        #  JSON
        ref_json_out = out_dir / f"{antibody_id}_reference_{ref_name.replace(' ', '_')}_abevaluator.json"
        with open(ref_json_out, "w", encoding="utf-8") as f:
            json.dump(ref_eval_result.results, f, indent=2, default=str, ensure_ascii=False)
        print(info(f"\n  💾 : {ref_json_out.name}"))
    else:
        if not any([ref_vh, ref_vl]):
            print(info("\n[Phase 4]  --ref-vh/--ref-vl，。"))
            print(info("  :  --ref-vh SEQ --ref-vl SEQ --ref-name ''  4 "))

    # ──  & JSON  ──────────────────────────────────────────────────────
    #  JSON（）
    opt_pipeline_json = out_dir / f"{antibody_id}_opt_pipeline_result.json"
    with open(opt_pipeline_json, "w", encoding="utf-8") as f:
        json.dump(opt_result, f, indent=2, default=str, ensure_ascii=False)

    #  AbEvaluator JSON
    orig_json = out_dir / f"{antibody_id}_abevaluator_orig_result.json"
    with open(orig_json, "w", encoding="utf-8") as f:
        json.dump(orig_eval_result.results, f, indent=2, default=str, ensure_ascii=False)

    # ──  ──────────────────────────────────────────────────────
    from datetime import datetime as _dt
    _today = _dt.now().strftime("%Y-%m-%d")
    client_name = getattr(args, "client_name", "") or ""
    no_client_report = getattr(args, "no_client_report", False)

    # 1. （Markdown）— 4 section structure
    tech_md_lines = [
        f"# CMC  — {antibody_id}",
        f"",
        f"****: {_today}  ",
        f"****: AbEvaluator → optimization_pipeline → AbEvaluator → EvaluationComparison  ",
        f"",
        "---",
        "",
        "## 、 15 ",
        "",
    ]
    orig_cmc_report = orig_eval_result.results.get("cmc_advisor", {})
    orig_adi_val = float(orig_cmc_report.get("ADI") or orig_cmc_report.get("adi") or orig_adi)
    tech_md_lines.append(f"**ADI**: {orig_adi_val:.1f}")
    tech_md_lines.append("")
    tech_md_lines.append("|  |  |  |  |")
    tech_md_lines.append("|---|---|---|---|")
    for m, mv in orig_cmc_report.get("annotated", {}).items():
        if not isinstance(mv, dict):
            continue
        v = mv.get("value", "—")
        if isinstance(v, list):
            v = len(v)
        tech_md_lines.append(f"| {mv.get('label', m)} | {v} | {mv.get('percentile_band','—')} | {mv.get('gate','—')} |")
    tech_md_lines.append("")

    # Optimization section
    tech_md_lines += [
        "---",
        "",
        "## 、",
        "",
    ]
    if best_raw:
        muts = best_raw.get("mutations", [])
        if muts:
            tech_md_lines.append("|  |  |  →  |  |")
            tech_md_lines.append("|---|---|---|---|")
            for m in muts:
                chain = m.get("chain", "?")
                pos   = m.get("kabat_pos") or m.get("position", "?")
                orig_aa = m.get("original", "?")
                new_aa  = m.get("suggested", "?")
                reason  = m.get("reason", "")
                tech_md_lines.append(f"| {chain} | {pos} | {orig_aa}→{new_aa} | {reason} |")
            tech_md_lines.append("")
        else:
            tech_md_lines.append(" FR （ CDR/Vernier ）。")
            tech_md_lines.append("")
    else:
        tech_md_lines.append("。")
        tech_md_lines.append("")

    # Re-assessment section
    tech_md_lines += [
        "---",
        "",
        "## 、 15 ",
        "",
    ]
    if best_raw:
        opt_cmc_report = opt_eval_result.results.get("cmc_advisor", {})
        opt_adi_val = float(opt_cmc_report.get("ADI") or opt_cmc_report.get("adi") or opt_adi)
        tech_md_lines.append(f"**ADI**: {opt_adi_val:.1f} (: {orig_adi_val:.1f}, Δ = {opt_adi_val - orig_adi_val:+.1f})")
        tech_md_lines.append("")
        tech_md_lines.append("|  |  |  |  |  |")
        tech_md_lines.append("|---|---|---|---|---|")
        orig_ann = orig_cmc_report.get("annotated", {})
        opt_ann  = opt_cmc_report.get("annotated", {})
        for m in orig_ann:
            ov = orig_ann[m].get("value")
            nv = opt_ann.get(m, {}).get("value")
            if isinstance(ov, list): ov = len(ov)
            if isinstance(nv, list): nv = len(nv)
            try:
                delta_s = f"{float(nv) - float(ov):+.3f}" if ov is not None and nv is not None else "—"
            except (TypeError, ValueError):
                delta_s = "—"
            gate = opt_ann.get(m, {}).get("gate", "—")
            lbl  = orig_ann[m].get("label", m)
            tech_md_lines.append(f"| {lbl} | {ov} | {nv} | {delta_s} | {gate} |")
        tech_md_lines.append("")
    else:
        tech_md_lines.append("（）")
        tech_md_lines.append("")

    # Clinical comparison section
    tech_md_lines += [
        "---",
        "",
        f"## 、（{ref_name}）",
        "",
    ]
    if ref_eval_result and best_raw:
        from core.evaluation.evaluator import EvaluationComparison as _EC
        comp2 = _EC(
            original=orig_eval_result,
            optimized=opt_eval_result,
            reference=ref_eval_result,
            original_label=f"{antibody_id}()",
            optimized_label=f"{antibody_id}()",
            reference_label=ref_name,
        )
        tech_md_lines.append(comp2.summary_text())
        tech_md_lines.append("")
    elif ref_eval_result:
        ref_cmc2 = ref_eval_result.results.get("cmc_advisor", {})
        tech_md_lines.append(f"**{ref_name} ADI**: {float(ref_cmc2.get('ADI') or ref_cmc2.get('adi') or 0.0):.1f}")
        tech_md_lines.append("")
        tech_md_lines.append("（，）")
        tech_md_lines.append("")
    else:
        tech_md_lines.append("（ —  --ref-vh/--ref-vl ）")
        tech_md_lines.append("")

    tech_md_lines += [
        "---",
        "",
        "## ：QA ",
        "",
        f"|  | QA  | PASS | WARN | FAIL |",
        "|---|---|---|---|---|",
    ]
    for phase_label, ev_result in [
        ("", orig_eval_result),
        ("", opt_eval_result if best_raw else None),
        (ref_name, ref_eval_result),
    ]:
        if ev_result is None:
            continue
        qa = ev_result.results.get("_qa", {})
        tech_md_lines.append(
            f"| {phase_label} | {qa.get('status','—')} "
            f"| {qa.get('n_pass',0)} | {qa.get('n_warn',0)} | {qa.get('n_fail',0)} |"
        )
    tech_md_lines += [
        "",
        f"* InSynBio AbEngineCore  — {_today}*",
    ]

    tech_md_path = out_dir / f"{antibody_id}_CMC_TECHNICAL_REPORT.md"
    tech_md_path.write_text("\n".join(tech_md_lines), encoding="utf-8")
    print(info(f"  📄  (Markdown): {tech_md_path.name}"))

    # 2. （ 4 ）
    if not no_client_report:
        try:
            from core.evaluation.client_report import write_client_report as _wcr
            _wcr(
                orig_eval_result,
                out_dir / f"{antibody_id}_CLIENT_REPORT.md",
                ref_result=ref_eval_result,
                ab_name=antibody_id,
                ref_name=ref_name,
                client_name=client_name,
                project_id=antibody_id,
                date_str=_today,
            )
        except Exception as _e:
            print(warn(f"  ⚠️  : {_e}"))

    # ──  PDF  ─────────────────────────────────────────────────────────
    if getattr(args, "pdf", False):
        try:
            _sys_path = str(Path(__file__).resolve().parent)
            if _sys_path not in sys.path:
                sys.path.insert(0, _sys_path)
            from md_to_pdf import batch_convert as _bc
            md_targets = [str(tech_md_path)]
            if not no_client_report:
                _cr = out_dir / f"{antibody_id}_CLIENT_REPORT.md"
                if _cr.exists():
                    md_targets.append(str(_cr))
            results = _bc(md_targets)
            for _, pdf_p, ok in results:
                if ok and pdf_p:
                    print(info(f"  📑 PDF: {Path(pdf_p).name}"))
                elif not ok:
                    print(warn(f"  ⚠️  PDF : {pdf_p}"))
        except Exception as _pdf_e:
            print(warn(f"  ⚠️  PDF : {_pdf_e}"))

    print(info(f"\n  📁 : {out_dir}"))
    print(info(f"  📄  (JSON): {orig_json.name}"))
    print(info(f"  📄  (JSON): {opt_pipeline_json.name}"))
    if best_raw:
        print(info(f"  📄  (JSON): {antibody_id}_optimized_abevaluator_result.json"))
    print(info(f"  📄 : {tech_md_path.name}"))
    if not no_client_report:
        print(info(f"  📄 : {antibody_id}_CLIENT_REPORT.md"))
    print()

    final_code = 0 if deliverable else 2

    # Self-Evolution: emit RunEvent
    try:
        from core.evolution.event_collector import EventCollector
        _collector = EventCollector()
        _run_event = _collector.from_evidence_gate(
            project_id=antibody_id,
            family="cmc_optimization",
            entrypoint="cmc_optimize_pipeline.py",
            evidence_ctx=_evidence_ctx,
            exit_code=final_code,
        )
        _run_event.report_generated = not no_client_report
        _collector.emit(_run_event)
    except Exception:
        pass

    return final_code


# ─────────────────────────────────────────────────────────────────────────────
# 4. CLI 
# ─────────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cmc_optimize_pipeline",
        description=textwrap.dedent("""\
            AbEngineCore CMC  — 

            : AbEvaluator.run()  ←  + 
            :    optimization_pipeline  ←  +  + 
            : AbEvaluator → opt_pipeline → AbEvaluator → 
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            :
              #  — 
              python scripts/cmc_optimize_pipeline.py mumab4d5

              # 
              python scripts/cmc_optimize_pipeline.py mumab4d5 --mode evaluate

              # （）
              python scripts/cmc_optimize_pipeline.py mumab4d5 --mode full

              # 
              python scripts/cmc_optimize_pipeline.py mumab4d5 \\
                  --vh EVQLLESGGGLVQ... --vl DIQMTQSPSSLSA...
        """),
    )

    p.add_argument(
        "project",
        nargs="?",
        help="（， 'mumab4d5', 'muMAb4D5 v2', 'pdl1'）",
    )
    p.add_argument(
        "--vh", metavar="SEQ",
        help="VH （）",
    )
    p.add_argument(
        "--vl", metavar="SEQ",
        help="VL （）",
    )
    p.add_argument(
        "--mode", choices=["evaluate", "optimize", "full"],
        default="full",
        help=": evaluate=, optimize=, full=（）",
    )
    p.add_argument(
        "--antibody-id", dest="antibody_id", metavar="ID",
        help="（，）",
    )
    p.add_argument(
        "--out", metavar="DIR",
        help="（: <project_dir>/cmc_optimization/）",
    )
    p.add_argument(
        "--mouse-pdb", dest="mouse_pdb", metavar="PATH",
        help=" PDB（）",
    )
    p.add_argument(
        "--init-pdb", dest="init_pdb", metavar="PATH",
        help=" PDB（）",
    )
    p.add_argument(
        "--relaxed", action="store_true",
        help=": （ ADI≥60 + FAIL=0 ）",
    )

    # ── Phase 4: clinical reference comparison ────────────────────────────────
    ref_group = p.add_argument_group(
        "Phase 4 — （）",
        " VH/VL  4 。",
    )
    ref_group.add_argument(
        "--ref-vh", metavar="SEQ",
        help=" VH （ trastuzumab）",
    )
    ref_group.add_argument(
        "--ref-vl", metavar="SEQ",
        help=" VL ",
    )
    ref_group.add_argument(
        "--ref-name", metavar="NAME", default="",
        help="（，：）",
    )
    ref_group.add_argument(
        "--ref-pdb", metavar="PATH",
        help=" PDB （，）",
    )

    # ── Report options ────────────────────────────────────────────────────────
    report_group = p.add_argument_group("")
    report_group.add_argument(
        "--client-name", metavar="NAME", default="",
        help="（）",
    )
    report_group.add_argument(
        "--no-client-report", action="store_true",
        help="（ JSON  Markdown）",
    )
    report_group.add_argument(
        "--pdf", action="store_true",
        help=" Markdown  PDF（ fpdf2  msyh.ttc ）",
    )
    return p


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    #  PDB （）
    if not hasattr(args, "_pdbs"):
        args._pdbs = {}

    return run(args)


if __name__ == "__main__":
    sys.exit(main())
