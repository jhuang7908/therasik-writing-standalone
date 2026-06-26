"""
Build SASA-based structural reference statistics for VHH (n=69) and IgG/Fv (n=73).

Outputs (saved to data/reference/):
  VHH69_sasa_structural_stats_v1.json
  IgG73_sasa_structural_stats_v1.json

Run from repo root with anarcii env:
  conda run -n anarcii python scripts/build_sasa_reference_stats.py

Provenance:
  VHH: data/vhh_structural_union/vhh_structural_union_index.json (n=69)
  IgG: data/design_rules/igg_like_75_immunebuilder_predictions/ (n=73 whole-Fv)
"""
import json, os, sys, math, traceback
from pathlib import Path

# Allow imports from repo root
REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from core.cmc.vhh_cmc_engine import compute_vhh_structural_metrics

# ── helpers ──────────────────────────────────────────────────────────────────

def _percentiles(vals):
    """Compute p5/p25/p50/p75/p95/mean/stdev from a list of floats."""
    v = sorted(x for x in vals if x is not None and math.isfinite(x))
    if not v:
        return None
    n = len(v)
    def _p(pct):
        idx = (pct / 100.0) * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        return round(v[lo] * (1 - frac) + v[hi] * frac, 4)
    mn = sum(v) / n
    var = sum((x - mn) ** 2 for x in v) / n
    return {
        "n": n,
        "mean": round(mn, 4),
        "stdev": round(var ** 0.5, 4),
        "p5": _p(5),
        "p25": _p(25),
        "p50": _p(50),
        "p75": _p(75),
        "p95": _p(95),
    }


def _compute_igg_fv_structural_metrics(pdb_path: str, vh_chain: str = "H", vl_chain: str = "L"):
    """
    Compute SASA structural metrics for a VH+VL Fv PDB.
    Returns dict with keys: psh_vh, psh_vl, ppc_vh, ppc_vl, pnc_vh, pnc_vl,
                           sap_sasa_vh, sap_sasa_vl, plddt (if B-factor).
    Uses BioPython ShrakeRupley — same logic as compute_vhh_structural_metrics().
    """
    try:
        from Bio.PDB import PDBParser  # type: ignore[attr-defined]
        from Bio.PDB.SASA import ShrakeRupley  # type: ignore[attr-defined]
    except ImportError:
        return {"_error": "biopython_not_available"}

    _HYDROPHOBIC = set("VILMFYWCA")
    _POS_CHARGED = set("KRH")
    _NEG_CHARGED = set("DE")

    def _chain_metrics(chain_obj):
        sr = ShrakeRupley()
        sr.compute(chain_obj, level="R")
        total_sasa = 0.0
        hydro_sasa = 0.0
        ppc_run = 0; max_ppc = 0
        pnc_run = 0; max_pnc = 0
        sap_wins = []; win_buf = []
        plddt_vals = []
        residues = list(chain_obj.get_residues())
        for res in residues:
            aa3 = res.get_resname().strip()
            try:
                from Bio.Data.IUPACData import protein_letters_3to1  # type: ignore
                aa1 = protein_letters_3to1.get(aa3.capitalize(), "X")
            except Exception:
                aa1 = "X"
            sasa = res.sasa if hasattr(res, "sasa") else 0.0
            total_sasa += sasa
            if aa1 in _HYDROPHOBIC:
                hydro_sasa += sasa
            if aa1 in _POS_CHARGED:
                ppc_run += 1; pnc_run = 0
            elif aa1 in _NEG_CHARGED:
                pnc_run += 1; ppc_run = 0
            else:
                ppc_run = 0; pnc_run = 0
            max_ppc = max(max_ppc, ppc_run)
            max_pnc = max(max_pnc, pnc_run)
            # pLDDT from B-factor
            for atom in res.get_atoms():
                plddt_vals.append(atom.get_bfactor())
                break
            # SAP 7-mer window
            win_buf.append((aa1, sasa))
            if len(win_buf) == 7:
                win_sasa = sum(s for _, s in win_buf)
                win_h_sasa = sum(s for a, s in win_buf if a in _HYDROPHOBIC)
                if win_sasa > 0:
                    sap_wins.append(win_h_sasa / win_sasa)
                win_buf.pop(0)

        psh = round(sum(s for res in residues
                        for aa3 in [res.get_resname().strip()]
                        for aa1 in [__import__('Bio.Data.IUPACData', fromlist=['protein_letters_3to1'])
                                    .protein_letters_3to1.get(aa3.capitalize(), 'X')]
                        if aa1 in _HYDROPHOBIC
                        for s in [res.sasa if hasattr(res, 'sasa') else 0.0]) * 0.01, 3)
        sap_sasa = round(max(sap_wins) if sap_wins else 0.0, 4)
        plddt = round(sum(plddt_vals) / len(plddt_vals), 2) if plddt_vals else None
        return {
            "psh": psh,
            "ppc": max_ppc,
            "pnc": max_pnc,
            "sap_sasa": sap_sasa,
            "plddt": plddt,
        }

    try:
        parser = PDBParser(QUIET=True)
        structure = parser.get_structure("fv", pdb_path)
        model = structure[0]  # type: ignore[index]
        result = {}
        for chain_id, label in [(vh_chain, "vh"), (vl_chain, "vl")]:
            if chain_id in model:
                m = _chain_metrics(model[chain_id])
                result[f"psh_{label}"] = m["psh"]
                result[f"ppc_{label}"] = m["ppc"]
                result[f"pnc_{label}"] = m["pnc"]
                result[f"sap_sasa_{label}"] = m["sap_sasa"]
                if "plddt" not in result:
                    result["plddt"] = m["plddt"]
        return result
    except Exception as e:
        return {"_error": str(e)}


# ── VHH batch ─────────────────────────────────────────────────────────────────

def build_vhh_stats():
    idx_path = REPO / "data/vhh_structural_union/vhh_structural_union_index.json"
    idx = json.loads(idx_path.read_text())
    entries = idx.get("clinical_vhh", []) + idx.get("database_b", [])

    collectors = {
        "psh": [], "ppc": [], "pnc": [], "sap_sasa": [],
        "cdr_H1_sasa": [], "cdr_H2_sasa": [], "cdr_H3_sasa": [],
        "plddt": [],
    }
    errors = []

    for e in entries:
        pdb_rel = e.get("pdb_model", "")
        pdb_path = str(REPO / pdb_rel)
        if not os.path.exists(pdb_path):
            errors.append({"id": e["id"], "error": "pdb_not_found", "path": pdb_path})
            continue
        try:
            m = compute_vhh_structural_metrics(pdb_path)
            if m.get("_struct_cmc_error"):
                errors.append({"id": e["id"], "error": m["_struct_cmc_error"]})
                continue
            collectors["psh"].append(m.get("psh"))
            collectors["ppc"].append(m.get("ppc"))
            collectors["pnc"].append(m.get("pnc"))
            collectors["sap_sasa"].append(m.get("sap_sasa"))
            cdr = m.get("cdr_sasa") or {}
            collectors["cdr_H1_sasa"].append(cdr.get("H1"))
            collectors["cdr_H2_sasa"].append(cdr.get("H2"))
            collectors["cdr_H3_sasa"].append(cdr.get("H3"))
            collectors["plddt"].append(m.get("plddt"))
            plddt_disp = f"{m.get('plddt'):.1f}" if m.get('plddt') is not None else "—"
            print(f"  ✓ {e['id']:50s}  psh={m.get('psh'):.3f}  plddt={plddt_disp}")
        except Exception as ex:
            errors.append({"id": e["id"], "error": str(ex)})
            print(f"  ✗ {e['id']:50s}  ERROR: {ex}")

    stats = {}
    for k, vals in collectors.items():
        s = _percentiles([v for v in vals if v is not None])
        if s:
            stats[k] = s

    out = {
        "_meta": {
            "benchmark_id": "VHH69_sasa_structural_v1",
            "status": "active_reference",
            "source": "vhh_structural_union_index.json (clinical_vhh n=40 + database_b n=29)",
            "n_input": len(entries),
            "n_computed": sum(1 for v in collectors["psh"] if v is not None),
            "n_errors": len(errors),
            "generated_by": "scripts/build_sasa_reference_stats.py",
            "metrics": ["psh", "ppc", "pnc", "sap_sasa", "cdr_H1_sasa", "cdr_H2_sasa", "cdr_H3_sasa", "plddt"],
        },
        "structural_metrics": stats,
        "errors": errors,
    }
    out_path = REPO / "data/reference/VHH69_sasa_structural_stats_v1.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved VHH stats → {out_path}  (n_computed={out['_meta']['n_computed']}, n_errors={len(errors)})")
    return out


# ── IgG/Fv batch ──────────────────────────────────────────────────────────────

def build_igg_stats():
    pdb_dir = REPO / "data/design_rules/igg_like_75_immunebuilder_predictions"
    pdbs = sorted(
        p for p in pdb_dir.glob("*.pdb")
        if "_Arm" not in p.name and "_tmp" not in p.name
    )
    print(f"\nIgG/Fv: found {len(pdbs)} whole-Fv PDB files")

    collectors = {
        "psh_vh": [], "psh_vl": [],
        "ppc_vh": [], "ppc_vl": [],
        "pnc_vh": [], "pnc_vl": [],
        "sap_sasa_vh": [], "sap_sasa_vl": [],
        "plddt": [],
    }
    errors = []

    for p in pdbs:
        try:
            m = _compute_igg_fv_structural_metrics(str(p))
            if "_error" in m:
                errors.append({"id": p.stem, "error": m["_error"]})
                print(f"  ✗ {p.stem:50s}  ERROR: {m['_error']}")
                continue
            for k in collectors:
                v = m.get(k)
                if v is not None:
                    collectors[k].append(v)
            print(f"  ✓ {p.stem:50s}  psh_vh={m.get('psh_vh'):.3f}  sap_vh={m.get('sap_sasa_vh'):.4f}")
        except Exception as ex:
            errors.append({"id": p.stem, "error": str(ex)})
            traceback.print_exc()

    stats = {}
    for k, vals in collectors.items():
        s = _percentiles([v for v in vals if v is not None])
        if s:
            stats[k] = s

    out = {
        "_meta": {
            "benchmark_id": "IgG73_sasa_structural_v1",
            "status": "active_reference",
            "source": "data/design_rules/igg_like_75_immunebuilder_predictions/ (whole-Fv, ABodyBuilder2)",
            "n_input": len(pdbs),
            "n_computed": sum(1 for v in collectors["psh_vh"] if v is not None),
            "n_errors": len(errors),
            "generated_by": "scripts/build_sasa_reference_stats.py",
            "metrics": list(collectors.keys()),
        },
        "structural_metrics": stats,
        "errors": errors,
    }
    out_path = REPO / "data/reference/IgG73_sasa_structural_stats_v1.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved IgG stats → {out_path}  (n_computed={out['_meta']['n_computed']}, n_errors={len(errors)})")
    return out


if __name__ == "__main__":
    print("=== VHH69 SASA structural stats ===")
    vhh_out = build_vhh_stats()
    print("\n=== IgG73 SASA structural stats ===")
    igg_out = build_igg_stats()
    print("\nDone.")
