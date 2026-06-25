import yaml
import pandas as pd
import json
from pathlib import Path

def get_framework_canonical():
    path = Path(r"output/framework_library/canonical/vh_frameworks.canonical_assigned.yaml")
    if not path.exists():
        return {}
    
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        
    mapping = {}
    for fw in data.get('frameworks', []):
        fw_id = fw['framework_id']
        # Remove suffix if any (e.g. IGHV3-23*01_FR -> IGHV3-23*01)
        germline = fw_id.split('_')[0]
        mapping[germline] = {
            'H1': fw.get('canonical', {}).get('cdr1', {}).get('class', 'unknown'),
            'H2': fw.get('canonical', {}).get('cdr2', {}).get('class', 'unknown')
        }
    return mapping

def analyze_slice3_north():
    fw_canon = get_framework_canonical()
    slice3_path = Path(r"data/thera_sabdab/features/germline_match_slice_3_vhh_design.parquet")
    df = pd.read_parquet(slice3_path)
    
    # Also need CDR sequences to verify lengths
    canon_json_path = Path(r"data/thera_sabdab/features/slice3_vhh_canonical_config.json")
    with open(canon_json_path, 'r', encoding='utf-8') as f:
        canon_data = json.load(f)
    cdr_map = {item['antibody_id']: item for item in canon_data}

    results = []
    print(f"{'Antibody ID':<15} | {'Best Germline':<15} | {'H1 Class':<10} | {'H2 Class':<10}")
    print("-" * 60)
    
    for _, row in df.iterrows():
        ab_id = row['antibody_id']
        germline = row['vh_best_germline_global']
        
        # Get defaults from germline
        h1_cls = "unknown"
        h2_cls = "unknown"
        
        if germline in fw_canon:
            h1_cls = fw_canon[germline]['H1']
            h2_cls = fw_canon[germline]['H2']
        
        # Heuristic for unknown or native
        cdr_info = cdr_map.get(ab_id, {})
        h1_seq = cdr_info.get('cdr1', '')
        h2_seq = cdr_info.get('cdr2', '')
        
        # North 2011 standard length for H1-13-1 is 13 (Kabat) which is 8 (IMGT)
        # North 2011 standard length for H2-10-1 is 10 (Kabat) which is 8 (IMGT)
        
        if h1_cls == "unknown" or h1_cls == "?":
            if len(h1_seq) == 8: h1_cls = "H1-13-1"
            elif len(h1_seq) == 9: h1_cls = "H1-14-1"
            elif len(h1_seq) == 7: h1_cls = "H1-12-1"
            
        if h2_cls == "unknown" or h2_cls == "?":
            if len(h2_seq) == 8: h2_cls = "H2-10-1"
            elif len(h2_seq) == 7: h2_cls = "H2-9-1"
            elif len(h2_seq) == 10: h2_cls = "H2-12-1"

        print(f"{ab_id:<15} | {germline:<15} | {h1_cls:<10} | {h2_cls:<10}")
        
        results.append({
            "antibody_id": ab_id,
            "germline": germline,
            "h1_north": h1_cls,
            "h2_north": h2_cls,
            "h1_len": len(h1_seq),
            "h2_len": len(h2_seq)
        })

    # Save results
    output_path = Path(r"data/thera_sabdab/features/slice3_vhh_north_canonical.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")

if __name__ == "__main__":
    analyze_slice3_north()
