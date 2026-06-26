import json
import pandas as pd
import os
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite")

# Input Paths
north_json = PROJECT_ROOT / "data" / "thera_sabdab" / "features" / "slice3_vhh_north_canonical.json"
slice3_parquet = PROJECT_ROOT / "data" / "thera_sabdab" / "features" / "germline_match_slice_3_vhh_design.parquet"
vhh_library_path = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_special_fr_templates_v1.jsonl"
meta_path = PROJECT_ROOT / "data" / "thera_sabdab" / "out" / "antibody_meta_models.json"

def get_strategy_data():
    # Reuse strategy logic
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
    
    df = pd.read_parquet(slice3_parquet)
    
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
            "h_identity": row['vh_identity_global']
        }
    return strategy_map

def generate_north_analysis():
    # Load Strategy Data
    strat_map = get_strategy_data()
    
    # Load North Data
    with open(north_json, 'r', encoding='utf-8') as f:
        north_list = json.load(f)
    
    # Combine
    combined = []
    for item in north_list:
        ab_id = item['antibody_id']
        s_info = strat_map.get(ab_id, {})
        
        combined.append({
            "ID": ab_id,
            "Strategy": s_info.get("strategy", "N/A"),
            "H-Identity": f"{s_info.get('h_identity', 0):.2%}",
            "H1-North": item['h1_north'],
            "H2-North": item['h2_north'],
            "H1-Len": item['h1_len'],
            "H2-Len": item['h2_len']
        })
    
    # Print Markdown Table
    print("\n## Slice 3 VHH North–Dunbrack Canonical Mode Analysis\n")
    print(f"| {'Antibody ID':<15} | {'Strategy':<8} | {'H-Iden':<8} | {'H1-North':<10} | {'H2-North':<10} | {'H1-L':<4} | {'H2-L':<4} |")
    print(f"| {'-'*15} | {'-'*8} | {'-'*8} | {'-'*10} | {'-'*10} | {'-'*4} | {'-'*4} |")
    
    for c in sorted(combined, key=lambda x: x['Strategy']):
        print(f"| {c['ID']:<15} | {c['Strategy']:<8} | {c['H-Identity']:<8} | {c['H1-North']:<10} | {c['H2-North']:<10} | {c['H1-Len']:<4} | {c['H2-Len']:<4} |")

    # Correlation Analysis
    df_combined = pd.DataFrame(combined)
    
    print("\n### Correlation: Strategy vs Canonical Mode\n")
    
    print("#### H1 Canonical Mode Distribution")
    print(df_combined.groupby(['Strategy', 'H1-North']).size().unstack(fill_value=0))
    
    print("\n#### H2 Canonical Mode Distribution")
    print(df_combined.groupby(['Strategy', 'H2-North']).size().unstack(fill_value=0))

if __name__ == "__main__":
    generate_north_analysis()
