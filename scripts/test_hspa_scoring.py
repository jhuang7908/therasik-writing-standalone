import json
from pathlib import Path
from typing import Dict, List, Any

class HSPAScorer:
    def __init__(self, atlas_path: Path):
        print(f"Loading InSynBio HSPA from {atlas_path}...")
        with open(atlas_path) as f:
            data = json.load(f)
        self.peptides = set(data["peptides"])
        self.meta = {
            "version": data["version"],
            "protein_count": data["protein_count"],
            "peptide_count": data["peptide_count"]
        }
        print(f"HSPA Loaded: {self.meta['peptide_count']} unique 9-mers.")

    def score_sequence(self, seq: str) -> Dict[str, Any]:
        seq = seq.upper().strip()
        if len(seq) < 9:
            return {"error": "Sequence too short"}
        
        n_mers = [seq[i:i+9] for i in range(len(seq) - 8)]
        total = len(n_mers)
        found = [p for p in n_mers if p in self.peptides]
        
        score = len(found) / total if total > 0 else 0.0
        
        return {
            "hspa_score": round(score, 4),
            "found_count": len(found),
            "total_count": total,
            "risky_peptides": [p for p in n_mers if p not in self.peptides],
            "atlas_info": self.meta
        }

if __name__ == "__main__":
    scorer = HSPAScorer(Path("data/hspa/human_surface_peptide_atlas_v2.json"))
    
    # Test with a VHH sequence (F37Y candidate)
    test_vhh = "QVQLQESGGGSVQAGGSLRLSCAASGRTFSSYAMGWYRQAPGKEREGVAAISSSGGSTYYADSVKGRFTISRDNAKNTVYLQMNSLKPEDTAVYYCAAAGLGSSTWLDYWGQGTQVTVSS"
    res = scorer.score_sequence(test_vhh)
    
    print("\n--- HSPA Analysis: VHH F37Y Candidate ---")
    print(f"HSPA Compatibility Score: {res['hspa_score']:.2%} (Fraction of 9-mers found in human surfaceome)")
    print(f"Total 9-mers: {res['total_count']}")
    print(f"Found in Surfaceome: {res['found_count']}")
    print(f"Risky Peptides (Not in Surfaceome): {len(res['risky_peptides'])}")
    if res['risky_peptides']:
        print(f"Example Risky Peptide: {res['risky_peptides'][0]}")
