import json
import pandas as pd
import os
from collections import Counter

# Paths
germline_jsonl = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\germlines\vhh_v1\vhh_germline_assets_clean.jsonl"
slice3_parquet = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\features\germline_match_slice_3_vhh_design.parquet"

def analyze_mutation_regularity():
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

    df = pd.read_parquet(slice3_parquet)
    
    # Categories of positions
    HALLMARKS = {37, 44, 45, 47}
    VERNIER_ANCHORS = {28, 29, 94}
    VERNIER_TUNING = {49, 71, 73, 78}
    
    all_mutations = []
    
    for _, row in df.iterrows():
        ab_id = row['antibody_id']
        query_seq = row['vh_fr1_fr3']
        best_h_id = row['vh_best_germline_global']
        
        if best_h_id not in human_refs: continue
        h_ref = human_refs[best_h_id]
        h_seq = h_ref['seq']
        h_kabat = h_ref['kabat']
        
        h_kabat_list = sorted(h_kabat.keys(), key=lambda x: (int(''.join(filter(str.isdigit, x))), ''.join(filter(str.isalpha, x))))
        
        for i, k_pos in enumerate(h_kabat_list):
            if i >= len(query_seq) or i >= len(h_seq): break
            if query_seq[i] != h_seq[i]:
                pos_int = int(''.join(filter(str.isdigit, k_pos)))
                m_cat = "Other"
                if pos_int in HALLMARKS: m_cat = "Hallmark"
                elif pos_int in VERNIER_ANCHORS: m_cat = "Vernier Anchor"
                elif pos_int in VERNIER_TUNING: m_cat = "Vernier Tuning"
                
                all_mutations.append({
                    'id': ab_id,
                    'pos': k_pos,
                    'pos_int': pos_int,
                    'cat': m_cat
                })

    # Frequency analysis
    mut_counts = Counter([m['pos'] for m in all_mutations])
    
    print("Top Mutated Positions in Slice 3 (Ranked by Frequency):")
    print(f"{'Pos':<10} | {'Count':<6} | {'Category':<15} | {'Description'}")
    print("-" * 60)
    
    sorted_muts = sorted(mut_counts.items(), key=lambda x: x[1], reverse=True)
    
    for pos, count in sorted_muts[:20]:
        pos_int = int(''.join(filter(str.isdigit, pos)))
        cat = "Other"
        if pos_int in HALLMARKS: cat = "Hallmark"
        elif pos_int in VERNIER_ANCHORS: cat = "Vernier Anchor"
        elif pos_int in VERNIER_TUNING: cat = "Vernier Tuning"
        
        desc = ""
        if pos_int == 45: desc = "Critical FR2 Interface"
        elif pos_int == 37: desc = "FR2 VHH Signature"
        elif pos_int == 71: desc = "Vernier (CDR2/3 support)"
        elif pos_int == 1: desc = "N-terminal Surface"
        elif pos_int == 108: desc = "J-region / Surface"
        
        print(f"{pos:<10} | {count:<6} | {cat:<15} | {desc}")

if __name__ == "__main__":
    analyze_mutation_regularity()
