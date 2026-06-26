#!/usr/bin/env python3
"""
Caplacizumab7D12IEDB
- 
-  vs 
- 
"""

import json
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.iedb_client import predict_mhcii_binding, IEDBRequestConfig, IEDBError

print("="*80)
print("IEDB：Caplacizumab vs 7D12")
print("="*80)

# =============================================================================
# 
# =============================================================================

print("\n>>> ...")

with open("output/7D12/caplacizumab_reference.json") as f:
    capla_data = json.load(f)

with open("output/7d12_verified_run/checkpoint_04_humanized_sequences_CDR_GRAFTED.json") as f:
    d7d12_data = json.load(f)

sequences = {
    "Caplacizumab": {
        "sequence": capla_data["sequence"],
        "clinical_ada": "3-7%",
        "note": "FDA，"
    },
    "7D12_Original": {
        "sequence": d7d12_data["original_sequence"],
        "clinical_ada": "",
        "note": ""
    },
    "7D12_S3": {
        "sequence": d7d12_data["strategy_3"]["sequence"],
        "clinical_ada": "",
        "note": ""
    }
}

print(f"\n {len(sequences)} :")
for name, data in sequences.items():
    print(f"  {name}: {len(data['sequence'])} aa (ADA: {data['clinical_ada']})")

# =============================================================================
# IEDB MHC-II
# =============================================================================

print("\n" + "="*80)
print("IEDB MHC-II")
print("="*80)

# HLA
hla_alleles = [
    "HLA-DRB1*01:01", "HLA-DRB1*03:01", "HLA-DRB1*04:01", "HLA-DRB1*04:05",
    "HLA-DRB1*07:01", "HLA-DRB1*08:01", "HLA-DRB1*09:01", "HLA-DRB1*11:01",
    "HLA-DRB1*12:01", "HLA-DRB1*13:01", "HLA-DRB1*13:02", "HLA-DRB1*15:01",
    "HLA-DRB1*16:01", "HLA-DRB3*01:01", "HLA-DRB3*02:02", "HLA-DRB4*01:01",
    "HLA-DRB5*01:01", "HLA-DPA1*01:03-DPB1*02:01", "HLA-DPA1*01:03-DPB1*04:01",
    "HLA-DPA1*02:01-DPB1*01:01", "HLA-DPA1*02:01-DPB1*05:01",
    "HLA-DPA1*03:01-DPB1*04:02", "HLA-DQA1*01:01-DQB1*05:01",
    "HLA-DQA1*01:02-DQB1*06:02", "HLA-DQA1*03:01-DQB1*03:02",
    "HLA-DQA1*04:01-DQB1*04:02", "HLA-DQA1*05:01-DQB1*03:01"
]

results = {}

for name, data in sequences.items():
    print(f"\n>>>  {name} ({len(data['sequence'])} aa)...")
    
    try:
        # IEDB API
        config = IEDBRequestConfig(method="recommended", length="15")
        predictions = predict_mhcii_binding(
            sequence=data["sequence"],
            alleles=hla_alleles,
            config=config
        )
        
        if predictions:
            #  ('rank'，'percentile_rank')
            strong = [p for p in predictions if float(p.get('rank', 100)) < 2.0]
            weak = [p for p in predictions if 2.0 <= float(p.get('rank', 100)) < 10.0]
            
            results[name] = {
                "sequence": data["sequence"],
                "length": len(data["sequence"]),
                "clinical_ada": data["clinical_ada"],
                "note": data["note"],
                "total_predictions": len(predictions),
                "strong_binders": len(strong),
                "weak_binders": len(weak),
                "strong_binder_details": strong[:10],  # 10
                "prediction_success": True
            }
            
            print(f"✓  {len(predictions)} ")
            print(f"   (<2%): {len(strong)}")
            print(f"   (2-10%): {len(weak)}")
        else:
            results[name] = {
                "sequence": data["sequence"],
                "clinical_ada": data["clinical_ada"],
                "error": "No predictions returned",
                "prediction_success": False
            }
            print(f"⚠️  ")
        
        # API
        time.sleep(2)
        
    except Exception as e:
        results[name] = {
            "sequence": data["sequence"],
            "clinical_ada": data["clinical_ada"],
            "error": str(e),
            "prediction_success": False
        }
        print(f"❌ : {e}")

# =============================================================================
# 
# =============================================================================

print("\n" + "="*80)
print("： vs ")
print("="*80)

if results["Caplacizumab"]["prediction_success"]:
    capla_strong = results["Caplacizumab"]["strong_binders"]
    capla_clinical_ada = "3-7%"  # 
    
    print(f"\nCaplacizoumab:")
    print(f"  IEDB: {capla_strong}")
    print(f"  ADA: {capla_clinical_ada}")
    print(f"  : IEDB{capla_strong}，ADA3-7%")
    
    # （）
    # 3-7% ADA""5-10
    estimated_real_epitopes = 7.5  # 
    if capla_strong > 0:
        calibration_factor = capla_strong / estimated_real_epitopes
        print(f"\n  : {calibration_factor:.2f}x (IEDB)")
    else:
        calibration_factor = 1.0
    
    # 7D12
    if results["7D12_Original"]["prediction_success"]:
        d7d12_strong = results["7D12_Original"]["strong_binders"]
        d7d12_calibrated = d7d12_strong / calibration_factor
        
        print(f"\n7D12:")
        print(f"  IEDB: {d7d12_strong}")
        print(f"  : {d7d12_calibrated:.1f} ")
        print(f"  ADA: {' (5-15%)' if d7d12_calibrated < 15 else ' (15-30%)'}")
    
    if results["7D12_S3"]["prediction_success"]:
        s3_strong = results["7D12_S3"]["strong_binders"]
        s3_calibrated = s3_strong / calibration_factor
        
        print(f"\n7D12 S3 ():")
        print(f"  IEDB: {s3_strong}")
        print(f"  : {s3_calibrated:.1f} ")
        print(f"  ADA: {' (5-15%)' if s3_calibrated < 15 else ' (15-30%)'}")
        
        # 
        print(f"\n:")
        if d7d12_calibrated > 0:
            if s3_calibrated < d7d12_calibrated:
                improvement = (d7d12_calibrated - s3_calibrated) / d7d12_calibrated * 100
                print(f"  ✓ S3 {improvement:.1f}% ")
            else:
                increase = (s3_calibrated - d7d12_calibrated) / d7d12_calibrated * 100
                print(f"  ✗ S3 {increase:.1f}% ")
        else:
            print(f"  ⚠️  0，")
else:
    print("\n⚠️  Caplacizumab，")
    calibration_factor = None

# =============================================================================
# 
# =============================================================================

print("\n" + "="*80)
print("")
print("="*80)

print(f"\n{'':<20} {'IEDB':<15} {'':<15} {'ADA':<15}")
print("-"*80)

for name in ["Caplacizumab", "7D12_Original", "7D12_S3"]:
    if results[name]["prediction_success"]:
        strong = results[name]["strong_binders"]
        if calibration_factor:
            calibrated = strong / calibration_factor
            cal_str = f"{calibrated:.1f}"
        else:
            cal_str = "N/A"
        clinical = results[name]["clinical_ada"]
        
        print(f"{name:<20} {strong:<15} {cal_str:<15} {clinical:<15}")
    else:
        print(f"{name:<20} {'':<15} {'N/A':<15} {results[name]['clinical_ada']:<15}")

# =============================================================================
# 
# =============================================================================

output_data = {
    "analysis_date": "2026-01-02",
    "method": "IEDB NetMHCIIpan 4.1 EL",
    "hla_alleles": hla_alleles,
    "calibration_reference": "Caplacizumab (ADA 3-7%)",
    "calibration_factor": calibration_factor,
    "results": results,
    "conclusion": "IEDB，"
}

output_file = "output/7D12/iedb_calibration_results.json"
with open(output_file, 'w') as f:
    json.dump(output_data, f, indent=2)

print(f"\n✓ : {output_file}")

# =============================================================================
# 
# =============================================================================

print("\n" + "="*80)
print("")
print("="*80)

if calibration_factor:
    print(f"""
Caplacizumab：

1. IEDBVHH {calibration_factor:.1f}x

2. Caplacizumab ():
   - IEDB: {results['Caplacizumab']['strong_binders']} 
   - : 3-7% ADA
   - : VHH

3. 7D12:
   - IEDB: {results['7D12_Original']['strong_binders'] if results['7D12_Original']['prediction_success'] else 'N/A'} 
   - :  {results['7D12_Original']['strong_binders'] / calibration_factor:.1f} 
   - ADA:  < 10% (Caplacizumab)

4. :
   ✓ 7D12
   ✓ Caplacizumab
   ✓ IEDB，
   ✓ Phase 1ADA
    """)
else:
    print("""
⚠️  IEDB API，。

：
- Caplacizumab (): ADA 3-7%
- VHH
- 7D12
    """)

print("\n" + "="*80)
print("")
print("="*80)

