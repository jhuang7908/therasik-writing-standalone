"""
build_pet_clinical_combined_profile.py
──────────────────────────────────────────────────────────────────────────────
/ — VH + VL (κ / λ) 


-----------
Level 1 ()    weight=3  — pet_antibody_atlas/master_table.csv
Level 2 (CMC ) weight=2  — dog/cat_scaffold_cmc_optimization_tier1_tier2_v1.json Tier-1
Level 3 ()   weight=1  — dog/cat_ighv/igkv/iglv_aa_freq_kabat_v2.json

 (v3/)
--------------
dog_ighv_clinical_combined_v1.json   (VH)
dog_igkv_clinical_combined_v1.json   (VL kappa)
dog_iglv_clinical_combined_v1.json   (VL lambda)
cat_ighv_clinical_combined_v1.json   (VH)
cat_igkv_clinical_combined_v1.json   (VL kappa)
cat_iglv_clinical_combined_v1.json   (VL lambda)

: anarcii conda 
Usage:
    python scripts/build_pet_clinical_combined_profile.py
    python scripts/build_pet_clinical_combined_profile.py --species dog
    python scripts/build_pet_clinical_combined_profile.py --chain VH
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]

# ── Input paths ───────────────────────────────────────────────────────────────
ATLAS_CSV = REPO / "data/pet_antibody_atlas/master_table.csv"
DOG_SCAFFOLD_JSON = REPO / "data/germlines/canis_lupus_familiaris_ig_aa/dog_scaffold_cmc_optimization_tier1_tier2_v1.json"
CAT_SCAFFOLD_JSON = REPO / "data/germlines/felis_catus_ig_aa/cat_scaffold_cmc_optimization_tier1_tier2_v1.json"

# v2 germline frequency archives (fallback Level 3)
_GERMLINE_V2: Dict[str, Dict[str, str]] = {
    "dog": {
        "IGHV": str(REPO / "data/reference/pet_replacement_profiles/v2/dog_ighv_aa_freq_kabat_v2.json"),
        "IGKV": str(REPO / "data/reference/pet_replacement_profiles/v2/dog_igkv_aa_freq_kabat_v2.json"),
        "IGLV": str(REPO / "data/reference/pet_replacement_profiles/v2/dog_iglv_aa_freq_kabat_v2.json"),
    },
    "cat": {
        "IGHV": str(REPO / "data/reference/pet_replacement_profiles/v2/cat_ighv_aa_freq_kabat_v2.json"),
        "IGKV": str(REPO / "data/reference/pet_replacement_profiles/v2/cat_igkv_aa_freq_kabat_v2.json"),
        "IGLV": str(REPO / "data/reference/pet_replacement_profiles/v2/cat_iglv_aa_freq_kabat_v2.json"),
    },
}

# Locus → ANARCI chain type
_LOCUS_CHAIN: Dict[str, str] = {"IGHV": "H", "IGKV": "K", "IGLV": "L"}

# Locus → atlas CSV column
_LOCUS_SEQ_COL: Dict[str, str] = {"IGHV": "vh_seq", "IGKV": "vl_seq", "IGLV": "vl_seq"}

# Locus → atlas CSV germline-db column value to filter on
_LOCUS_DB_FILTER: Dict[str, Optional[str]] = {
    "IGHV": None,       # VH doesn't need db filter
    "IGKV": "IGKV",    # filter vl_germline_db == IGKV
    "IGLV": "IGLV",    # filter vl_germline_db == IGLV
}

# ── Output paths ──────────────────────────────────────────────────────────────
OUT_DIR = REPO / "data/reference/pet_replacement_profiles/v3"

# ── Weights ───────────────────────────────────────────────────────────────────
W_CLINICAL = 3
W_SCAFFOLD = 2
W_GERMLINE = 1  # germline freq is already 0-1; multiplied by this weight

# √n scaling — saturates at N_TARGET sequences (avoids single-sample dominance)
N_TARGET_CLINICAL = 10
N_TARGET_SCAFFOLD = 5

# ── 9-mer window ──────────────────────────────────────────────────────────────
CONTEXT_HALF = 4  # ±4 residues → 9 total


def _l1_effective_weight(n_clinical: int) -> float:
    """L1 √n-scaled weight; saturates at N_TARGET_CLINICAL=10."""
    if n_clinical <= 0:
        return 0.0
    import math
    return W_CLINICAL * min(1.0, math.sqrt(n_clinical) / math.sqrt(N_TARGET_CLINICAL))


def _l2_effective_weight(n_scaffold: int) -> float:
    """L2 √n-scaled weight; saturates at N_TARGET_SCAFFOLD=5."""
    if n_scaffold <= 0:
        return 0.0
    import math
    return W_SCAFFOLD * min(1.0, math.sqrt(n_scaffold) / math.sqrt(N_TARGET_SCAFFOLD))


# ══════════════════════════════════════════════════════════════════════════════
# ANARCI Kabat numbering
# ══════════════════════════════════════════════════════════════════════════════

def _locus_to_chain(locus: str) -> str:
    return _LOCUS_CHAIN.get(locus, "H")


def kabat_number(seq: str, chain: str = "H") -> Optional[List[Tuple[Tuple[int, str], str]]]:
    """
    Run ANARCI Kabat numbering on a single VH sequence.
    Returns list of ((pos, ins), aa) or None on failure.
    """
    try:
        from anarci import anarci  # type: ignore
        results, _, _ = anarci(
            [("q", seq)],
            scheme="kabat",
            output=False,
            allow=(chain,),
        )
        if not results or results[0] is None:
            return None
        numbered = results[0][0][0]  # list of ((pos,ins), aa)
        return [((pos, ins.strip()), aa) for (pos, ins), aa in numbered if aa != "-" and aa.isalpha()]
    except Exception as e:
        print(f"    [WARN] ANARCI failed: {e}", file=sys.stderr)
        return None


def extract_positions(numbered: List[Tuple[Tuple[int, str], str]]) -> Dict[str, str]:
    """Return {kabat_pos_str → aa}. E.g. '52A' or '50'."""
    result: Dict[str, str] = {}
    for (pos, ins), aa in numbered:
        key = f"{pos}{ins}" if ins else str(pos)
        result[key] = aa
    return result


def extract_9mers(numbered: List[Tuple[Tuple[int, str], str]]) -> Dict[str, str]:
    """
    For each position in the numbered sequence, extract the 9-aa window
    centered on that position. Returns {pos_key → 9mer_str}.
    """
    entries = [((pos, ins), aa) for (pos, ins), aa in numbered]
    out: Dict[str, str] = {}
    n = len(entries)
    for i, ((pos, ins), aa) in enumerate(entries):
        start = max(0, i - CONTEXT_HALF)
        end = min(n, i + CONTEXT_HALF + 1)
        window = "".join(a for (_, _), a in entries[start:end])
        # Pad with '-' if near terminus
        n_left = CONTEXT_HALF - (i - start)
        n_right = CONTEXT_HALF - (end - i - 1)
        window = "-" * n_left + window + "-" * n_right
        key = f"{pos}{ins}" if ins else str(pos)
        out[key] = window
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Data loading
# ══════════════════════════════════════════════════════════════════════════════

def load_atlas_sequences(species: str, locus: str) -> List[Dict[str, str]]:
    """
    Parse master_table.csv and return sequences for specified species + locus.
    Chimeric antibodies are included but weighted lower (_clinical_weight).
    """
    seq_col = _LOCUS_SEQ_COL.get(locus, "vh_seq")
    db_filter = _LOCUS_DB_FILTER.get(locus)
    rows = []
    with ATLAS_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pet = row.get("pet_type", "").strip().lower()
            if species == "dog" and pet != "canine":
                continue
            if species == "cat" and pet != "feline":
                continue
            seq = row.get(seq_col, "").strip()
            if not seq or len(seq) < 60:
                continue
            # VL locus filter: check vl_germline_db column
            if db_filter is not None:
                vl_db = row.get("vl_germline_db", "").strip()
                if db_filter not in vl_db:
                    continue
            rows.append({
                "antibody_id": row.get("antibody_id", ""),
                "seq": seq,
                "genetics": row.get("genetics", ""),
                "phase": row.get("phase", ""),
                "notes": row.get("notes", ""),
            })
    return rows


def load_scaffold_sequences(species: str, locus: str) -> List[str]:
    """
    Load Tier-1 scaffold sequences for specified locus from CMC optimization JSON.
    """
    path = DOG_SCAFFOLD_JSON if species == "dog" else CAT_SCAFFOLD_JSON
    if not path.is_file():
        print(f"[WARN] scaffold JSON not found: {path}", file=sys.stderr)
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    seqs = []
    for row in data.get("rows", []):
        if row.get("tier") != "tier1":
            continue
        if row.get("locus", "") != locus:
            continue
        seq = row.get("sequence_aa_kabat_norm") or row.get("sequence_aa_imgt", "")
        if seq and len(seq) > 50:
            seqs.append(seq)
    return seqs


def load_germline_freq(species: str, locus: str) -> Dict[str, Dict[str, float]]:
    """Load existing v2 germline frequency profiles for specified locus."""
    path_str = _GERMLINE_V2.get(species, {}).get(locus, "")
    if not path_str or not Path(path_str).is_file():
        print(f"[WARN] germline v2 not found: {path_str}", file=sys.stderr)
        return {}
    data = json.loads(Path(path_str).read_text(encoding="utf-8"))
    return data.get("positions", {})


# ══════════════════════════════════════════════════════════════════════════════
# Aggregation
# ══════════════════════════════════════════════════════════════════════════════

def _clinical_weight(genetics: str, phase: str, notes: str) -> int:
    """
    Assign per-sequence weight within Level-1 block.
    Approved = 3, Caninised/Felinised = 2, Chimeric = 1.
    InSynBio engineered (no phase) = 1 (internal reference).
    """
    p = phase.lower()
    g = genetics.lower()
    n = notes.lower()
    if "approved" in p:
        return 3
    if "caninised" in g or "felinised" in g or "genetically canine" in g:
        return 2
    if "insynbio" in n or "preclinical" in p:
        return 1
    return 1  # chimeric / unknown


def build_combined_profile(species: str, locus: str) -> Dict[str, Any]:
    """Main aggregation function for one species + locus combination."""
    chain = _locus_to_chain(locus)
    print(f"\n[{species.upper()} / {locus}] Loading data sources ...")

    atlas_rows = load_atlas_sequences(species, locus)
    scaffold_seqs = load_scaffold_sequences(species, locus)
    germline_freq = load_germline_freq(species, locus)

    print(f"  Level-1 clinical sequences: {len(atlas_rows)}")
    print(f"  Level-2 CMC Tier-1 scaffold sequences: {len(scaffold_seqs)}")
    print(f"  Level-3 germline positions available: {len(germline_freq)}")

    level1_counts: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    level2_counts: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    n_clinical_seqs: Dict[str, int] = defaultdict(int)
    n_scaffold_seqs: Dict[str, int] = defaultdict(int)
    all_9mers: Dict[str, List[str]] = defaultdict(list)

    # ── Level 1: clinical sequences ───────────────────────────────────────────
    for row in atlas_rows:
        seq = row["seq"]
        print(f"  Numbering {row['antibody_id']} ({locus}) ...")
        numbered = kabat_number(seq, chain=chain)
        if not numbered:
            print(f"    [SKIP] numbering failed for {row['antibody_id']} {locus}")
            continue

        pos_map = extract_positions(numbered)
        ninemer_map = extract_9mers(numbered)
        cw = _clinical_weight(row["genetics"], row["phase"], row["notes"])

        for pos_key, aa in pos_map.items():
            level1_counts[pos_key][aa] += cw
            n_clinical_seqs[pos_key] += 1
            mer = ninemer_map.get(pos_key)
            if mer and mer not in all_9mers[pos_key]:
                all_9mers[pos_key].append(mer)

    # ── Level 2: CMC scaffold sequences ───────────────────────────────────────
    for i, seq in enumerate(scaffold_seqs):
        print(f"  Numbering {locus} scaffold {i+1}/{len(scaffold_seqs)} ...")
        numbered = kabat_number(seq, chain=chain)
        if not numbered:
            continue
        pos_map = extract_positions(numbered)
        ninemer_map = extract_9mers(numbered)
        for pos_key, aa in pos_map.items():
            level2_counts[pos_key][aa] += 1
            n_scaffold_seqs[pos_key] += 1
            mer = ninemer_map.get(pos_key)
            if mer and mer not in all_9mers[pos_key]:
                all_9mers[pos_key].append(mer)

    # ── Merge all three levels ────────────────────────────────────────────────
    all_positions = set(level1_counts.keys()) | set(level2_counts.keys()) | set(germline_freq.keys())

    positions_out: Dict[str, Any] = {}
    for pos_key in sorted(all_positions, key=lambda k: (int(''.join(c for c in k if c.isdigit()) or '0'),
                                                         ''.join(c for c in k if c.isalpha()))):
        l1 = dict(level1_counts.get(pos_key, {}))
        l2 = dict(level2_counts.get(pos_key, {}))
        l3 = dict(germline_freq.get(pos_key, {}))

        combined: Dict[str, float] = defaultdict(float)
        # L1: √n-scaled effective weight (avoids 1-sequence dominance)
        w1_eff = _l1_effective_weight(n_clinical_seqs.get(pos_key, 0))
        l1_total = sum(l1.values()) or 1.0
        for aa, cnt in l1.items():
            combined[aa] += (cnt / l1_total) * w1_eff
        # L2: √n-scaled (saturates at 5 scaffolds)
        w2_eff = _l2_effective_weight(n_scaffold_seqs.get(pos_key, 0))
        l2_total = sum(l2.values()) or 1.0
        for aa, cnt in l2.items():
            combined[aa] += (cnt / l2_total) * w2_eff
        for aa, freq in l3.items():
            combined[aa] += freq * W_GERMLINE

        c_total = sum(combined.values()) or 1.0
        combined_norm = {aa: round(v / c_total, 5) for aa, v in combined.items()}
        combined_sorted = dict(sorted(combined_norm.items(), key=lambda kv: -kv[1]))
        preferred = next(iter(combined_sorted)) if combined_sorted else None

        positions_out[pos_key] = {
            "combined_preferred": preferred,
            "combined_freq": combined_sorted,
            "level1_clinical_counts": l1,
            "level2_scaffold_counts": l2,
            "level3_germline_freq": l3,
            "n_clinical_seqs": n_clinical_seqs.get(pos_key, 0),
            "n_scaffold_seqs": n_scaffold_seqs.get(pos_key, 0),
            "9mer_contexts": all_9mers.get(pos_key, []),
        }

    scaffold_path = str(DOG_SCAFFOLD_JSON if species == "dog" else CAT_SCAFFOLD_JSON)
    germline_path = _GERMLINE_V2.get(species, {}).get(locus, "")
    return {
        "metadata": {
            "profile_id": f"{species}_{locus.lower()}_clinical_combined_v1",
            "species": "Canis lupus familiaris" if species == "dog" else "Felis catus",
            "locus": locus,
            "chain": chain,
            "numbering_scheme": "Kabat",
            "data_type": "clinical_combined_three_tier",
            "level1_source": "pet_antibody_atlas/master_table.csv",
            "level1_n_sequences": len(atlas_rows),
            "level1_weights": {"approved": 3, "caninised_felinised": 2, "chimeric_engineered": 1},
            "level1_n_scaling": {"formula": "min(1, sqrt(n)/sqrt(N_target))", "N_target": N_TARGET_CLINICAL},
            "level2_n_scaling": {"formula": "min(1, sqrt(n)/sqrt(N_target))", "N_target": N_TARGET_SCAFFOLD},
            "level2_source": scaffold_path,
            "level2_tier": "tier1_only",
            "level2_n_sequences": len(scaffold_seqs),
            "level3_source": germline_path,
            "priority_weights": {"L1_clinical": W_CLINICAL, "L2_scaffold": W_SCAFFOLD, "L3_germline": W_GERMLINE},
            "context_window": f"±{CONTEXT_HALF} residues (9-mer)",
            "schema_version": "clinical_combined_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "positions": positions_out,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build pet clinical combined substitution profiles — VH + VL (κ/λ)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--species", choices=["dog", "cat", "both"], default="both",
                    help="Species to build profiles for (default: both)")
    ap.add_argument("--chain", choices=["VH", "VL_kappa", "VL_lambda", "all"], default="all",
                    help="Chain / locus to build (default: all)")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target_species = ["dog", "cat"] if args.species == "both" else [args.species]

    locus_map = {"VH": ["IGHV"], "VL_kappa": ["IGKV"], "VL_lambda": ["IGLV"],
                 "all": ["IGHV", "IGKV", "IGLV"]}
    target_loci = locus_map[args.chain]

    for species in target_species:
        for locus in target_loci:
            profile = build_combined_profile(species, locus)
            locus_slug = locus.lower()  # ighv / igkv / iglv
            out_path = OUT_DIR / f"{species}_{locus_slug}_clinical_combined_v1.json"
            out_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
            n_pos = len(profile["positions"])
            n_with_clinical = sum(
                1 for v in profile["positions"].values() if v["n_clinical_seqs"] > 0
            )
            print(f"\n[{species.upper()} / {locus}] Done.")
            print(f"  Total positions: {n_pos}")
            print(f"  Positions with clinical data: {n_with_clinical}")
            print(f"  Output: {out_path}")


if __name__ == "__main__":
    main()
