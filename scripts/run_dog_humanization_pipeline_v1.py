#!/usr/bin/env python3
"""
run_dog_humanization_pipeline_v1.py
===================================
Master pipeline for Dog Antibody Humanization (Caninization).

Logic:
  1. Priority 1: CDR Grafting (if Qualified Scaffold exists).
     - Qualified = CDR Length Match AND FR Identity > 65%.
  2. Priority 2: Surface Reshaping (Fallback).
     - Used if no qualified scaffold found.
     - Preserves mouse core, mutates surface to dog.

Usage:
  python run_dog_humanization_pipeline_v1.py --vh <SEQ> --vl <SEQ> --name <PROJECT_NAME>
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Add suite root to path
SUITE_ROOT = Path(__file__).resolve().parents[1]
if str(SUITE_ROOT) not in sys.path:
    sys.path.insert(0, str(SUITE_ROOT))

try:
    from core.humanization.kabat_utils import get_kabat_numbering, sorted_keys, is_in_cdr
except ImportError:
    print("[ERR] Core modules not found. Ensure environment is set up.")
    sys.exit(1)

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

SCAFFOLD_FILE = SUITE_ROOT / "data" / "germlines" / "canis_lupus_familiaris_ig_aa" / "dog_scaffold_cmc_optimization_tier1_tier2_v1.json"
IDENTITY_THRESHOLD = 65.0  # %

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def load_scaffolds() -> List[Dict[str, Any]]:
    if not SCAFFOLD_FILE.exists():
        print(f"[ERR] Scaffold file missing: {SCAFFOLD_FILE}")
        sys.exit(1)
    data = json.loads(SCAFFOLD_FILE.read_text(encoding="utf-8"))
    
    # Extract clean scaffold list
    scaffolds = []
    for row in data.get("rows", []):
        seq = (row.get("optimization") or {}).get("sequence_aa_opt")
        if seq:
            scaffolds.append({
                "gene": row.get("gene"),
                "chain": row.get("chain"),
                "tier": row.get("tier"),
                "sequence": seq,
                "fr_segments": row.get("fr_segments", {})
            })
    return scaffolds

def get_cdr_lengths(seq: str, chain: str) -> Dict[str, int]:
    """Calculate Kabat CDR lengths."""
    kd = get_kabat_numbering(seq)
    if not kd:
        return {}
    
    # Ranges: VH [26-35, 50-65, 95-102], VL [24-34, 50-56, 89-97]
    ranges = {
        "VH": {"1": (26, 35), "2": (50, 65), "3": (95, 102)},
        "VL": {"1": (24, 34), "2": (50, 56), "3": (89, 97)}
    }
    
    lengths = {}
    for cdr_id, (lo, hi) in ranges.get(chain, {}).items():
        count = 0
        for (pos, ins) in kd.keys():
            if lo <= pos <= hi:
                count += 1
        lengths[cdr_id] = count
    return lengths

def calculate_identity(seq1: str, seq2: str) -> float:
    """Simple sequence identity (length normalized to max length)."""
    # Note: For rigorous alignment, Needleman-Wunsch is better, 
    # but for pre-numbered/similar length Ig, simple match is often used as proxy.
    # Here we use a simple alignment-free check assuming roughly same length/numbering.
    # Actually, let's use Kabat-based identity to be accurate.
    
    kd1 = get_kabat_numbering(seq1)
    kd2 = get_kabat_numbering(seq2)
    
    if not kd1 or not kd2:
        return 0.0
        
    common_keys = set(kd1.keys()) & set(kd2.keys())
    matches = sum(1 for k in common_keys if kd1[k] == kd2[k])
    
    # Denominator: positions present in BOTH (intersection) or UNION?
    # Standard identity usually Union or Min length. Let's use Union of FR positions if we want FR identity.
    # But here we want overall. Let's use Union.
    union_len = len(set(kd1.keys()) | set(kd2.keys()))
    if union_len == 0: return 0.0
    
    return (matches / union_len) * 100.0

def perform_grafting(mouse_seq: str, scaffold_seq: str, chain: str) -> str:
    """Graft mouse CDRs onto scaffold."""
    m_kd = get_kabat_numbering(mouse_seq)
    s_kd = get_kabat_numbering(scaffold_seq)
    
    # Output is scaffold...
    grafted_map = s_kd.copy()
    
    # ...overwritten by Mouse CDRs
    # Iterate Mouse Keys
    for k_pos, k_ins in m_kd.keys():
        if is_in_cdr(k_pos, chain):
            grafted_map[(k_pos, k_ins)] = m_kd[(k_pos, k_ins)]
            
    # Note: If mouse CDR has insertion that scaffold lacks, we add it.
    # If scaffold has insertion mouse lacks, we should remove it? 
    # Grafting usually means "Take Mouse CDR loop exactly".
    # So we should CLEAR scaffold CDR positions first.
    
    # 1. Remove all Scaffold CDR residues
    keys_to_remove = [k for k in grafted_map.keys() if is_in_cdr(k[0], chain)]
    for k in keys_to_remove:
        del grafted_map[k]
        
    # 2. Add all Mouse CDR residues
    for k, aa in m_kd.items():
        if is_in_cdr(k[0], chain):
            grafted_map[k] = aa
            
    # Reassemble
    return "".join(grafted_map[k] for k in sorted_keys(grafted_map))

def perform_veneering(mouse_seq: str, scaffold_seq: str, chain: str) -> Tuple[str, List[str]]:
    """Surface reshaping (reuse logic)."""
    # Import locally to avoid circular dep issues if refactoring
    from scripts.run_dog_surface_reshaping_v1 import veneer_sequence
    res_seq, muts, _ = veneer_sequence(mouse_seq, scaffold_seq, chain)
    return res_seq, muts

# --------------------------------------------------------------------------- #
# Pipeline Logic
# --------------------------------------------------------------------------- #

def process_chain(name: str, seq: str, chain: str, scaffolds: List[Dict]) -> Dict:
    print(f"\nProcessing {name} ({chain})...")
    
    # 1. Analyze Input
    m_lens = get_cdr_lengths(seq, chain)
    print(f"  Input CDR Lengths: {m_lens}")
    
    # 2. Scan Scaffolds
    candidates = []
    for sc in scaffolds:
        if sc["chain"] != chain:
            continue
            
        s_lens = get_cdr_lengths(sc["sequence"], chain)
        ident = calculate_identity(seq, sc["sequence"])
        
        # Check CDR Length Match (H1, H2 only for VH; L1, L2, L3 for VL)
        # Usually H3 is excluded from length check as it's replaced entirely.
        length_match = True
        for cdr in ["1", "2"]: # Check 1 and 2
            if m_lens.get(cdr) != s_lens.get(cdr):
                length_match = False
                break
        
        candidates.append({
            "scaffold": sc,
            "identity": ident,
            "length_match": length_match,
            "s_lens": s_lens
        })
        
    # Sort by Identity
    candidates.sort(key=lambda x: x["identity"], reverse=True)
    
    # 3. Select Strategy
    best_graft_cand = next((c for c in candidates if c["length_match"] and c["identity"] >= IDENTITY_THRESHOLD), None)
    
    result = {}
    
    if best_graft_cand:
        # STRATEGY: GRAFTING
        sc = best_graft_cand["scaffold"]
        print(f"  [PASS] Qualified Scaffold Found: {sc['gene']} (Identity: {best_graft_cand['identity']:.1f}%, CDRs Match)")
        print("  -> Executing Priority 1: CDR Grafting")
        
        grafted_seq = perform_grafting(seq, sc["sequence"], chain)
        result = {
            "strategy": "CDR_Grafting",
            "scaffold": sc["gene"],
            "identity": best_graft_cand["identity"],
            "sequence": grafted_seq,
            "note": "Qualified scaffold found."
        }
    else:
        # STRATEGY: VENEERING
        # Pick highest identity scaffold regardless of length match
        best_veneer_cand = candidates[0] if candidates else None
        
        if not best_veneer_cand:
            print("  [FAIL] No scaffolds found for chain?")
            return {}
            
        sc = best_veneer_cand["scaffold"]
        print(f"  [WARN] No Qualified Scaffold (Best Match: {sc['gene']}, Identity: {best_veneer_cand['identity']:.1f}%, Length Match: {best_veneer_cand['length_match']})")
        print("  -> Executing Priority 2: Surface Reshaping (Fallback)")
        
        res_seq, muts = perform_veneering(seq, sc["sequence"], chain)
        result = {
            "strategy": "Surface_Reshaping",
            "scaffold": sc["gene"],
            "identity": best_veneer_cand["identity"],
            "sequence": res_seq,
            "mutations": muts,
            "note": "Fallback triggered: No scaffold met CDR length + Identity > 65% criteria."
        }
        
    return result

def main():
    parser = argparse.ArgumentParser(description="Dog Humanization Pipeline")
    parser.add_argument("--vh", type=str, help="Mouse VH sequence")
    parser.add_argument("--vl", type=str, help="Mouse VL sequence")
    parser.add_argument("--name", type=str, default="MyAntibody", help="Project Name")
    
    args = parser.parse_args()
    
    if not args.vh and not args.vl:
        # Demo Mode
        print("Running Demo Mode (Pembrolizumab)...")
        args.vh = "QVQLVQSGVEVKKPGASVKVSCKASGYTFTNYYMYWVRQAPGQGLEWMGINPSNGGTNFNEKFKNRVTLTTDSSTTTAYMELKSLQFDDTAVYYCARRDYRFDMGFDYWGQGTTVTVSS"
        args.vl = "EIVLTQSPATLSLSPGERATLSCRASKGVSTSGYSYLHWYQQKPGQAPRLLIYLASYLESGVPARFSGSGSGTDFTLTISSLEPEDFAVYYCQHSRDLPLTFGGGTKVEIK"
        args.name = "Pembrolizumab_Demo"

    scaffolds = load_scaffolds()
    
    results = {}
    
    if args.vh:
        results["VH"] = process_chain(args.name, args.vh, "VH", scaffolds)
        
    if args.vl:
        results["VL"] = process_chain(args.name, args.vl, "VL", scaffolds)
        
    # Output Report
    out_file = Path(f"{args.name}_dog_humanization_result.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print("\n" + "="*60)
    print("FINAL REPORT")
    print("="*60)
    for chain, res in results.items():
        print(f"\nChain: {chain}")
        print(f"  Strategy: {res['strategy']}")
        print(f"  Scaffold: {res['scaffold']}")
        print(f"  Sequence: {res['sequence']}")
        if "mutations" in res:
            print(f"  Mutations: {len(res['mutations'])} ({', '.join(res['mutations'][:5])}...)")
            
    print(f"\nFull details saved to: {out_file}")

if __name__ == "__main__":
    main()
