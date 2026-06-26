import json
import pandas as pd
import os
import csv
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite")

# Input Paths
strategy_script = PROJECT_ROOT / "scripts" / "analyze_vhh_strategies_v2.py"
canonical_json = PROJECT_ROOT / "data" / "thera_sabdab" / "features" / "slice3_vhh_canonical_config.json"
slice3_parquet = PROJECT_ROOT / "data" / "thera_sabdab" / "features" / "germline_match_slice_3_vhh_design.parquet"
vhh_library_path = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_special_fr_templates_v1.jsonl"
meta_path = PROJECT_ROOT / "data" / "thera_sabdab" / "out" / "antibody_meta_models.json"

def get_strategy_data():
    # 1. Load VHH-specific libraries
    vhh_templates = []
    with open(vhh_library_path, 'r', encoding='utf-8') as f:
        for line in f:
            l = json.loads(line)
            source_id = l.get('source_sequence_id', '')
            is_human = 'Homo' in source_id or 'human' in source_id.lower()
            vhh_templates.append({
                'id': l['fr_id'],
                'seq': l['fr_sequence'],
                'origin': 'Human' if is_human else 'Camelid'
            })
    
    # 2. Load Slice 3 data
    df = pd.read_parquet(slice3_parquet)
    
    # 3. Load Metadata
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta_list = json.load(f)
    meta_map = {m['antibody_id']: m for m in meta_list}

    strategy_map = {}
    for _, row in df.iterrows():
        ab_id = row['antibody_id']
        query_seq = row['vh_fr1_fr3']
        if not query_seq: continue
        
        best_match = None
        max_score = 0
        for temp in vhh_templates:
            ref_seq = temp['seq']
            matches = sum(1 for a, b in zip(query_seq, ref_seq) if a == b)
            score = matches / max(len(query_seq), len(ref_seq))
            if score > max_score:
                max_score = score
                best_match = temp
        
        strategy = "Unknown"
        if best_match:
            if best_match['origin'] == 'Human':
                strategy = "BM"
            else:
                if row['vh_identity_global'] > 0.85:
                    strategy = "SR"
                else:
                    strategy = "Native"
        
        strategy_map[ab_id] = {
            "strategy": strategy,
            "best_lib": best_match['id'] if best_match else "N/A",
            "lib_origin": best_match['origin'] if best_match else "N/A",
            "h_identity": row['vh_identity_global']
        }
    return strategy_map

def generate_unified_analysis():
    # Load Strategy Data
    strat_map = get_strategy_data()
    
    # Load Canonical Data
    with open(canonical_json, 'r', encoding='utf-8') as f:
        canon_list = json.load(f)
    
    # Combine
    combined = []
    for item in canon_list:
        ab_id = item['antibody_id']
        s_info = strat_map.get(ab_id, {})
        
        combined.append({
            "ID": ab_id,
            "Strategy": s_info.get("strategy", "N/A"),
            "H-Identity": f"{s_info.get('h_identity', 0):.2%}",
            "CDR1-Conf": item['cdr1_cluster'],
            "CDR1-Score": item['cdr1_score'],
            "CDR2-Conf": item['cdr2_cluster'],
            "CDR2-Score": item['cdr2_score'],
            "CDR3-Len": len(item['cdr3']),
            "Lib-Origin": s_info.get("lib_origin", "N/A")
        })
    
    # Print Markdown Table
    print(f"| {'Antibody ID':<15} | {'Strategy':<8} | {'H-Iden':<8} | {'CDR1-Conf':<12} | {'CDR2-Conf':<12} | {'CDR3-L':<6} |")
    print(f"| {'-'*15} | {'-'*8} | {'-'*8} | {'-'*12} | {'-'*12} | {'-'*6} |")
    
    for c in sorted(combined, key=lambda x: x['Strategy']):
        print(f"| {c['ID']:<15} | {c['Strategy']:<8} | {c['H-Identity']:<8} | {c['CDR1-Conf']:<12} | {c['CDR2-Conf']:<12} | {c['CDR3-Len']:<6} |")

    # Group Analysis
    print("\n### Correlation Analysis")
    df_combined = pd.DataFrame(combined)
    
    # Check CDR1 patterns per Strategy
    print("\n#### CDR1 Configuration vs Strategy")
    print(df_combined.groupby(['Strategy', 'CDR1-Conf']).size().unstack(fill_value=0))
    
    # Check CDR2 patterns per Strategy
    print("\n#### CDR2 Configuration vs Strategy")
    print(df_combined.groupby(['Strategy', 'CDR2-Conf']).size().unstack(fill_value=0))

if __name__ == "__main__":
    generate_unified_analysis()
