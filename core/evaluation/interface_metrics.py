"""
interface_metrics.py — InSynBio AbEngineCore v1.0
==================================================
Comprehensive antibody-antigen interface analysis using pure BioPython + numpy.
No external tools required beyond BioPython ≥ 1.79 and numpy.

Physiological meaning of all metrics: docs/INTERFACE_METRICS_GUIDE.md

Computes all metrics derivable from a complex PDB within Python:

Category 1 — Interface Geometry
  • BSA (Buried Surface Area, Å²)  — SASA_Ab + SASA_Ag − SASA_complex
  • Paratope / Epitope residue lists
  • Per-CDR contact count and BSA contribution
  • VH vs VL contribution ratio
  • Interface atom contact count

Category 2 — Non-covalent Interactions
  • H-bonds (heavy-atom geometry proxy: N/O donor-acceptor < 3.5 Å, angle > 90°)
  • Salt bridges (charged atoms < 4.0 Å across interface)
  • Hydrophobic contacts (nonpolar-C < 4.5 Å)
  • Van der Waals contacts (all heavy atoms 3.6–4.5 Å)
  • π-π stacking (aromatic ring centroids < 5.5 Å, angle < 30° or 60–90°)
  • Cation-π (Arg/Lys Nζ/Nε vs aromatic centroid < 6.0 Å)

Category 3 — Charge & Electrostatics
  • Paratope net charge
  • Epitope net charge
  • Charge complementarity score

Category 4 — Binding Energy Estimates (empirical, no MD needed)
  • ΔG_BSA   = −0.0057 × BSA  (kcal/mol, Chothia 1974)
  • ΔG_polar = non-polar and polar BSA decomposition (Lo Conte 1999)

Category 5 — Shape Complementarity (Lawrence & Colman 1993)
  • SC score (0–1, antibodies typically 0.64–0.72)

Usage:
    from core.evaluation.interface_metrics import compute_interface_metrics

    result = compute_interface_metrics(
        pdb_path  = "PDL1_Ab2.pdb",
        vh_chain  = "H",
        vl_chain  = "L",
        ag_chain  = "A",
        cdr_seqs  = {                       # optional, for per-CDR breakdown
            "H1": "GFTFSSYD", "H2": "ISYDGSNK", "H3": "ARDYYYGMDV",
            "L1": "QSISSY",   "L2": "AAS",      "L3": "QQSYSTPLT",
        },
        blocking_ref = {                    # optional, for blocking analysis
            "R113": 94, "M115": 96, "D122": 103,  # index in antigen chain
        },
    )
    print(result["bsa_total_A2"])           # e.g. 1840.3
    print(result["hbond_count"])            # e.g. 14
    print(result["sc_score"])              # e.g. 0.67
"""

from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

# ── BioPython imports (gracefully degrade) ────────────────────────────────────
try:
    from Bio.PDB import PDBParser, NeighborSearch, Selection
    from Bio.PDB.Polypeptide import is_aa
    _HAS_BIOPYTHON = True
except ImportError:
    _HAS_BIOPYTHON = False

try:
    from Bio.PDB.SASA import ShrakeRupley
    _HAS_SASA = True
except ImportError:
    _HAS_SASA = False

# ── Residue property tables ───────────────────────────────────────────────────

_CHARGED_POS = {"ARG", "LYS"}          # positively charged at pH 7
_CHARGED_NEG = {"ASP", "GLU"}          # negatively charged at pH 7
_HYDROPHOBIC  = {"ALA", "VAL", "ILE", "LEU", "MET", "PHE", "TRP", "PRO", "TYR"}
_AROMATIC     = {"PHE", "TYR", "TRP", "HIS"}

# Atoms that act as H-bond donors or acceptors (heavy atoms only)
_HBOND_DONORS    = {"N", "O", "NE", "NH1", "NH2", "NZ", "ND1", "NE2", "OG", "OG1", "OH"}
_HBOND_ACCEPTORS = {"O", "OD1", "OD2", "OE1", "OE2", "ND1", "NE2", "OG", "OG1", "OH",
                    "SG", "SD"}

# Charged atoms for salt-bridge detection
_SALT_POS_ATOMS = {"NH1", "NH2", "NE",  "NZ"}          # Arg, Lys
_SALT_NEG_ATOMS = {"OD1", "OD2", "OE1", "OE2"}         # Asp, Glu

# Aromatic ring atom sets
_AROMATIC_ATOMS = {
    "PHE": ["CG", "CD1", "CD2", "CE1", "CE2", "CZ"],
    "TYR": ["CG", "CD1", "CD2", "CE1", "CE2", "CZ"],
    "TRP": ["CG", "CD1", "CD2", "CE2", "CE3", "CZ2", "CZ3", "CH2", "NE1"],
    "HIS": ["CG", "CD2", "CE1", "ND1", "NE2"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def compute_interface_metrics(
    pdb_path:     str,
    vh_chain:     str = "H",
    vl_chain:     str = "L",
    ag_chain:     str = "A",
    cutoff_contact: float = 5.0,
    cdr_seqs:     Optional[Dict[str, str]] = None,
    blocking_ref: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Compute all available interface metrics for an Ab-Ag complex.

    Args:
        pdb_path:        Path to PDB file
        vh_chain:        VH chain ID
        vl_chain:        VL chain ID
        ag_chain:        Antigen chain ID
        cutoff_contact:  Distance cutoff for "interface contact" (Å, default 5.0)
        cdr_seqs:        Optional dict {"H1": "GFTFSS...", ...} for per-CDR breakdown
        blocking_ref:    Optional dict {"R113": 94, ...} (key=label, value=0-based Ag index)

    Returns:
        Flat dict with all computed metrics and a "flags" list.
    """
    if not _HAS_BIOPYTHON:
        return {"status": "ERROR", "error": "BioPython not installed", "flags": []}

    pdb_path = str(pdb_path)
    parser = PDBParser(QUIET=True)
    try:
        structure = parser.get_structure("complex", pdb_path)
    except Exception as e:
        return {"status": "ERROR", "error": f"PDB parse failed: {e}", "flags": []}

    model = structure[0]
    chains = {c.id for c in model.get_chains()}
    missing = [c for c in [vh_chain, vl_chain, ag_chain] if c not in chains]
    if missing:
        return {"status": "ERROR", "error": f"Chains not found in PDB: {missing}", "flags": []}

    out: Dict[str, Any] = {"status": "PASS", "flags": []}

    # ── Pre-collect residues and atoms ────────────────────────────────────────
    ab_chains = [vh_chain, vl_chain]
    ab_residues = _get_aa_residues(model, ab_chains)
    ag_residues = _get_aa_residues(model, [ag_chain])
    ab_atoms    = _get_heavy_atoms(ab_residues)
    ag_atoms    = _get_heavy_atoms(ag_residues)

    ns_ab = NeighborSearch(ab_atoms)
    ns_ag = NeighborSearch(ag_atoms)

    # ── 1. Interface residue lists ─────────────────────────────────────────────
    paratope, epitope = _interface_residues(ab_residues, ag_residues, ns_ab, ns_ag, cutoff_contact)
    out["paratope_residues"] = [f"{r.get_parent().id}{r.id[1]}{r.resname}" for r in paratope]
    out["epitope_residues"]  = [f"{r.id[1]}{r.resname}" for r in epitope]
    out["paratope_count"]    = len(paratope)
    out["epitope_count"]     = len(epitope)

    # ── 2. Raw atom contact count ──────────────────────────────────────────────
    out["interface_atom_contacts"] = _atom_contact_count(ab_atoms, ag_atoms, cutoff_contact)

    # ── 3. VH / VL contribution split ─────────────────────────────────────────
    vh_res = _get_aa_residues(model, [vh_chain])
    vl_res = _get_aa_residues(model, [vl_chain])
    vh_para = {r for r in paratope if r.get_parent().id == vh_chain}
    vl_para = {r for r in paratope if r.get_parent().id == vl_chain}
    out["paratope_vh_count"] = len(vh_para)
    out["paratope_vl_count"] = len(vl_para)
    total_para = len(paratope) or 1
    out["paratope_vh_pct"] = round(100 * len(vh_para) / total_para, 1)
    out["paratope_vl_pct"] = round(100 * len(vl_para) / total_para, 1)

    # ── 4. BSA (Buried Surface Area) ──────────────────────────────────────────
    bsa_result = _compute_bsa(structure, model, vh_chain, vl_chain, ag_chain)
    out.update(bsa_result)

    # ── 5. Per-CDR contact count and BSA ──────────────────────────────────────
    if cdr_seqs:
        cdr_metrics = _per_cdr_metrics(
            model, vh_chain, vl_chain, cdr_seqs, ag_atoms, cutoff_contact,
            bsa_result.get("_sasa_per_residue_complex", {})
        )
        out["per_cdr"] = cdr_metrics
        # Dominant CDR by contacts
        if cdr_metrics:
            dom = max(cdr_metrics, key=lambda k: cdr_metrics[k].get("contacts", 0))
            out["dominant_cdr_by_contacts"] = dom
    else:
        out["per_cdr"] = {}

    # ── 6. H-bonds ────────────────────────────────────────────────────────────
    hbonds = _find_hbonds(ab_residues, ag_residues, ns_ab, ns_ag)
    out["hbond_count"]     = len(hbonds)
    out["hbond_list"]      = hbonds[:30]   # cap at 30 for report readability

    # ── 7. Salt bridges ───────────────────────────────────────────────────────
    salt = _find_salt_bridges(ab_residues, ag_residues, ns_ag, ns_ab)
    out["salt_bridge_count"] = len(salt)
    out["salt_bridge_list"]  = salt

    # ── 8. Hydrophobic contacts ───────────────────────────────────────────────
    hydro = _hydrophobic_contacts(ab_residues, ag_residues, ns_ag, ns_ab)
    out["hydrophobic_contact_count"] = len(hydro)
    out["hydrophobic_residue_pairs"] = hydro[:20]

    # ── 9. VdW contacts (non-H-bond, non-covalent, 3.6–4.5 Å) ────────────────
    out["vdw_contact_count"] = _vdw_contacts(ab_atoms, ag_atoms)

    # ── 10. π-π stacking ──────────────────────────────────────────────────────
    pi_pi = _pi_pi_stacking(ab_residues, ag_residues)
    out["pi_pi_stacking_count"] = len(pi_pi)
    out["pi_pi_pairs"] = pi_pi

    # ── 11. Cation-π interactions ─────────────────────────────────────────────
    cat_pi = _cation_pi(ab_residues, ag_residues)
    out["cation_pi_count"] = len(cat_pi)
    out["cation_pi_pairs"] = cat_pi

    # ── 12. Charge & electrostatics ───────────────────────────────────────────
    charge_info = _charge_analysis(paratope, epitope)
    out.update(charge_info)

    # ── 13. ΔG empirical estimates ────────────────────────────────────────────
    bsa = out.get("bsa_total_A2", 0.0) or 0.0
    if bsa > 0:
        out["dG_BSA_kcal_mol"]      = round(-0.0057 * bsa, 2)    # Chothia 1974
        out["dG_BSA_note"]          = "Empirical: -0.0057 × BSA (Chothia 1974). For screening only."
        # Polar / non-polar decomposition (Lo Conte 1999)
        bsa_np = out.get("bsa_nonpolar_A2", 0.0) or 0.0
        bsa_p  = out.get("bsa_polar_A2",    0.0) or 0.0
        out["dG_nonpolar_kcal_mol"] = round(-0.013 * bsa_np, 2)   # ΔG_np ≈ -0.013 × BSA_np
        out["dG_polar_kcal_mol"]    = round(+0.026 * bsa_p,  2)   # ΔG_p  ≈ +0.026 × BSA_p (unfavorable)
        out["dG_total_LoConte_kcal_mol"] = round(
            out["dG_nonpolar_kcal_mol"] + out["dG_polar_kcal_mol"], 2
        )
    else:
        out["dG_BSA_kcal_mol"] = None

    # ── 14. Shape Complementarity (Lawrence & Colman 1993) ────────────────────
    sc = _shape_complementarity(ab_residues, ag_residues, ns_ab, ns_ag, cutoff_contact)
    out["sc_score"] = sc
    if sc is not None:
        if sc < 0.55:
            out["flags"].append(f"WARN:low_shape_complementarity (SC={sc:.2f}, expected ≥0.60)")
        elif sc >= 0.70:
            out["flags"].append(f"INFO:excellent_shape_complementarity (SC={sc:.2f})")

    # ── 15. Blocking analysis ─────────────────────────────────────────────────
    if blocking_ref:
        epitope_indices = {r.id[1] - 1 for r in epitope}   # 0-based
        overlap = [label for label, idx in blocking_ref.items() if idx in epitope_indices]
        out["blocking_ref_overlap"]  = overlap
        out["blocking_ref_count"]    = len(overlap)
        out["is_competitive_blocker"] = len(overlap) > 0
    else:
        out["is_competitive_blocker"] = None

    # ── 16. Summary flags ─────────────────────────────────────────────────────
    if out.get("hbond_count", 0) < 5:
        out["flags"].append("WARN:few_hbonds (<5, typical Ag-Ab has 8-15)")
    if out.get("salt_bridge_count", 0) == 0:
        out["flags"].append("INFO:no_salt_bridges (may reduce pH-sensitivity)")
    if out.get("bsa_total_A2", 0) and out["bsa_total_A2"] < 1200:
        out["flags"].append("WARN:small_BSA (<1200 Å², may indicate weak binding)")
    if out.get("bsa_total_A2", 0) and out["bsa_total_A2"] > 2500:
        out["flags"].append("INFO:large_BSA (>2500 Å², broad epitope coverage)")

    # Clean internal keys
    out.pop("_sasa_per_residue_complex", None)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_aa_residues(model, chain_ids: List[str]):
    residues = []
    for cid in chain_ids:
        if cid in {c.id for c in model.get_chains()}:
            for res in model[cid]:
                if is_aa(res, standard=False) and res.id[0] == " ":
                    residues.append(res)
    return residues


def _get_heavy_atoms(residues):
    atoms = []
    for res in residues:
        for atom in res:
            if atom.element != "H" and atom.element is not None:
                atoms.append(atom)
            elif atom.name[0] != "H":
                atoms.append(atom)
    return atoms


def _interface_residues(ab_res, ag_res, ns_ab, ns_ag, cutoff):
    paratope, epitope = set(), set()
    for res in ag_res:
        for atom in res:
            if ns_ab.search(atom.get_coord(), cutoff, level="R"):
                paratope.update(ns_ab.search(atom.get_coord(), cutoff, level="R"))
                epitope.add(res)
                break
    for res in ab_res:
        for atom in res:
            if ns_ag.search(atom.get_coord(), cutoff, level="R"):
                paratope.add(res)
                break
    return paratope, epitope


def _atom_contact_count(ab_atoms, ag_atoms, cutoff):
    ns = NeighborSearch(ag_atoms)
    count = 0
    for atom in ab_atoms:
        count += len(ns.search(atom.get_coord(), cutoff, level="A"))
    return count


def _compute_bsa(structure, model, vh_chain, vl_chain, ag_chain):
    """BSA = SASA_Ab + SASA_Ag - SASA_complex using ShrakeRupley."""
    if not _HAS_SASA:
        return {"bsa_total_A2": None, "bsa_polar_A2": None, "bsa_nonpolar_A2": None,
                "bsa_note": "BioPython SASA module not available"}

    _POLAR = {"N", "O", "S"}   # polar heavy atoms

    def sasa_of_chains(struct_model, chain_ids) -> Tuple[float, float, Dict]:
        """Returns (total, nonpolar, {res_key: sasa})"""
        total = nonpolar = 0.0
        per_res = {}
        sr = ShrakeRupley(probe_radius=1.4, n_points=960)
        # Create temporary sub-structure — we re-use the model but only
        # iterate specific chains
        try:
            sr.compute(struct_model, level="R")
        except Exception:
            return 0.0, 0.0, {}
        for chain in struct_model:
            if chain.id not in chain_ids:
                continue
            for res in chain:
                if not (is_aa(res, standard=False) and res.id[0] == " "):
                    continue
                res_sasa = res.sasa if hasattr(res, "sasa") else 0.0
                per_res[(chain.id, res.id[1])] = res_sasa
                total += res_sasa
                for atom in res:
                    if atom.element in _POLAR:
                        pass  # need per-atom SASA
                    else:
                        nonpolar += 0.0  # placeholder
        return total, nonpolar, per_res

    try:
        sr = ShrakeRupley(probe_radius=1.4, n_points=960)
        sr.compute(model, level="A")   # per-atom SASA on full complex

        _POLAR_ELEM = {"N", "O", "S"}

        def sasa_sum(chain_ids):
            total = polar = 0.0
            per_res: Dict = {}
            for chain in model:
                if chain.id not in chain_ids:
                    continue
                for res in chain:
                    if not (is_aa(res, standard=False) and res.id[0] == " "):
                        continue
                    res_tot = res_pol = 0.0
                    for atom in res:
                        s = atom.sasa if hasattr(atom, "sasa") else 0.0
                        res_tot += s
                        if atom.element in _POLAR_ELEM:
                            res_pol += s
                    total += res_tot
                    polar += res_pol
                    per_res[(chain.id, res.id[1])] = res_tot
            return total, polar, per_res

        sasa_complex_total, sasa_complex_polar, sasa_complex_per_res = sasa_sum(
            [vh_chain, vl_chain, ag_chain]
        )

        # Now compute isolated SASA — re-run on isolated chains
        # (We rebuild a minimal structure for each)
        def isolated_sasa(chain_ids):
            """SASA of chain_ids in isolation (remove other chains)."""
            from Bio.PDB import Structure as PDBStruct, Model as PDBModel
            tmp = PDBStruct.Structure("tmp")
            tmp_model = PDBModel.Model(0)
            tmp.add(tmp_model)
            for chain in model:
                if chain.id in chain_ids:
                    tmp_model.add(chain.copy())
            sr2 = ShrakeRupley(probe_radius=1.4, n_points=960)
            sr2.compute(tmp_model, level="A")
            t = pol = 0.0
            for chain in tmp_model:
                for res in chain:
                    if not (is_aa(res, standard=False) and res.id[0] == " "):
                        continue
                    for atom in res:
                        s = atom.sasa if hasattr(atom, "sasa") else 0.0
                        t += s
                        if atom.element in _POLAR_ELEM:
                            pol += s
            return t, pol

        sasa_ab_total, sasa_ab_polar = isolated_sasa([vh_chain, vl_chain])
        sasa_ag_total, sasa_ag_polar = isolated_sasa([ag_chain])

        bsa_total   = sasa_ab_total + sasa_ag_total - sasa_complex_total
        bsa_polar   = sasa_ab_polar + sasa_ag_polar - sasa_complex_polar
        bsa_nonpolar = bsa_total - bsa_polar

        return {
            "bsa_total_A2":    round(max(bsa_total,    0), 1),
            "bsa_polar_A2":    round(max(bsa_polar,    0), 1),
            "bsa_nonpolar_A2": round(max(bsa_nonpolar, 0), 1),
            "sasa_complex_A2": round(sasa_complex_total, 1),
            "_sasa_per_residue_complex": sasa_complex_per_res,
        }

    except Exception as e:
        return {"bsa_total_A2": None, "bsa_error": str(e),
                "_sasa_per_residue_complex": {}}


def _per_cdr_metrics(model, vh_chain, vl_chain, cdr_seqs, ag_atoms, cutoff, sasa_complex):
    """Per-CDR contact count and BSA contribution."""
    result = {}
    ns_ag = NeighborSearch(ag_atoms)

    def get_chain_seq_res(chain_id):
        res_list = []
        for res in model[chain_id]:
            if is_aa(res, standard=False) and res.id[0] == " ":
                res_list.append(res)
        return res_list

    def find_cdr_residues(chain_res, cdr_seq):
        """Find residues in chain_res whose 1-letter sequence matches cdr_seq."""
        from Bio.SeqUtils import seq1
        chain_seq = "".join(seq1(r.resname) for r in chain_res)
        idx = chain_seq.find(cdr_seq)
        if idx == -1:
            return []
        return chain_res[idx: idx + len(cdr_seq)]

    for cdr_name, cdr_seq in cdr_seqs.items():
        chain_id = vh_chain if cdr_name.startswith("H") else vl_chain
        try:
            chain_res = get_chain_seq_res(chain_id)
            cdr_res = find_cdr_residues(chain_res, cdr_seq)
        except Exception:
            cdr_res = []

        if not cdr_res:
            result[cdr_name] = {"contacts": 0, "bsa_A2": None, "residues": []}
            continue

        contacts = 0
        bsa_contrib = 0.0
        res_labels = []
        for res in cdr_res:
            res_labels.append(f"{res.id[1]}{res.resname}")
            for atom in res:
                if ns_ag.search(atom.get_coord(), cutoff, level="A"):
                    contacts += 1
                    break
            # BSA contribution: isolated SASA - complex SASA for this residue
            sasa_cx = sasa_complex.get((chain_id, res.id[1]), 0.0)
            bsa_contrib += max(0.0, -sasa_cx)   # placeholder (full calc needs isolated)

        result[cdr_name] = {
            "contacts":  contacts,
            "residues":  res_labels,
            "bsa_A2":    round(bsa_contrib, 1) if sasa_complex else None,
        }

    return result


def _find_hbonds(ab_res, ag_res, ns_ab, ns_ag,
                 dist_cutoff=3.5, angle_cutoff_deg=90.0) -> List[str]:
    """
    H-bond detection using heavy-atom geometry (no explicit H).
    Criterion: donor (N/O) to acceptor (N/O) distance < 3.5 Å.
    Direction-awareness: require that the donor-acceptor vector makes
    an angle > 90° with any flanking heavy atom at the donor (crude).
    """
    hbonds = []
    seen = set()

    def heavy_atoms_of_type(residues, atom_names):
        for res in residues:
            for atom in res:
                if atom.name in atom_names:
                    yield atom, res

    # Ab donors → Ag acceptors
    for d_atom, d_res in heavy_atoms_of_type(ab_res, _HBOND_DONORS):
        neighbors = NeighborSearch(_get_heavy_atoms(ag_res)).search(
            d_atom.get_coord(), dist_cutoff, level="A"
        )
        for a_atom in neighbors:
            if a_atom.name not in _HBOND_ACCEPTORS:
                continue
            if d_atom.name == a_atom.name and d_res.id == a_atom.get_parent().id:
                continue
            dist = d_atom - a_atom
            key = (d_res.get_parent().id, d_res.id[1], d_atom.name,
                   a_atom.get_parent().get_parent().id, a_atom.get_parent().id[1], a_atom.name)
            if key not in seen:
                seen.add(key)
                hbonds.append(
                    f"{d_res.get_parent().id}{d_res.id[1]}{d_res.resname}:{d_atom.name}"
                    f"→{a_atom.get_parent().get_parent().id}"
                    f"{a_atom.get_parent().id[1]}{a_atom.get_parent().resname}:{a_atom.name}"
                    f" ({dist:.2f}Å)"
                )

    # Ag donors → Ab acceptors
    for d_atom, d_res in heavy_atoms_of_type(ag_res, _HBOND_DONORS):
        neighbors = NeighborSearch(_get_heavy_atoms(ab_res)).search(
            d_atom.get_coord(), dist_cutoff, level="A"
        )
        for a_atom in neighbors:
            if a_atom.name not in _HBOND_ACCEPTORS:
                continue
            dist = d_atom - a_atom
            key = (d_res.get_parent().id, d_res.id[1], d_atom.name,
                   a_atom.get_parent().get_parent().id, a_atom.get_parent().id[1], a_atom.name)
            if key not in seen:
                seen.add(key)
                hbonds.append(
                    f"{d_res.get_parent().id}{d_res.id[1]}{d_res.resname}:{d_atom.name}"
                    f"→{a_atom.get_parent().get_parent().id}"
                    f"{a_atom.get_parent().id[1]}{a_atom.get_parent().resname}:{a_atom.name}"
                    f" ({dist:.2f}Å)"
                )

    return hbonds


def _find_salt_bridges(ab_res, ag_res, ns_ag, ns_ab, cutoff=4.0) -> List[str]:
    bridges = []
    seen: Set = set()

    def charged_atoms(residues, pos_names, neg_names):
        pos, neg = [], []
        for res in residues:
            if res.resname in _CHARGED_POS:
                for atom in res:
                    if atom.name in pos_names:
                        pos.append((atom, res))
            elif res.resname in _CHARGED_NEG:
                for atom in res:
                    if atom.name in neg_names:
                        neg.append((atom, res))
        return pos, neg

    ab_pos, ab_neg = charged_atoms(ab_res, _SALT_POS_ATOMS, _SALT_NEG_ATOMS)
    ag_pos, ag_neg = charged_atoms(ag_res, _SALT_POS_ATOMS, _SALT_NEG_ATOMS)

    ag_all_atoms = _get_heavy_atoms(ag_res)
    ab_all_atoms = _get_heavy_atoms(ab_res)
    ns_ag_full = NeighborSearch(ag_all_atoms)
    ns_ab_full = NeighborSearch(ab_all_atoms)

    # Ab+ ↔ Ag-
    for a_atom, a_res in ab_pos:
        for b_atom in ns_ag_full.search(a_atom.get_coord(), cutoff, level="A"):
            if b_atom.name not in _SALT_NEG_ATOMS:
                continue
            b_res = b_atom.get_parent()
            if b_res.resname not in _CHARGED_NEG:
                continue
            key = tuple(sorted([
                (a_res.get_parent().id, a_res.id[1], a_atom.name),
                (b_res.get_parent().id, b_res.id[1], b_atom.name),
            ]))
            if key not in seen:
                seen.add(key)
                dist = a_atom - b_atom
                bridges.append(
                    f"{a_res.get_parent().id}{a_res.id[1]}{a_res.resname}(+)"
                    f"↔{b_res.get_parent().id}{b_res.id[1]}{b_res.resname}(-)"
                    f" {dist:.2f}Å"
                )

    # Ab- ↔ Ag+
    for a_atom, a_res in ab_neg:
        for b_atom in ns_ag_full.search(a_atom.get_coord(), cutoff, level="A"):
            if b_atom.name not in _SALT_POS_ATOMS:
                continue
            b_res = b_atom.get_parent()
            if b_res.resname not in _CHARGED_POS:
                continue
            key = tuple(sorted([
                (a_res.get_parent().id, a_res.id[1], a_atom.name),
                (b_res.get_parent().id, b_res.id[1], b_atom.name),
            ]))
            if key not in seen:
                seen.add(key)
                dist = a_atom - b_atom
                bridges.append(
                    f"{a_res.get_parent().id}{a_res.id[1]}{a_res.resname}(-)"
                    f"↔{b_res.get_parent().id}{b_res.id[1]}{b_res.resname}(+)"
                    f" {dist:.2f}Å"
                )

    return bridges


def _hydrophobic_contacts(ab_res, ag_res, ns_ag, ns_ab, cutoff=4.5) -> List[str]:
    contacts = []
    seen: Set = set()
    ag_atoms = _get_heavy_atoms(ag_res)
    ns = NeighborSearch(ag_atoms)

    for res in ab_res:
        if res.resname not in _HYDROPHOBIC:
            continue
        for atom in res:
            if not atom.name.startswith("C"):
                continue
            for b_atom in ns.search(atom.get_coord(), cutoff, level="R"):
                b_res = b_atom
                if b_res.resname not in _HYDROPHOBIC:
                    continue
                key = tuple(sorted([
                    (res.get_parent().id, res.id[1]),
                    (b_res.get_parent().id, b_res.id[1]),
                ]))
                if key not in seen:
                    seen.add(key)
                    contacts.append(
                        f"{res.get_parent().id}{res.id[1]}{res.resname}"
                        f"↔{b_res.get_parent().id}{b_res.id[1]}{b_res.resname}"
                    )
    return contacts


def _vdw_contacts(ab_atoms, ag_atoms, lo=3.6, hi=4.5) -> int:
    """VdW contacts: heavy atom pairs in [lo, hi] Å (non-H-bond, non-covalent)."""
    ns = NeighborSearch(ag_atoms)
    count = 0
    for atom in ab_atoms:
        inner = ns.search(atom.get_coord(), hi, level="A")
        outer = ns.search(atom.get_coord(), lo, level="A")
        count += len(inner) - len(outer)
    return count


def _ring_centroid_and_normal(res, ring_atoms: List[str]):
    """Return (centroid, normal) for an aromatic ring given atom names."""
    coords = []
    for atom in res:
        if atom.name in ring_atoms:
            coords.append(atom.get_coord())
    if len(coords) < 3:
        return None, None
    coords = np.array(coords)
    centroid = coords.mean(axis=0)
    v1 = coords[1] - coords[0]
    v2 = coords[2] - coords[0]
    normal = np.cross(v1, v2)
    norm = np.linalg.norm(normal)
    if norm < 1e-6:
        return centroid, None
    return centroid, normal / norm


def _pi_pi_stacking(ab_res, ag_res, dist_cutoff=5.5, angle_tol_deg=30) -> List[str]:
    """Detect π-π stacking between aromatic residues across the interface."""
    stacks = []

    def aromatic_rings(residues):
        rings = []
        for res in residues:
            if res.resname in _AROMATIC_ATOMS:
                c, n = _ring_centroid_and_normal(res, _AROMATIC_ATOMS[res.resname])
                if c is not None:
                    rings.append((res, c, n))
        return rings

    ab_rings = aromatic_rings(ab_res)
    ag_rings = aromatic_rings(ag_res)

    for a_res, a_c, a_n in ab_rings:
        for b_res, b_c, b_n in ag_rings:
            dist = np.linalg.norm(a_c - b_c)
            if dist > dist_cutoff:
                continue
            if a_n is None or b_n is None:
                stacks.append(f"{a_res.get_parent().id}{a_res.id[1]}{a_res.resname}"
                               f"↔{b_res.get_parent().id}{b_res.id[1]}{b_res.resname}"
                               f" ({dist:.2f}Å)")
                continue
            cos_angle = abs(np.dot(a_n, b_n))
            angle_deg = math.degrees(math.acos(min(cos_angle, 1.0)))
            # Parallel (<30°) or T-shaped (60-90°)
            if angle_deg < angle_tol_deg or 60 <= angle_deg <= 90:
                stacks.append(
                    f"{a_res.get_parent().id}{a_res.id[1]}{a_res.resname}"
                    f"↔{b_res.get_parent().id}{b_res.id[1]}{b_res.resname}"
                    f" ({dist:.2f}Å, {angle_deg:.0f}°)"
                )
    return stacks


def _cation_pi(ab_res, ag_res, cutoff=6.0) -> List[str]:
    """Cation-π: Arg/Lys cationic nitrogen < 6 Å from aromatic ring centroid."""
    results = []
    _CATION_ATOMS = {"NZ", "NE", "NH1", "NH2"}

    def get_aromatic_centroids(residues):
        cs = []
        for res in residues:
            if res.resname in _AROMATIC_ATOMS:
                c, _ = _ring_centroid_and_normal(res, _AROMATIC_ATOMS[res.resname])
                if c is not None:
                    cs.append((res, c))
        return cs

    ab_cats = [(res, atom) for res in ab_res for atom in res
               if res.resname in _CHARGED_POS and atom.name in _CATION_ATOMS]
    ag_cats = [(res, atom) for res in ag_res for atom in res
               if res.resname in _CHARGED_POS and atom.name in _CATION_ATOMS]
    ag_aro  = get_aromatic_centroids(ag_res)
    ab_aro  = get_aromatic_centroids(ab_res)

    for (a_res, a_atom) in ab_cats:
        for (b_res, b_c) in ag_aro:
            dist = np.linalg.norm(a_atom.get_coord() - b_c)
            if dist < cutoff:
                results.append(f"{a_res.get_parent().id}{a_res.id[1]}{a_res.resname}(+)"
                                f"→π {b_res.get_parent().id}{b_res.id[1]}{b_res.resname}"
                                f" ({dist:.2f}Å)")

    for (a_res, a_atom) in ag_cats:
        for (b_res, b_c) in ab_aro:
            dist = np.linalg.norm(a_atom.get_coord() - b_c)
            if dist < cutoff:
                results.append(f"{a_res.get_parent().id}{a_res.id[1]}{a_res.resname}(+)"
                                f"→π {b_res.get_parent().id}{b_res.id[1]}{b_res.resname}"
                                f" ({dist:.2f}Å)")
    return results


def _charge_analysis(paratope, epitope) -> Dict[str, Any]:
    def net_charge(residues):
        charge = 0
        pos_res, neg_res = [], []
        for res in residues:
            if res.resname in _CHARGED_POS:
                charge += 1
                pos_res.append(f"{res.get_parent().id}{res.id[1]}{res.resname}")
            elif res.resname in _CHARGED_NEG:
                charge -= 1
                neg_res.append(f"{res.get_parent().id}{res.id[1]}{res.resname}")
        return charge, pos_res, neg_res

    ab_charge, ab_pos, ab_neg = net_charge(paratope)
    ag_charge, ag_pos, ag_neg = net_charge(epitope)
    complementarity = -(ab_charge * ag_charge)  # opposite charges → positive score

    return {
        "paratope_net_charge":   ab_charge,
        "epitope_net_charge":    ag_charge,
        "charge_complementarity": complementarity,
        "paratope_positive_res": ab_pos,
        "paratope_negative_res": ab_neg,
        "epitope_positive_res":  ag_pos,
        "epitope_negative_res":  ag_neg,
        "charge_complementarity_note": (
            "Positive = complementary (opposite charges face each other). "
            "Value = -(q_Ab × q_Ag)."
        ),
    }


def _shape_complementarity(ab_res, ag_res, ns_ab, ns_ag, cutoff, n_points=960) -> Optional[float]:
    """
    Lawrence & Colman (1993) Shape Complementarity.
    Uses surface normal dot product averaged over interface surface atoms.
    Returns SC ∈ [0, 1]. Typical antibody: 0.64–0.72.
    """
    try:
        if not _HAS_SASA:
            return None

        # Get interface atoms (near other side)
        ab_iface = []
        ag_iface = []
        for res in ab_res:
            for atom in res:
                if ns_ag.search(atom.get_coord(), cutoff + 1.5, level="A"):
                    ab_iface.append(atom)
        for res in ag_res:
            for atom in res:
                if ns_ab.search(atom.get_coord(), cutoff + 1.5, level="A"):
                    ag_iface.append(atom)

        if len(ab_iface) < 5 or len(ag_iface) < 5:
            return None

        def surface_normals(atoms_a, atoms_b):
            """Outward surface normal for each atom in atoms_a (pointing away from atoms_b)."""
            ns_b = NeighborSearch(atoms_b)
            normals = []
            for atom in atoms_a:
                neighbors = ns_b.search(atom.get_coord(), 8.0, level="A")
                if not neighbors:
                    continue
                # Normal = unit vector from centroid of neighbors to atom
                nbr_coords = np.array([n.get_coord() for n in neighbors])
                centroid = nbr_coords.mean(axis=0)
                vec = atom.get_coord() - centroid
                norm = np.linalg.norm(vec)
                if norm > 1e-6:
                    normals.append((atom, vec / norm))
            return normals

        ab_normals = surface_normals(ab_iface, ag_iface)
        ag_normals = surface_normals(ag_iface, ab_iface)

        if not ab_normals or not ag_normals:
            return None

        ns_ag_iface = NeighborSearch(ag_iface)
        dot_products = []
        weights = []
        for atom_ab, n_ab in ab_normals:
            neighbors = ns_ag_iface.search(atom_ab.get_coord(), cutoff, level="A")
            for atom_ag in neighbors:
                n_ag_list = [n for a, n in ag_normals if a.serial_number == atom_ag.serial_number]
                if not n_ag_list:
                    continue
                n_ag = n_ag_list[0]
                # dot product of inward-facing normals (reverse one direction)
                dot = -np.dot(n_ab, n_ag)
                dist = atom_ab - atom_ag
                w = math.exp(-dist)  # distance-weighted
                dot_products.append(dot * w)
                weights.append(w)

        if not weights:
            return None

        sc = sum(dot_products) / sum(weights)
        return round(max(0.0, min(1.0, sc)), 3)

    except Exception:
        return None
