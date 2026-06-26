import json
import pandas as pd
import os
from pathlib import Path
from collections import Counter, defaultdict

# Setup paths
PROJECT_ROOT = Path(r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite")

# Input Paths
north_json = PROJECT_ROOT / "data" / "thera_sabdab" / "features" / "slice3_vhh_north_canonical.json"
slice3_parquet = PROJECT_ROOT / "data" / "thera_sabdab" / "features" / "germline_match_slice_3_vhh_design.parquet"
vhh_library_path = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_special_fr_templates_v1.jsonl"
germline_jsonl = PROJECT_ROOT / "data" / "germlines" / "vhh_v1" / "vhh_germline_assets_clean.jsonl"

# Hallmark and Vernier positions (Kabat)
HALLMARKS = {37, 44, 45, 47}
VERNIER = {2, 27, 28, 29, 30, 47, 48, 49, 67, 69, 71, 73, 78, 93, 94, 103} # Extended list

def get_human_refs():
    human_refs = {}
    with open(germline_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            l = json.loads(line)
            if 'Homo' in l['sequence_id']:
                name = l['sequence_id'].split('|')[1]
                human_refs[name] = {
                    'seq': l['segments']['FR1'] + l['segments']['FR2'] + l['segments']['FR3'],
                    'kabat': l['kabat_map']
                }
    return human_refs

def get_strategy_map():
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
            if best_match['origin'] == 'Human': strategy = "BM"
            else:
                if row['vh_identity_global'] > 0.85: strategy = "SR"
                else: strategy = "Native"
        
        strategy_map[ab_id] = strategy
    return strategy_map

def analyze_correlation():
    human_refs = get_human_refs()
    strat_map = get_strategy_map()
    with open(north_json, 'r', encoding='utf-8') as f:
        north_list = json.load(f)
    
    df = pd.read_parquet(slice3_parquet)
    
    # Grouped analysis storage
    # Key: (H1-North, H2-North), Strategy
    analysis = defaultdict(lambda: {
        'count': 0,
        'germlines': Counter(),
        'mut_pos_freq': Counter(),
        'hallmark_muts': Counter(),
        'vernier_muts': Counter()
    })

    for item in north_list:
        ab_id = item['antibody_id']
        h1_cls = item['h1_north']
        h2_cls = item['h2_north']
        strat = strat_map.get(ab_id, "Unknown")
        
        group_key = (h1_cls, h2_cls, strat)
        analysis[group_key]['count'] += 1
        
        row = df[df['antibody_id'] == ab_id].iloc[0]
        germline = row['vh_best_germline_global']
        analysis[group_key]['germlines'][germline] += 1
        
        # Mutation analysis
        query_seq = row['vh_fr1_fr3']
        if germline in human_refs:
            ref = human_refs[germline]
            h_seq = ref['seq']
            h_kabat = ref['kabat']
            h_kabat_list = sorted(
                h_kabat.keys(),
                key=lambda x: (
                    int("".join(filter(str.isdigit, x))),
                    "".join(filter(str.isalpha, x)),
                ),
            )
            
            for i, k_pos in enumerate(h_kabat_list):
                if i >= len(query_seq) or i >= len(h_seq): break
                if query_seq[i] != h_seq[i]:
                    pos_int = int(''.join(filter(str.isdigit, k_pos)))
                    mut_str = f"{k_pos}{h_seq[i]}->{query_seq[i]}"
                    analysis[group_key]['mut_pos_freq'][k_pos] += 1
                    if pos_int in HALLMARKS:
                        analysis[group_key]['hallmark_muts'][mut_str] += 1
                    if pos_int in VERNIER:
                        analysis[group_key]['vernier_muts'][mut_str] += 1

    # Print Results
    print("# Correlation Analysis: Canonical Mode vs Design Strategy\n")
    
    for (h1, h2, strat), data in sorted(analysis.items()):
        print(f"## Group: {h1} | {h2} | Strategy: {strat} (N={data['count']})")
        
        # 1. Framework Choice
        top_gl = data['germlines'].most_common(2)
        gl_str = ", ".join([f"{gl} ({c})" for gl, c in top_gl])
        print(f"- **Top Germlines**: {gl_str}")
        
        # 2. Key Mutations
        h_muts = data['hallmark_muts'].most_common(3)
        h_str = ", ".join([f"{m} ({c})" for m, c in h_muts]) if h_muts else "None"
        print(f"- **Key Hallmarks**: {h_str}")
        
        v_muts = data['vernier_muts'].most_common(5)
        v_str = ", ".join([f"{m} ({c})" for m, c in v_muts]) if v_muts else "None"
        print(f"- **Key Verniers**: {v_str}")
        
        # 3. Regularity
        top_others = []
        for p, c in data['mut_pos_freq'].most_common(10):
            p_int = int(''.join(filter(str.isdigit, p)))
            if p_int not in HALLMARKS and p_int not in VERNIER:
                top_others.append(f"{p} ({c})")
        
        o_str = ", ".join(top_others[:5]) if top_others else "None"
        print(f"- **Other Regular Muts**: {o_str}")
        print()

if __name__ == "__main__":
    analyze_correlation()
