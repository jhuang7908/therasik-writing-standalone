import sys
from pathlib import Path
import requests
import io
import pandas as pd
import json

# Add project root to path to allow importing scripts
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

def run_albumin_comparison():
    # P07724: Mouse Serum Albumin
    # P19121: Chicken Serum Albumin
    # P02768: Human Serum Albumin (for reference)
    
    accessions = {
        "Human Albumin": "P02768",
        "Mouse Albumin": "P07724",
        "Chicken Albumin": "P19121"
    }
    
    scorer = ToleranceScorer(Path("data/atlas/insynbio_tolerance_atlas_v1.json"))
    
    print("\n" + "="*60)
    print("  Albumin Immunogenicity Comparison (HTA V1.0)")
    print("="*60)
    
    for label, acc in accessions.items():
        seq = get_sequence(acc)
        if not seq:
            print(f"Error fetching {label} ({acc})")
            continue
            
        res = scorer.score_sequence(seq)
        
        print(f"\n[{label}] ({acc})")
        print(f"  Full Tolerance Score: {res['full_score']:.2%}")
        for subset, score in res["subset_scores"].items():
            print(f"    - {subset:<20}: {score:.2%}")
        print(f"  Risky 9-mers: {len(res['risky_peptides'])} / {res['total_9mers']}")

if __name__ == "__main__":
    run_albumin_comparison()
