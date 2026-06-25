"""
structural_integrity_veto.py
============================
VAM Stage 2.5 — Structural Integrity Veto (V1.5)

Prevents "high-affinity / low-expression" mutants from reaching expensive
OpenMM MD simulations by applying two mandatory geometric checks plus an
optional rescue pathway.

Root cause this module was built to catch
------------------------------------------
Ab278 anti-fentanyl affinity maturation (2026-04-24):
  - H:W107I/L  → ΔVol ≈ −61 Å³ at VH-VL interface → physical cavity → low expression
  - L:N116E    → new D/E pair with adjacent L:D115 (Cβ-Cβ 1.3 Å) → electrostatic explosion

Checks
------
  CHECK 1 — Interface Packing Veto       (VETO_PACKING)        — VH-VL collapse
  CHECK 2 — Charge Neighborhood Veto     (VETO_CHARGE)         — same-sign D/E or K/R clash
  CHECK 3 — Expression-sensitive FR warn (WARN_EXPRESSION)     — non-blocking
  CHECK 4 — Antigen Contact Preservation (VETO_AFFINITY /      — protects key
                                          WARN_AFFINITY)         antigen contacts
                                                                 (works for protein
                                                                 antigen chains AND
                                                                 hapten HETATM ligands)

Usage
-----
  from core.structure.structural_integrity_veto import run_stage2_5

  results = run_stage2_5(
      pdb_path="complex.pdb",
      ab_chains=["H", "L"],
      candidates=[{"chain":"H","resi":107,"wt":"W","mut":"I"}],
      affinity_ddg={"H:107:W:I": -2.3},   # Stage 2 EvoEF2 result
      rescue=True,
  )
  # returns {"passed":[], "vetoed":[], "rescued":[], "warned":[]}
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Residue volume table (van der Waals solvent-excluded volumes, Å³)
# Source: Creighton 1993 / Chothia 1975 consensus
# ---------------------------------------------------------------------------
RESIDUE_VOL: dict[str, float] = {
    "G": 60,
    "A": 88,
    "S": 89,
    "P": 122,
    "V": 140,
    "T": 116,
    "C": 108,
    "I": 167,
    "L": 167,
    "N": 114,
    "D": 111,
    "Q": 144,
    "K": 168,
    "E": 138,
    "M": 162,
    "H": 153,
    "F": 190,
    "R": 173,
    "Y": 193,
    "W": 228,
}

# Aromatic large residues (sources of interface packing)
_AROMATIC_LARGE = {"W", "Y", "F"}

# Small / aliphatic residues (potential void-creators)
_SMALL_ALIPHATIC = {"G", "A", "V", "I", "L"}

# Charged residue groups
_NEGATIVE = {"D", "E"}
_POSITIVE = {"K", "R"}

# Expression-sensitive framework positions (Kabat numbering)
# These are at VH-VL contact zone; mutations here are frequently de-stabilising
_EXPR_SENSITIVE_VH = {78, 89}
_EXPR_SENSITIVE_VL = {84, 87}

# Veto / rescue thresholds
_PACKING_DVOL_THRESHOLD = -30.0        # Å³ — ΔVol more negative than this → packing veto
_INTERFACE_CBETA_CUTOFF = 6.0          # Å  — cross-chain Cβ-Cβ ≤ this → "is at interface"
_CHARGE_CBETA_CUTOFF = 4.0             # Å  — same-sign charged pair within this → charge veto
_RESCUE_AFFINITY_THRESHOLD = -1.5      # kcal/mol — EvoEF2 ΔΔG must be better than this to rescue
_RESCUE_COMPENSATION_VOL = 25.0        # Å³ — minimum volume contribution from compensatory mutation
_ANTIGEN_CONTACT_CUTOFF = 4.0          # Å  — heavy-atom dist defining "antigen contact"
_CRITICAL_CONTACT_THRESHOLD = 3        # ≥ this many heavy-atom contacts → CRITICAL contact

# Chemical class table (for conservative-substitution scoring)
_AA_CHEMCLASS: dict[str, str] = {
    "G": "small", "A": "small",
    "V": "aliphatic", "I": "aliphatic", "L": "aliphatic", "M": "aliphatic",
    "F": "aromatic", "Y": "aromatic", "W": "aromatic",
    "S": "polar", "T": "polar", "N": "polar", "Q": "polar",
    "C": "polar_sulfur",
    "P": "constraint",
    "H": "polar_charged",
    "K": "positive", "R": "positive",
    "D": "negative", "E": "negative",
}


# ---------------------------------------------------------------------------
# Data classes for results
# ---------------------------------------------------------------------------

@dataclass
class VetoResult:
    mutation: dict                    # {"chain", "resi", "wt", "mut"}
    veto_type: str                    # "VETO_PACKING" | "VETO_CHARGE" | "WARN_EXPRESSION" | "PASS"
    reason: str
    delta_vol: Optional[float] = None
    charge_neighbor: Optional[str] = None
    rescue_suggestion: Optional[dict] = None   # compensatory mutation dict if rescuable


@dataclass
class Stage25Result:
    passed: list[dict] = field(default_factory=list)
    vetoed: list[VetoResult] = field(default_factory=list)
    rescued: list[dict] = field(default_factory=list)   # original + compensatory mutations
    warned: list[VetoResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# PDB parsing helpers (minimal, no external dependency beyond stdlib)
# ---------------------------------------------------------------------------

def _parse_pdb_atoms(pdb_path: str, include_hetatm: bool = False) -> list[dict]:
    """
    Parse ATOM (and optionally HETATM) records. Returns list of:
      {"record", "chain", "resi", "resname", "name", "x", "y", "z"}

    Set include_hetatm=True when working with antibody-hapten complexes
    (e.g. AutoDock outputs where the small molecule is HETATM).
    """
    atoms: list[dict] = []
    with open(pdb_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            tag = line[:6].strip()
            if tag == "ATOM" or (include_hetatm and tag == "HETATM"):
                try:
                    atoms.append({
                        "record":  tag,
                        "chain":   line[21].strip(),
                        "resi":    int(line[22:26].strip()),
                        "resname": line[17:20].strip(),
                        "name":    line[12:16].strip(),
                        "x":       float(line[30:38]),
                        "y":       float(line[38:46]),
                        "z":       float(line[46:54]),
                    })
                except (ValueError, IndexError):
                    pass
    return atoms


def _cbeta_coords(atoms: list[dict]) -> dict[tuple[str, int], tuple[float, float, float]]:
    """
    Return {(chain, resi): (x, y, z)} using Cβ; fall back to Cα for Gly.
    """
    cbeta: dict[tuple, tuple] = {}
    ca: dict[tuple, tuple] = {}
    for a in atoms:
        key = (a["chain"], a["resi"])
        if a["name"] == "CB":
            cbeta[key] = (a["x"], a["y"], a["z"])
        elif a["name"] == "CA":
            ca[key] = (a["x"], a["y"], a["z"])
    merged = {**ca, **cbeta}   # Cβ overrides Cα
    return merged


def _dist(p1: tuple, p2: tuple) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))


def _resname_to_1letter(three: str) -> str:
    _MAP = {
        "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
        "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
        "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
        "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
    }
    return _MAP.get(three.upper(), "X")


def _get_residue_aa(atoms: list[dict], chain: str, resi: int) -> str:
    for a in atoms:
        if a["chain"] == chain and a["resi"] == resi:
            return _resname_to_1letter(a["resname"])
    return "X"

def _min_heavy_atom_dist(atoms: list[dict], chain1: str, resi1: int, chain2: str, resi2: int) -> float:
    # Get all heavy atoms (not starting with H) for both residues
    res1_atoms = [a for a in atoms if a["chain"] == chain1 and a["resi"] == resi1 and not a["name"].startswith("H")]
    res2_atoms = [a for a in atoms if a["chain"] == chain2 and a["resi"] == resi2 and not a["name"].startswith("H")]
    if not res1_atoms or not res2_atoms:
        return 999.0
    min_d = 999.0
    for a1 in res1_atoms:
        p1 = (a1["x"], a1["y"], a1["z"])
        for a2 in res2_atoms:
            p2 = (a2["x"], a2["y"], a2["z"])
            d = _dist(p1, p2)
            if d < min_d:
                min_d = d
    return min_d

def _is_interface(atoms: list[dict], chain: str, resi: int, other_chains: list[str]) -> tuple[bool, list[tuple[str, int]]]:
    # Check if any heavy atom of (chain, resi) is within 5.0 A of any heavy atom of other chains
    res_atoms = [a for a in atoms if a["chain"] == chain and a["resi"] == resi and not a["name"].startswith("H")]
    other_atoms = [a for a in atoms if a["chain"] in other_chains and not a["name"].startswith("H")]
    contacts = set()
    is_iface = False
    for a1 in res_atoms:
        p1 = (a1["x"], a1["y"], a1["z"])
        for a2 in other_atoms:
            p2 = (a2["x"], a2["y"], a2["z"])
            if _dist(p1, p2) <= 5.0:
                is_iface = True
                contacts.add((a2["chain"], a2["resi"]))
    return is_iface, list(contacts)


# ---------------------------------------------------------------------------
# CHECK 1 — Interface Packing Veto
# ---------------------------------------------------------------------------

def interface_packing_veto(
    mut: dict,
    atoms: list[dict],
    cbeta: dict[tuple[str, int], tuple[float, float, float]],
    ab_chains: list[str],
    companion_mutations: list[dict] | None = None,
) -> VetoResult:
    """
    Returns VETO_PACKING if a large-aromatic → small-aliphatic mutation
    occurs at the VH-VL interface without compensatory volume nearby.
    """
    chain, resi, wt_aa, mut_aa = mut["chain"], mut["resi"], mut["wt"], mut["mut"]
    key = (chain, resi)

    # Volume delta
    vol_wt  = RESIDUE_VOL.get(wt_aa, 130)
    vol_mut = RESIDUE_VOL.get(mut_aa, 130)
    delta_vol = vol_mut - vol_wt

    # Only care about large-aromatic → small mutations
    if wt_aa not in _AROMATIC_LARGE or mut_aa not in _SMALL_ALIPHATIC:
        return VetoResult(mut, "PASS", "Not an aromatic→aliphatic substitution", delta_vol)

    if delta_vol >= _PACKING_DVOL_THRESHOLD:
        return VetoResult(mut, "PASS", f"ΔVol={delta_vol:.0f} Å³ — within threshold", delta_vol)

    # Is the residue at the VH-VL interface?
    mut_coord = cbeta.get(key)
    if mut_coord is None:
        return VetoResult(mut, "PASS",
                          f"No Cβ found for {chain}:{resi} — skipping interface check", delta_vol)

    other_chains = [c for c in ab_chains if c != chain]
    is_iface, cross_chain_close = _is_interface(atoms, chain, resi, other_chains)

    if not is_iface:
        return VetoResult(mut, "PASS",
                          f"ΔVol={delta_vol:.0f} Å³ but not at VH-VL interface", delta_vol)

    # Check for compensatory mutations nearby
    compensation_vol = 0.0
    if companion_mutations:
        for comp in companion_mutations:
            if comp.get("chain") == chain and comp.get("resi") == resi:
                continue   # skip self
            comp_coord = cbeta.get((comp["chain"], comp["resi"]))
            if comp_coord and _dist(mut_coord, comp_coord) <= 5.0:
                dv = RESIDUE_VOL.get(comp.get("mut",""), 130) - RESIDUE_VOL.get(comp.get("wt",""), 130)
                if dv > 0:
                    compensation_vol += dv

    if compensation_vol >= _RESCUE_COMPENSATION_VOL:
        return VetoResult(mut, "PASS",
                          f"ΔVol={delta_vol:.0f} Å³ but compensated by +{compensation_vol:.0f} Å³", delta_vol)

    # Build rescue suggestion: find neighbor residues that could be enlarged
    rescue_candidates = []
    for (c2, r2), coord in cbeta.items():
        if c2 == chain and r2 == resi:
            continue
        if _dist(mut_coord, coord) <= 5.0:
            rescue_candidates.append((c2, r2, coord))

    rescue_sugg = None
    if rescue_candidates:
        rescue_sugg = {
            "description": "Volume compensatory mutation — enlarge a neighboring small residue",
            "target_positions": [{"chain": c, "resi": r} for c, r, _ in rescue_candidates[:3]],
            "suggested_substitutions": "A→V (+52 Å³) or G→A (+28 Å³) or V→I (+27 Å³)",
        }

    return VetoResult(
        mutation=mut,
        veto_type="VETO_PACKING",
        reason=(
            f"Large aromatic {wt_aa}→{mut_aa} at VH-VL interface "
            f"({chain}:{resi}); ΔVol={delta_vol:.0f} Å³ < threshold {_PACKING_DVOL_THRESHOLD:.0f} Å³; "
            f"interface contacts: {cross_chain_close[:3]}"
        ),
        delta_vol=delta_vol,
        rescue_suggestion=rescue_sugg,
    )


# ---------------------------------------------------------------------------
# CHECK 2 — Charge Neighborhood Veto
# ---------------------------------------------------------------------------

def charge_neighborhood_veto(
    mut: dict,
    atoms: list[dict],
    cbeta: dict[tuple[str, int], tuple[float, float, float]],
    all_mutations: list[dict] | None = None,
) -> VetoResult:
    """
    Returns VETO_CHARGE if the mutation introduces a same-sign charged pair
    (D/E or K/R) within Cβ-Cβ ≤ 4.0 Å.
    """
    chain, resi, wt_aa, mut_aa = mut["chain"], mut["resi"], mut["wt"], mut["mut"]

    # Only care about mutations that introduce a charged residue
    new_charge_sign = None
    if mut_aa in _NEGATIVE:
        new_charge_sign = "-"
    elif mut_aa in _POSITIVE:
        new_charge_sign = "+"
    else:
        return VetoResult(mut, "PASS", f"{mut_aa} is not charged", None)

    # Existing charges in structure (from WT sequence in PDB)
    mut_coord = cbeta.get((chain, resi))
    if mut_coord is None:
        return VetoResult(mut, "PASS", f"No Cβ for {chain}:{resi}", None)

    # Build set of all charged residue positions after applying mutations
    mutations_map: dict[tuple, str] = {(m["chain"], m["resi"]): m["mut"]
                                       for m in (all_mutations or [mut])}

    conflict_residues = []
    for (c2, r2), coord in cbeta.items():
        if c2 == chain and r2 == resi:
            continue
        # Determine residue identity after mutations
        aa = mutations_map.get((c2, r2)) or _get_residue_aa(atoms, c2, r2)
        existing_sign = None
        if aa in _NEGATIVE:
            existing_sign = "-"
        elif aa in _POSITIVE:
            existing_sign = "+"
        else:
            continue

        if existing_sign == new_charge_sign:
            d = _min_heavy_atom_dist(atoms, chain, resi, c2, r2)
            if d < _CHARGE_CBETA_CUTOFF:
                conflict_residues.append((c2, r2, aa, d))

    if not conflict_residues:
        return VetoResult(mut, "PASS",
                          f"{chain}:{resi} {wt_aa}→{mut_aa} introduces {new_charge_sign} charge but no same-sign neighbor within {_CHARGE_CBETA_CUTOFF} Å")

    closest = min(conflict_residues, key=lambda x: x[3])
    c2, r2, aa2, d = closest

    # Build rescue suggestion
    neutral_alt = "N" if mut_aa in _NEGATIVE else "Q"
    rescue_sugg = {
        "description": f"Neutralize the new charge: {mut_aa}→{neutral_alt} at {chain}:{resi}",
        "compensatory_mutation": {"chain": chain, "resi": resi, "wt": mut_aa, "mut": neutral_alt},
        "or_neutralize_neighbor": {
            "description": f"Alternatively neutralize existing charge at {c2}:{r2} ({aa2})",
            "chain": c2, "resi": r2, "wt": aa2,
            "mut": "N" if aa2 in _NEGATIVE else "Q",
        },
    }

    return VetoResult(
        mutation=mut,
        veto_type="VETO_CHARGE",
        reason=(
            f"Same-sign charge pair after {wt_aa}→{mut_aa} at {chain}:{resi}: "
            f"new {new_charge_sign} residue + existing {aa2} at {c2}:{r2} "
            f"(Cβ-Cβ={d:.1f} Å < {_CHARGE_CBETA_CUTOFF} Å)"
        ),
        charge_neighbor=f"{c2}:{r2}:{aa2}",
        rescue_suggestion=rescue_sugg,
    )


# ---------------------------------------------------------------------------
# CHECK 4 — Antigen Contact Preservation (works for protein OR hapten)
# ---------------------------------------------------------------------------

def _extract_antigen_atoms(
    atoms: list[dict],
    ag_chains: list[str] | None = None,
    ag_resnames: list[str] | None = None,
) -> list[dict]:
    """
    Filter atoms belonging to the antigen.
      - Protein antigen: pass ag_chains=["A"] (uses ATOM records with that chain)
      - Hapten / small molecule: pass ag_resnames=["FEN"] (uses HETATM records)
      - Both can be combined.
    Excludes hydrogens.
    """
    chains = set(ag_chains or [])
    resnames = set(r.upper() for r in (ag_resnames or []))
    out: list[dict] = []
    for a in atoms:
        if a["name"].startswith("H"):
            continue
        in_chain = chains and a["chain"] in chains and a.get("record") == "ATOM"
        in_resname = resnames and a["resname"].upper() in resnames
        if in_chain or in_resname:
            out.append(a)
    return out


def compute_contact_residues(
    atoms: list[dict],
    antigen_atoms: list[dict],
    ab_chains: list[str],
    cutoff: float = _ANTIGEN_CONTACT_CUTOFF,
) -> dict[tuple[str, int], dict]:
    """
    For every antibody residue with at least one heavy atom within `cutoff`
    of any antigen atom, return:
      {(chain, resi): {"resname": str, "n_contacts": int, "min_dist": float}}
    """
    contacts: dict[tuple[str, int], dict] = {}
    ab_atoms = [
        a for a in atoms
        if a["chain"] in ab_chains
        and a.get("record") == "ATOM"
        and not a["name"].startswith("H")
    ]
    cutoff_sq = cutoff * cutoff
    for a1 in ab_atoms:
        x1, y1, z1 = a1["x"], a1["y"], a1["z"]
        for a2 in antigen_atoms:
            dx = x1 - a2["x"]; dy = y1 - a2["y"]; dz = z1 - a2["z"]
            d2 = dx*dx + dy*dy + dz*dz
            if d2 <= cutoff_sq:
                key = (a1["chain"], a1["resi"])
                rec = contacts.get(key)
                if rec is None:
                    rec = {
                        "resname": _resname_to_1letter(a1["resname"]),
                        "n_contacts": 0,
                        "min_dist": 999.0,
                    }
                    contacts[key] = rec
                rec["n_contacts"] += 1
                d = math.sqrt(d2)
                if d < rec["min_dist"]:
                    rec["min_dist"] = d
    return contacts


def _is_conservative_substitution(wt: str, mut: str, vol_tol: float = 25.0) -> tuple[bool, str]:
    """
    Decide whether wt→mut preserves the chemical role at a contact residue.
    Returns (is_conservative, reason).
    """
    if wt == mut:
        return True, "identity"
    cls_wt = _AA_CHEMCLASS.get(wt, "x")
    cls_mut = _AA_CHEMCLASS.get(mut, "x")
    dvol = abs(RESIDUE_VOL.get(mut, 130) - RESIDUE_VOL.get(wt, 130))
    if cls_wt == cls_mut and dvol <= vol_tol:
        return True, f"same chemical class ({cls_wt}); ΔVol={dvol:.0f} Å³"
    if cls_wt == "aromatic" and cls_mut == "aromatic":
        return True, f"aromatic↔aromatic; ΔVol={dvol:.0f} Å³"
    return False, f"{cls_wt}→{cls_mut}; ΔVol={dvol:.0f} Å³"


def contact_preservation_veto(
    mut: dict,
    contact_map: dict[tuple[str, int], dict],
    critical_threshold: int = _CRITICAL_CONTACT_THRESHOLD,
) -> VetoResult:
    """
    CHECK 4 — Protect antigen-contact residues from non-conservative replacement.

    Tiers
    -----
      n_contacts >= critical_threshold + non-conservative   → VETO_AFFINITY
      n_contacts in 1..(critical_threshold-1) + non-cons.   → WARN_AFFINITY
      conservative substitution at any contact              → PASS
      no antigen contact                                    → PASS
    """
    chain, resi, wt_aa, mut_aa = mut["chain"], mut["resi"], mut["wt"], mut["mut"]
    rec = contact_map.get((chain, resi))
    if rec is None or rec["n_contacts"] == 0:
        return VetoResult(mut, "PASS", f"{chain}:{resi} not an antigen-contact residue")

    n = rec["n_contacts"]
    is_cons, cons_reason = _is_conservative_substitution(wt_aa, mut_aa)
    if is_cons:
        return VetoResult(
            mut, "PASS",
            f"{chain}:{resi}({wt_aa}) is antigen contact (n={n}, "
            f"min={rec['min_dist']:.1f} Å), but {wt_aa}→{mut_aa} is conservative ({cons_reason})",
        )

    if n >= critical_threshold:
        suggestion = {
            "description": (
                f"{chain}:{resi} is a CRITICAL antigen-contact residue; "
                f"keep chemical role of {wt_aa}"
            ),
            "suggested": (
                "W↔Y↔F (aromatic) for aromatic WT; "
                "V↔I↔L↔M (aliphatic) for hydrophobic WT; "
                "S↔T or N↔Q for polar WT"
            ),
        }
        return VetoResult(
            mut, "VETO_AFFINITY",
            reason=(
                f"{chain}:{resi}({wt_aa}) is CRITICAL antigen contact "
                f"(n={n} heavy-atom contacts, min={rec['min_dist']:.1f} Å); "
                f"{wt_aa}→{mut_aa} non-conservative ({cons_reason})"
            ),
            rescue_suggestion=suggestion,
        )

    return VetoResult(
        mut, "WARN_AFFINITY",
        reason=(
            f"{chain}:{resi}({wt_aa}) contacts antigen (n={n}, "
            f"min={rec['min_dist']:.1f} Å); {wt_aa}→{mut_aa} non-conservative "
            f"({cons_reason}) — review affinity loss risk"
        ),
    )


# ---------------------------------------------------------------------------
# CHECK 3 — Expression-sensitive FR site warning (non-blocking)
# ---------------------------------------------------------------------------

def expression_site_warn(mut: dict) -> VetoResult | None:
    """
    Returns WARN_EXPRESSION if mutation is at a known expression-sensitive
    framework position. Does NOT veto — only tags for reporting.
    """
    chain, resi = mut["chain"], mut["resi"]
    if chain == "H" and resi in _EXPR_SENSITIVE_VH:
        return VetoResult(
            mut, "WARN_EXPRESSION",
            f"VH:{resi} is expression-sensitive (Kabat FR {resi}); validate folding",
        )
    if chain == "L" and resi in _EXPR_SENSITIVE_VL:
        return VetoResult(
            mut, "WARN_EXPRESSION",
            f"VL:{resi} is expression-sensitive (Kabat FR {resi}); validate folding",
        )
    return None


# ---------------------------------------------------------------------------
# Main entry point: run_stage2_5
# ---------------------------------------------------------------------------

def run_stage2_5(
    pdb_path: str,
    ab_chains: list[str],
    candidates: list[dict],
    affinity_ddg: dict[str, float] | None = None,
    rescue: bool = True,
    antigen_chains: list[str] | None = None,
    antigen_resnames: list[str] | None = None,
) -> Stage25Result:
    """
    Run Stage 2.5 Structural Integrity Veto on a batch of mutation candidates.

    Parameters
    ----------
    pdb_path : str
        Path to WT antibody-antigen complex PDB.
    ab_chains : list[str]
        Antibody chain IDs (e.g. ["H","L"]).
    candidates : list[dict]
        Each candidate: {"chain":str, "resi":int, "wt":str, "mut":str}.
        Multi-mutation candidates can be a list of such dicts wrapped in a
        list; single-mutation candidates are plain dicts.
    affinity_ddg : dict[str, float], optional
        Stage 2 EvoEF2 ΔΔG values keyed by "CHAIN:RESI:WT:MUT" strings.
        Used to decide if vetoed candidates are worth rescuing.
    rescue : bool
        If True, high-affinity vetoed candidates get rescue suggestions.
    antigen_chains : list[str], optional
        Protein-antigen chain IDs (e.g. ["A"]). Activates CHECK 4 when set.
    antigen_resnames : list[str], optional
        Hapten / small-molecule HETATM residue names (e.g. ["FEN"]).
        Activates CHECK 4 when set. Both chains and resnames may be combined.

    Returns
    -------
    Stage25Result with .passed / .vetoed / .rescued / .warned / .summary
    """
    include_het = bool(antigen_resnames)
    atoms = _parse_pdb_atoms(pdb_path, include_hetatm=include_het)
    cbeta = _cbeta_coords(atoms)

    # Build antigen contact map if antigen is specified
    contact_map: dict[tuple[str, int], dict] = {}
    if antigen_chains or antigen_resnames:
        ag_atoms = _extract_antigen_atoms(atoms, antigen_chains, antigen_resnames)
        if ag_atoms:
            contact_map = compute_contact_residues(atoms, ag_atoms, ab_chains)

    result = Stage25Result()
    # Stash the contact map onto the result for downstream auditing
    result.summary["antigen_contact_map"] = {
        f"{c}:{r}": v for (c, r), v in contact_map.items()
    }

    def _ddg_key(m: dict) -> str:
        return f"{m['chain']}:{m['resi']}:{m['wt']}:{m['mut']}"

    audit: list[dict] = []   # flat check log for backward-compatible consumers
    candidate_audit: list[dict] = []
    result.summary["audit"] = audit
    result.summary["candidate_audit"] = candidate_audit

    for cand_idx, cand in enumerate(candidates):
        # Normalise: accept single dict or list-of-dicts (multi-mutation)
        if isinstance(cand, dict):
            mut_list = [cand]
        else:
            mut_list = list(cand)

        veto_hit: VetoResult | None = None
        all_vetoes: list[VetoResult] = []
        cand_warnings: list[VetoResult] = []
        cand_checks: list[dict] = []

        def _record_check(mut: dict, check: str, res: VetoResult) -> None:
            entry = {
                "candidate_index": cand_idx,
                "mutation": mut,
                "check": check,
                "verdict": res.veto_type,
                "reason": res.reason,
            }
            audit.append(entry)
            cand_checks.append(entry)

        for mut in mut_list:
            # CHECK 1
            pr = interface_packing_veto(mut, atoms, cbeta, ab_chains,
                                         companion_mutations=mut_list)
            _record_check(mut, "1_packing", pr)
            if pr.veto_type.startswith("VETO_"):
                all_vetoes.append(pr)
                if veto_hit is None:
                    veto_hit = pr

            # CHECK 2
            cr = charge_neighborhood_veto(mut, atoms, cbeta, all_mutations=mut_list)
            _record_check(mut, "2_charge", cr)
            if cr.veto_type.startswith("VETO_"):
                all_vetoes.append(cr)
                if veto_hit is None:
                    veto_hit = cr

            # CHECK 4 — antigen contact preservation (only if antigen given)
            if contact_map:
                ar = contact_preservation_veto(mut, contact_map)
                _record_check(mut, "4_contact", ar)
                if ar.veto_type.startswith("VETO_"):
                    all_vetoes.append(ar)
                    if veto_hit is None:
                        veto_hit = ar
                if ar.veto_type == "WARN_AFFINITY":
                    result.warned.append(ar)
                    cand_warnings.append(ar)

        # Collect warnings (non-blocking)
        for mut in mut_list:
            warn = expression_site_warn(mut)
            if warn:
                result.warned.append(warn)
                cand_warnings.append(warn)

        if veto_hit is None:
            result.passed.append(cand)
            candidate_verdict = "WARN" if cand_warnings else "PASS"
        else:
            candidate_verdict = "+".join(dict.fromkeys(v.veto_type for v in all_vetoes))
            # Check if rescue is warranted
            rescued = False
            if rescue and veto_hit.rescue_suggestion:
                ddg_val = None
                if affinity_ddg:
                    for mut in mut_list:
                        ddg_val = affinity_ddg.get(_ddg_key(mut))
                        if ddg_val is not None:
                            break
                if ddg_val is not None and ddg_val < _RESCUE_AFFINITY_THRESHOLD:
                    rescue_compound = {
                        "original_mutations": mut_list,
                        "rescue_type": veto_hit.veto_type,
                        "rescue_suggestion": veto_hit.rescue_suggestion,
                        "affinity_ddg": ddg_val,
                        "note": (
                            "RESCUE_CANDIDATE: apply compensatory mutation, then "
                            "re-screen through Stage 1 (ThermoMPNN) + Stage 2 (EvoEF2)"
                        ),
                    }
                    result.rescued.append(rescue_compound)
                    rescued = True

            if not rescued:
                result.vetoed.append(veto_hit)

        candidate_audit.append({
            "candidate_index": cand_idx,
            "candidate": cand,
            "mutations": mut_list,
            "verdict": candidate_verdict,
            "primary_veto": (
                {
                    "mutation": veto_hit.mutation,
                    "veto_type": veto_hit.veto_type,
                    "reason": veto_hit.reason,
                    "rescue_suggestion": veto_hit.rescue_suggestion,
                }
                if veto_hit else None
            ),
            "all_vetoes": [
                {
                    "mutation": v.mutation,
                    "veto_type": v.veto_type,
                    "reason": v.reason,
                    "rescue_suggestion": v.rescue_suggestion,
                }
                for v in all_vetoes
            ],
            "warnings": [
                {
                    "mutation": w.mutation,
                    "veto_type": w.veto_type,
                    "reason": w.reason,
                }
                for w in cand_warnings
            ],
            "checks": cand_checks,
        })

    result.summary.update({
        "total_input": len(candidates),
        "passed": len(result.passed),
        "vetoed": len(result.vetoed),
        "rescued": len(result.rescued),
        "warned": len(result.warned),
        "pass_rate": (
            f"{len(result.passed) / len(candidates) * 100:.1f}%"
            if candidates else "N/A"
        ),
    })
    return result


# ---------------------------------------------------------------------------
# CLI convenience wrapper (standalone use)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(
        description="Stage 2.5 Structural Integrity Veto (VAM V1.5)"
    )
    ap.add_argument("--pdb", required=True, help="WT complex PDB")
    ap.add_argument("--ab-chains", nargs="+", required=True)
    ap.add_argument("--candidates-json", required=True,
                    help='JSON file: [{"chain":"H","resi":107,"wt":"W","mut":"I"}, ...]')
    ap.add_argument("--affinity-ddg-json", default=None,
                    help='JSON file: {"H:107:W:I": -2.3, ...}')
    ap.add_argument("--no-rescue", action="store_true")
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    candidates = json.loads(open(args.candidates_json).read())
    ddg_map = (json.loads(open(args.affinity_ddg_json).read())
               if args.affinity_ddg_json else None)

    res = run_stage2_5(
        pdb_path=args.pdb,
        ab_chains=args.ab_chains,
        candidates=candidates,
        affinity_ddg=ddg_map,
        rescue=not args.no_rescue,
    )

    import dataclasses

    def _ser(obj):
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        return str(obj)

    out = {
        "summary": res.summary,
        "passed": res.passed,
        "vetoed": [dataclasses.asdict(v) for v in res.vetoed],
        "rescued": res.rescued,
        "warned": [dataclasses.asdict(w) for w in res.warned],
    }
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, default=_ser)
        print(f"Written to {args.output}")
    else:
        print(json.dumps(out, indent=2, default=_ser))
