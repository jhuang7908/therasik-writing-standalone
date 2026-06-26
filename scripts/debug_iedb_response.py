#!/usr/bin/env python3
"""
IEDB
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.iedb_client import predict_mhcii_binding, IEDBRequestConfig

# （）
test_seq = "EVQLVESGGGLVQAGGSLRLSCAASGRTFSSYAMGWFRQAPGKEREFVAAISWSGGSTYYADSVKGRFTISRDNAKNTVYLQMNSLKPEDTAVYYCAAVRLSIDPWGQGTQVTVSS"

# HLA
test_alleles = ["HLA-DRB1*01:01", "HLA-DRB1*03:01", "HLA-DRB1*04:01"]

print("="*80)
print("IEDB")
print("="*80)

print(f"\n: {len(test_seq)} aa")
print(f"HLA: {len(test_alleles)}")

config = IEDBRequestConfig(method="recommended", length="15")

try:
    predictions = predict_mhcii_binding(
        sequence=test_seq,
        alleles=test_alleles,
        config=config
    )
    
    print(f"\n✓  {len(predictions)} ")
    
    if predictions:
        print(f"\n5:")
        for i, pred in enumerate(predictions[:5]):
            print(f"\n {i+1}:")
            for key, value in pred.items():
                print(f"  {key}: {value}")
        
        # 
        print(f"\n:")
        print(list(predictions[0].keys()))
        
        # percentile_rank
        if 'percentile_rank' in predictions[0]:
            print(f"\n✓  'percentile_rank' ")
        else:
            print(f"\n⚠️   'percentile_rank' ")
            print(f"rank:")
            for key in predictions[0].keys():
                if 'rank' in key.lower() or 'percent' in key.lower():
                    print(f"  - {key}")
        
        # 
        for key in predictions[0].keys():
            if 'rank' in key.lower() or 'percent' in key.lower():
                try:
                    values = [float(p.get(key, 100)) for p in predictions]
                    strong = [v for v in values if v < 2.0]
                    weak = [v for v in values if 2.0 <= v < 10.0]
                    print(f"\n '{key}':")
                    print(f"   (<2): {len(strong)}")
                    print(f"   (2-10): {len(weak)}")
                    print(f"  : {min(values):.2f}")
                    print(f"  : {max(values):.2f}")
                except:
                    pass
    
except Exception as e:
    print(f"\n❌ : {e}")
    import traceback
    traceback.print_exc()















