#!/usr/bin/env python3
"""
Unified dog/cat petization CLI.

Production-candidate CLI facade for caninization and felinization. It routes
VH/VL chains through graft + Vernier, surface reshaping, or deep-FR anchoring
while writing a machine-readable protocol JSON and FASTA.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from Bio.SeqUtils.ProtParam import ProteinAnalysis

SUITE = Path(__file__).resolve().parents[1]
if str(SUITE) not in sys.path:
    sys.path.insert(0, str(SUITE))

from core.cmc.generic_cmc_scanner import scan_cmc_liabilities  # noqa: E402
from core.humanization.kabat_utils import (  # noqa: E402
    MAX_CDR3_VH,
    MAX_CDR3_VL,
    assemble_humanized_v,
    get_kabat_numbering,
    is_in_cdr,
    sorted_keys,
    verify_cdr_preservation,
)


DOG_SCAFFOLDS = (
    SUITE
    / "data"
    / "germlines"
    / "canis_lupus_familiaris_ig_aa"
    / "dog_scaffold_cmc_optimization_tier1_tier2_v1.json"
)
CAT_SCAFFOLDS = (
    SUITE
    / "data"
    / "germlines"
    / "felis_catus_ig_aa"
    / "cat_scaffold_cmc_optimization_tier1_tier2_v1.json"
)

VERNIER_KABAT_VH = [2, 27, 28, 29, 30, 47, 48, 49, 67, 69, 71, 73, 78, 93, 94]
VERNIER_KABAT_VL = [2, 4, 36, 46, 49, 69, 71, 98]

VH_SURFACE_KABAT = {
    1, 3, 5, 10, 11, 12, 13, 15, 19, 23, 26, 27, 28,
    40, 41, 42, 43, 44, 45, 52, 53, 54, 55,
    60, 61, 62, 64, 65, 68, 70, 72, 73, 74, 75, 76,
    82, 83, 84, 85, 87, 88, 89,
    105, 108, 110, 112,
}
VL_SURFACE_KABAT = {
    1, 3, 5, 7, 9, 10, 12, 15, 16, 18, 20, 22, 24,
    40, 41, 42, 43, 44, 45,
    53, 54, 55, 56, 57,
    60, 63, 65, 66, 67, 69, 70, 74, 76, 77, 79, 80,
    81, 84, 85,
    100, 103, 105, 107,
}

FR_IDENTITY_HIGH = 70.0
FR_IDENTITY_MIN_GRAFT = 65.0

# Kabat positions immediately flanking CDR boundaries (within 3 positions of CDR start/end)
# Used by detect_fr_shm_positions to identify CDR-proximal FR positions.
_CDR_BOUNDARY_WINDOW = 3
_CDR_RANGES_VH = {"H1": (26, 35), "H2": (50, 65), "H3": (95, 102)}
_CDR_RANGES_VL = {"L1": (24, 34), "L2": (50, 56), "L3": (89, 97)}

# Universal FR4 sequences based on clinical pet antibodies (Zoetis/Merck)
# and human therapeutic standards. These are the "safe" defaults for petization.
UNIVERSAL_PET_FR4 = {
    "VH": "WGQGTLVTVSS",  # Matches Human IGHJ4 and Dog Clinical (Lokivetmab, etc.)
    "VL_kappa": "FGQGTKLEIK",  # Matches Human IGKJ2 and Dog Clinical
    "VL_lambda": "FGGGTHLTVL",  # Bedinvetmab style
}


def _cdr_proximal_fr_positions(chain: str, window: int = _CDR_BOUNDARY_WINDOW) -> Set[int]:
    """Return FR Kabat positions within `window` of any CDR boundary (not in CDR themselves)."""
    ranges = _CDR_RANGES_VH if chain == "VH" else _CDR_RANGES_VL
    proximal: Set[int] = set()
    for lo, hi in ranges.values():
        for delta in range(1, window + 1):
            p_lo = lo - delta
            p_hi = hi + delta
            if p_lo >= 1 and not is_in_cdr(p_lo, chain):
                proximal.add(p_lo)
            if p_hi <= 120 and not is_in_cdr(p_hi, chain):
                proximal.add(p_hi)
    return proximal


def detect_fr_shm_positions(
    donor_seq: str,
    chain: str,
    germline_seqs: Optional[List[str]] = None,
    window: int = _CDR_BOUNDARY_WINDOW,
) -> List[int]:
    """
    Identify FR positions in ``donor_seq`` that differ from ALL supplied ``germline_seqs``
    AND are within ``window`` Kabat positions of a CDR boundary.

    These are candidate somatic hypermutation sites in FR that may have been
    selected to support CDR conformation and should be preserved (deep_fr_anchor).

    Args:
        donor_seq: Input (donor) VH or VL amino acid sequence.
        chain: "VH" or "VL".
        germline_seqs: List of reference germline sequences for comparison.
                       If None or empty, returns empty list (cannot auto-detect).
        window: Number of positions flanking CDR boundaries to consider proximal.

    Returns:
        List of Kabat positions (int, base position only) that are:
          - Non-CDR
          - Within window of a CDR boundary
          - Differ from all provided germlines at that position
    """
    if not germline_seqs:
        return []

    donor_kd = get_kabat_numbering(donor_seq) or {}
    if not donor_kd:
        return []

    proximal = _cdr_proximal_fr_positions(chain, window)
    shm_positions: List[int] = []

    for pos in sorted(proximal):
        key = (pos, "")
        donor_aa = donor_kd.get(key)
        if not donor_aa:
            continue
        all_germlines_agree = True
        any_germline_differs = False
        for gseq in germline_seqs:
            g_kd = get_kabat_numbering(gseq) or {}
            g_aa = g_kd.get(key)
            if g_aa and g_aa != donor_aa:
                any_germline_differs = True
            if g_aa and g_aa == donor_aa:
                all_germlines_agree = False
        if any_germline_differs and all_germlines_agree:
            shm_positions.append(pos)

    return shm_positions


def read_sequence(raw: Optional[str], file_path: Optional[Path]) -> str:
    if file_path:
        lines = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines()]
        lines = [line for line in lines if line and not line.startswith(">")]
        return "".join(lines).replace(" ", "").upper()
    if raw:
        return raw.strip().replace(" ", "").upper()
    raise SystemExit("Sequence is required")


def load_scaffold_rows(species: str) -> List[Dict[str, Any]]:
    path = DOG_SCAFFOLDS if species == "dog" else CAT_SCAFFOLDS
    if not path.exists():
        raise SystemExit(f"Missing scaffold registry for {species}: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for row in data.get("rows", []):
        seq = (row.get("optimization") or {}).get("sequence_aa_opt") or row.get("sequence_aa_kabat_norm")
        if not seq:
            continue
        rows.append({
            **row,
            "sequence": seq,
            "registry_path": str(path),
        })
    return rows


def cdr_lengths(seq: str, chain: str) -> Dict[str, int]:
    kd = get_kabat_numbering(seq) or {}
    ranges = {
        "VH": {"1": (26, 35), "2": (50, 65), "3": (95, 102)},
        "VL": {"1": (24, 34), "2": (50, 56), "3": (89, 97)},
    }
    return {
        cdr: sum(1 for key in kd if lo <= key[0] <= hi)
        for cdr, (lo, hi) in ranges[chain].items()
    }


def fr_identity(input_seq: str, scaffold_seq: str, chain: str) -> float:
    input_kd = get_kabat_numbering(input_seq) or {}
    scaffold_kd = get_kabat_numbering(scaffold_seq) or {}
    if not input_kd or not scaffold_kd:
        return 0.0
    max_pos = 94 if chain == "VH" else 88
    input_keys = {key for key in input_kd if key[0] <= max_pos and not is_in_cdr(key[0], chain)}
    scaffold_keys = {key for key in scaffold_kd if key[0] <= max_pos and not is_in_cdr(key[0], chain)}
    common = input_keys & scaffold_keys
    if not common:
        return 0.0
    matches = sum(1 for key in common if input_kd.get(key) == scaffold_kd.get(key))
    return round(matches / len(common) * 100.0, 2)


def fr1_3_from_sequence(seq: str, chain: str) -> str:
    kd = get_kabat_numbering(seq) or {}
    if not kd:
        return ""
    ranges = {"VH": ((1, 25), (36, 49), (66, 94)), "VL": ((1, 23), (35, 49), (57, 88))}
    chunks = []
    for lo, hi in ranges[chain]:
        chunks.extend(kd[key] for key in sorted_keys(kd) if lo <= key[0] <= hi and not is_in_cdr(key[0], chain))
    return "".join(chunks)


def fast_identity(seq_a: str, seq_b: str) -> float:
    if not seq_a or not seq_b:
        return 0.0
    n = min(len(seq_a), len(seq_b))
    if n == 0:
        return 0.0
    matches = sum(1 for a, b in zip(seq_a[:n], seq_b[:n]) if a == b)
    return round(matches / max(len(seq_a), len(seq_b)) * 100.0, 2)


def extract_fr4_tail(seq: str, chain: str) -> str:
    kd = get_kabat_numbering(seq) or {}
    lo = (MAX_CDR3_VH + 1) if chain == "VH" else (MAX_CDR3_VL + 1)
    return "".join(kd[key] for key in sorted_keys(kd) if key[0] >= lo)


def parse_positions(raw: str) -> List[int]:
    if not raw:
        return []
    out = []
    for token in raw.replace(";", ",").split(","):
        token = token.strip()
        if token:
            out.append(int(token))
    return out


def graft_sequence(
    donor_seq: str,
    scaffold_seq: str,
    chain: str,
    backmut_positions: Iterable[int],
    fr4_strategy: str = "universal_clinical",
    locus: str = "IGHV",
) -> Tuple[str, List[Dict[str, Any]]]:
    donor_kd = get_kabat_numbering(donor_seq) or {}
    scaffold_kd = get_kabat_numbering(scaffold_seq) or {}
    if not donor_kd or not scaffold_kd:
        raise ValueError(f"Kabat numbering failed for {chain}")
    bm_map: Dict[int, str] = {}
    details: List[Dict[str, Any]] = []
    for pos in backmut_positions:
        if is_in_cdr(pos, chain):
            continue
        donor_aa = donor_kd.get((pos, ""))
        scaffold_aa = scaffold_kd.get((pos, ""))
        if donor_aa and scaffold_aa and donor_aa != scaffold_aa:
            bm_map[pos] = donor_aa
            details.append({"kabat_pos": pos, "from": scaffold_aa, "to": donor_aa})

    # FR4 Strategy
    if fr4_strategy == "donor_retention":
        fr4 = extract_fr4_tail(donor_seq, chain)
    elif fr4_strategy == "universal_clinical":
        if chain == "VH":
            fr4 = UNIVERSAL_PET_FR4["VH"]
        elif locus in ("IGLV", "IGLC") or "lambda" in locus.lower():
            fr4 = UNIVERSAL_PET_FR4["VL_lambda"]
        else:
            fr4 = UNIVERSAL_PET_FR4["VL_kappa"]
    else:
        # Fallback to donor retention
        fr4 = extract_fr4_tail(donor_seq, chain)

    assembled = assemble_humanized_v(
        chain=chain,
        mouse_num=donor_kd,
        germ_num=scaffold_kd,
        bm_map=bm_map,
        fr4=fr4,
    )
    return assembled, details


def _norm_ins(ins: str) -> str:
    return ins if ins not in (None, " ") else ""


def surface_reshape_sequence(
    donor_seq: str,
    scaffold_seq: str,
    chain: str,
    reshape_keys: Optional[Set[Tuple[int, str]]] = None,
    fr4_strategy: str = "universal_clinical",
    locus: str = "IGHV",
    is_vhh: bool = False,
) -> Tuple[str, List[str]]:
    """Reshape donor toward scaffold at selected Kabat keys (FR only).

    If ``reshape_keys`` is None, uses legacy Kabat surface position tables
    (:data:`VH_SURFACE_KABAT` / :data:`VL_SURFACE_KABAT`).
    """
    donor_kd = get_kabat_numbering(donor_seq) or {}
    scaffold_kd = get_kabat_numbering(scaffold_seq) or {}
    if not donor_kd or not scaffold_kd:
        raise ValueError(f"Kabat numbering failed for surface reshaping {chain}")
    surface_set = VH_SURFACE_KABAT if chain == "VH" else VL_SURFACE_KABAT
    reshaped = donor_kd.copy()
    mutations: List[str] = []
    vhh_hallmarks = {37, 44, 45, 47}

    # 1. Reshape FR1-FR3 surface positions
    for key in sorted_keys(donor_kd):
        pos, ins = key
        if pos > (MAX_CDR3_VH if chain == "VH" else MAX_CDR3_VL):
            continue  # Skip FR4 positions here, handled below
        ins_n = _norm_ins(ins)
        if reshape_keys is not None:
            if (pos, ins_n) not in reshape_keys or is_in_cdr(pos, chain):
                continue
        else:
            if pos not in surface_set or is_in_cdr(pos, chain):
                continue
        if is_vhh and pos in vhh_hallmarks:
            continue  # Protect VHH hallmark residues from reshaping
        if key not in scaffold_kd:
            continue
        donor_aa = donor_kd[key]
        scaffold_aa = scaffold_kd[key]
        if donor_aa != scaffold_aa:
            reshaped[key] = scaffold_aa
            mutations.append(f"{donor_aa}{pos}{ins}{scaffold_aa}")

    # 2. Re-assemble with FR4 strategy
    v_parts = []
    max_v = MAX_CDR3_VH if chain == "VH" else MAX_CDR3_VL
    for key in sorted_keys(reshaped):
        if key[0] <= max_v:
            v_parts.append(reshaped[key])

    if fr4_strategy == "donor_retention":
        fr4 = extract_fr4_tail(donor_seq, chain)
    elif fr4_strategy == "universal_clinical":
        if chain == "VH":
            fr4 = UNIVERSAL_PET_FR4["VH"]
        elif locus in ("IGLV", "IGLC") or "lambda" in locus.lower():
            fr4 = UNIVERSAL_PET_FR4["VL_lambda"]
        else:
            fr4 = UNIVERSAL_PET_FR4["VL_kappa"]
    else:
        fr4 = extract_fr4_tail(donor_seq, chain)

    return "".join(v_parts) + fr4, mutations


_CMC_PI_RANGES: Dict[str, Dict[str, Dict[str, float]]] = {
    "dog": {
        "VH": {"lo": 5.5, "hi": 10.5, "warn_lo": 6.5, "warn_hi": 9.5},
        "VL_kappa": {"lo": 4.0, "hi": 8.5, "warn_lo": 4.5, "warn_hi": 7.5},
        "VL_lambda": {"lo": 4.5, "hi": 9.0, "warn_lo": 5.0, "warn_hi": 8.0},
    },
    "cat": {
        "VH": {"lo": 5.5, "hi": 10.5, "warn_lo": 6.5, "warn_hi": 9.5},
        "VL_kappa": {"lo": 4.5, "hi": 8.5, "warn_lo": 5.0, "warn_hi": 7.5},
        "VL_lambda": {"lo": 4.5, "hi": 9.0, "warn_lo": 5.0, "warn_hi": 8.0},
    },
}

# Kabat positions with heightened Met oxidation risk in Vernier / CDR contexts
_MET_OXIDATION_VERNIER_VH = {34, 48, 49, 82}
# Kabat positions for Trp exposure risk (surface-facing orientations)
_TRP_OXIDATION_RISK_VH = {33, 47, 103}


def _pi_flag(pi: float, ranges: Dict[str, float]) -> str:
    if pi < ranges["lo"] or pi > ranges["hi"]:
        return "FAIL"
    if pi < ranges["warn_lo"] or pi > ranges["warn_hi"]:
        return "WARN"
    return "PASS"


def _species_cmc_flags(
    seq: str,
    chain: str,
    locus: str,
    pi: float,
    instability: float,
    gravy: float,
    species: str,
) -> List[Dict[str, str]]:
    """Species- and chain-aware CMC flags beyond generic scan."""
    flags: List[Dict[str, str]] = []
    sp = species if species in _CMC_PI_RANGES else "dog"

    # Determine chain key for pI lookup
    if chain == "VH":
        range_key = "VH"
    elif locus in ("IGLV", "IGLC") or locus.startswith("lambda"):
        range_key = "VL_lambda"
    else:
        range_key = "VL_kappa"

    pi_ranges = _CMC_PI_RANGES[sp].get(range_key, _CMC_PI_RANGES[sp]["VH"])
    pi_status = _pi_flag(pi, pi_ranges)
    if pi_status != "PASS":
        flags.append({
            "flag": f"pI_out_of_range_{pi_status.lower()}",
            "severity": pi_status,
            "detail": f"pI={pi:.2f}; target {pi_ranges['warn_lo']}–{pi_ranges['warn_hi']} ({sp}/{range_key})",
        })

    # Instability
    if instability > 45.0:
        flags.append({"flag": "instability_high", "severity": "FAIL",
                       "detail": f"instability_index={instability:.1f} > 45.0 — aggregation risk"})
    elif instability > 35.0:
        flags.append({"flag": "instability_elevated", "severity": "WARN",
                       "detail": f"instability_index={instability:.1f} (WARN threshold 35–45)"})

    # Aggregation proxy
    if gravy > 0.2:
        flags.append({"flag": "gravy_hydrophobic", "severity": "WARN",
                       "detail": f"GRAVY={gravy:.3f} > 0.2 — hydrophobic tendency, monitor aggregation"})

    # Met at Vernier positions in VH (oxidation risk)
    if chain == "VH":
        kd = get_kabat_numbering(seq) or {}
        for pos in _MET_OXIDATION_VERNIER_VH:
            residue = kd.get((pos, ""))
            if residue == "M":
                flags.append({
                    "flag": f"oxidation_M_vernier_kabat{pos}",
                    "severity": "WARN",
                    "detail": f"Met at Vernier/CDR-proximal Kabat {pos} — elevated oxidation risk; consider M→L",
                })
        for pos in _TRP_OXIDATION_RISK_VH:
            residue = kd.get((pos, ""))
            if residue == "W":
                flags.append({
                    "flag": f"oxidation_W_surface_kabat{pos}",
                    "severity": "WARN",
                    "detail": f"Trp at surface-exposed Kabat {pos} — monitor photo-oxidation",
                })

    # CDR3 NG deamidation (chain-agnostic high risk)
    kd = get_kabat_numbering(seq) or {}
    cdr3_range = (95, 102) if chain == "VH" else (89, 97)
    cdr3_seq = "".join(
        aa for (pos, ins), aa in sorted(kd.items(), key=lambda x: (x[0][0], x[0][1]))
        if cdr3_range[0] <= pos <= cdr3_range[1]
    )
    for i in range(len(cdr3_seq) - 1):
        if cdr3_seq[i] == "N" and cdr3_seq[i + 1] == "G":
            flags.append({
                "flag": "deamidation_NG_cdr3_high_risk",
                "severity": "FAIL",
                "detail": f"NG motif in CDR3 at position {i+1} of CDR3 loop — very high deamidation risk",
            })

    return flags


def sequence_cmc(seq: str, chain: str = "VH", locus: str = "IGHV", species: str = "dog") -> Dict[str, Any]:
    """Species-aware CMC triage for petized VH or VL sequences.

    Args:
        seq: Amino acid sequence.
        chain: "VH" or "VL".
        locus: IMGT/NCBI locus identifier (e.g. "IGHV", "IGKV", "IGLV").
        species: "dog" or "cat".
    """
    scan = scan_cmc_liabilities(seq)
    analysis = ProteinAnalysis(seq)
    pi = round(float(analysis.isoelectric_point()), 2)
    instability = round(float(analysis.instability_index()), 2)
    gravy = round(float(analysis.gravy()), 3)
    sp_flags = _species_cmc_flags(seq, chain, locus, pi, instability, gravy, species)
    all_flags = sp_flags  # generic_scan is in separate field; species flags are the actionable layer
    overall = "FAIL" if any(f["severity"] == "FAIL" for f in all_flags) else (
        "WARN" if any(f["severity"] == "WARN" for f in all_flags) else "PASS"
    )
    return {
        "overall": overall,
        "generic_scan": scan,
        "species_flags": sp_flags,
        "metrics": {
            "length": len(seq),
            "pI": pi,
            "instability_index": instability,
            "gravy": gravy,
            "chain": chain,
            "locus": locus,
            "species": species,
        },
    }


def select_candidate(seq: str, chain: str, rows: List[Dict[str, Any]], strategy: str) -> Dict[str, Any]:
    input_cdr = cdr_lengths(seq, chain)
    input_fr13 = fr1_3_from_sequence(seq, chain)
    candidates: List[Dict[str, Any]] = []
    for row in rows:
        if row.get("chain") != chain:
            continue
        scaffold_seq = row["sequence"]
        scaffold_cdr = row.get("cdr_lengths") or cdr_lengths(scaffold_seq, chain)
        length_match = input_cdr.get("1") == scaffold_cdr.get("1") and input_cdr.get("2") == scaffold_cdr.get("2")
        scaffold_fr13 = row.get("fr1_3_concat") or ""
        identity = fast_identity(input_fr13, scaffold_fr13) if scaffold_fr13 else fr_identity(seq, scaffold_seq, chain)
        tier_score = {"tier1": 0, "tier2": 1, "tier3": 2}.get(row.get("tier"), 3)
        candidates.append({
            "row": row,
            "fr_identity": identity,
            "length_match": length_match,
            "cdr_lengths": scaffold_cdr,
            "tier_score": tier_score,
        })
    if not candidates:
        raise ValueError(f"No {chain} scaffold candidates")

    if strategy in {"graft_vernier", "deep_fr_anchor", "auto"}:
        candidates.sort(key=lambda item: (not item["length_match"], item["tier_score"], -item["fr_identity"], item["row"].get("rank_within_chain", 9999)))
    else:
        candidates.sort(key=lambda item: (item["tier_score"], -item["fr_identity"], item["row"].get("rank_within_chain", 9999)))
    return candidates[0]


def resolve_strategy(requested: str, vh_candidate: Dict[str, Any], vl_candidate: Dict[str, Any], has_anchor_positions: bool) -> Dict[str, str]:
    if requested != "auto":
        return {"vh": requested, "vl": requested}
    if has_anchor_positions:
        return {"vh": "deep_fr_anchor", "vl": "deep_fr_anchor"}
    
    out = {}
    vh_ok = vh_candidate["length_match"] and vh_candidate["fr_identity"] >= FR_IDENTITY_MIN_GRAFT
    vl_ok = vl_candidate["length_match"] and vl_candidate["fr_identity"] >= FR_IDENTITY_MIN_GRAFT
    
    out["vh"] = "graft_vernier" if vh_ok else "surface_reshaping"
    out["vl"] = "graft_vernier" if vl_ok else "surface_reshaping"
    return out


def run_petization(
    vh: str,
    vl: Optional[str],
    species: str,
    strategy: str,
    vh_anchor_positions: List[int],
    vl_anchor_positions: List[int],
    fv_pdb: Optional[Path] = None,
    pdb_chain_vh: str = "H",
    pdb_chain_vl: str = "L",
    surface_guidance_mode: str = "kabat_only",
    surface_drop_static_if_buried: bool = False,
    surface_rsa_min: float = 0.12,
    surface_min_dist_cdr: float = 5.0,
    run_struct_qc: bool = False,
    struct_qc_out_dir: Optional[Path] = None,
    struct_qc_label: str = "petized",
    struct_qc_prefer_immunebuilder: bool = True,
    fr4_strategy: str = "universal_clinical",
    molecule: str = "vhvl",
    force_vh_germline: Optional[str] = None,
    force_vl_germline: Optional[str] = None,
) -> Dict[str, Any]:
    is_vhh = molecule == "vhh"
    rows = load_scaffold_rows(species)
    
    if force_vh_germline:
        vh_matches = [r for r in rows if r.get("gene") == force_vh_germline and r.get("chain") == "VH"]
        if not vh_matches:
            raise ValueError(f"Forced VH germline {force_vh_germline} not found in {species} registry")
        vh_candidate = {
            "row": vh_matches[0],
            "fr_identity": fr_identity(vh, vh_matches[0]["sequence"], "VH"),
            "length_match": cdr_lengths(vh, "VH") == (vh_matches[0].get("cdr_lengths") or cdr_lengths(vh_matches[0]["sequence"], "VH")),
            "tier_score": {"tier1": 0, "tier2": 1, "tier3": 2}.get(vh_matches[0].get("tier"), 3),
        }
    else:
        vh_candidate = select_candidate(vh, "VH", rows, strategy)

    if is_vhh:
        vl_candidate = None
    elif force_vl_germline:
        vl_matches = [r for r in rows if r.get("gene") == force_vl_germline and r.get("chain") == "VL"]
        if not vl_matches:
            raise ValueError(f"Forced VL germline {force_vl_germline} not found in {species} registry")
        vl_candidate = {
            "row": vl_matches[0],
            "fr_identity": fr_identity(vl, vl_matches[0]["sequence"], "VL"),
            "length_match": cdr_lengths(vl, "VL") == (vl_matches[0].get("cdr_lengths") or cdr_lengths(vl_matches[0]["sequence"], "VL")),
            "tier_score": {"tier1": 0, "tier2": 1, "tier3": 2}.get(vl_matches[0].get("tier"), 3),
        }
    else:
        vl_candidate = select_candidate(vl, "VL", rows, strategy)

    vh_locus = vh_candidate["row"].get("locus", "IGHV")
    vl_locus = vl_candidate["row"].get("locus", "IGKV") if vl_candidate else None

    # Auto FR-SHM detection: use top-candidate scaffold sequences as germline references.
    # Only runs when strategy == "auto" and no anchor positions already supplied.
    fr_shm_vh: List[int] = []
    fr_shm_vl: List[int] = []
    if strategy == "auto" and not (vh_anchor_positions or vl_anchor_positions):
        vh_scaffold_seq = vh_candidate["row"]["sequence"]
        top_vh_seqs = [r["sequence"] for r in rows if r.get("chain") == "VH"][:3]
        fr_shm_vh = detect_fr_shm_positions(vh, "VH", germline_seqs=top_vh_seqs or [vh_scaffold_seq])
        if fr_shm_vh:
            vh_anchor_positions = sorted(set(vh_anchor_positions) | set(fr_shm_vh))

        if not is_vhh and vl_candidate:
            vl_scaffold_seq = vl_candidate["row"]["sequence"]
            top_vl_seqs = [r["sequence"] for r in rows if r.get("chain") == "VL"][:3]
            fr_shm_vl = detect_fr_shm_positions(vl, "VL", germline_seqs=top_vl_seqs or [vl_scaffold_seq])
            if fr_shm_vl:
                vl_anchor_positions = sorted(set(vl_anchor_positions) | set(fr_shm_vl))

    if is_vhh:
        # VHH uses surface_reshaping if auto
        if strategy == "auto":
            selected_strategies = {"vh": "surface_reshaping", "vl": "none"}
        else:
            selected_strategies = {"vh": strategy, "vl": "none"}
    else:
        selected_strategies = resolve_strategy(
            strategy,
            vh_candidate,
            vl_candidate,
            bool(vh_anchor_positions or vl_anchor_positions),
        )

    vh_scaffold = vh_candidate["row"]["sequence"]
    vl_scaffold = vl_candidate["row"]["sequence"] if vl_candidate else None
    
    vh_reshape_keys: Optional[Set[Tuple[int, str]]] = None
    vl_reshape_keys: Optional[Set[Tuple[int, str]]] = None
    surface_guidance: Dict[str, Any] = {"enabled": False}

    use_structure_surface = (
        fv_pdb is not None
        and fv_pdb.is_file()
        and (
            surface_guidance_mode in ("union", "intersect")
            or (surface_guidance_mode == "kabat_only" and surface_drop_static_if_buried)
        )
    )

    if (
        selected_strategies["vh"] == "surface_reshaping"
        or selected_strategies["vl"] == "surface_reshaping"
    ):
        if use_structure_surface:
            from scripts.petization_surface_guided import build_reshape_keys_for_petization  # noqa: E402

            surface_guidance = {
                "enabled": True,
                "pdb": str(fv_pdb.resolve()),
                "mode": surface_guidance_mode,
                "drop_static_if_buried": surface_drop_static_if_buried,
                "rsa_min": surface_rsa_min,
                "min_dist_cdr_ca": surface_min_dist_cdr,
                "vh": None,
                "vl": None,
            }
            if selected_strategies["vh"] == "surface_reshaping":
                vh_reshape_keys, vh_sg = build_reshape_keys_for_petization(
                    fv_pdb,
                    vh,
                    "VH",
                    pdb_chain_vh,
                    VH_SURFACE_KABAT,
                    surface_guidance_mode,
                    surface_drop_static_if_buried,
                    rsa_min_exposed=surface_rsa_min,
                    min_dist_cdr_ca=surface_min_dist_cdr,
                )
                surface_guidance["vh"] = vh_sg
            if not is_vhh and selected_strategies["vl"] == "surface_reshaping":
                vl_reshape_keys, vl_sg = build_reshape_keys_for_petization(
                    fv_pdb,
                    vl,
                    "VL",
                    pdb_chain_vl,
                    VL_SURFACE_KABAT,
                    surface_guidance_mode,
                    surface_drop_static_if_buried,
                    rsa_min_exposed=surface_rsa_min,
                    min_dist_cdr_ca=surface_min_dist_cdr,
                )
                surface_guidance["vl"] = vl_sg
        elif fv_pdb is not None and not fv_pdb.is_file():
            surface_guidance = {"enabled": False, "error": f"PDB not found: {fv_pdb}"}
        elif fv_pdb is not None and fv_pdb.is_file() and not use_structure_surface:
            surface_guidance = {
                "enabled": False,
                "note": "PDB provided but surface_guidance_mode is kabat_only without --surface-drop-buried; using legacy Kabat tables only",
                "pdb": str(fv_pdb.resolve()),
            }

    if selected_strategies["vh"] == "surface_reshaping":
        vh_out, vh_mutations = surface_reshape_sequence(
            vh, vh_scaffold, "VH", reshape_keys=vh_reshape_keys,
            fr4_strategy=fr4_strategy, locus=vh_locus, is_vhh=is_vhh
        )
        vh_bm: List[Dict[str, Any]] = []
    else:
        vh_positions = list(VERNIER_KABAT_VH)
        if selected_strategies["vh"] == "deep_fr_anchor":
            vh_positions = sorted(set(vh_positions + vh_anchor_positions))
        vh_out, vh_bm = graft_sequence(
            vh, vh_scaffold, "VH", vh_positions,
            fr4_strategy=fr4_strategy, locus=vh_locus
        )
        vh_mutations = []

    if not is_vhh:
        if selected_strategies["vl"] == "surface_reshaping":
            vl_out, vl_mutations = surface_reshape_sequence(
                vl, vl_scaffold, "VL", reshape_keys=vl_reshape_keys,
                fr4_strategy=fr4_strategy, locus=vl_locus
            )
            vl_bm: List[Dict[str, Any]] = []
        else:
            vl_positions = list(VERNIER_KABAT_VL)
            if selected_strategies["vl"] == "deep_fr_anchor":
                vl_positions = sorted(set(vl_positions + vl_anchor_positions))
            vl_out, vl_bm = graft_sequence(
                vl, vl_scaffold, "VL", vl_positions,
                fr4_strategy=fr4_strategy, locus=vl_locus
            )
            vl_mutations = []
    else:
        vl_out = None
        vl_mutations = []
        vl_bm = []

    cdr_checks = {
        "vh": verify_cdr_preservation(get_kabat_numbering(vh_out) or {}, get_kabat_numbering(vh) or {}, "VH"),
    }
    if not is_vhh:
        cdr_checks["vl"] = verify_cdr_preservation(get_kabat_numbering(vl_out) or {}, get_kabat_numbering(vl) or {}, "VL")
    
    if is_vhh:
        status = "PASS" if not cdr_checks["vh"] else "FAIL"
    else:
        status = "PASS" if not cdr_checks["vh"] and not cdr_checks["vl"] else "FAIL"

    # Phase 4.5 — Structure QC (optional, triggered by run_struct_qc=True)
    struct_qc_result: Optional[Dict[str, Any]] = None
    if run_struct_qc and status == "PASS":
        from scripts.petization_struct_qc import run_struct_qc as _run_sq  # noqa: E402
        _qc_dir = struct_qc_out_dir or (SUITE / "projects" / "petization_runs" / struct_qc_label / "struct_qc")
        struct_qc_result = _run_sq(
            vh_petized=vh_out,
            vl_petized=vl_out,
            out_dir=_qc_dir,
            label=struct_qc_label,
            input_pdb=fv_pdb,
            prefer_immunebuilder=struct_qc_prefer_immunebuilder,
        )
        # Downgrade overall status if structure check FAILs
        if struct_qc_result.get("status") == "FAIL":
            status = "FAIL"
        elif struct_qc_result.get("status") == "WARN" and status == "PASS":
            status = "WARN"

    if is_vhh:
        overall_strategy = selected_strategies["vh"]
    else:
        overall_strategy = "mixed" if selected_strategies["vh"] != selected_strategies["vl"] else selected_strategies["vh"]

    res = {
        "abenginecore_version": "petization_cli_v1.4.0 (Engine V5.1.0)",
        "petization_standard": "docs/PETIZATION_STANDARD_V1.0.md",
        "standard_version": "V1.2.0",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "overall_status": status,
        "species": species,
        "molecule": molecule,
        "strategy_requested": strategy,
        "strategy_selected": overall_strategy,
        "strategies_by_chain": selected_strategies,
        "fr4_strategy": fr4_strategy,
        "selection": {
            "vh": {
                "germline": vh_candidate["row"].get("gene"),
                "tier": vh_candidate["row"].get("tier"),
                "fr_identity": vh_candidate["fr_identity"],
                "length_match": vh_candidate["length_match"],
                "source": vh_candidate["row"].get("source"),
            }
        },
        "fr_shm_auto_detected": {
            "vh": fr_shm_vh,
            "note": (
                "Positions within CDR-boundary window that differ from all top scaffolds; "
                "auto-added to anchor list when strategy=auto."
                if (fr_shm_vh or fr_shm_vl) else "No CDR-proximal FR-SHM detected."
            ),
        },
        "sequences": {
            "input_vh": vh,
            "petized_vh": vh_out,
        },
        "mutations": {
            "vh_backmutations": vh_bm,
            "vh_surface_reshaping": vh_mutations,
        },
        "surface_guidance": surface_guidance,
        "cmc": {
            "vh": sequence_cmc(
                vh_out, chain="VH",
                locus=vh_candidate["row"].get("locus", "IGHV"),
                species=species,
            )
        },
        "_qa_audit": {
            "cdr_preservation": cdr_checks,
            "structure_qc": struct_qc_result,
            "structure_qc_required": struct_qc_result is None,
            "structure_qc_note": (
                "Structure QC completed (Phase 4.5)." if struct_qc_result
                else "Run with --run-struct-qc to execute Phase 4.5 automatically."
            ),
            "fc_guidance": {
                "cat": "Prefer native cat IgG2 for effector-silent programs; human LALA-PG/LS/YTE are references only and require feline Fc mapping/FTO.",
                "dog": "Use dog IgG-Bm or project-approved canine Fc; verify Fc IP status before final format.",
            }.get(species),
        },
    }

    if not is_vhh:
        res["selection"]["vl"] = {
            "germline": vl_candidate["row"].get("gene") if vl_candidate else None,
            "tier": vl_candidate["row"].get("tier") if vl_candidate else None,
            "fr_identity": vl_candidate["fr_identity"] if vl_candidate else None,
            "length_match": vl_candidate["length_match"] if vl_candidate else None,
            "source": vl_candidate["row"].get("source") if vl_candidate else None,
        }
        res["fr_shm_auto_detected"]["vl"] = fr_shm_vl
        res["sequences"]["input_vl"] = vl
        res["sequences"]["petized_vl"] = vl_out
        res["mutations"]["vl_backmutations"] = vl_bm
        res["mutations"]["vl_surface_reshaping"] = vl_mutations
        res["cmc"]["vl"] = sequence_cmc(
            vl_out, chain="VL",
            locus=vl_candidate["row"].get("locus", "IGKV") if vl_candidate else "IGKV",
            species=species,
        ) if vl_out else None

    return res


def write_outputs(result: Dict[str, Any], out_dir: Path, project: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "petization_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    fasta = f">{project}_{result['species']}_{result['strategy_selected']}_VH\n{result['sequences']['petized_vh']}\n"
    if result.get("molecule") != "vhh":
        fasta += f">{project}_{result['species']}_{result['strategy_selected']}_VL\n{result['sequences']['petized_vl']}\n"
    (out_dir / "petization_sequences.fasta").write_text(fasta, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified dog/cat petization pipeline")
    parser.add_argument("--project", required=True)
    parser.add_argument("--species", choices=["dog", "cat"], required=True)
    parser.add_argument("--molecule", choices=["vhvl", "vhh"], default="vhvl", help="Molecule type: vhvl (default) or vhh")
    parser.add_argument("--vh")
    parser.add_argument("--vl")
    parser.add_argument("--vh-file", type=Path)
    parser.add_argument("--vl-file", type=Path)
    parser.add_argument(
        "--strategy",
        choices=["auto", "graft_vernier", "surface_reshaping", "deep_fr_anchor"],
        default="auto",
    )
    parser.add_argument(
        "--fr4-strategy",
        choices=["universal_clinical", "donor_retention"],
        default="universal_clinical",
        help="FR4 selection: universal_clinical (safe common set) or donor_retention (keep donor tail)",
    )
    parser.add_argument("--vh-anchor-positions", default="", help="Comma-separated Kabat FR positions to force preserve")
    parser.add_argument("--vl-anchor-positions", default="", help="Comma-separated Kabat FR positions to force preserve")
    parser.add_argument(
        "--fv-pdb",
        type=Path,
        default=None,
        help="Fv/Fab PDB for structure-guided surface reshaping (SASA + CDR distance; use with --surface-guidance)",
    )
    parser.add_argument("--pdb-chain-vh", default="H", help="PDB chain id for VH (default H)")
    parser.add_argument("--pdb-chain-vl", default="L", help="PDB chain id for VL (default L)")
    parser.add_argument(
        "--surface-guidance",
        choices=["kabat_only", "union", "intersect"],
        default="kabat_only",
        help="union: Kabat surface table ∪ struct-exposed FR; intersect: table ∩ struct; "
        "kabat_only with --surface-drop-buried uses PDB to prune buried static sites",
    )
    parser.add_argument(
        "--surface-drop-buried",
        action="store_true",
        help="Remove static Kabat surface sites with very low RSA in the supplied PDB",
    )
    parser.add_argument("--surface-rsa-min", type=float, default=0.12, help="Min relative SASA for struct extras (default 0.12)")
    parser.add_argument(
        "--surface-min-dist-cdr",
        type=float,
        default=5.0,
        help="Min CA distance to nearest CDR CA for struct extras (Å, default 5)",
    )
    parser.add_argument(
        "--run-struct-qc",
        action="store_true",
        help="Phase 4.5: predict Fv structure and run VH-VL angle / CDR RMSD / free-Cys QC",
    )
    parser.add_argument("--force-vh-germline", help="Force a specific VH germline gene name")
    parser.add_argument("--force-vl-germline", help="Force a specific VL germline gene name")
    parser.add_argument(
        "--struct-qc-igfold",
        action="store_true",
        help="Use IgFold (batch-mode) instead of ImmuneBuilder for Phase 4.5 prediction",
    )
    parser.add_argument("--out-dir", type=Path, default=Path("projects/petization_runs"))
    args = parser.parse_args()

    vh = read_sequence(args.vh, args.vh_file)
    vl = None if args.molecule == "vhh" else read_sequence(args.vl, args.vl_file)
    result = run_petization(
        vh=vh,
        vl=vl,
        species=args.species,
        molecule=args.molecule,
        strategy=args.strategy,
        vh_anchor_positions=parse_positions(args.vh_anchor_positions),
        vl_anchor_positions=parse_positions(args.vl_anchor_positions),
        fv_pdb=args.fv_pdb,
        pdb_chain_vh=args.pdb_chain_vh,
        pdb_chain_vl=args.pdb_chain_vl,
        surface_guidance_mode=args.surface_guidance,
        surface_drop_static_if_buried=args.surface_drop_buried,
        surface_rsa_min=args.surface_rsa_min,
        surface_min_dist_cdr=args.surface_min_dist_cdr,
        run_struct_qc=args.run_struct_qc,
        struct_qc_out_dir=args.out_dir / args.project / "struct_qc",
        struct_qc_label=args.project,
        struct_qc_prefer_immunebuilder=not args.struct_qc_igfold,
        fr4_strategy=args.fr4_strategy,
        force_vh_germline=args.force_vh_germline,
        force_vl_germline=args.force_vl_germline,
    )
    out_dir = args.out_dir / args.project
    write_outputs(result, out_dir, args.project)
    print(json.dumps({
        "project": args.project,
        "species": args.species,
        "overall_status": result["overall_status"],
        "strategy_selected": result["strategy_selected"],
        "vh_germline": result["selection"]["vh"]["germline"],
        "vl_germline": result["selection"].get("vl", {}).get("germline") if "vl" in result["selection"] else None,
        "out_dir": str(out_dir),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
