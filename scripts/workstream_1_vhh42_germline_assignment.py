#!/usr/bin/env python3
"""
Workstream 1: VHH42 Germline Assignment

Assigns human germline to each of 42 VHH by:
1. Running ANARCI on each VHH sequence (Kabat numbering)
2. Extracting FR1, FR2, FR3 as concatenated strings
3. Scoring against human IGHV germline Kabat cache
4. Finding top-3 closest human germlines by CDR length, FR identity, Vernier similarity

Output: data/vhh_clinical_39_union/vhh42_germline_assignments.json
"""

import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

SUITE_ROOT = Path(__file__).resolve().parent.parent
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))
DATA_ROOT = SUITE_ROOT / "data"
VHH_ATLAS_ROOT = DATA_ROOT / "vhh_39_clinical_atlas"
VHH_UNION_ROOT = DATA_ROOT / "vhh_clinical_39_union"
CACHE_ROOT = DATA_ROOT / "germlines" / "human_ig_aa" / "_cache"
CONFIG_ROOT = SUITE_ROOT / "config"

# Input/output
MASTER_TABLE = VHH_ATLAS_ROOT / "master_table.csv"
GERMLINE_OUTPUT = VHH_UNION_ROOT / "vhh42_germline_assignments.json"

# Data sources (per Standard §3.2a — all clinically validated, zero ORF)
# Primary scoring library: 11 VH germlines from 840 clinical therapeutic antibodies
THERA_GERMLINE_MAP = DATA_ROOT / "thera_sabdab" / "out" / "thera_germline_mapping.csv"
# Kabat sequence data for those 11 germlines
IGHV_CACHE = CACHE_ROOT / "IGHV_kabat_cache.json"
# ADA risk lookup (v2.0 — 138 antibodies, 48 VH germlines)
ADA_ANCHORS = CONFIG_ROOT / "clinical_germline_anchors.json"

# Standard amino acid chemistry classes
AA_CHEM_CLASS = {
    'A': 'nonpolar', 'G': 'nonpolar', 'V': 'nonpolar', 'L': 'nonpolar', 'I': 'nonpolar', 'M': 'nonpolar', 'F': 'aromatic', 'W': 'aromatic', 'P': 'nonpolar',
    'S': 'polar', 'T': 'polar', 'C': 'polar', 'Y': 'aromatic',
    'N': 'polar', 'Q': 'polar',
    'D': 'acidic', 'E': 'acidic',
    'K': 'basic', 'R': 'basic', 'H': 'basic',
}

VERNIER_POS_VH = [2, 27, 28, 29, 30, 48, 49, 67, 69, 71, 73, 78, 93, 94]
VERNIER_TIER_VH = {
    71: "T1",
    2: "T2", 27: "T2", 28: "T2", 29: "T2", 30: "T2", 69: "T2", 93: "T2", 94: "T2",
    48: "T3", 49: "T3", 67: "T3", 73: "T3", 78: "T3",
}
TIER_WEIGHTS = {"T1": 3.0, "T2": 2.0, "T3": 1.0}


def chem_class(aa: str) -> str:
    """Get chemical class of amino acid."""
    return AA_CHEM_CLASS.get(aa, 'unknown')


def compute_vernier_similarity_str_keys(donor_vernier: Dict[str, str], germ_vernier: Dict[str, str]) -> float:
    """
    Compute Vernier similarity score using string-keyed vernier dicts.
    Cache stores vernier_residues as {"71": "R", "2": "V", ...} (string keys).
    Scoring: exact match = 2.0w, same chem class = 0.5w; w = tier weight.
    """
    score = 0.0
    max_score = 0.0

    for pos in VERNIER_POS_VH:
        pos_str = str(pos)
        donor_aa = donor_vernier.get(pos_str, "")
        germ_aa = germ_vernier.get(pos_str, "")

        if not donor_aa or not germ_aa:
            continue

        tier = VERNIER_TIER_VH.get(pos, "T3")
        weight = TIER_WEIGHTS.get(tier, 1.0)
        max_score += 2.0 * weight

        if donor_aa == germ_aa:
            score += 2.0 * weight
        elif chem_class(donor_aa) == chem_class(germ_aa):
            score += 0.5 * weight

    return round(score / max_score, 4) if max_score else 0.0


def fr_identity_pct(donor_fr: str, germ_fr: str) -> float:
    """Compute FR identity percentage (position-by-position, shorter length)."""
    if not donor_fr or not germ_fr:
        return 0.0
    min_len = min(len(donor_fr), len(germ_fr))
    if min_len == 0:
        return 0.0
    matches = sum(1 for i in range(min_len) if donor_fr[i] == germ_fr[i])
    return round(100.0 * matches / min_len, 2)


def extract_vernier_from_fr_segments(fr1: str, cdr1: str, fr2: str, fr3: str) -> Dict[str, str]:
    """
    Extract Vernier residues from pre-segmented FR1/CDR1/FR2/FR3 using Kabat absolute offsets.

    VHH atlas boundary (Kabat): FR1=1-25, CDR1=26-35, FR2=36-49, FR3=66-94+
    Offset formula: pos N in region R → R[N - region_start] (0-indexed)

    Positions 27/28/29/30 are in CDR1 (Kabat 26-35), NOT in FR1.
    Positions 93/94 are in FR3 (Kabat 66...) at absolute offsets 27/28.
    """
    def _get(s, idx):
        return s[idx] if 0 <= idx < len(s) else ""

    return {
        "2":  _get(fr1, 1),           # FR1[1]  Kabat 2
        "27": _get(cdr1, 1),          # CDR1[1] Kabat 27
        "28": _get(cdr1, 2),          # CDR1[2] Kabat 28
        "29": _get(cdr1, 3),          # CDR1[3] Kabat 29
        "30": _get(cdr1, 4),          # CDR1[4] Kabat 30
        "48": _get(fr2, 12),          # FR2[12] Kabat 48
        "49": _get(fr2, 13),          # FR2[13] Kabat 49
        "67": _get(fr3, 1),           # FR3[1]  Kabat 67
        "69": _get(fr3, 3),           # FR3[3]  Kabat 69
        "71": _get(fr3, 5),           # FR3[5]  Kabat 71
        "73": _get(fr3, 7),           # FR3[7]  Kabat 73
        "78": _get(fr3, 12),          # FR3[12] Kabat 78
        "93": _get(fr3, 27),          # FR3[27] Kabat 93 (93-66=27)
        "94": _get(fr3, 28),          # FR3[28] Kabat 94 (94-66=28)
    }


def load_vhh_sequences() -> List[Dict[str, str]]:
    """
    Load VHH sequences AND FR/CDR regions: master_table (pre-segmented) plus
    vhh42_sabdab_supplement.json (Kabat segmentation via ANARCII for 3 Database-B chains).
    """
    vhh_list = []

    if MASTER_TABLE.exists():
        with open(MASTER_TABLE, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('Name', '').strip()
                seq = row.get('Sequence', '').strip()
                fr1 = row.get('FR1', '').strip()
                fr2 = row.get('FR2', '').strip()
                fr3 = row.get('FR3', '').strip()
                cdr1 = row.get('CDR1', '').strip()
                cdr2 = row.get('CDR2', '').strip()
                cdr3 = row.get('CDR3', '').strip()
                if name and seq:
                    vhh_list.append({
                        "name": name,
                        "sequence": seq,
                        "fr1": fr1, "fr2": fr2, "fr3": fr3,
                        "cdr1": cdr1, "cdr2": cdr2, "cdr3": cdr3,
                        "origin": "clinical",
                    })

    try:
        from core.vhh.vhh42_reference_loader import (
            kabat_fr_cdr_segments_for_vhh,
            load_sabdab_supplement_entries,
        )
        for entry in load_sabdab_supplement_entries():
            name = (entry.get("id") or "").strip()
            seq = (entry.get("sequence") or "").strip()
            if not name or not seq:
                continue
            seg = kabat_fr_cdr_segments_for_vhh(seq)
            if not seg:
                print(
                    "[Warning] Kabat segmentation failed for supplement %s — skipped" % name,
                    file=sys.stderr,
                )
                continue
            vhh_list.append({
                "name": name,
                "sequence": seq,
                "fr1": seg["fr1"],
                "fr2": seg["fr2"],
                "fr3": seg["fr3"],
                "cdr1": seg["cdr1"],
                "cdr2": seg["cdr2"],
                "cdr3": seg["cdr3"],
                "origin": "SAbDab_humanized",
            })
    except ImportError as e:
        print("[Warning] Could not load SAbDab supplement: %s" % e, file=sys.stderr)

    return vhh_list


def load_clinical_germline_scoring_library() -> Dict[str, Dict]:
    """
    Load the 11 clinically validated VH germlines from 840 therapeutic antibody data.
    Data sources (per Standard §3.2a, all functional, zero ORF):
      - thera_sabdab/out/thera_germline_mapping.csv → clinical frequency weights
      - germlines/human_ig_aa/_cache/IGHV_kabat_cache.json → sequence / Vernier data
    Returns: {germline_id: {fr_concat, vernier_residues, kabat_cdr_lengths, clinical_count}}
    """
    # Step 1: Load clinical frequency from 840-antibody dataset
    if not THERA_GERMLINE_MAP.exists():
        print("[Error] thera_germline_mapping.csv not found", file=sys.stderr)
        return {}
    clinical_germlines: Dict[str, int] = {}
    with open(THERA_GERMLINE_MAP, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get("chain", "") == "VH":
                clinical_germlines[row["germline"]] = int(row["count"])

    total_count = sum(clinical_germlines.values())
    print("  Clinical VH germline library: %d germlines, %d total antibodies (zero ORF)" % (
        len(clinical_germlines), total_count))

    # Step 2: Load sequence data from Kabat cache (only for the 11 clinical germlines)
    if not IGHV_CACHE.exists():
        print("[Error] IGHV_kabat_cache.json not found", file=sys.stderr)
        return {}
    with open(IGHV_CACHE, encoding='utf-8') as f:
        all_genes = json.load(f).get("genes", {})

    scoring_lib: Dict[str, Dict] = {}
    for germ_id, count in clinical_germlines.items():
        entry = all_genes.get(germ_id, {})
        if not entry.get("fr_concat"):
            print("[Warning] %s not in Kabat cache — skipped" % germ_id, file=sys.stderr)
            continue
        scoring_lib[germ_id] = {
            "fr_concat":          entry["fr_concat"],
            "vernier_residues":   entry.get("vernier_residues", {}),
            "kabat_cdr_lengths":  entry.get("kabat_cdr_lengths", {}),
            "clinical_count":     count,
            "clinical_freq":      round(count / total_count, 4),
        }

    return scoring_lib


def load_ada_anchors() -> Dict[str, Dict]:
    """
    Load ADA risk lookup from clinical_germline_anchors.json v2.0.
    Data source: 138 ADA antibodies, 48 VH germlines.
    """
    if not ADA_ANCHORS.exists():
        print("[Warning] clinical_germline_anchors.json not found", file=sys.stderr)
        return {}
    with open(ADA_ANCHORS, encoding='utf-8') as f:
        data = json.load(f)
    return data.get("germlines", {})


def score_vhh_against_germlines(vhh_entry: Dict[str, str], scoring_lib: Dict[str, Dict]) -> List[Dict[str, Any]]:
    """
    Score a VHH against the 11 clinically validated human IGHV germlines.
    Data source: thera_germline_mapping.csv (840 therapeutic antibodies) + IGHV_kabat_cache.json.
    All entries in scoring_lib are functional — zero ORF possible.
    No ANARCI required: uses pre-segmented FR/CDR from frozen atlas.

    Composite score (per §3.2a):
      0.35 × Vernier_similarity   (structural compatibility)
      0.35 × FR_identity          (sequence similarity)
      0.20 × CDR_match            (CDR1/CDR2 length compatibility)
      0.10 × clinical_freq        (clinical frequency weight — 840 antibodies)
    """
    fr1  = vhh_entry.get("fr1", "")
    fr2  = vhh_entry.get("fr2", "")
    fr3  = vhh_entry.get("fr3", "")
    cdr1 = vhh_entry.get("cdr1", "")
    cdr2 = vhh_entry.get("cdr2", "")

    donor_fr_concat = fr1 + fr2 + fr3
    donor_cdr_lens  = {"CDR1": len(cdr1), "CDR2": len(cdr2)}
    donor_vernier   = extract_vernier_from_fr_segments(fr1, cdr1, fr2, fr3)

    candidates = []

    for germline_id, entry in scoring_lib.items():
        try:
            germ_fr      = entry["fr_concat"]
            germ_cdr_len = entry.get("kabat_cdr_lengths", {})
            germ_vernier = entry.get("vernier_residues", {})
            clin_freq    = entry.get("clinical_freq", 0.0)

            # CDR1 and CDR2 length match (CDR3 always 0 in germline — excluded)
            cdr_match = (
                int(donor_cdr_lens["CDR1"] == germ_cdr_len.get("CDR1", -1)) +
                int(donor_cdr_lens["CDR2"] == germ_cdr_len.get("CDR2", -1))
            )  # 0-2

            fr_id      = fr_identity_pct(donor_fr_concat, germ_fr)
            vernier_sim = compute_vernier_similarity_str_keys(donor_vernier, germ_vernier)

            score = (
                0.35 * vernier_sim +
                0.35 * (fr_id / 100.0) +
                0.20 * (cdr_match / 2.0) +
                0.10 * clin_freq
            )

            candidates.append({
                "germline":          germline_id,
                "score":             round(score, 4),
                "fr_identity_pct":   fr_id,
                "vernier_similarity": vernier_sim,
                "cdr_match":         cdr_match,
                "clinical_count":    entry.get("clinical_count", 0),
                "clinical_freq_pct": round(clin_freq * 100, 1),
            })
        except Exception:
            continue

    candidates.sort(key=lambda x: -x["score"])
    return candidates[:3]


def assign_germlines_to_all_vhh(
    vhh_list: List[Dict[str, str]],
    scoring_lib: Dict[str, Dict],
    ada_anchors: Dict[str, Dict],
) -> List[Dict[str, Any]]:
    """
    Assign closest clinical human germline + ADA risk to each VHH.
    Scoring library: 11 germlines from 840 therapeutic antibodies (zero ORF).
    ADA lookup: clinical_germline_anchors.json v2.0 (138 antibodies).
    """
    results = []

    for i, vhh in enumerate(vhh_list, 1):
        name   = vhh.get("name", "")
        seq    = vhh.get("sequence", "")
        origin = vhh.get("origin", "clinical")
        cdr3   = vhh.get("cdr3", "")

        print("[%d/%d] %s" % (i, len(vhh_list), name))

        alternatives = score_vhh_against_germlines(vhh, scoring_lib)
        top_germ = alternatives[0] if alternatives else {}
        top_id   = top_germ.get("germline", "UNASSIGNED")

        # ADA risk lookup from rebuilt v2.0 anchor file
        ada_entry = ada_anchors.get(top_id, {})
        ada_risk   = ada_entry.get("majority_risk", "UNKNOWN")
        ada_dist   = ada_entry.get("ada_risk_distribution", {})
        ada_mean   = ada_entry.get("ada_pct_mean")
        ada_n      = ada_entry.get("n_antibodies", 0)

        record = {
            "name":                  name,
            "vhh_sequence":          seq,
            "origin":                origin,
            "cdr3_len":              len(cdr3),
            # Germline assignment
            "top_human_germline":    top_id,
            "top_score":             top_germ.get("score", 0.0),
            "top_fr_identity_pct":   top_germ.get("fr_identity_pct", 0.0),
            "top_vernier_similarity":top_germ.get("vernier_similarity", 0.0),
            "top_cdr_match":         top_germ.get("cdr_match", 0),
            "top_clinical_freq_pct": top_germ.get("clinical_freq_pct", 0.0),
            "alternatives":          alternatives[1:] if len(alternatives) > 1 else [],
            # ADA risk (from clinical_germline_anchors.json v2.0)
            "ada_majority_risk":     ada_risk,
            "ada_risk_distribution": ada_dist,
            "ada_pct_mean":          ada_mean,
            "ada_n_antibodies":      ada_n,
            "ada_source":            "clinical_germline_anchors.json v2.0 (138 antibodies)",
        }

        results.append(record)
        print("    top=%-20s  score=%.4f  FR=%.1f%%  vernier=%.4f  clin_freq=%.1f%%  ADA=%s" % (
            top_id, record["top_score"], record["top_fr_identity_pct"],
            record["top_vernier_similarity"], record["top_clinical_freq_pct"],
            ada_risk))

    return results


def main():
    print("=" * 70)
    print("Workstream 1: VHH42 Germline Assignment  [v2.0 — Clinical Library]")
    print("Standard: VHH_HUMANIZATION_DESIGN_STANDARD.md V2.0 §3.2a")
    print("=" * 70)
    print()

    # Load VHH sequences (pre-segmented, frozen atlas)
    print("[Info] Loading VHH sequences (frozen atlas)...")
    vhh_list = load_vhh_sequences()
    print("  Loaded: %d VHH" % len(vhh_list))
    print()

    # Load clinical germline scoring library (11 germlines from 840 therapeutics)
    print("[Info] Loading clinical germline scoring library...")
    print("  Source: thera_germline_mapping.csv (840 clinical antibodies)")
    scoring_lib = load_clinical_germline_scoring_library()
    print("  Scoring library: %d germlines (all functional, zero ORF)" % len(scoring_lib))
    print()

    if not scoring_lib:
        print("[Error] Scoring library empty — check thera_germline_mapping.csv", file=sys.stderr)
        return 1

    # Load ADA anchor file v2.0
    print("[Info] Loading ADA risk anchors (clinical_germline_anchors.json v2.0)...")
    ada_anchors = load_ada_anchors()
    print("  ADA anchors: %d VH germlines (138 antibodies)" % len(ada_anchors))
    print()

    # Assign germlines + ADA risk
    print("[Info] Assigning germlines...")
    print()
    results = assign_germlines_to_all_vhh(vhh_list, scoring_lib, ada_anchors)
    print()

    if not results:
        print("[Error] No results computed", file=sys.stderr)
        return 1

    # Write output
    print("[Info] Writing output...")
    GERMLINE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with open(GERMLINE_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump({
            "_meta": {
                "version": "2.0",
                "date": "2026-04-18",
                "standard": "VHH_HUMANIZATION_DESIGN_STANDARD_V2.0 §3.2a",
                "scoring_source": "thera_germline_mapping.csv (840 clinical antibodies, 11 VH germlines)",
                "ada_source": "clinical_germline_anchors.json v2.0 (138 antibodies)",
                "method": "FR1+FR2+FR3 identity + Vernier similarity + CDR match + clinical freq",
                "no_anarci_required": True,
                "n": len(results),
                "note": "Germline assignment is for ADA risk lookup only. Rows = 39 clinical atlas + 3 SAbDab supplement (VHH42 per-sequence parity).",
            },
            "germline_assignments": results
        }, f, indent=2, ensure_ascii=False)

    print("  Written: %s" % GERMLINE_OUTPUT)
    print()
    print("=" * 70)
    print("Workstream 1 Complete")
    print("  VHH processed:   %d" % len(results))
    print("  Germline library: %d clinical germlines (zero ORF)" % len(scoring_lib))
    print("  ADA anchors:      %d germlines (v2.0, 138 antibodies)" % len(ada_anchors))
    print("=" * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())
