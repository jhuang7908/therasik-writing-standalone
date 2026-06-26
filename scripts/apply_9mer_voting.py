#!/usr/bin/env python3
"""
scripts/apply_9mer_voting.py

Demonstrates how to use the 9-mer context database to "vote" for the best 
amino acid replacement at a specific position in a specific antibody.
"""

import json
from pathlib import Path
import sys

SUITE_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = SUITE_ROOT / "config" / "clinical_842_9mer_db.json"

# The standard 20 amino acids
AMINO_ACIDS = list("ACDEFGHIKLMNPQRSTVWY")

def load_db():
    if not DB_PATH.exists():
        print("Please run scripts/build_clinical_9mer_db.py first.")
        sys.exit(1)
    data = json.loads(DB_PATH.read_text(encoding="utf-8"))
    return data["9mers"]

def vote_for_position(full_seq: str, target_pos: int, db: dict):
    """
    Evaluates all 20 amino acids at target_pos based on 9AA context voting.
    """
    scores = {}
    
    # We evaluate each of the 20 AAs
    for aa in AMINO_ACIDS:
        # Create mutated sequence
        mutated_seq = full_seq[:target_pos] + aa + full_seq[target_pos+1:]
        
        # Find all 9-mer windows that overlap with target_pos
        # A 9-mer covers target_pos if its start index is between target_pos-8 and target_pos
        start_idx = max(0, target_pos - 8)
        end_idx = min(len(full_seq) - 9, target_pos)
        
        total_votes = 0
        windows_found = 0
        
        for i in range(start_idx, end_idx + 1):
            nine_mer = mutated_seq[i:i+9]
            # Lookup frequency in 842 clinical database
            freq = db.get(nine_mer, 0)
            total_votes += freq
            windows_found += 1
            
        scores[aa] = total_votes

    # Sort AAs by votes (descending)
    ranked_aas = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked_aas

if __name__ == "__main__":
    db = load_db()
    
    # Example: Atezolizumab (IGHV3-23*04) VH framework
    # EVQLVESGGGLVQPGGSLRLSCAAS GFTFSDSWIH WVRQAPGKGLEWVA WISPYGGSTYYADSVKG RFTISADTSKNTAYLQMNSLRAEDTAVYYCAR
    example_seq = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSDSWIHWVRQAPGKGLEWVAWISPYGGSTYYADSVKGRFTISADTSKNTAYLQMNSLRAEDTAVYYCAR"
    
    # Let's test a framework position. Kabat 11 (Linear index 10). In IGHV3-23 this is usually 'L'.
    target_pos = 10
    original_aa = example_seq[target_pos]
    
    print(f"--- 9AA Context Voting Test ---")
    print(f"Sequence length: {len(example_seq)}")
    print(f"Target position: {target_pos} (Original AA: {original_aa})")
    
    # Print the context
    start_ctx = max(0, target_pos - 4)
    end_ctx = min(len(example_seq), target_pos + 5)
    print(f"Local Context (±4 AA): {example_seq[start_ctx:target_pos]}[{original_aa}]{example_seq[target_pos+1:end_ctx]}")
    print("-" * 30)
    
    ranked = vote_for_position(example_seq, target_pos, db)
    
    print("Voting Results (Top 5):")
    for aa, votes in ranked[:5]:
        marker = " (Original)" if aa == original_aa else ""
        print(f"  {aa} : {votes} votes{marker}")
    
    if ranked[0][1] == 0:
        print("\n[!] Sparse Data Warning: No 9-mers for any AA at this position exist in the 842 clinical database. 842 is too small for strict 9AA context voting everywhere.")
