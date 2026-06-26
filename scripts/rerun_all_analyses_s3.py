#!/usr/bin/env python3
"""
Rerun CMC, Immunogenicity, Developability for corrected S3
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cmc.generic_cmc_scanner import scan_cmc_liabilities
# Note: Only running CMC for now, as other modules have issues

def run_cmc_analysis(sequences):
    """Run CMC analysis for all sequences"""
    print("\n" + "="*80)
    print("CMC LIABILITIES ANALYSIS")
    print("="*80)
    
    results = {}
    for name, seq in sequences.items():
        print(f"\n{name}:")
        cmc_result = scan_cmc_liabilities(seq, antibody_type='VHH', return_dict=True)
        results[name] = cmc_result
        
        # Print summary
        total = sum(len(v) if isinstance(v, list) else 0 for k, v in cmc_result.items() if k != 'summary')
        print(f"  Total CMC sites: {total}")
        if 'summary' in cmc_result:
            print(f"  Summary: {cmc_result['summary']}")
    
    return results

def run_immunogenicity_analysis(sequences):
    """Run immunogenicity analysis"""
    print("\n" + "="*80)
    print("IMMUNOGENICITY ANALYSIS")
    print("="*80)
    
    results = {}
    for name, seq in sequences.items():
        print(f"\n{name}:")
        try:
            immuno_result = assess_immunogenicity_v3(seq, antibody_type='VHH')
            results[name] = immuno_result
            
            # Print summary
            if isinstance(immuno_result, dict):
                if 'total_hotspots' in immuno_result:
                    print(f"  Total hotspots: {immuno_result['total_hotspots']}")
                if 'risk_level' in immuno_result:
                    print(f"  Risk level: {immuno_result['risk_level']}")
            else:
                print(f"  Result: {immuno_result}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results[name] = {'error': str(e)}
    
    return results

def run_developability_analysis(sequences):
    """Run developability analysis"""
    print("\n" + "="*80)
    print("DEVELOPABILITY ANALYSIS")
    print("="*80)
    
    results = {}
    for name, seq in sequences.items():
        print(f"\n{name}:")
        try:
            dev_result = assess_developability(seq)
            results[name] = dev_result
            
            # Print summary
            if isinstance(dev_result, dict):
                if 'overall_score' in dev_result:
                    print(f"  Overall score: {dev_result['overall_score']:.2f}")
                if 'aggregation_risk' in dev_result:
                    print(f"  Aggregation risk: {dev_result.get('aggregation_risk', 'N/A')}")
            else:
                print(f"  Score: {dev_result}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results[name] = {'error': str(e)}
    
    return results

def main():
    # Load sequences
    json_path = Path("output/7d12_verified_run/checkpoint_04_humanized_sequences_FINAL.json")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    sequences = {
        'Original': data['original_sequence'],
        'S1': data['strategy_1']['sequence'],
        'S2': data['strategy_2']['sequence'],
        'S3': data['strategy_3']['sequence'],
    }
    
    print("="*80)
    print("RERUNNING ALL ANALYSES WITH CORRECTED S3")
    print("="*80)
    print(f"\nSequences:")
    for name, seq in sequences.items():
        print(f"  {name}: {len(seq)} aa")
    
    # Run analyses
    cmc_results = run_cmc_analysis(sequences)
    immuno_results = {}  # Skipped for now
    dev_results = {}  # Skipped for now
    # immuno_results = run_immunogenicity_analysis(sequences)
    # dev_results = run_developability_analysis(sequences)
    
    # Save results
    output_data = {
        'timestamp': '2026-01-03',
        'sequences': sequences,
        'cmc': cmc_results,
        'immunogenicity': immuno_results,
        'developability': dev_results
    }
    
    output_path = Path("output/7D12/s3_corrected_full_analysis.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to: {output_path}")
    
    # Print comparison
    print("\n" + "="*80)
    print("QUICK COMPARISON")
    print("="*80)
    print(f"\n{'Variant':<10} {'Mutations':<12} {'Humanization':<15} {'CMC Sites':<12} {'Immuno Risk':<15}")
    print("-" * 75)
    
    for name in ['Original', 'S1', 'S2', 'S3']:
        if name == 'Original':
            mutations = 'N/A'
            humanization = '0%'
        else:
            strategy_key = f"strategy_{name[1]}"
            mutations = data[strategy_key]['back_mutation_count']
            humanization = f"{data[strategy_key]['humanization_percent']:.1f}%"
        
        cmc_count = sum(len(v) if isinstance(v, list) else 0 
                       for k, v in cmc_results[name].items() if k != 'summary')
        
        immuno_risk = 'Pending'  # Will analyze separately
        
        print(f"{name:<10} {str(mutations):<12} {humanization:<15} {cmc_count:<12} {str(immuno_risk):<15}")

if __name__ == "__main__":
    main()

