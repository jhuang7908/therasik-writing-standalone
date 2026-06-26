#!/usr/bin/env python3
"""
Phase 4.5 — Structure QC for petization.

Predicts Fv structure (ImmuneBuilder or IgFold) for the petized VH+VL sequences,
then runs RMSD / VH-VL angle / free-Cys checks via analyze_structure.

Priority per project convention:
  - Single antibody → ImmuneBuilder (ABodyBuilder2) via subprocess
  - Batch / fallback  → IgFold direct import

Returns a structured dict for inclusion in result["_qa_audit"]["structure_qc"].
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

# CDR RMSD pass thresholds (Å)
CDR_RMSD_THRESHOLD = {"H1": 1.5, "H2": 1.5, "H3": 2.0, "L1": 1.5, "L2": 1.5, "L3": 2.0}
# VH-VL angle tolerance (± degrees from reference or expected range 40-70°)
VH_VL_ANGLE_RANGE = (35.0, 75.0)


# ---------------------------------------------------------------------------
# Structure prediction helpers
# ---------------------------------------------------------------------------

def _predict_immunebuilder(vh: str, vl: Optional[str], out_pdb: Path) -> Dict[str, Any]:
    """Predict Fv via ABodyBuilder2 (or NanoBodyBuilder2) in a subprocess."""
    model_type = "abody" if vl else "nanobody"
    payload = {"out_path": str(out_pdb), "H": vh, "model_type": model_type}
    if vl:
        payload["L"] = vl
    tmp_json = out_pdb.parent / (out_pdb.stem + "_payload.json")
    tmp_json.write_text(json.dumps(payload), encoding="utf-8")
    predict_script = SUITE / "scripts" / "predict_one_immunebuilder.py"
    try:
        result = subprocess.run(
            [sys.executable, str(predict_script), "--json", str(tmp_json)],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            return {
                "success": False,
                "tool": "ImmuneBuilder",
                "error": result.stderr.strip()[-500:] or result.stdout.strip()[-200:],
            }
        if not out_pdb.is_file():
            return {"success": False, "tool": "ImmuneBuilder", "error": "PDB not written"}
        return {"success": True, "tool": "ImmuneBuilder", "pdb": str(out_pdb)}
    except subprocess.TimeoutExpired:
        return {"success": False, "tool": "ImmuneBuilder", "error": "timeout (300s)"}
    except Exception as e:
        return {"success": False, "tool": "ImmuneBuilder", "error": str(e)}
    finally:
        try:
            tmp_json.unlink(missing_ok=True)
        except Exception:
            pass


def _predict_igfold(vh: str, vl: str, out_pdb: Path) -> Dict[str, Any]:
    """Predict Fv via IgFold (direct import, batch-friendly)."""
    try:
        import sys as _sys
        # Apply known compatibility fixes before import
        _fixes_script = SUITE / "scripts" / "run_igfold_fab_bispecific.py"
        if _fixes_script.is_file():
            import importlib.util
            spec = importlib.util.spec_from_file_location("_igfold_fab", str(_fixes_script))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            try:
                mod._apply_torch_weights_only_fix()
                mod._apply_transformers_trie_fix()
                mod._install_anarci_shim()
            except Exception:
                pass
        from igfold import IgFoldRunner
        out_pdb.parent.mkdir(parents=True, exist_ok=True)
        runner = IgFoldRunner()
        runner.fold(str(out_pdb), sequences={"H": vh, "L": vl}, do_refine=False, do_renum=True)
        if not out_pdb.is_file():
            return {"success": False, "tool": "IgFold", "error": "PDB not written"}
        return {"success": True, "tool": "IgFold", "pdb": str(out_pdb)}
    except ImportError:
        return {"success": False, "tool": "IgFold", "error": "IgFold not installed"}
    except Exception as e:
        return {"success": False, "tool": "IgFold", "error": str(e)}


def predict_fv_structure(
    vh: str,
    vl: Optional[str],
    out_dir: Path,
    label: str,
    prefer_immunebuilder: bool = True,
) -> Dict[str, Any]:
    """
    Predict Fv structure, trying ImmuneBuilder first (if prefer_immunebuilder),
    then IgFold as fallback.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_pdb = out_dir / f"{label}_fv_predicted.pdb"

    if prefer_immunebuilder:
        res = _predict_immunebuilder(vh, vl, out_pdb)
        if res["success"]:
            return res
        fallback_err = res.get("error", "")
        res2 = _predict_igfold(vh, vl, out_pdb)
        if res2["success"]:
            res2["fallback_from"] = "ImmuneBuilder"
            res2["fallback_reason"] = fallback_err
            return res2
        return {
            "success": False,
            "tool": "none",
            "error": f"ImmuneBuilder: {fallback_err} | IgFold: {res2.get('error')}",
        }
    else:
        res = _predict_igfold(vh, vl, out_pdb)
        if res["success"]:
            return res
        fallback_err = res.get("error", "")
        res2 = _predict_immunebuilder(vh, vl, out_pdb)
        if res2["success"]:
            res2["fallback_from"] = "IgFold"
            res2["fallback_reason"] = fallback_err
            return res2
        return {
            "success": False,
            "tool": "none",
            "error": f"IgFold: {fallback_err} | ImmuneBuilder: {res2.get('error')}",
        }


# ---------------------------------------------------------------------------
# RMSD helpers
# ---------------------------------------------------------------------------

def _cdr_ca_rmsd(pdb_a: Path, pdb_b: Path, chain_vh: str = "H", chain_vl: str = "L") -> Dict[str, Any]:
    """
    Compute per-CDR CA RMSD between two Fv PDBs.
    Returns dict: {"H1": float, ...} for available CDRs, plus "errors" list.
    Requires BioPython + ANARCI.
    """
    try:
        import numpy as np
        from Bio.PDB import PDBParser

        try:
            import anarci
        except ImportError:
            return {"errors": ["ANARCI not available; CDR RMSD skipped"]}

        KABAT_CDR_VH = {"H1": (26, 35), "H2": (50, 65), "H3": (95, 102)}
        KABAT_CDR_VL = {"L1": (24, 34), "L2": (50, 56), "L3": (89, 97)}

        def _seq_and_res(chain_obj) -> tuple:
            seq, res = [], []
            for r in chain_obj.get_residues():
                if r.id[0] != " ":
                    continue
                try:
                    from Bio.PDB.Polypeptide import is_aa
                    from Bio.SeqUtils import seq1
                    if is_aa(r, standard=True):
                        seq.append(seq1(r.resname))
                        res.append(r)
                except Exception:
                    pass
            return "".join(seq), res

        def _cdr_indices(num_list, cdr_ranges) -> Dict[str, list]:
            idx_map: Dict[str, list] = {k: [] for k in cdr_ranges}
            for idx, ((pos, ins), aa) in enumerate(num_list):
                if aa == "-":
                    continue
                for name, (lo, hi) in cdr_ranges.items():
                    if lo <= pos <= hi:
                        idx_map[name].append(idx)
                        break
            return idx_map

        parser = PDBParser(QUIET=True)
        sa = parser.get_structure("a", str(pdb_a))[0]
        sb = parser.get_structure("b", str(pdb_b))[0]

        results: Dict[str, Any] = {}
        errors: list = []

        for chain_id, cdr_ranges, chain_label in [
            (chain_vh, KABAT_CDR_VH, "H"),
            (chain_vl, KABAT_CDR_VL, "L"),
        ]:
            if chain_id not in sa or chain_id not in sb:
                errors.append(f"Chain {chain_id} missing in one of the PDBs")
                continue
            seq_a, res_a = _seq_and_res(sa[chain_id])
            seq_b, res_b = _seq_and_res(sb[chain_id])
            if not seq_a or not seq_b:
                errors.append(f"Empty sequence for chain {chain_id}")
                continue
            try:
                num_a_raw, _, _ = anarci.anarci([(chain_label, seq_a)], scheme="kabat")
                num_b_raw, _, _ = anarci.anarci([(chain_label, seq_b)], scheme="kabat")
                num_a = num_a_raw[0][0][0] if num_a_raw and num_a_raw[0][0] else []
                num_b = num_b_raw[0][0][0] if num_b_raw and num_b_raw[0][0] else []
            except Exception as e:
                errors.append(f"ANARCI chain {chain_id}: {e}")
                continue
            idx_a = _cdr_indices(num_a, cdr_ranges)
            idx_b = _cdr_indices(num_b, cdr_ranges)
            for cdr_name in cdr_ranges:
                ia = idx_a.get(cdr_name, [])
                ib = idx_b.get(cdr_name, [])
                if not ia or not ib:
                    continue
                ca_a = [res_a[i]["CA"].coord for i in ia if i < len(res_a) and "CA" in res_a[i]]
                ca_b = [res_b[i]["CA"].coord for i in ib if i < len(res_b) and "CA" in res_b[i]]
                n = min(len(ca_a), len(ca_b))
                if n == 0:
                    continue
                diff = np.array(ca_a[:n]) - np.array(ca_b[:n])
                rmsd = float(np.sqrt((diff ** 2).sum(axis=1).mean()))
                results[cdr_name] = round(rmsd, 3)
        results["errors"] = errors
        return results
    except Exception as e:
        return {"errors": [f"CDR RMSD failed: {e}"]}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_struct_qc(
    vh_petized: str,
    vl_petized: Optional[str],
    out_dir: Path,
    label: str,
    input_pdb: Optional[Path] = None,
    prefer_immunebuilder: bool = True,
    chain_vh: str = "H",
    chain_vl: str = "L",
) -> Dict[str, Any]:
    """
    Full structure QC gate for petization Phase 4.5.

    Steps:
      1. Predict Fv structure of petized sequences
      2. Run VH-VL angle + free-Cys check via analyze_structure
      3. If input_pdb supplied: compute CDR CA RMSD (input vs petized)
      4. Determine overall structure_qc status

    Returns a dict for inclusion in result["_qa_audit"]["structure_qc"].
    """
    qc: Dict[str, Any] = {
        "phase": "4.5_structure_qc",
        "label": label,
        "status": "NOT_RUN",
        "prediction": None,
        "metrics": None,
        "cdr_rmsd": None,
        "flags": [],
        "errors": [],
    }

    # Step 1: Predict structure of petized Fv
    pred = predict_fv_structure(vh_petized, vl_petized, out_dir, label, prefer_immunebuilder)
    qc["prediction"] = {
        "success": pred["success"],
        "tool": pred.get("tool"),
        "pdb": pred.get("pdb"),
        "fallback_from": pred.get("fallback_from"),
        "error": pred.get("error") if not pred["success"] else None,
    }

    if not pred["success"]:
        qc["status"] = "WARN"
        qc["errors"].append(f"Structure prediction failed: {pred.get('error')}")
        qc["flags"].append({"flag": "struct_prediction_failed", "severity": "WARN",
                             "detail": pred.get("error", "")[:200]})
        return qc

    petized_pdb = Path(pred["pdb"])

    # Step 2: VH-VL angle + Vernier packing via existing analyze_structure
    try:
        from scripts.structure_metrics_humanization import analyze_structure, metrics_to_dict
        m = analyze_structure(petized_pdb, chain_vh=chain_vh, chain_vl=chain_vl, skip_sasa=True)
        mdict = metrics_to_dict(m)
        qc["metrics"] = {
            "vh_vl_angle_deg": mdict.get("vh_vl_angle_deg"),
            "interface_n_pairs": mdict.get("interface_n_pairs"),
            "interface_min_dist_A": mdict.get("interface_min_dist_A"),
            "vernier_sasa_total": mdict.get("vernier_sasa_total"),
            "canonical": mdict.get("canonical"),
            "errors": mdict.get("errors", []),
        }
        if m.errors:
            qc["errors"].extend(m.errors)

        # VH-VL angle gate
        angle = mdict.get("vh_vl_angle_deg")
        if angle is not None:
            lo, hi = VH_VL_ANGLE_RANGE
            if not (lo <= angle <= hi):
                qc["flags"].append({
                    "flag": "vh_vl_angle_out_of_range",
                    "severity": "WARN",
                    "detail": f"angle={angle:.1f}° outside expected {lo}–{hi}°",
                })

        # Interface sanity
        n_pairs = mdict.get("interface_n_pairs", 0)
        if isinstance(n_pairs, int) and n_pairs < 5:
            qc["flags"].append({
                "flag": "vhvl_interface_weak",
                "severity": "WARN",
                "detail": f"interface_n_pairs={n_pairs} < 5; check VH-VL packing",
            })

    except Exception as e:
        qc["errors"].append(f"analyze_structure: {e}")
        qc["flags"].append({"flag": "analyze_structure_error", "severity": "WARN", "detail": str(e)[:200]})

    # Free Cys check (sequence-level, fast)
    from core.humanization.kabat_utils import get_kabat_numbering, is_in_cdr, sorted_keys
    chains_to_check = [("VH", vh_petized)]
    if vl_petized:
        chains_to_check.append(("VL", vl_petized))
    
    for chain_label, seq in chains_to_check:
        kd = get_kabat_numbering(seq) or {}
        # Canonical disulfide positions: VH 22–92; VL 23–88 (Kabat)
        canon_cys = {22, 92} if chain_label == "VH" else {23, 88}
        free_cys = []
        for key in sorted_keys(kd):
            pos, ins = key
            if kd[key] == "C" and pos not in canon_cys:
                free_cys.append(f"{chain_label}:{pos}{ins}")
        if free_cys:
            qc["flags"].append({
                "flag": "non_canonical_cys",
                "severity": "WARN",
                "detail": f"Free Cys at {free_cys} — risk of aberrant disulfide",
            })

    # Step 3: CDR RMSD vs input (if input_pdb supplied)
    if input_pdb is not None and input_pdb.is_file():
        rmsd_result = _cdr_ca_rmsd(input_pdb, petized_pdb, chain_vh=chain_vh, chain_vl=chain_vl)
        cdr_errors = rmsd_result.pop("errors", [])
        qc["cdr_rmsd"] = rmsd_result
        if cdr_errors:
            qc["errors"].extend(cdr_errors)
        for cdr, rmsd_val in rmsd_result.items():
            threshold = CDR_RMSD_THRESHOLD.get(cdr)
            if threshold and isinstance(rmsd_val, float) and rmsd_val > threshold:
                qc["flags"].append({
                    "flag": f"cdr_rmsd_high_{cdr}",
                    "severity": "WARN",
                    "detail": f"{cdr} RMSD={rmsd_val:.3f} Å > {threshold} Å threshold",
                })
    elif input_pdb is not None and not input_pdb.is_file():
        qc["errors"].append(f"Input PDB not found for RMSD: {input_pdb}")

    # Determine overall status
    fail_flags = [f for f in qc["flags"] if f["severity"] == "FAIL"]
    warn_flags = [f for f in qc["flags"] if f["severity"] == "WARN"]
    if fail_flags:
        qc["status"] = "FAIL"
    elif warn_flags or qc["errors"]:
        qc["status"] = "WARN"
    else:
        qc["status"] = "PASS"

    return qc
