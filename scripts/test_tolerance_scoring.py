import json
from pathlib import Path
from typing import Dict, List, Any

class ToleranceScorer:
    def __init__(self, atlas_path: Path):
        print(f"Loading InSynBio Tolerance Atlas from {atlas_path}...")
        with open(atlas_path) as f:
            self.data = json.load(f)
        
        # Build sets for fast lookup
        self.subsets = {}
        for name, content in self.data["subsets"].items():
            self.subsets[name] = set(content["peptides"])
        
        self.full_set = set(self.data["full_set"]["peptides"])
        print(f"Atlas Loaded. Full Set: {len(self.full_set)} unique 9-mers.")

    def score_sequence(self, seq: str) -> Dict[str, Any]:
        seq = seq.upper().strip()
        if len(seq) < 9:
            return {"error": "Sequence too short"}
        
        n_mers = [seq[i:i+9] for i in range(len(seq) - 8)]
        total = len(n_mers)
        
        results = {
            "total_9mers": total,
            "subset_scores": {},
            "full_score": 0.0,
            "risky_peptides": []
        }
        
        # Score each subset
        for name, p_set in self.subsets.items():
            found = sum(1 for p in n_mers if p in p_set)
            results["subset_scores"][name] = round(found / total, 4)
            
        # Score full set
        found_full = sum(1 for p in n_mers if p in self.full_set)
        results["full_score"] = round(found_full / total, 4)
        
        # Identify risky peptides (not in full set)
        results["risky_peptides"] = [p for p in n_mers if p not in self.full_set]
        
        return results

if __name__ == "__main__":
    scorer = ToleranceScorer(Path("data/atlas/insynbio_tolerance_atlas_v1.json"))
    
    # Test with a bacterial enzyme (e.g. Urate Oxidase from Aspergillus flavus - often used as drug)
    # Sequence for Rasburicase
    rasburicase = "MAHYRNDYKKNDEVEFVRTGYGKDMIKVLHIQRDGKYHSIKEVATSVQLTLSSKKDYLHGDNSDVIPTDTIKNTVHVLAKFKGIKSIETFAVTICEHFLSSFKHVIRAQVYVEEVPWKRFEKNGVKHVHAFIYTPTGTHFCEVEQIRNGPPVIHSGIKDLKVLKTTQSGFEGFIKDQFTTLPEVKDRCFATQVYCKWRYHQGRDVDFEATWDTVRSIVLQKFAGPYDKGEYSPSVQKTLYDIQVLTLGQVPEIEDMEISLPNIHYLNIDMSKMGLINKEEVLLPLDNPYGKITGTVKRKLSSRL"
    
    res = scorer.score_sequence(rasburicase)
    
    print("\n--- Tolerance Analysis: Rasburicase (Bacterial Enzyme) ---")
    print(f"Full Tolerance Score: {res['full_score']:.2%} (Fraction of 9-mers found in Atlas)")
    for name, score in res["subset_scores"].items():
        print(f"  - {name:<20}: {score:.2%}")
    
    print(f"\nTotal 9-mers: {res['total_9mers']}")
    print(f"Risky Peptides (Not in any set): {len(res['risky_peptides'])}")
    if res['risky_peptides']:
        print(f"Example Risky Peptide: {res['risky_peptides'][0]}")
