"""
fr_mutation_sites.py — FR-only sequence indices for CMC candidate mutations
===========================================================================
Enumerates specific residue positions in VH/VL that lie in IMGT framework
regions (not CDR), for display alongside rule-based CMC metrics.

CMC mutation policy filters (applied in order):
  1. FR-only mask -- CDR positions are never emitted as automated substitutions.
  2. Vernier mask -- canonical CDR-support positions are protected.
  3. Surface exposure -- exposed framework candidates are preferred; buried core is protected.
  4. Structure protection -- positions within 5 A of CDR loops or the VH/VL interface are protected when a PDB is available.

Sequence-only mode still emits conservative FR-only candidates, but structure-aware reports apply the full CMC mutation policy layer.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from Bio.SeqUtils.ProtParam import ProteinAnalysis

from core.vhh_humanization import IMGT_REGIONS

_HYDRO_RUN = set("AILMFWV")
_POS_CHARGE = set("KR")
_NEG_CHARGE = set("DE")
# Conservative replacements for pI / net-charge too_high (user-facing; not a clinical claim)
_AA_REPLACEMENT_HINT = {
    "K": "Q",
    "R": "Q",
    "D": "N",
    "E": "N",
}
_NEG_REPLACEMENT_HINT = {
    "D": "N",
    "E": "Q",
}
# Hydrophobicity-reducing substitutions (aggregation / patch risk).
# Goal: lower local hydrophobicity while maintaining backbone geometry.
# Tier 1 = most conservative (similar size); Tier 2 = acceptable fallback.
_HYDRO_REDUCE_HINT: Dict[str, str] = {
    "A": "S",   # Ala → Ser: +OH, minimal steric change
    "I": "T",   # Ile → Thr: +OH, β-branched still
    "L": "S",   # Leu → Ser
    "M": "T",   # Met → Thr: removes thioether
    "F": "S",   # Phe → Ser: removes aromatic / hydrophobic bulk
    "W": "S",   # Trp → Ser: large → small; verify structurally first
    "V": "T",   # Val → Thr: isosteric +OH
}
_HYDRO_REDUCE_NOTE: Dict[str, str] = {
    "W": "Trp often structurally important; verify by structure before substituting.",
    "F": "Phe aromatic packing may stabilize fold; confirm SASA > 30% before modifying.",
}

# ── Vernier IMGT sets ─────────────────────────────────────────────────────────
# Built from kabat_utils at import time; soft-fallback to empty sets on error.
try:
    from core.humanization.kabat_utils import (
        VERNIER_KABAT_TO_IMGT_VH,
        VERNIER_KABAT_TO_IMGT_VL,
    )
    _VERNIER_IMGT_VH: Set[int] = set(VERNIER_KABAT_TO_IMGT_VH.values())
    _VERNIER_IMGT_VL: Set[int] = set(VERNIER_KABAT_TO_IMGT_VL.values())
except Exception:
    _VERNIER_IMGT_VH = set()
    _VERNIER_IMGT_VL = set()

SASA_THRESHOLD = 0.30  # relative SASA; residues below this are treated as buried


# ─────────────────────────────────────────────────────────────────────────────
# Smart-CMC safety guards (Smoke-test driven 2026-05-15)
# ─────────────────────────────────────────────────────────────────────────────

# Charge safe-zone targets (used to stop greedy charge mutation enumeration).
# Sources: AbRef-458 clinical p25–p75 envelope for IgG VH+VL Fv.
CHARGE_SAFE_ZONE = {
    "net_charge_pH7": (0.5, 3.0),
    "pI":             (6.5, 8.5),
}

# Hydrophobic residues that, when introduced as substitutes (e.g. G→A), can
# extend an existing run and create a new aggregation motif (≥3 consecutive
# hydrophobic residues). Used by _would_create_aggregation_motif.
_AGG_HYDRO = set("AILMFWVY")  # Y included because YxY-style aromatic patches still aggregate


# ─────────────────────────────────────────────────────────────────────────────
# DeepFR-CTX HARD-veto guard (Option A)
# ─────────────────────────────────────────────────────────────────────────────
# Mirror of contextual_substitution_engine._is_protected() HARD tier.
# Source: ctx_guard.py / ABENGINECORE_GOVERNANCE §3 / standards_ssot DFR-1.0.
#
# Positions listed here are NEVER allowed as CMC mutation candidates,
# regardless of the metric being optimised (stability, charge, hydrophobicity).
#
# SOFT tier (VK FR2 Tyr/Phe interface) is NOT blocked here; those can
# participate in CMC mutations because they are not structurally indispensable
# in all contexts.  Add to _SOFT_DEEPFR_PROTECTED if policy changes.

def _is_deepfr_ctx_hard_protected(aa: str, region: str, chain: str) -> Tuple[bool, str]:
    """
    Returns (True, reason) if this residue is HARD-protected under DeepFR-CTX
    and must never be a CMC mutation candidate.

    Parameters
    ----------
    aa     : single-letter amino acid at this position
    region : IMGT/Chothia region label, e.g. "FR1", "FR2", "CDR1", …
    chain  : "VH" or "VL" (VK treated as VL)

    Protection rules (HARD tier only):
      • Cys (all FR, VH + VL)   — canonical disulfide bond; structural
      • Trp in VH FR1 or FR2    — β-sheet anchor (Kabat W36 / equivalent)
      • Trp in VL (all FR)      — VL structural anchor (Kabat W35 equivalent)
    """
    aa = aa.upper()
    region_upper = (region or "").upper()
    chain_upper = (chain or "").upper()

    if aa == "C":
        return True, "deepfr_ctx_hard: canonical_cys"

    if chain_upper == "VH" and aa == "W" and region_upper in ("FR1", "FR2"):
        return True, "deepfr_ctx_hard: conserved_trp_VH_beta_sheet_anchor"

    if chain_upper in ("VL", "VK") and aa == "W":
        return True, "deepfr_ctx_hard: conserved_trp_VL_structural_anchor"

    return False, ""


def _would_create_aggregation_motif(
    seq: str, idx0: int, new_aa: str, run_len_threshold: int = 3
) -> bool:
    """
    Check whether substituting seq[idx0] → new_aa creates a new ≥N-consecutive
    hydrophobic run that did not exist with the original residue.

    Smoke-test 2026-05-15 evidence: abiprubart Stability variant (VL 98 G→A,
    VL 99 G→A) introduced an AAA run flanked by existing hydrophobic residues,
    raising agg_motifs from 2 → 3 even while improving instability_index.
    """
    if not seq or not (0 <= idx0 < len(seq)) or len(new_aa) != 1:
        return False
    new_aa = new_aa.upper()
    if new_aa not in _AGG_HYDRO:
        return False  # non-hydrophobic substitution can't create a hydrophobic run
    orig_aa = seq[idx0].upper()
    if orig_aa in _AGG_HYDRO:
        return False  # already hydrophobic; substitution doesn't change run topology
    # Build modified sequence (cheap; single char)
    modified = seq[:idx0] + new_aa + seq[idx0 + 1:]
    # Count hydrophobic neighbours on both sides
    left = 0
    j = idx0 - 1
    while j >= 0 and modified[j].upper() in _AGG_HYDRO:
        left += 1
        j -= 1
    right = 0
    j = idx0 + 1
    while j < len(modified) and modified[j].upper() in _AGG_HYDRO:
        right += 1
        j += 1
    new_run_len = left + 1 + right  # this is the run length after substitution
    if new_run_len < run_len_threshold:
        return False
    # Did the same window exist before? Check the same span in the original seq.
    # If original idx0 was non-hydrophobic, original had max consecutive run = max(left, right).
    original_max = max(left, right)
    return original_max < run_len_threshold


def _find_max_hydro_window(seq: str, window: int = 9) -> Tuple[int, int, float]:
    """
    Return (start_0idx, end_0idx_exclusive, fraction) for the highest-density
    hydrophobic 9-mer window in ``seq``. End is exclusive (slice-compatible).
    """
    s = (seq or "").upper()
    if len(s) < window:
        return 0, len(s), round(sum(1 for a in s if a in _HYDRO_RUN) / max(window, 1), 3)
    best_i = 0
    best_count = -1
    for i in range(len(s) - window + 1):
        c = sum(1 for a in s[i:i + window] if a in _HYDRO_RUN)
        if c > best_count:
            best_count = c
            best_i = i
    return best_i, best_i + window, round(best_count / window, 3)


def _is_window_cdr_internal(
    rows: List[Dict[str, Any]], start_0idx: int, end_0idx: int, min_cdr_frac: float = 0.6
) -> Tuple[bool, str]:
    """
    Given the row map for a chain, return (is_cdr_driven, region_label).
    True when ≥`min_cdr_frac` of the window residues fall inside any CDR.
    """
    if not rows:
        return False, "UNK"
    row_map = {r["seq_idx0"]: r.get("region", "UNK") for r in rows}
    total = max(end_0idx - start_0idx, 1)
    cdr_count = 0
    cdr_labels: List[str] = []
    for i in range(start_0idx, end_0idx):
        reg = row_map.get(i, "UNK")
        if reg.startswith("CDR"):
            cdr_count += 1
            if reg not in cdr_labels:
                cdr_labels.append(reg)
    is_cdr = (cdr_count / total) >= min_cdr_frac
    return is_cdr, "/".join(cdr_labels) if cdr_labels else "FR"


def _compute_protect_55_as_cdr2(rows: List[Dict[str, Any]]) -> bool:
    cdr2_raw_len = 0
    has_55 = False
    for row in rows:
        pos = row.get("pos")
        aa = row.get("aa")
        if not isinstance(pos, int) or not isinstance(aa, str) or aa == "-":
            continue
        if IMGT_REGIONS["CDR2"]["start"] <= pos <= IMGT_REGIONS["CDR2"]["end"]:
            cdr2_raw_len += 1
        if pos == 55:
            has_55 = True
    return bool(has_55 and (cdr2_raw_len + 1 >= 17))


def _imgt_residue_region(pos: int, protect_55: bool) -> str:
    if IMGT_REGIONS["FR1"]["start"] <= pos <= IMGT_REGIONS["FR1"]["end"]:
        return "FR1"
    if IMGT_REGIONS["CDR1"]["start"] <= pos <= IMGT_REGIONS["CDR1"]["end"]:
        return "CDR1"
    if IMGT_REGIONS["FR2"]["start"] <= pos <= IMGT_REGIONS["FR2"]["end"]:
        if pos == 55 and protect_55:
            return "CDR2"
        return "FR2"
    if IMGT_REGIONS["CDR2"]["start"] <= pos <= IMGT_REGIONS["CDR2"]["end"]:
        return "CDR2"
    if IMGT_REGIONS["FR3"]["start"] <= pos <= IMGT_REGIONS["FR3"]["end"]:
        return "FR3"
    if IMGT_REGIONS["CDR3"]["start"] <= pos <= IMGT_REGIONS["CDR3"]["end"]:
        return "CDR3"
    if IMGT_REGIONS["FR4"]["start"] <= pos <= IMGT_REGIONS["FR4"]["end"]:
        return "FR4"
    return "UNK"


def _is_fr(region: str) -> bool:
    return region.startswith("FR") and region != "UNK"


def _is_vernier(imgt_pos: int, chain: str) -> bool:
    """Return True when the IMGT position belongs to the Vernier zone for that chain."""
    vset = _VERNIER_IMGT_VH if chain == "VH" else _VERNIER_IMGT_VL
    return imgt_pos in vset


# ── SASA helper ───────────────────────────────────────────────────────────────

def _compute_sasa_map(pdb_path: str) -> Dict[Tuple[str, int], float]:
    """
    Compute per-residue relative SASA using FreeSASA (preferred) or BioPython SASA.
    Returns {(chain_id, resnum): relative_sasa} or empty dict on failure.
    """
    result: Dict[Tuple[str, int], float] = {}
    try:
        import freesasa  # type: ignore

        st = freesasa.Structure(pdb_path)
        res = freesasa.calc(st)
        for i in range(st.nAtoms()):
            chain = st.atomChain(i)
            resnum = st.atomResidueNumber(i)
            resnum_int = int(str(resnum).strip())
            key = (chain, resnum_int)
            if key not in result:
                try:
                    rel = res.relativeArea(i)
                    result[key] = rel if rel is not None else 0.0
                except Exception:
                    result[key] = 0.0
            else:
                # accumulate max per residue (atom with most exposure wins)
                try:
                    rel = res.relativeArea(i)
                    if rel is not None and rel > result[key]:
                        result[key] = rel
                except Exception:
                    pass
        return result
    except ImportError:
        pass
    except Exception:
        # FreeSASA installed but API/calculation mismatch — fall through to BioPython / Cα proxy.
        pass

    # Fallback 1: BioPython ShrakeRupley SASA (BioPython ≥ 1.80)
    try:
        import Bio.PDB as bpdb  # type: ignore
        from Bio.PDB.SASA import ShrakeRupley  # type: ignore

        parser = bpdb.PDBParser(QUIET=True)
        structure = parser.get_structure("ab", pdb_path)
        sr = ShrakeRupley()
        sr.compute(structure, level="R")
        _REF = {
            "ALA": 106, "ARG": 248, "ASN": 157, "ASP": 163, "CYS": 135,
            "GLN": 198, "GLU": 194, "GLY": 84,  "HIS": 184, "ILE": 169,
            "LEU": 164, "LYS": 205, "MET": 188, "PHE": 197, "PRO": 136,
            "SER": 130, "THR": 142, "TRP": 227, "TYR": 222, "VAL": 142,
        }
        for model in structure:
            for chain in model:
                for res in chain:
                    if not bpdb.is_aa(res, standard=True):
                        continue
                    resnum = res.id[1]
                    sasa = res.sasa
                    ref = _REF.get(res.resname, 180)
                    rel = min(1.0, sasa / ref) if ref > 0 else 0.0
                    result[(chain.id, resnum)] = rel
        if result:
            return result
    except Exception:
        pass

    # Fallback 2: pure-Python Cα neighbor-count exposure proxy.
    # Residues with few Cα neighbors within 10 Å are treated as exposed.
    # No external library required — reads ATOM records directly.
    try:
        import math

        ca_atoms: List[Any] = []  # list of (chain, resnum, x, y, z)
        with open(pdb_path) as fh:
            for line in fh:
                if line.startswith("ATOM") and line[12:16].strip() == "CA":
                    chain_id = line[21]
                    resnum = int(line[22:26].strip())
                    x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])
                    ca_atoms.append((chain_id, resnum, x, y, z))

        if not ca_atoms:
            return {}

        # Neighbor cutoff: 10 Å; highly buried residues have ≥ 16 neighbors
        CUTOFF2 = 10.0 ** 2
        MAX_NEIGHBORS = 16.0

        for i, (ci, ri, xi, yi, zi) in enumerate(ca_atoms):
            n = 0
            for j, (cj, rj, xj, yj, zj) in enumerate(ca_atoms):
                if i == j:
                    continue
                d2 = (xi - xj) ** 2 + (yi - yj) ** 2 + (zi - zj) ** 2
                if d2 <= CUTOFF2:
                    n += 1
            # Exposed fraction: fewer neighbors → more exposed
            rel = max(0.0, 1.0 - n / MAX_NEIGHBORS)
            result[(ci, ri)] = round(rel, 3)
        return result
    except Exception:
        return {}


def _pdb_chain_for(chain_label: str, pdb_chains: List[str]) -> Optional[str]:
    """
    Map 'VH' → 'H', 'VL' → 'L' if those chain IDs exist; otherwise first/second.
    ABodyBuilder2 PDBs always write H and L chains.
    """
    want = {"VH": "H", "VL": "L"}.get(chain_label, "")
    if want in pdb_chains:
        return want
    # fallback: pick by index
    idx = 0 if chain_label == "VH" else 1
    return pdb_chains[idx] if idx < len(pdb_chains) else None


def _indexed_rows(chain_label: str, seq: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    if not (seq or "").strip():
        return [], None
    try:
        from core.numbering.imgt_anarcii import imgt_number_anarcii_indexed
        data = imgt_number_anarcii_indexed(seq)
    except Exception as e:
        return [], str(e)
    out: List[Dict[str, Any]] = []
    protect = _compute_protect_55_as_cdr2([{ "pos": r.get("pos"), "aa": r.get("aa") } for r in data.get("rows") or []])
    for r in data.get("rows") or []:
        pos = r.get("pos")
        if not isinstance(pos, int):
            continue
        seq_idx = r.get("seq_idx")
        aa = (r.get("aa") or "").upper()
        if not isinstance(seq_idx, int) or len(aa) != 1:
            continue
        region = _imgt_residue_region(pos, protect)
        out.append(
            {
                "chain": chain_label,
                "seq_idx0": int(seq_idx),
                "imgt": pos,
                "aa": aa,
                "region": region,
            }
        )
    return out, None


def _window(seq: str, i0: int, half: int = 5) -> str:
    s = (seq or "").replace(" ", "").upper()
    if not s or i0 < 0 or i0 >= len(s):
        return ""
    a = max(0, i0 - half)
    b = min(len(s), i0 + half + 1)
    return s[a:b]


def enumerate_fr_charge_candidates(
    vh: str,
    vl: str,
    max_sites: int = 8,
    sasa_map: Optional[Dict[Tuple[str, int], float]] = None,
    pdb_chains: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    K/R in FR: candidate sites to reduce pI / net positive charge (too_high).

    Filters applied (in order):
      1. FR-only  — CDR positions removed by _is_fr().
      2. Vernier  — IMGT positions in _VERNIER_IMGT_VH/VL removed.
      3. SASA     — when sasa_map is provided, only positions with
                    relative SASA ≥ SASA_THRESHOLD (0.30) are retained.
    """
    vh_r, e1 = _indexed_rows("VH", vh)
    vl_r, e2 = _indexed_rows("VL", vl)
    err = e1 or e2
    pdb_chains = pdb_chains or []
    cands: List[Dict[str, Any]] = []
    for row in vh_r + vl_r:
        if not _is_fr(row["region"]):
            continue
        if row["aa"] not in _POS_CHARGE:
            continue
        chain = row["chain"]
        imgt_pos = row["imgt"]
        # DeepFR-CTX HARD-veto gate
        _dfc_blocked, _ = _is_deepfr_ctx_hard_protected(row["aa"], row["region"], chain)
        if _dfc_blocked:
            continue
        # Vernier mask
        if _is_vernier(imgt_pos, chain):
            continue
        # SASA filter
        sasa_val: Optional[float] = None
        if sasa_map is not None:
            pdb_cid = _pdb_chain_for(chain, pdb_chains)
            if pdb_cid is not None:
                sasa_val = sasa_map.get((pdb_cid, row["seq_idx0"] + 1))
                if sasa_val is None or sasa_val < SASA_THRESHOLD:
                    continue
        i0 = row["seq_idx0"]
        full = (vh if chain == "VH" else vl) or ""
        entry: Dict[str, Any] = {
            "chain": chain,
            "index_1": i0 + 1,
            "imgt": imgt_pos,
            "from_aa": row["aa"],
            "to_aa_hint": _AA_REPLACEMENT_HINT.get(row["aa"], "Q"),
            "region": row["region"],
            "window": _window(full, i0, 6),
        }
        if sasa_val is not None:
            entry["sasa_rel"] = round(sasa_val, 3)
        cands.append(entry)
        if len(cands) >= max_sites:
            break
    return cands, err


def enumerate_fr_negative_charge_candidates(
    vh: str,
    vl: str,
    max_sites: int = 8,
    sasa_map: Optional[Dict[Tuple[str, int], float]] = None,
    pdb_chains: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    D/E in FR: candidate sites to reduce negative charge patch / acidic surface burden (too_high on pnc-like metrics).

    Same filters as enumerate_fr_charge_candidates (FR-only, Vernier mask, optional SASA).
    """
    vh_r, e1 = _indexed_rows("VH", vh)
    vl_r, e2 = _indexed_rows("VL", vl)
    err = e1 or e2
    pdb_chains = pdb_chains or []
    cands: List[Dict[str, Any]] = []
    for row in vh_r + vl_r:
        if not _is_fr(row["region"]):
            continue
        if row["aa"] not in _NEG_CHARGE:
            continue
        chain = row["chain"]
        imgt_pos = row["imgt"]
        # DeepFR-CTX HARD-veto gate
        _dfc_blocked, _ = _is_deepfr_ctx_hard_protected(row["aa"], row["region"], chain)
        if _dfc_blocked:
            continue
        if _is_vernier(imgt_pos, chain):
            continue
        sasa_val: Optional[float] = None
        if sasa_map is not None:
            pdb_cid = _pdb_chain_for(chain, pdb_chains)
            if pdb_cid is not None:
                sasa_val = sasa_map.get((pdb_cid, row["seq_idx0"] + 1))
                if sasa_val is None or sasa_val < SASA_THRESHOLD:
                    continue
        i0 = row["seq_idx0"]
        full = (vh if chain == "VH" else vl) or ""
        aa = row["aa"]
        entry: Dict[str, Any] = {
            "chain": chain,
            "index_1": i0 + 1,
            "imgt": imgt_pos,
            "from_aa": aa,
            "to_aa_hint": _NEG_REPLACEMENT_HINT.get(aa, "N"),
            "region": row["region"],
            "window": _window(full, i0, 6),
        }
        if sasa_val is not None:
            entry["sasa_rel"] = round(sasa_val, 3)
        cands.append(entry)
        if len(cands) >= max_sites:
            break
    return cands, err


def enumerate_fr_hydrophobic_runs(
    vh: str,
    vl: str,
    min_len: int = 3,
    max_runs: int = 5,
    sasa_map: Optional[Dict[Tuple[str, int], float]] = None,
    pdb_chains: Optional[List[str]] = None,
    indexed_rows_vh: Optional[List[Dict[str, Any]]] = None,
    indexed_rows_vl: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Unbroken hydrophobic runs (AILMFWV) in FR — aggregation-motif style targets.

    Filters applied:
      1. FR-only  — sequence positions outside FR are excluded.
      2. Vernier  — positions whose IMGT number is in Vernier set are excluded.
      3. SASA     — run is only emitted if the mean relative SASA of the run
                    residues ≥ SASA_THRESHOLD (requires sasa_map).
    """
    if indexed_rows_vh is None or indexed_rows_vl is None:
        vh_r, e1 = _indexed_rows("VH", vh)
        vl_r, e2 = _indexed_rows("VL", vl)
        err = e1 or e2
    else:
        vh_r, vl_r, err = indexed_rows_vh, indexed_rows_vl, None
    pdb_chains = pdb_chains or []
    by_chain = (("VH", vh, vh_r), ("VL", vl, vl_r))
    runs: List[Dict[str, Any]] = []
    for label, full, idx_rows in by_chain:
        s = (full or "").replace(" ", "").upper()
        if not s or not idx_rows:
            continue
        # Base instability for this chain (side-effect guard)
        _PA = None
        _base_ii_chain = 100.0  # sentinel: guard disabled
        try:
            from Bio.SeqUtils.ProtParam import ProteinAnalysis as _PA  # type: ignore[assignment]
            _base_ii_chain = _PA(s.replace("X", "A")).instability_index()
        except Exception:
            pass
        # Map seq_idx0 → (is FR, is vernier, imgt)
        row_map: Dict[int, Dict[str, Any]] = {r["seq_idx0"]: r for r in idx_rows}
        pdb_cid = _pdb_chain_for(label, pdb_chains) if sasa_map else None
        i = 0
        while i < len(s) and len(runs) < max_runs:
            r = row_map.get(i)
            if not r or not _is_fr(r["region"]) or s[i] not in _HYDRO_RUN:
                i += 1
                continue
            # Collect run
            j = i
            run_residues: List[Dict[str, Any]] = []
            while j < len(s):
                rj = row_map.get(j)
                if not rj or not _is_fr(rj["region"]) or s[j] not in _HYDRO_RUN:
                    break
                run_residues.append(rj)
                j += 1
            L = j - i
            if L >= min_len:
                # Vernier check: skip entire run if any position is Vernier
                has_vernier = any(_is_vernier(rr["imgt"], label) for rr in run_residues)
                if not has_vernier:
                    seg = s[i:j]
                    # Build per-residue mutation hints for this run
                    per_residue: List[Dict[str, Any]] = []
                    for rr in run_residues:
                        aa = rr["aa"]
                        # DeepFR-CTX HARD-veto gate — skip structurally critical residues
                        _dfc_blocked, _ = _is_deepfr_ctx_hard_protected(aa, rr["region"], label)
                        if _dfc_blocked:
                            continue
                        hint = _HYDRO_REDUCE_HINT.get(aa, "S")
                        # Side-effect instability guard: hydrophobic mutation must not
                        # push chain instability_index above the clinical gate (40.0)
                        lin0_rr = rr["seq_idx0"]
                        if _PA is not None and _base_ii_chain < 100.0:
                            try:
                                _mut_s = s[:lin0_rr] + hint + s[lin0_rr + 1:]
                                _new_ii = _PA(_mut_s.replace("X", "A")).instability_index()
                                if _base_ii_chain < 40.0 and _new_ii >= 40.0:
                                    continue  # would push chain instability above gate
                                elif _base_ii_chain >= 40.0 and _new_ii > _base_ii_chain + 1.0:
                                    continue  # already high: cap worsening
                            except Exception:
                                pass
                        site_entry: Dict[str, Any] = {
                            "index_1": rr["seq_idx0"] + 1,
                            "imgt": rr["imgt"],
                            "from_aa": aa,
                            "to_aa_hint": hint,
                            "region": rr["region"],
                        }
                        note = _HYDRO_REDUCE_NOTE.get(aa)
                        if note:
                            site_entry["caution"] = note
                        per_residue.append(site_entry)
                    entry: Dict[str, Any] = {
                        "chain": label,
                        "start_1": i + 1,
                        "end_1": j,
                        "length": L,
                        "segment": seg,
                        "window": _window(s, (i + j) // 2, 7),
                        "per_residue": per_residue,
                    }
                    # SASA check: compute mean SASA of run
                    if sasa_map is not None and pdb_cid is not None:
                        sasa_vals = [
                            sasa_map.get((pdb_cid, rr["seq_idx0"] + 1), 0.0)
                            for rr in run_residues
                        ]
                        mean_sasa = sum(sasa_vals) / len(sasa_vals) if sasa_vals else 0.0
                        entry["sasa_rel_mean"] = round(mean_sasa, 3)
                        # Attach per-residue SASA too
                        for pr_item, rr in zip(per_residue, run_residues):
                            sv = sasa_map.get((pdb_cid, rr["seq_idx0"] + 1))
                            if sv is not None:
                                pr_item["sasa_rel"] = round(sv, 3)
                        if mean_sasa < SASA_THRESHOLD:
                            i = j
                            continue
                    runs.append(entry)
            i = j
    return runs[:max_runs], err


# Destabilizing dipeptide motifs: first residue → recommended substitute
# Rules based on Guruprasad et al. 1990 and Colby et al. common FR instability hotspots.
_INSTABILITY_DIPEPTIDE: Dict[str, Dict[str, str]] = {
    # motif: {first_aa: replacement_hint}
    # Rule: charged aa (D/E) → charge-conservative hint (D→E or E→D).
    #       neutral aa (N/Q/G) → charge-neutral hint only.
    # QG: Q→A (not Q→E) — Glu would add a new negative charge, hurting pI and ADI.
    "NG": {"N": "S"},   # Asn-Gly → deamidation + β-turn instability
    "DG": {"D": "E"},   # Asp-Gly → isomerization prone (D→E: same charge family)
    "DP": {"D": "E"},   # Asp-Pro → cis-Pro instability (charge-conservative)
    "NS": {"N": "S"},   # Asn-Ser → deamidation risk
    "NF": {"N": "S"},   # Asn-Phe → deamidation
    "QG": {"Q": "A"},   # Gln-Gly → backbone instability; A is neutral (Ala-Gly DIWV ~ -0.21)
    "GG": {"G": "A"},   # Gly-Gly → backbone flexibility hotspot
    "GP": {"G": "A"},   # Gly-Pro → cis-Pro facilitation
}

# Charge class for conservation check
_NEGATIVE_CHARGE_AA = frozenset("DE")
_POSITIVE_CHARGE_AA = frozenset("KRH")
_NEUTRAL_AA         = frozenset("ACFGILMNPQSTVWY")


def enumerate_fr_instability_candidates(
    vh: str,
    vl: str,
    max_sites: int = 8,
    sasa_map: Optional[Dict[Tuple[str, int], float]] = None,
    pdb_chains: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Scan FR residues for known destabilizing dipeptide motifs (NG, DG, DP, NS, NF, QG, GG, GP).

    Only positions that are:
      1. In a framework region (not CDR)
      2. Not in the Vernier zone
      3. (Optional) Exposed by SASA ≥ threshold
    are returned as candidate substitution targets.
    """
    vh_r, e1 = _indexed_rows("VH", vh)
    vl_r, e2 = _indexed_rows("VL", vl)
    err = e1 or e2
    pdb_chains = pdb_chains or []
    cands: List[Dict[str, Any]] = []

    for label, seq_str, rows in (("VH", vh, vh_r), ("VL", vl, vl_r)):
        s = (seq_str or "").replace(" ", "").upper()
        if not s or not rows:
            continue
        row_map: Dict[int, Dict[str, Any]] = {r["seq_idx0"]: r for r in rows}
        pdb_cid = _pdb_chain_for(label, pdb_chains) if sasa_map else None
        # Track cumulative mutations within this chain so candidates emitted in
        # the same pass don't combine to create aggregation motifs (e.g. two
        # adjacent G→A substitutions on briakinumab/abiprubart VL).
        working_s = s

        for i in range(len(s) - 1):
            r0 = row_map.get(i)
            r1 = row_map.get(i + 1)
            if not r0 or not r1:
                continue
            if not _is_fr(r0["region"]):
                continue
            if _is_vernier(r0["imgt"], label):
                continue
            dipeptide = s[i:i+2]
            motif_rule = _INSTABILITY_DIPEPTIDE.get(dipeptide)
            if not motif_rule:
                continue
            aa0 = s[i]
            # DeepFR-CTX HARD-veto gate
            _dfc_blocked, _ = _is_deepfr_ctx_hard_protected(aa0, r0["region"], label)
            if _dfc_blocked:
                continue
            hint = motif_rule.get(aa0, "S")

            # ── F1 guard: refuse to introduce a new aggregation motif ─────────
            # Check against the working sequence (= base seq with previously
            # accepted mutations already applied). Smoke test 2026-05-15 showed
            # abiprubart G98A+G99A raised agg_motifs 2→3 only when both were
            # applied — independent checks against the base sequence missed it.
            if _would_create_aggregation_motif(working_s, i, hint):
                # Try a polar fallback that cannot create a hydrophobic run
                # even after stacking on the working sequence.
                _polar_fallbacks = ("S", "T", "N", "Q")
                alt = next(
                    (a for a in _polar_fallbacks
                     if a != hint and not _would_create_aggregation_motif(working_s, i, a)),
                    None,
                )
                if alt is None:
                    # No safe substitution — skip this candidate entirely.
                    continue
                hint = alt
            # ── F3 guard: charge-conservation — prefer neutral hints for neutral originals ──
            # A neutral original AA (Q, N, G, S…) should not be replaced by a charged AA
            # (E, D, K, R) as this shifts pI and ADI-charge components independently of the
            # instability goal. Only allow a charged hint if:
            #   (a) the original is already charged (same class), OR
            #   (b) no charge-neutral alternative passes F1 + F2.
            if hint in _NEGATIVE_CHARGE_AA or hint in _POSITIVE_CHARGE_AA:
                if aa0 in _NEUTRAL_AA:
                    # Original is neutral but hint is charged — try neutral alternatives
                    _neutral_alts = [a for a in ("A", "S", "T", "N") if a != aa0 and a != hint]
                    _neutral_found = None
                    for _alt in _neutral_alts:
                        if _would_create_aggregation_motif(working_s, i, _alt):
                            continue
                        _t = working_s[:i] + _alt + working_s[i + 1:]
                        try:
                            _ii_b = ProteinAnalysis(working_s.replace("X", "A")).instability_index()
                            _ii_a = ProteinAnalysis(_t.replace("X", "A")).instability_index()
                            if _ii_a < _ii_b - 0.01:
                                _neutral_found = _alt
                                break
                        except Exception:
                            _neutral_found = _alt  # if Bio fails, allow
                            break
                    if _neutral_found is not None:
                        hint = _neutral_found  # replace charged hint with neutral
                    # If no neutral alt passes, allow original charged hint as last resort

            # ── F2 guard: verify mutation actually lowers Biopython instability_index ──
            # The simplified dipeptide motif table only tracks ~8 known bad patterns.
            # A G→A substitution removes the [G][G] contribution but simultaneously
            # creates a new [prev][A] dipeptide whose Guruprasad DIWV may be higher,
            # leaving the net instability worse. Verify with the real scorer.
            _test_s = working_s[:i] + hint + working_s[i + 1:]
            try:
                _ii_before = ProteinAnalysis(working_s.replace("X", "A")).instability_index()
                _ii_after  = ProteinAnalysis(_test_s.replace("X", "A")).instability_index()
                if _ii_after >= _ii_before - 0.01:
                    # Mutation does not improve instability on this chain — skip
                    continue
            except Exception:
                pass  # If Bio fails, allow the candidate through (conservative fallback)

            # Accept this candidate: bake it into the working sequence so the
            # next candidate sees the updated context.
            working_s = working_s[:i] + hint + working_s[i + 1:]

            sasa_val: Optional[float] = None
            if sasa_map is not None and pdb_cid is not None:
                sasa_val = sasa_map.get((pdb_cid, i + 1))
                if sasa_val is None or sasa_val < SASA_THRESHOLD:
                    continue

            entry: Dict[str, Any] = {
                "chain": label,
                "index_1": i + 1,
                "imgt": r0["imgt"],
                "from_aa": aa0,
                "to_aa_hint": hint,
                "motif": dipeptide,
                "region": r0["region"],
                "window": _window(s, i, 5),
                "note": f"{dipeptide} dipeptide — known FR instability motif",
            }
            if sasa_val is not None:
                entry["sasa_rel"] = round(sasa_val, 3)
            cands.append(entry)
            if len(cands) >= max_sites:
                break
        if len(cands) >= max_sites:
            break

    return cands, err


def _detect_cdr_driven_hydrophobic_patch(
    vh: str,
    vl: str,
    vh_rows: List[Dict[str, Any]],
    vl_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Find which chain owns the global max hydrophobic 9-mer window and report
    whether that window sits inside a CDR. Used by build_candidate_payload_for_metric
    to decide whether FR mutations can plausibly move ``hydro_patch_max9``.
    """
    result: Dict[str, Any] = {"cdr_driven": False, "location": None, "fraction": 0.0}
    candidates: List[Tuple[str, str, List[Dict[str, Any]]]] = []
    if vh and vh_rows:
        candidates.append(("VH", vh, vh_rows))
    if vl and vl_rows:
        candidates.append(("VL", vl, vl_rows))
    if not candidates:
        return result
    best_chain = ""
    best_start = 0
    best_end = 0
    best_frac = -1.0
    for label, full, rows in candidates:
        start, end, frac = _find_max_hydro_window(full, window=9)
        if frac > best_frac:
            best_frac = frac
            best_chain = label
            best_start = start
            best_end = end
    if best_chain:
        rows = vh_rows if best_chain == "VH" else vl_rows
        is_cdr, region_label = _is_window_cdr_internal(rows, best_start, best_end, min_cdr_frac=0.55)
        result["cdr_driven"] = is_cdr
        result["fraction"] = best_frac
        result["location"] = (
            f"{best_chain} positions {best_start + 1}-{best_end} ({region_label})"
            if is_cdr else f"{best_chain} positions {best_start + 1}-{best_end} (FR-accessible)"
        )
    return result


def _trim_charge_sites_to_safe_zone(
    sites: List[Dict[str, Any]],
    vh: str,
    vl: str,
    direction: str = "reduce",
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Iteratively apply candidate charge mutations and stop when net_charge_pH7
    and pI both land inside CHARGE_SAFE_ZONE. Returns the minimum subset and
    a stop_meta dict describing how far the trim got and the projected metrics.

    Strategy: greedy (Biopython recompute after each candidate). Sites are
    consumed in the input order (already ranked by FR-only + SASA + Vernier).
    """
    if not sites:
        return [], None
    try:
        from Bio.SeqUtils.ProtParam import ProteinAnalysis
    except Exception:
        return sites, None  # graceful fallback — keep prior behaviour

    nc_lo, nc_hi = CHARGE_SAFE_ZONE["net_charge_pH7"]
    pi_lo, pi_hi = CHARGE_SAFE_ZONE["pI"]

    def _project(vh_s: str, vl_s: str) -> Tuple[float, float]:
        combined = (vh_s or "") + (vl_s or "")
        if not combined:
            return 0.0, 7.0
        pa = ProteinAnalysis(combined.upper())
        return float(pa.charge_at_pH(7.0)), float(pa.isoelectric_point())

    def _in_zone(nc: float, pi: float) -> bool:
        return (nc_lo <= nc <= nc_hi) and (pi_lo <= pi <= pi_hi)

    cur_vh = vh or ""
    cur_vl = vl or ""
    nc0, pi0 = _project(cur_vh, cur_vl)
    # If already in zone, don't propose any charge mutations.
    if _in_zone(nc0, pi0):
        return [], {
            "stopped": "already_in_safe_zone",
            "net_charge_pH7_before": round(nc0, 2),
            "pI_before": round(pi0, 2),
            "applied_count": 0,
            "available_count": len(sites),
        }

    accepted: List[Dict[str, Any]] = []
    skipped_overshoot = 0
    for s in sites:
        chain = s.get("chain")
        idx1 = s.get("index_1")
        new_aa = (s.get("to_aa_hint") or "").upper()
        if not (chain and idx1 and new_aa):
            continue
        # Apply tentatively
        if chain == "VH":
            tmp = cur_vh[:idx1 - 1] + new_aa + cur_vh[idx1:]
            test_vh, test_vl = tmp, cur_vl
        elif chain == "VL":
            tmp = cur_vl[:idx1 - 1] + new_aa + cur_vl[idx1:]
            test_vh, test_vl = cur_vh, tmp
        else:
            continue
        nc1, pi1 = _project(test_vh, test_vl)
        # Reject moves that overshoot away from the safe zone (e.g. charge crosses zero)
        if direction == "reduce":
            if nc1 < nc_lo - 1.0:  # overshoots strongly negative
                skipped_overshoot += 1
                continue
        else:  # raise
            if nc1 > nc_hi + 1.0:
                skipped_overshoot += 1
                continue
        # Accept
        cur_vh, cur_vl = test_vh, test_vl
        accepted.append(s)
        nc0, pi0 = nc1, pi1
        if _in_zone(nc0, pi0):
            break

    meta = {
        "stopped": "in_safe_zone" if _in_zone(nc0, pi0) else "exhausted_candidates",
        "net_charge_pH7_projected": round(nc0, 2),
        "pI_projected": round(pi0, 2),
        "target_net_charge_pH7": [nc_lo, nc_hi],
        "target_pI": [pi_lo, pi_hi],
        "applied_count": len(accepted),
        "available_count": len(sites),
        "skipped_overshoot": skipped_overshoot,
    }
    return accepted, meta


def build_candidate_payload_for_metric(
    metric: str,
    direction: str,
    vh: str,
    vl: str,
    pdb_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return structured sites/snippets for a single (metric, direction) from MutationAdvisor.

    Args:
        pdb_path: Optional path to an ABodyBuilder2 PDB. When supplied,
                  SASA is computed and used as a third filter layer after
                  the FR-only and Vernier masks.
    """
    ml = (metric or "").lower()
    d = (direction or "").lower()
    out: Dict[str, Any] = {"metric": metric, "direction": direction}
    vh = (vh or "").strip().upper()
    vl = (vl or "").strip().upper()

    # Pre-compute SASA map once (shared between charge and hydrophobic calls)
    sasa_map: Optional[Dict[Tuple[str, int], float]] = None
    pdb_chains: List[str] = []
    if pdb_path and Path(pdb_path).is_file():
        sasa_map = _compute_sasa_map(str(pdb_path))
        if sasa_map:
            pdb_chains = sorted({c for c, _ in sasa_map.keys()})
            out["sasa_filter_applied"] = True
            out["sasa_threshold"] = SASA_THRESHOLD
    out["vernier_filter_applied"] = bool(_VERNIER_IMGT_VH or _VERNIER_IMGT_VL)

    if ml in ("pi", "net_charge_ph7") and d == "too_high":
        sites, err = enumerate_fr_charge_candidates(
            vh, vl, max_sites=8, sasa_map=sasa_map, pdb_chains=pdb_chains
        )
        # F2 safe-zone: stop adding K/R→Q once global pI/charge lands in safe zone.
        trimmed, stop_meta = _trim_charge_sites_to_safe_zone(
            sites, vh=vh, vl=vl, direction="reduce"
        )
        out["fr_positive_charge_sites"] = trimmed
        if stop_meta:
            out["safe_zone_stop"] = stop_meta
        if err:
            out["enumeration_note"] = err
    elif ml in ("pi", "net_charge_ph7") and d == "too_low":
        sites, err = enumerate_fr_negative_charge_candidates(
            vh, vl, max_sites=8, sasa_map=sasa_map, pdb_chains=pdb_chains
        )
        # F2 safe-zone: stop adding D/E→N/Q once global pI/charge lands in safe zone.
        trimmed, stop_meta = _trim_charge_sites_to_safe_zone(
            sites, vh=vh, vl=vl, direction="raise"
        )
        out["fr_negative_charge_sites"] = trimmed
        if stop_meta:
            out["safe_zone_stop"] = stop_meta
        if err:
            out["enumeration_note"] = err
    elif ml in ("charge_patch_max7", "ppc") and d == "too_high":
        # Local positive patch: return all FR candidates (no global safe-zone trimming).
        sites, err = enumerate_fr_charge_candidates(
            vh, vl, max_sites=8, sasa_map=sasa_map, pdb_chains=pdb_chains
        )
        out["fr_positive_charge_sites"] = sites
        if err:
            out["enumeration_note"] = err
    elif ml == "pnc" and d == "too_high":
        # Local negative patch: return all FR candidates (no global safe-zone trimming).
        sites, err = enumerate_fr_negative_charge_candidates(
            vh, vl, max_sites=8, sasa_map=sasa_map, pdb_chains=pdb_chains
        )
        out["fr_negative_charge_sites"] = sites
        if err:
            out["enumeration_note"] = err
    elif ml == "instability_index" and d == "too_high":
        # Instability: scan for destabilizing dipeptide motifs (NG, DG, DP, NS, NF, QG, GG, GP) in FR.
        # NOTE: hydrophobic-run substitutions (L/A/I → S/T) are NOT included here.
        # Empirically, making hydrophobic FR residues polar increases the Biopython dipeptide
        # instability score and worsens the metric. Hydrophobic run corrections belong in the
        # hydrophobic category only (agg_motifs / psh / SAP path).
        motif_sites, merr = enumerate_fr_instability_candidates(
            vh, vl, max_sites=8, sasa_map=sasa_map, pdb_chains=pdb_chains
        )
        out["fr_instability_sites"] = motif_sites
        if merr:
            out["enumeration_note"] = merr
    elif ml in ("agg_motifs", "gravy", "hydro_patch_max9", "sap_score", "psh"):
        # ── F3: CDR-driven hydrophobic patch detection ─────────────────
        # Smoke 2026-05-15 showed briakinumab hydro_patch_max9 = 0.67 located
        # entirely in CDR-H3 (`THGSHDNW`); proposed VL FR3 mutations did not
        # move the patch (still 0.67) and dropped ADI by 3.1. When the patch
        # is CDR-internal we SUPPRESS the FR-run list (clients should not be
        # nudged to apply destabilising L/A/I→S/T in FR3 when the patch lives
        # in CDR-H3) and surface an explicit advisory instead.
        cdr_driven = False
        if ml in ("hydro_patch_max9", "sap_score", "psh") or (ml == "agg_motifs" and d == "too_high"):
            try:
                vh_rows_check, _ = _indexed_rows("VH", vh)
                vl_rows_check, _ = _indexed_rows("VL", vl)
                advisory = _detect_cdr_driven_hydrophobic_patch(
                    vh, vl, vh_rows_check, vl_rows_check
                )
                if advisory.get("cdr_driven"):
                    cdr_driven = True
                    out["patch_is_cdr_driven"] = True
                    out["patch_location"] = advisory.get("location")
                    out["enumeration_note"] = (
                        f"Hydrophobic patch peak is CDR-internal "
                        f"({advisory.get('location')}). FR-only mutations cannot move "
                        f"the local hydro_patch_max9 metric and empirically reduce ADI "
                        f"by destabilising FR3 packing (smoke 2026-05-15: ADI ▼3.1). "
                        f"Addressing this patch requires CDR redesign or affinity maturation "
                        f"(premium service)."
                    )
            except Exception:
                pass

        if ml == "agg_motifs" or d == "too_high":
            if not cdr_driven:
                runs, err = enumerate_fr_hydrophobic_runs(
                    vh, vl, min_len=3, max_runs=5, sasa_map=sasa_map, pdb_chains=pdb_chains
                )
                out["fr_hydrophobic_runs"] = runs
                if err:
                    out["enumeration_note"] = err
            else:
                out["fr_hydrophobic_runs"] = []  # explicit empty list
        elif ml == "gravy" and d == "too_low":
            # Hydrophobic-run hints target elevated hydrophobicity / patches (too_high). Below-band GRAVY is
            # often acceptable or polarity-driven; do not invent buried hydrophobic edits without context.
            out["enumeration_note"] = (
                "GRAVY sits below the gate band (more hydrophilic than the blended cohort range). "
                "FR hydrophobic-run substitution hints are emitted only when GRAVY is high vs the gate "
                "(too_high). No sites listed—review charge / SAP / patch metrics if surface polarity is the concern."
            )
    if pdb_path and Path(pdb_path).is_file():
        try:
            from core.cmc.cmc_mutation_policy import apply_cmc_mutation_policy

            vh_rows, _ = _indexed_rows("VH", vh)
            vl_rows, _ = _indexed_rows("VL", vl)
            out = apply_cmc_mutation_policy(
                out,
                indexed_rows={"VH": vh_rows, "VL": vl_rows},
                pdb_path=str(pdb_path),
            )
        except Exception:
            out["mutation_policy"] = {
                "version": "CMC_MUTATION_POLICY_V1.2",
                "public_summary": "FR-only suggestions use conservative sequence filters; structure-protection policy was not available for this run.",
                "protected_candidate_count": None,
            }
    return out


def apply_mutations_to_sequence(seq: str, per_residue: List[Dict[str, Any]]) -> str:
    """
    Apply per-residue mutation hints to seq (0-indexed seq_idx0 or 1-based index_1).
    Returns the mutated sequence string.
    """
    s = list((seq or "").strip().upper())
    for p in sorted(per_residue, key=lambda x: x.get("index_1", 0)):
        idx1 = p.get("index_1")
        if idx1 is None:
            continue
        i0 = int(idx1) - 1
        if 0 <= i0 < len(s):
            hint = str(p.get("to_aa_hint", "") or "").strip().upper()
            if hint and len(hint) == 1:
                s[i0] = hint
    return "".join(s)


def build_mutation_summary(
    vh: str, vl: str, candidate_payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Given a candidate payload from build_candidate_payload_for_metric, return:
      - charge_mutants: {chain: {orig_seq, mutant_seq, mutations: [(pos1, from, to), ...]}}
      - hydro_mutants:  same structure per run
    """
    vh_s = (vh or "").strip().upper()
    vl_s = (vl or "").strip().upper()
    summary: Dict[str, Any] = {}

    # Charge sites (positive or negative surface balancing)
    sites = (candidate_payload.get("fr_positive_charge_sites") or []) + (candidate_payload.get("fr_negative_charge_sites") or [])
    if sites:
        vh_pr = [s for s in sites if s.get("chain") == "VH"]
        vl_pr = [s for s in sites if s.get("chain") == "VL"]
        ops: List[Dict[str, Any]] = []
        if vh_pr:
            muted_vh = apply_mutations_to_sequence(vh_s, vh_pr)
            for p in vh_pr:
                ops.append({"chain": "VH", "pos": p.get("index_1"), "from": p.get("from_aa"), "to": p.get("to_aa_hint"), "region": p.get("region")})
            summary["charge_vh"] = {"original": vh_s, "mutant": muted_vh, "mutations": ops}
        if vl_pr:
            muted_vl = apply_mutations_to_sequence(vl_s, vl_pr)
            ops_vl: List[Dict[str, Any]] = []
            for p in vl_pr:
                ops_vl.append({"chain": "VL", "pos": p.get("index_1"), "from": p.get("from_aa"), "to": p.get("to_aa_hint"), "region": p.get("region")})
            summary["charge_vl"] = {"original": vl_s, "mutant": muted_vl, "mutations": ops_vl}

    # Hydrophobic runs
    runs = candidate_payload.get("fr_hydrophobic_runs") or []
    if runs:
        run_mutants: List[Dict[str, Any]] = []
        for run in runs:
            pr = run.get("per_residue") or []
            if not pr:
                continue
            chain = run.get("chain", "")
            seq_src = vh_s if chain == "VH" else vl_s
            muted = apply_mutations_to_sequence(seq_src, pr)
            muts = [{"pos": p.get("index_1"), "from": p.get("from_aa"), "to": p.get("to_aa_hint"), "region": p.get("region")} for p in pr]
            run_mutants.append({"chain": chain, "span": f"{run.get('start_1')}–{run.get('end_1')}", "original_run": run.get("segment"), "original_seq": seq_src, "mutant_seq": muted, "mutations": muts})
        if run_mutants:
            summary["hydro_runs"] = run_mutants

    return summary





