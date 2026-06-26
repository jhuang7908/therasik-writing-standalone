#!/usr/bin/env python3
"""
run_dog_surface_reshaping_v1.py
===============================
Performs "Surface Reshaping" (Veneering) on an input antibody sequence
using the Tier 1 & Tier 2 Dog Scaffolds (CMC-optimized).

Method:
  1. Number input sequence (Kabat).
  2. Align with target Dog Scaffold (Kabat).
  3. Identify "Surface Positions" (based on Pedersen/Roguska/Studnicka definitions).
  4. For each surface position NOT in a CDR:
     - If Input AA != Dog AA: Mutate Input -> Dog.
  5. Output the reshaped sequence.

Usage:
  python run_dog_surface_reshaping_v1.py --seq <SEQ> --chain <VH/VL> --target <SCAFFOLD_ID>

  # List available scaffolds:
  python run_dog_surface_reshaping_v1.py --list
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add suite root to path
SUITE_ROOT = Path(__file__).resolve().parents[1]
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

try:
    from core.humanization.kabat_utils import get_kabat_numbering, is_in_cdr, sorted_keys
except ImportError:
    # Fallback for standalone usage if core is not perfectly set up
    print("[WARN] Could not import core.humanization.kabat_utils. Using local fallback.")
    # (Simplified fallback would go here, but we assume environment is correct)
    sys.exit(1)


# --------------------------------------------------------------------------- #
# Surface Definitions (Kabat Numbering)
# --------------------------------------------------------------------------- #
# Based on solvent accessibility > 30% in typical Fv structures.
# Excludes CDRs (though some definitions include CDRs, we strictly exclude them for reshaping).

VH_SURFACE_KABAT = {
    1, 3, 5, 10, 11, 12, 13, 15, 19, 23, 26, 27, 28,  # FR1
    40, 41, 42, 43, 44, 45, 52, 53, 54, 55,           # FR2 (52 is often surface if not CDR)
    60, 61, 62, 64, 65, 68, 70, 72, 73, 74, 75, 76,   # FR3
    82, 83, 84, 85, 87, 88, 89,                       # FR3 (82/82A/82B/82C handled by logic)
    105, 108, 110, 112                                # FR4
}

VL_SURFACE_KABAT = {
    1, 3, 5, 7, 9, 10, 12, 15, 16, 18, 20, 22, 24,    # FR1
    40, 41, 42, 43, 44, 45,                           # FR2
    53, 54, 55, 56, 57,                               # FR2/FR3 boundary
    60, 63, 65, 66, 67, 69, 70, 74, 76, 77, 79, 80,   # FR3
    81, 84, 85,                                       # FR3
    100, 103, 105, 107                                # FR4
}

# --------------------------------------------------------------------------- #
# Data Loading
# --------------------------------------------------------------------------- #

SCAFFOLD_FILE = SUITE_ROOT / "data" / "germlines" / "canis_lupus_familiaris_ig_aa" / "dog_scaffold_cmc_optimization_tier1_tier2_v1.json"

def load_scaffolds() -> Dict[str, Dict]:
    if not SCAFFOLD_FILE.exists():
        print(f"[ERR] Scaffold file not found: {SCAFFOLD_FILE}")
        sys.exit(1)
    
    data = json.loads(SCAFFOLD_FILE.read_text(encoding="utf-8"))
    scaffolds = {}
    for row in data.get("rows", []):
        gene = row.get("gene")
        # Use the OPTIMIZED sequence (CMC fixed)
        seq = (row.get("optimization") or {}).get("sequence_aa_opt")
        if gene and seq:
            scaffolds[gene] = {
                "gene": gene,
                "chain": row.get("chain"),
                "tier": row.get("tier"),
                "sequence": seq
            }
    return scaffolds

# --------------------------------------------------------------------------- #
# Reshaping Logic
# --------------------------------------------------------------------------- #

def veneer_sequence(
    input_seq: str,
    target_seq: str,
    chain: str
) -> Tuple[str, List[str], List[str]]:
    """
    Returns: (reshaped_sequence, mutations_log, notes)
    """
    # 1. Number sequences
    in_num = get_kabat_numbering(input_seq)
    tg_num = get_kabat_numbering(target_seq)
    
    if not in_num:
        return "", [], ["Failed to number input sequence"]
    if not tg_num:
        return "", [], ["Failed to number target sequence"]

    # 2. Define surface set
    surface_set = VH_SURFACE_KABAT if chain == "VH" else VL_SURFACE_KABAT
    
    # 3. Iterate input positions
    # We reconstruct the sequence position by position.
    # If a position is Surface AND Non-CDR AND differs from Target -> Mutate.
    
    reshaped_map = in_num.copy()
    mutations = []
    
    # Iterate through all input keys
    for k_pos, k_ins in sorted_keys(in_num):
        # Is it a surface position? (Check integer part)
        if k_pos not in surface_set:
            continue
            
        # Is it in a CDR?
        if is_in_cdr(k_pos, chain):
            continue
            
        # Does target have this position?
        if (k_pos, k_ins) not in tg_num:
            # Target might have a gap here or different length. 
            # If target lacks it, we usually KEEP input (can't mutate to nothing easily in fixed framework)
            # Or we could delete? For veneering, usually keep unless it's a major structural clash.
            continue
            
        in_aa = in_num[(k_pos, k_ins)]
        tg_aa = tg_num[(k_pos, k_ins)]
        
        if in_aa != tg_aa:
            # MUTATE
            reshaped_map[(k_pos, k_ins)] = tg_aa
            mutations.append(f"{in_aa}{k_pos}{k_ins}{tg_aa} (Surface)")

    # 4. Reassemble sequence
    # We use the sorted keys of the INPUT (preserving length/indels of input)
    # but with updated AAs.
    reshaped_seq = "".join(reshaped_map[k] for k in sorted_keys(reshaped_map))
    
    return reshaped_seq, mutations, []

# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(description="Dog Surface Reshaping Tool")
    parser.add_argument("--list", action="store_true", help="List available dog scaffolds")
    parser.add_argument("--seq", type=str, help="Input amino acid sequence")
    parser.add_argument("--chain", type=str, choices=["VH", "VL"], help="Chain type")
    parser.add_argument("--target", type=str, help="Target Dog Scaffold ID (e.g., IGHV3-35*01)")
    
    args = parser.parse_args()
    
    scaffolds = load_scaffolds()
    
    if args.list:
        print(f"{'ID':<15} | {'Chain':<5} | {'Tier':<8} | {'Sequence (Start)'}")
        print("-" * 60)
        for gid, data in scaffolds.items():
            print(f"{gid:<15} | {data['chain']:<5} | {data['tier']:<8} | {data['sequence'][:20]}...")
        return

    if not args.seq or not args.chain or not args.target:
        # DEMO MODE if no args
        print("No arguments provided. Running DEMO mode...")
        print("-" * 60)
        
        # Demo: Pembrolizumab VH -> Dog IGHV3-35*01 (Tier 1)
        demo_seq = "QVQLVQSGVEVKKPGASVKVSCKASGYTFTNYYMYWVRQAPGQGLEWMGINPSNGGTNFNEKFKNRVTLTTDSSTTTAYMELKSLQFDDTAVYYCARRDYRFDMGFDYWGQGTTVTVSS"
        demo_target = "IGHV3-35*01"
        demo_chain = "VH"
        
        print(f"Input (Pembro VH): {demo_seq[:20]}...")
        print(f"Target (Dog):      {demo_target}")
        
        res_seq, muts, notes = veneer_sequence(demo_seq, scaffolds[demo_target]["sequence"], demo_chain)
        
        print(f"\nReshaped Sequence: {res_seq}")
        print(f"Mutations ({len(muts)}): {', '.join(muts)}")
        if notes:
            print(f"Notes: {notes}")
        return

    # Real Run
    if args.target not in scaffolds:
        print(f"[ERR] Target scaffold '{args.target}' not found. Use --list to see options.")
        sys.exit(1)
        
    target_data = scaffolds[args.target]
    if target_data["chain"] != args.chain:
        print(f"[WARN] Chain mismatch? Input is {args.chain}, target {args.target} is {target_data['chain']}.")
    
    res_seq, muts, notes = veneer_sequence(args.seq, target_data["sequence"], args.chain)
    
    print(json.dumps({
        "input_seq": args.seq,
        "target_scaffold": args.target,
        "reshaped_seq": res_seq,
        "mutation_count": len(muts),
        "mutations": muts,
        "notes": notes
    }, indent=2))

if __name__ == "__main__":
    main()
