"""
core/humanization/resurfacing.py — V5.4 roadmap
================================================

Structure-driven surface reshaping for antibody Fv humanization.

Three pillars (see config/resurfacing_v1.json):

  1) 3D Safe Zone:
        RSA(i) >= rsa_min
        AND dist(i, any CDR atom) >= dist_to_cdr_min_a
        AND dist(i, other-chain atoms) >= dist_to_other_chain_min_a
        AND Kabat(i) NOT in protected set (Vernier/interface anchors)

  2) Data-driven Target AA:
        Use a per-Kabat-position consensus from human OGRDB germlines (FR positions).
        Reject targets that introduce P/G/C (unless donor was P/G/C),
        reject if Grantham(donor, target) > grantham_distance_max,
        reject low-frequency targets (< consensus_freq_min).

  3) Scored Decision:
        Combine RSA, distance, human-frequency, physchem-conservation into a score.
        AUTO_APPLY if score >= auto_apply_min, else PENDING_HUMAN if >= pending_human_min,
        else REJECTED.

This module is intentionally read-only with respect to the standard humanization
engine. It is invoked from a separate runner (e.g. a rabbit hybrid runner) when
a chain triggers the resurfacing path (low FR identity OR per-CDR RMSD failure).
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ----------------------------------------------------------------------------- #
# Physicochemical constants
# ----------------------------------------------------------------------------- #

# Grantham distance (1974) — pairwise AA chemical dissimilarity (0..215 ish).
# Used for "physicochemical conservation" filter and score component.
GRANTHAM = {
    "AR": 112, "AN": 111, "AD": 126, "AC": 195, "AQ": 91, "AE": 107, "AG": 60,
    "AH": 86, "AI": 94, "AL": 96, "AK": 106, "AM": 84, "AF": 113, "AP": 27,
    "AS": 99, "AT": 58, "AW": 148, "AY": 112, "AV": 64,
    "RN": 86, "RD": 96, "RC": 180, "RQ": 43, "RE": 54, "RG": 125, "RH": 29,
    "RI": 97, "RL": 102, "RK": 26, "RM": 91, "RF": 97, "RP": 103, "RS": 110,
    "RT": 71, "RW": 101, "RY": 77, "RV": 96,
    "ND": 23, "NC": 139, "NQ": 46, "NE": 42, "NG": 80, "NH": 68, "NI": 149,
    "NL": 153, "NK": 94, "NM": 142, "NF": 158, "NP": 91, "NS": 46, "NT": 65,
    "NW": 174, "NY": 143, "NV": 133,
    "DC": 154, "DQ": 61, "DE": 45, "DG": 94, "DH": 81, "DI": 168, "DL": 172,
    "DK": 101, "DM": 160, "DF": 177, "DP": 108, "DS": 65, "DT": 85, "DW": 181,
    "DY": 160, "DV": 152,
    "CQ": 154, "CE": 170, "CG": 159, "CH": 174, "CI": 198, "CL": 198, "CK": 202,
    "CM": 196, "CF": 205, "CP": 169, "CS": 112, "CT": 149, "CW": 215, "CY": 194,
    "CV": 192,
    "QE": 29, "QG": 87, "QH": 24, "QI": 109, "QL": 113, "QK": 53, "QM": 101,
    "QF": 116, "QP": 76, "QS": 68, "QT": 42, "QW": 130, "QY": 99, "QV": 96,
    "EG": 98, "EH": 40, "EI": 134, "EL": 138, "EK": 56, "EM": 126, "EF": 140,
    "EP": 93, "ES": 80, "ET": 65, "EW": 152, "EY": 122, "EV": 121,
    "GH": 98, "GI": 135, "GL": 138, "GK": 127, "GM": 127, "GF": 153, "GP": 42,
    "GS": 56, "GT": 59, "GW": 184, "GY": 147, "GV": 109,
    "HI": 94, "HL": 99, "HK": 32, "HM": 87, "HF": 100, "HP": 77, "HS": 89,
    "HT": 47, "HW": 115, "HY": 83, "HV": 84,
    "IL": 5, "IK": 102, "IM": 10, "IF": 21, "IP": 95, "IS": 142, "IT": 89,
    "IW": 61, "IY": 33, "IV": 29,
    "LK": 107, "LM": 15, "LF": 22, "LP": 98, "LS": 145, "LT": 92, "LW": 61,
    "LY": 36, "LV": 32,
    "KM": 95, "KF": 102, "KP": 103, "KS": 121, "KT": 78, "KW": 110, "KY": 85,
    "KV": 97,
    "MF": 28, "MP": 87, "MS": 135, "MT": 81, "MW": 67, "MY": 36, "MV": 21,
    "FP": 114, "FS": 155, "FT": 103, "FW": 40, "FY": 22, "FV": 50,
    "PS": 74, "PT": 38, "PW": 147, "PY": 110, "PV": 68,
    "ST": 58, "SW": 177, "SY": 144, "SV": 124,
    "TW": 128, "TY": 92, "TV": 69,
    "WY": 37, "WV": 88,
    "YV": 55,
}

CHARGED_POS = set("KRH")
CHARGED_NEG = set("DE")

# Side-chain max accessible surface area (Tien et al. 2013, "theoretical" reference)
# Used to compute relative SASA. Values in A^2.
TIEN_REF = {
    "ALA": 129.0, "ARG": 274.0, "ASN": 195.0, "ASP": 193.0, "CYS": 167.0,
    "GLU": 223.0, "GLN": 225.0, "GLY": 104.0, "HIS": 224.0, "ILE": 197.0,
    "LEU": 201.0, "LYS": 236.0, "MET": 224.0, "PHE": 240.0, "PRO": 159.0,
    "SER": 155.0, "THR": 172.0, "TRP": 285.0, "TYR": 263.0, "VAL": 174.0,
}

THREE_TO_ONE = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLU": "E", "GLN": "Q", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
}


def grantham(a: str, b: str) -> int:
    """Symmetric Grantham distance lookup. 0 for identity."""
    if a == b:
        return 0
    key = a + b
    if key in GRANTHAM:
        return GRANTHAM[key]
    rev = b + a
    return GRANTHAM.get(rev, 100)


# ----------------------------------------------------------------------------- #
# Config loader
# ----------------------------------------------------------------------------- #

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "resurfacing_v1.json"


def load_resurfacing_config(path: Optional[Path] = None) -> Dict[str, Any]:
    p = Path(path) if path else DEFAULT_CONFIG_PATH
    return json.loads(p.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------- #
# Per-residue structural feature extraction
# ----------------------------------------------------------------------------- #

@dataclass
class ResidueFeature:
    linear_index: int
    pdb_chain: str
    pdb_resnum: int
    donor_aa: str
    kabat_pos: Optional[int]
    kabat_ins: str
    region: str            # FR1/FR2/FR3/FR4/CDR1/CDR2/CDR3/UNK
    rsa: Optional[float]
    dist_to_cdr_a: Optional[float]
    dist_to_other_chain_a: Optional[float]


def _load_pdb_atoms(pdb_path: str) -> Dict[str, List[Tuple[int, str, np.ndarray]]]:
    """Return per-chain list of (resnum, resname, ca_xyz) in PDB order."""
    by_chain: Dict[str, List[Tuple[int, str, np.ndarray]]] = {}
    with open(pdb_path) as f:
        for line in f:
            if not (line.startswith("ATOM") or line.startswith("HETATM")):
                continue
            if line[12:16].strip() != "CA":
                continue
            chain = line[21]
            try:
                resnum = int(line[22:26].strip())
                resname = line[17:20].strip()
                xyz = np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])])
            except Exception:
                continue
            by_chain.setdefault(chain, []).append((resnum, resname, xyz))
    return by_chain


def _load_pdb_all_atoms(pdb_path: str) -> Dict[str, List[Tuple[int, str, np.ndarray]]]:
    """Return per-chain list of (resnum, atom_name, xyz) for all heavy atoms."""
    by_chain: Dict[str, List[Tuple[int, str, np.ndarray]]] = {}
    with open(pdb_path) as f:
        for line in f:
            if not (line.startswith("ATOM") or line.startswith("HETATM")):
                continue
            chain = line[21]
            atom = line[12:16].strip()
            if atom.startswith("H"):  # skip hydrogens
                continue
            try:
                resnum = int(line[22:26].strip())
                xyz = np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])])
            except Exception:
                continue
            by_chain.setdefault(chain, []).append((resnum, atom, xyz))
    return by_chain


def _compute_sasa_relative(pdb_path: str) -> Dict[Tuple[str, int], float]:
    """Compute relative SASA per residue. Try Bio.PDB.SASA first, fallback to neighbor count."""
    out: Dict[Tuple[str, int], float] = {}
    try:
        import Bio.PDB as bpdb  # type: ignore
        from Bio.PDB.SASA import ShrakeRupley  # type: ignore

        parser = bpdb.PDBParser(QUIET=True)
        structure = parser.get_structure("ab", pdb_path)
        sr = ShrakeRupley(probe_radius=1.4, n_points=960)
        sr.compute(structure, level="R")
        for model in structure:
            for chain in model:
                for res in chain:
                    if not bpdb.is_aa(res, standard=True):
                        continue
                    resnum = res.id[1]
                    sasa = res.sasa
                    ref = TIEN_REF.get(res.resname, 200.0)
                    rel = min(1.0, sasa / ref) if ref > 0 else 0.0
                    out[(chain.id, resnum)] = rel
        if out:
            return out
    except Exception:
        pass

    # Fallback: Cα neighbor count (more neighbors → buried).
    try:
        atoms = []
        with open(pdb_path) as f:
            for line in f:
                if line.startswith("ATOM") and line[12:16].strip() == "CA":
                    chain = line[21]
                    resnum = int(line[22:26].strip())
                    xyz = np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])])
                    atoms.append((chain, resnum, xyz))
        for i, (chain_i, resnum_i, xyz_i) in enumerate(atoms):
            n_neigh = 0
            for j, (_, _, xyz_j) in enumerate(atoms):
                if i == j:
                    continue
                if np.linalg.norm(xyz_i - xyz_j) <= 10.0:
                    n_neigh += 1
            # Empirical: <16 neighbors at 10A → exposed (rsa~0.4), >24 buried (rsa~0.05).
            rel = max(0.0, min(1.0, (24 - n_neigh) / 16.0))
            out[(chain_i, resnum_i)] = rel
    except Exception:
        pass
    return out


def _imgt_cdr_resnums(chain_letter: str) -> set:
    """Return set of IMGT residue numbers that fall in any CDR for this chain.
    Chain letter is 'H' for heavy or 'L' for light (PDB chain ID convention).
    """
    if chain_letter == "H":
        ranges = [(26, 32), (52, 56), (105, 117)]
    else:
        ranges = [(24, 34), (50, 56), (105, 117)]
    return {r for lo, hi in ranges for r in range(lo, hi + 1)}


def extract_residue_features(
    donor_pdb: str,
    donor_seq: str,
    chain_letter: str,
    kabat_dict: Dict[Tuple[int, str], str],
) -> List[ResidueFeature]:
    """For a given donor chain, return per-linear-position structural features.

    `kabat_dict` is the donor sequence's KabatDict (already computed by caller).
    """
    by_chain_ca = _load_pdb_atoms(donor_pdb)
    by_chain_all = _load_pdb_all_atoms(donor_pdb)
    rsa_map = _compute_sasa_relative(donor_pdb)

    if chain_letter not in by_chain_ca:
        return []

    other = "L" if chain_letter == "H" else "H"
    cdr_set = _imgt_cdr_resnums(chain_letter)

    # All CDR atom coordinates (this chain) → for distance to CDR
    cdr_atoms = np.array([
        xyz for resnum, _, xyz in by_chain_all.get(chain_letter, [])
        if resnum in cdr_set
    ]) if by_chain_all.get(chain_letter) else np.zeros((0, 3))

    other_atoms = np.array([
        xyz for _, _, xyz in by_chain_all.get(other, [])
    ]) if by_chain_all.get(other) else np.zeros((0, 3))

    # Per-residue heavy atoms (this chain), grouped by resnum
    per_res_atoms: Dict[int, List[np.ndarray]] = {}
    for resnum, atom, xyz in by_chain_all.get(chain_letter, []):
        per_res_atoms.setdefault(resnum, []).append(xyz)

    chain_residues = by_chain_ca[chain_letter]  # in PDB order
    if len(chain_residues) != len(donor_seq):
        # Tolerate small mismatch (terminal trim) by truncating to min.
        n = min(len(chain_residues), len(donor_seq))
        chain_residues = chain_residues[:n]

    # Build linear-index → kabat-key list, in the same order as the donor sequence.
    sorted_kabat = sorted(kabat_dict.keys(), key=lambda k: (k[0], k[1] or ""))
    if len(sorted_kabat) != len(donor_seq):
        # Anarcii sometimes drops a terminal residue. Pad with None.
        # Safer: align by length min.
        sorted_kabat = sorted_kabat[: len(donor_seq)]

    feats: List[ResidueFeature] = []
    for i, (resnum, resname, _) in enumerate(chain_residues):
        donor_aa = THREE_TO_ONE.get(resname, donor_seq[i] if i < len(donor_seq) else "X")
        kabat_key = sorted_kabat[i] if i < len(sorted_kabat) else (None, "")
        kabat_pos = kabat_key[0] if kabat_key else None
        kabat_ins = kabat_key[1] if kabat_key else ""

        rsa = rsa_map.get((chain_letter, resnum))

        # Distance to CDR atoms (this chain)
        my_atoms = per_res_atoms.get(resnum) or []
        if my_atoms and cdr_atoms.size > 0:
            min_d_cdr = min(
                float(np.min(np.linalg.norm(cdr_atoms - a, axis=1))) for a in my_atoms
            )
        else:
            min_d_cdr = None

        # Distance to other chain (interface)
        if my_atoms and other_atoms.size > 0:
            min_d_other = min(
                float(np.min(np.linalg.norm(other_atoms - a, axis=1))) for a in my_atoms
            )
        else:
            min_d_other = None

        # Kabat → region label
        region = _kabat_region(kabat_pos, "VH" if chain_letter == "H" else "VL")

        feats.append(ResidueFeature(
            linear_index=i,
            pdb_chain=chain_letter,
            pdb_resnum=resnum,
            donor_aa=donor_aa,
            kabat_pos=kabat_pos,
            kabat_ins=kabat_ins,
            region=region,
            rsa=round(rsa, 3) if rsa is not None else None,
            dist_to_cdr_a=round(min_d_cdr, 2) if min_d_cdr is not None else None,
            dist_to_other_chain_a=round(min_d_other, 2) if min_d_other is not None else None,
        ))
    return feats


def _kabat_region(pos: Optional[int], chain: str) -> str:
    if pos is None:
        return "UNK"
    if chain == "VH":
        if 1 <= pos <= 25:
            return "FR1"
        if 26 <= pos <= 35:
            return "CDR1"
        if 36 <= pos <= 49:
            return "FR2"
        if 50 <= pos <= 65:
            return "CDR2"
        if 66 <= pos <= 94:
            return "FR3"
        if 95 <= pos <= 102:
            return "CDR3"
        if 103 <= pos <= 113:
            return "FR4"
    else:  # VL
        if 1 <= pos <= 23:
            return "FR1"
        if 24 <= pos <= 34:
            return "CDR1"
        if 35 <= pos <= 49:
            return "FR2"
        if 50 <= pos <= 56:
            return "CDR2"
        if 57 <= pos <= 88:
            return "FR3"
        if 89 <= pos <= 97:
            return "CDR3"
        if 98 <= pos <= 110:
            return "FR4"
    return "UNK"


# ----------------------------------------------------------------------------- #
# Human consensus AA table
# ----------------------------------------------------------------------------- #

def build_human_consensus(
    germline_json_path: Path,
    cache_path: Optional[Path] = None,
    refresh: bool = False,
) -> Dict[str, Dict[str, float]]:
    """Build per-Kabat-position AA frequency table from OGRDB human germlines.

    Returns: { "VH": { "5": {"V": 0.62, "L": 0.20, ...}, ... }, ... }
    Numbering: each germline is Anarcii-numbered in Kabat scheme.
    """
    if cache_path and cache_path.exists() and not refresh:
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if cached.get("_source") == str(germline_json_path):
                return cached.get("table", {})
        except Exception:
            pass

    germlines = json.loads(germline_json_path.read_text(encoding="utf-8"))

    # Determine chain from filename
    name = germline_json_path.name.upper()
    if "IGHV" in name:
        chain_label = "VH"
    elif "IGKV" in name or "IGLV" in name:
        chain_label = "VL"
    else:
        chain_label = "UNK"

    # Number every germline once with Anarcii, then convert to Kabat.
    from anarcii import Anarcii  # type: ignore
    eng = Anarcii(seq_type="antibody", verbose=False)

    counts: Dict[str, Dict[str, int]] = {}
    seqs = [(gid, s) for gid, s in germlines.items() if isinstance(s, str) and s]
    if not seqs:
        return {}

    pairs = [(gid, s) for gid, s in seqs]
    try:
        eng.number(pairs)
    except Exception as e:
        return {"_error": f"anarcii failed: {e}"}
    try:
        result = eng.to_scheme("kabat")
    except Exception as e:
        return {"_error": f"anarcii to_scheme(kabat) failed: {e}"}

    if isinstance(result, dict):
        items = result.items()
    else:
        items = result

    for gid, entry in items:
        if not entry or not isinstance(entry, dict):
            continue
        numbering = entry.get("numbering") or []
        for (pos, ins), aa in numbering:
            if aa == "-" or not aa:
                continue
            key = str(pos) if not (ins and ins.strip()) else f"{pos}{ins.strip()}"
            counts.setdefault(key, {})
            counts[key][aa] = counts[key].get(aa, 0) + 1

    # Convert to frequencies
    freq_table: Dict[str, Dict[str, float]] = {}
    for kpos, aa_counts in counts.items():
        total = sum(aa_counts.values())
        if total <= 0:
            continue
        freq_table[kpos] = {aa: round(c / total, 4) for aa, c in aa_counts.items()}

    out = {chain_label: freq_table}
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(
            {"_source": str(germline_json_path), "table": out, "n_germlines": len(seqs)},
            indent=2, ensure_ascii=False,
        ), encoding="utf-8")
    return out


# ----------------------------------------------------------------------------- #
# Scored mutation selection
# ----------------------------------------------------------------------------- #

@dataclass
class CandidateMutation:
    linear_index: int
    pdb_resnum: int
    kabat_pos: Optional[int]
    kabat_ins: str
    region: str
    donor_aa: str
    target_aa: str
    rsa: Optional[float]
    dist_to_cdr_a: Optional[float]
    dist_to_other_chain_a: Optional[float]
    target_human_freq: Optional[float]
    grantham_distance: int
    score: float
    decision: str  # "AUTO_APPLY" / "PENDING_HUMAN" / "REJECTED"
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    rejection_reasons: List[str] = field(default_factory=list)


def _score_one(
    feat: ResidueFeature,
    target_aa: str,
    target_freq: Optional[float],
    config: Dict[str, Any],
    long_h3_root: bool,
    is_protected: bool,
) -> CandidateMutation:
    """Score a single donor→target candidate."""
    th = config["thresholds_3d"]
    sel = config["target_aa_selection"]
    sc = config["scoring"]
    weights = sc["weights"]
    pen = sc["penalties"]
    decisions = sc["decision"]

    reasons: List[str] = []
    breakdown: Dict[str, float] = {}

    donor_aa = feat.donor_aa
    if donor_aa == target_aa or target_aa in ("", "X", "-"):
        reasons.append("no_change")
        return CandidateMutation(
            linear_index=feat.linear_index, pdb_resnum=feat.pdb_resnum,
            kabat_pos=feat.kabat_pos, kabat_ins=feat.kabat_ins, region=feat.region,
            donor_aa=donor_aa, target_aa=target_aa,
            rsa=feat.rsa, dist_to_cdr_a=feat.dist_to_cdr_a,
            dist_to_other_chain_a=feat.dist_to_other_chain_a,
            target_human_freq=target_freq,
            grantham_distance=0,
            score=0.0, decision="REJECTED",
            score_breakdown={}, rejection_reasons=reasons,
        )

    # 1) Hard gates
    if is_protected:
        reasons.append("protected_kabat")
    if feat.region.startswith("CDR"):
        reasons.append("cdr_position")
    if feat.rsa is None or feat.rsa < th["rsa_min"]:
        reasons.append(f"rsa_below_min:{feat.rsa}<{th['rsa_min']}")
    if feat.dist_to_cdr_a is None or feat.dist_to_cdr_a < th["dist_to_cdr_min_a"]:
        reasons.append(f"too_close_to_cdr:{feat.dist_to_cdr_a}<{th['dist_to_cdr_min_a']}")
    if feat.dist_to_other_chain_a is None or feat.dist_to_other_chain_a < th["dist_to_other_chain_min_a"]:
        reasons.append(f"too_close_to_other_chain:{feat.dist_to_other_chain_a}<{th['dist_to_other_chain_min_a']}")
    if target_aa in sel["forbid_introduce"] and donor_aa not in sel["forbid_introduce"]:
        reasons.append(f"forbid_introduce:{target_aa}")
    if donor_aa in sel["forbid_remove"]:
        reasons.append(f"forbid_remove:{donor_aa}")
    g = grantham(donor_aa, target_aa)
    if g > sel["grantham_distance_max"]:
        reasons.append(f"grantham_distance:{g}>{sel['grantham_distance_max']}")
    if target_freq is not None and target_freq < sel["consensus_freq_min"]:
        reasons.append(f"low_human_freq:{target_freq}<{sel['consensus_freq_min']}")

    # 2) Score components (only meaningful when the hard gates are not all-fatal)
    rsa_score = (feat.rsa - th["rsa_min"]) / max(0.01, 1.0 - th["rsa_min"]) if feat.rsa is not None else 0.0
    dist_cdr_score = min(1.0, ((feat.dist_to_cdr_a or 0) - th["dist_to_cdr_min_a"]) / 6.0) \
        if feat.dist_to_cdr_a is not None else 0.0
    dist_int_score = min(1.0, ((feat.dist_to_other_chain_a or 0) - th["dist_to_other_chain_min_a"]) / 5.0) \
        if feat.dist_to_other_chain_a is not None else 0.0
    human_freq_score = min(1.0, (target_freq or 0.0) / 0.6)  # 60% considered "high consensus"
    physchem_score = max(0.0, 1.0 - g / 100.0)

    s = (
        weights["rsa"] * rsa_score
        + weights["dist_cdr"] * dist_cdr_score
        + weights["dist_interface"] * dist_int_score
        + weights["human_freq"] * human_freq_score
        + weights["physchem"] * physchem_score
    )
    breakdown.update({
        "rsa": round(weights["rsa"] * rsa_score, 3),
        "dist_cdr": round(weights["dist_cdr"] * dist_cdr_score, 3),
        "dist_interface": round(weights["dist_interface"] * dist_int_score, 3),
        "human_freq": round(weights["human_freq"] * human_freq_score, 3),
        "physchem": round(weights["physchem"] * physchem_score, 3),
    })

    # 3) Penalties
    charge_flip = (
        (donor_aa in CHARGED_POS and target_aa in CHARGED_NEG)
        or (donor_aa in CHARGED_NEG and target_aa in CHARGED_POS)
    )
    if charge_flip:
        s -= pen["charge_flip"]
        breakdown["charge_flip_penalty"] = -pen["charge_flip"]
    if target_aa in sel["forbid_introduce"] and donor_aa not in sel["forbid_introduce"]:
        s -= pen["forbidden_aa"]
        breakdown["forbidden_aa_penalty"] = -pen["forbidden_aa"]
    if is_protected:
        s -= pen["vernier_proximity"]
        breakdown["vernier_proximity_penalty"] = -pen["vernier_proximity"]
    if long_h3_root:
        s -= pen["long_h3_root"]
        breakdown["long_h3_root_penalty"] = -pen["long_h3_root"]

    # 4) Decision: any hard-gate violation → REJECTED regardless of score
    if reasons:
        decision = "REJECTED"
    elif s >= decisions["auto_apply_min"]:
        decision = "AUTO_APPLY"
    elif s >= decisions["pending_human_min"]:
        decision = "PENDING_HUMAN"
    else:
        decision = "REJECTED"
        reasons.append(f"score_below_min:{round(s,2)}<{decisions['pending_human_min']}")

    return CandidateMutation(
        linear_index=feat.linear_index,
        pdb_resnum=feat.pdb_resnum,
        kabat_pos=feat.kabat_pos,
        kabat_ins=feat.kabat_ins,
        region=feat.region,
        donor_aa=donor_aa, target_aa=target_aa,
        rsa=feat.rsa, dist_to_cdr_a=feat.dist_to_cdr_a,
        dist_to_other_chain_a=feat.dist_to_other_chain_a,
        target_human_freq=target_freq,
        grantham_distance=g,
        score=round(s, 3),
        decision=decision,
        score_breakdown=breakdown,
        rejection_reasons=reasons,
    )


def select_safe_mutations(
    donor_seq: str,
    features: List[ResidueFeature],
    chain: str,                      # "VH" or "VL"
    target_germline_seq: str,
    consensus_table: Dict[str, Dict[str, float]],   # subset for this chain
    config: Dict[str, Any],
    long_h3: bool = False,
) -> List[CandidateMutation]:
    """Iterate every donor FR position and produce a CandidateMutation for it."""
    protected = set(config.get("protected_kabat", {}).get(chain, []))
    long_h3_root_set = set(config.get("long_h3_root_kabat_vh", [])) if chain == "VH" and long_h3 else set()

    # Number target germline in Kabat once → per-Kabat-key map
    from .kabat_utils import get_kabat_numbering, sorted_keys  # noqa: PLC0415
    target_kabat = get_kabat_numbering(target_germline_seq) or {}

    chain_freq = consensus_table.get(chain, {})

    out: List[CandidateMutation] = []
    for feat in features:
        if feat.region.startswith("CDR"):
            continue   # CDRs never resurfaced
        if feat.kabat_pos is None:
            continue

        kabat_key_str = (
            str(feat.kabat_pos) if not (feat.kabat_ins and feat.kabat_ins.strip())
            else f"{feat.kabat_pos}{feat.kabat_ins.strip()}"
        )

        # Choose target AA: prefer per-position consensus AA (highest-frequency human residue)
        # that is *also* the chosen-germline residue when consistent. Otherwise use top consensus.
        target_aa = ""
        target_freq: Optional[float] = None
        per_pos_freq = chain_freq.get(kabat_key_str, {})
        if per_pos_freq:
            sorted_aa = sorted(per_pos_freq.items(), key=lambda kv: -kv[1])
            top_aa, top_f = sorted_aa[0]
            target_aa = top_aa
            target_freq = top_f
        else:
            # Fallback: target germline residue at same Kabat position
            tg = target_kabat.get((feat.kabat_pos, feat.kabat_ins))
            if tg:
                target_aa = tg
                target_freq = None

        is_protected = feat.kabat_pos in protected
        long_h3_root = (chain == "VH" and feat.kabat_pos in long_h3_root_set)

        cand = _score_one(
            feat=feat, target_aa=target_aa, target_freq=target_freq,
            config=config, long_h3_root=long_h3_root, is_protected=is_protected,
        )
        out.append(cand)

    return out


def apply_chain_caps(
    candidates: List[CandidateMutation],
    chain: str,
    config: Dict[str, Any],
) -> List[CandidateMutation]:
    """Enforce chain-level mutation caps. Down-rank lowest-score AUTO_APPLY first."""
    caps = config["chain_caps"]
    max_total = caps[f"{chain.lower()}_max_mut"]
    max_per_fr = caps["max_per_fr"][chain]

    auto_applied = sorted(
        [c for c in candidates if c.decision == "AUTO_APPLY"],
        key=lambda c: -c.score,
    )

    # Cap per-FR
    fr_count: Dict[str, int] = {}
    accepted: List[CandidateMutation] = []
    for c in auto_applied:
        fr = c.region if c.region.startswith("FR") else "FR?"
        if fr_count.get(fr, 0) >= max_per_fr:
            c.decision = "REJECTED"
            c.rejection_reasons.append(f"per_fr_cap:{fr}>={max_per_fr}")
            continue
        if len(accepted) >= max_total:
            c.decision = "REJECTED"
            c.rejection_reasons.append(f"chain_cap:{max_total}")
            continue
        accepted.append(c)
        fr_count[fr] = fr_count.get(fr, 0) + 1
    return candidates


def assemble_final_sequence(donor_seq: str, candidates: List[CandidateMutation]) -> str:
    """Apply only AUTO_APPLY mutations to donor sequence (linear position)."""
    seq = list(donor_seq)
    for c in candidates:
        if c.decision != "AUTO_APPLY":
            continue
        i = c.linear_index
        if 0 <= i < len(seq):
            seq[i] = c.target_aa
    return "".join(seq)


def summarise_decisions(candidates: List[CandidateMutation]) -> Dict[str, Any]:
    auto = [c for c in candidates if c.decision == "AUTO_APPLY"]
    pend = [c for c in candidates if c.decision == "PENDING_HUMAN"]
    rej = [c for c in candidates if c.decision == "REJECTED"]
    return {
        "n_auto_apply": len(auto),
        "n_pending_human": len(pend),
        "n_rejected": len(rej),
        "auto_apply": [asdict(c) for c in auto],
        "pending_human": [asdict(c) for c in pend],
        "rejected_top10": [asdict(c) for c in sorted(rej, key=lambda c: -c.score)[:10]],
    }
