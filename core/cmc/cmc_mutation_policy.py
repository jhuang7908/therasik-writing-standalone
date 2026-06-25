"""
CMC mutation policy layer for FR-only developability suggestions.

This module classifies candidate FR substitutions after sequence enumeration. It
keeps client-facing output concise while enforcing structural protection rules:
CDR-neighbor protection, VH/VL interface-neighbor protection, buried-core
protection, and surface-class routing.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

PROTECTED_DISTANCE_A = 5.0
BURIED_CORE_SASA = 0.10
EXPOSED_SURFACE_SASA = 0.30

_HYDROPHOBIC = set("AILMFWV")
_CHARGED = set("KRDE")
_POLAR = set("STNQHGPY")

AtomMap = Dict[Tuple[str, int], List[Tuple[float, float, float]]]


def apply_cmc_mutation_policy(
    candidate_payload: Dict[str, Any],
    *,
    indexed_rows: Mapping[str, Iterable[Mapping[str, Any]]],
    pdb_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Filter and annotate FR mutation candidates using CMC policy v1.2."""
    if not isinstance(candidate_payload, dict):
        return candidate_payload

    atom_map: AtomMap = {}
    pdb_chains: List[str] = []
    if pdb_path and Path(pdb_path).is_file():
        atom_map = _read_pdb_atoms(str(pdb_path))
        pdb_chains = sorted({chain for chain, _ in atom_map})

    cdr_atoms = _cdr_atom_coords(indexed_rows, atom_map, pdb_chains)
    protected: List[Dict[str, Any]] = []

    for key in ("fr_positive_charge_sites", "fr_negative_charge_sites", "fr_instability_sites"):
        sites = candidate_payload.get(key) or []
        kept: List[Dict[str, Any]] = []
        for site in sites:
            decision = _classify_site(site, atom_map, pdb_chains, cdr_atoms)
            site.update(decision["public"])
            if decision["allowed"]:
                kept.append(site)
            else:
                protected.append(site)
        candidate_payload[key] = kept

    runs = candidate_payload.get("fr_hydrophobic_runs") or []
    kept_runs: List[Dict[str, Any]] = []
    for run in runs:
        per_residue = run.get("per_residue") or []
        kept_res: List[Dict[str, Any]] = []
        for residue in per_residue:
            site = dict(residue)
            site["chain"] = run.get("chain")
            decision = _classify_site(site, atom_map, pdb_chains, cdr_atoms)
            residue.update(decision["public"])
            if decision["allowed"]:
                kept_res.append(residue)
            else:
                protected.append(residue)
        if kept_res:
            run["per_residue"] = kept_res
            run["selection_basis"] = "surface-exposed FR hydrophobic patch; protected structural neighbors excluded"
            kept_runs.append(run)
    candidate_payload["fr_hydrophobic_runs"] = kept_runs

    candidate_payload["mutation_policy"] = {
        "version": "CMC_MUTATION_POLICY_V1.2",
        "public_summary": (
            "FR-only suggestions prioritize non-critical exposed framework positions; "
            "CDR, Vernier, buried-core, and VH/VL-interface-neighbor residues are protected."
        ),
        "protected_candidate_count": len(protected),
    }
    return candidate_payload


def _read_pdb_atoms(pdb_path: str) -> AtomMap:
    atoms: AtomMap = {}
    with open(pdb_path, encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not line.startswith("ATOM"):
                continue
            atom_name = line[12:16].strip()
            if atom_name.startswith("H"):
                continue
            try:
                chain_id = line[21].strip() or " "
                resnum = int(line[22:26].strip())
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
            except ValueError:
                continue
            atoms.setdefault((chain_id, resnum), []).append((x, y, z))
    return atoms


def _pdb_chain_for(chain_label: str, pdb_chains: List[str]) -> Optional[str]:
    want = {"VH": "H", "VL": "L"}.get(str(chain_label), "")
    if want in pdb_chains:
        return want
    idx = 0 if chain_label == "VH" else 1
    return pdb_chains[idx] if idx < len(pdb_chains) else None


def _cdr_atom_coords(
    indexed_rows: Mapping[str, Iterable[Mapping[str, Any]]],
    atom_map: AtomMap,
    pdb_chains: List[str],
) -> List[Tuple[float, float, float]]:
    coords: List[Tuple[float, float, float]] = []
    if not atom_map:
        return coords
    for chain_label, rows in indexed_rows.items():
        pdb_chain = _pdb_chain_for(str(chain_label), pdb_chains)
        if not pdb_chain:
            continue
        for row in rows or []:
            region = str(row.get("region") or "")
            if not region.startswith("CDR"):
                continue
            seq_idx0 = row.get("seq_idx0")
            if not isinstance(seq_idx0, int):
                continue
            coords.extend(atom_map.get((pdb_chain, seq_idx0 + 1), []))
    return coords


def _classify_site(
    site: Mapping[str, Any],
    atom_map: AtomMap,
    pdb_chains: List[str],
    cdr_atoms: List[Tuple[float, float, float]],
) -> Dict[str, Any]:
    aa = str(site.get("from_aa") or "").upper()
    chain_label = str(site.get("chain") or "")
    idx1 = _as_int(site.get("index_1"))
    sasa = _as_float(site.get("sasa_rel"))

    surface_class = _surface_class(aa, sasa)
    protected_reasons: List[str] = []

    if sasa is not None and sasa < BURIED_CORE_SASA:
        protected_reasons.append("buried framework core")

    if atom_map and idx1 is not None:
        pdb_chain = _pdb_chain_for(chain_label, pdb_chains)
        site_atoms = atom_map.get((pdb_chain, idx1), []) if pdb_chain else []
        if site_atoms:
            cdr_dist = _min_distance(site_atoms, cdr_atoms)
            if cdr_dist is not None and cdr_dist <= PROTECTED_DISTANCE_A:
                protected_reasons.append("CDR-neighbor framework position")
            interface_dist = _min_distance_to_other_chain(site_atoms, atom_map, pdb_chain)
            if interface_dist is not None and interface_dist <= PROTECTED_DISTANCE_A:
                protected_reasons.append("VH/VL-interface-neighbor position")

    allowed = not protected_reasons
    if allowed:
        basis = _public_basis(surface_class)
    else:
        basis = "protected structural-neighbor or buried-core position; not recommended for automated substitution"

    return {
        "allowed": allowed,
        "public": {
            "surface_class": surface_class,
            "selection_basis": basis,
            "policy_decision": "candidate" if allowed else "protected",
        },
    }


def _surface_class(aa: str, sasa: Optional[float]) -> str:
    exposed = sasa is None or sasa >= EXPOSED_SURFACE_SASA
    if aa in _HYDROPHOBIC:
        return "exposed_hydrophobic_patch" if exposed else "buried_or_partially_buried_hydrophobic_core"
    if aa in _CHARGED:
        return "exposed_charged_hydrophilic_surface" if exposed else "partially_buried_charged_site"
    if aa in _POLAR:
        return "exposed_polar_surface" if exposed else "partially_buried_polar_site"
    return "framework_surface"


def _public_basis(surface_class: str) -> str:
    if surface_class == "exposed_hydrophobic_patch":
        return "surface-exposed FR hydrophobic patch; conservative developability substitution may reduce aggregation risk"
    if surface_class == "exposed_charged_hydrophilic_surface":
        return "surface-exposed FR charged site; use only for pI or charge-patch tuning with immunogenicity review"
    if surface_class == "exposed_polar_surface":
        return "surface-exposed FR polar site; conservative substitution only when needed for stability or motif cleanup"
    return "non-critical FR candidate; CDR and interface-neighbor residues protected"


def _min_distance(
    atoms_a: Iterable[Tuple[float, float, float]],
    atoms_b: Iterable[Tuple[float, float, float]],
) -> Optional[float]:
    best: Optional[float] = None
    b_list = list(atoms_b)
    if not b_list:
        return None
    for ax, ay, az in atoms_a:
        for bx, by, bz in b_list:
            d = math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)
            if best is None or d < best:
                best = d
    return best


def _min_distance_to_other_chain(
    site_atoms: Iterable[Tuple[float, float, float]],
    atom_map: AtomMap,
    pdb_chain: Optional[str],
) -> Optional[float]:
    if not pdb_chain:
        return None
    other_atoms: List[Tuple[float, float, float]] = []
    for (chain_id, _), coords in atom_map.items():
        if chain_id != pdb_chain:
            other_atoms.extend(coords)
    return _min_distance(site_atoms, other_atoms)


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
