import sys
from pathlib import Path
import requests
import io
import pandas as pd
import json

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.test_tolerance_scoring import ToleranceScorer

def get_sequence(accession: str) -> str:
    url = f"https://rest.uniprot.org/uniprotkb/{accession}.tsv"
    params = {"fields": "sequence"}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        df = pd.read_csv(io.StringIO(response.text), sep="\t")
        return str(df.iloc[0]["Sequence"])
    return ""

def analyze_aav9_tolerance():
    # Q6JC40: Capsid protein VP1 [Adeno-associated virus 9]
    aav9_vp1_acc = "Q6JC40"
    
    scorer = ToleranceScorer(Path("data/atlas/insynbio_tolerance_atlas_v1.json"))
    
    print("\n" + "="*60)
    print("  AAV9 Capsid Protein (VP1) Tolerance Analysis (HTA V1.0)")
    print("="*60)
    
    seq = get_sequence(aav9_vp1_acc)
    if not seq:
        print(f"Error fetching AAV9 VP1 ({aav9_vp1_acc})")
        return
        
    res = scorer.score_sequence(seq)
    
    print(f"\n[AAV9 VP1] ({aav9_vp1_acc}, {len(seq)} aa)")
    print(f"  Full Tolerance Score: {res['full_score']:.2%}")
    for subset, score in res["subset_scores"].items():
        print(f"    - {subset:<20}: {score:.2%}")
    
    print(f"\nTotal 9-mers: {res['total_9mers']}")
    print(f"Risky 9-mers (Not in HTA): {len(res['risky_peptides'])}")
    
    if res['risky_peptides']:
        print(f"\nExample Risky Peptides (Potential Immunogenic Hotspots):")
        for p in res['risky_peptides'][:5]:
            print(f"    - {p}")

if __name__ == "__main__":
    analyze_aav9_tolerance()
