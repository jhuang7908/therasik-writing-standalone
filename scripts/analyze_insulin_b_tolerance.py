import sys
from pathlib import Path
import json

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.test_tolerance_scoring import ToleranceScorer

def analyze_insulin_b_chain():
    # Human Insulin B Chain (residues 25-54 of P01308)
    b_chain = "FVNQHLCGSHLVEALYLVCGERGFFYTPKT"
    # Famous T1D autoepitope B:9-23
    b_9_23 = "SHLVEALYLVCGERG"
    
    scorer = ToleranceScorer(Path("data/atlas/insynbio_tolerance_atlas_v1.json"))
    
    print("\n" + "="*60)
    print("  Insulin B Chain Tolerance Analysis (HTA V1.0)")
    print("="*60)
    
    # Analyze Full B Chain
    res_b = scorer.score_sequence(b_chain)
    print(f"\n[Full Insulin B Chain] ({len(b_chain)} aa)")
    print(f"  Full Tolerance Score: {res_b['full_score']:.2%}")
    for subset, score in res_b['subset_scores'].items():
        print(f"    - {subset:<20}: {score:.2%}")
    
    # Analyze B:9-23 Fragment
    res_923 = scorer.score_sequence(b_9_23)
    print(f"\n[Insulin B:9-23 Autoepitope] ({len(b_9_23)} aa)")
    print(f"  Full Tolerance Score: {res_923['full_score']:.2%}")
    for subset, score in res_923['subset_scores'].items():
        print(f"    - {subset:<20}: {score:.2%}")
    
    if res_923['risky_peptides']:
        print(f"\n  Risky 9-mers in B:9-23 (Not found in HTA):")
        for p in res_923['risky_peptides']:
            print(f"    - {p}")

if __name__ == "__main__":
    analyze_insulin_b_chain()
