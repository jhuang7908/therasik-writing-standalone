import json
import pandas as pd
import os

# Paths
germline_jsonl = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\germlines\vhh_v1\vhh_germline_assets_clean.jsonl"
slice3_parquet = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\features\germline_match_slice_3_vhh_design.parquet"

# Known VHH Hallmark and Vernier positions (Kabat numbering)
HALLMARKS = [37, 44, 45, 47]
VERNIER_ANCHORS = [28, 29, 94]
VERNIER_TUNING = [49, 71, 73, 78]

def analyze_mutations():
    human_refs = {}
    with open(germline_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            l = json.loads(line)
            if 'Homo' in l['sequence_id']:
                # Simplify: Store by the germline name part
                name = l['sequence_id'].split('|')[1]
                human_refs[name] = {
                    'seq': l['segments']['FR1'] + l['segments']['FR2'] + l['segments']['FR3'],
                    'kabat': l['kabat_map']
                }

    df = pd.read_parquet(slice3_parquet)
    target_ids = ['Caplacizumab', 'Ozoralizumab', 'Letolizumab', 'Porustobart', 'Rimteravimab']
    
    results = []
    for ab_id in target_ids:
        row = df[df['antibody_id'] == ab_id]
        if row.empty: continue
        row = row.iloc[0]
        
        query_seq = row['vh_fr1_fr3']
        best_h_id = row['vh_best_germline_global']
        
        if best_h_id not in human_refs: continue
        h_ref = human_refs[best_h_id]
        h_seq = h_ref['seq']
        h_kabat = h_ref['kabat']
        
        h_kabat_list = sorted(h_kabat.keys(), key=lambda x: (int(''.join(filter(str.isdigit, x))), ''.join(filter(str.isalpha, x))))
        
        mutations = []
        for i, k_pos in enumerate(h_kabat_list):
            if i >= len(query_seq) or i >= len(h_seq): break
            q_aa = query_seq[i]
            h_aa = h_seq[i]
            
            if q_aa != h_aa:
                pos_int = int(''.join(filter(str.isdigit, k_pos)))
                m_type = "Other"
                if pos_int in HALLMARKS: m_type = "Hallmark"
                elif pos_int in VERNIER_ANCHORS: m_type = "Vernier Anchor"
                elif pos_int in VERNIER_TUNING: m_type = "Vernier Tuning"
                
                mutations.append({
                    'pos': k_pos,
                    'h': h_aa,
                    'q': q_aa,
                    'type': m_type
                })
        
        results.append({
            'id': ab_id,
            'germline': best_h_id,
            'mut_count': len(mutations),
            'muts': mutations,
            'h_identity': row['vh_identity_global']
        })

    for res in results:
        print(f"Antibody: {res['id']} (Template: {res['germline']}, Identity: {res['h_identity']:.2%})")
        print(f"Total Back-Mutations: {res['mut_count']}")
        hallmarks = [m for m in res['muts'] if m['type'] == "Hallmark"]
        verniers = [m for m in res['muts'] if "Vernier" in m['type']]
        others = [m for m in res['muts'] if m['type'] == "Other"]
        
        h_str = ", ".join([f"{m['pos']}{m['h']}->{m['q']}" for m in hallmarks])
        v_str = ", ".join([f"{m['pos']}{m['h']}->{m['q']}" for m in verniers])
        
        print(f"  - Hallmarks: {h_str}")
        print(f"  - Verniers:  {v_str}")
        print(f"  - Others:    {len(others)} positions")
        print("-" * 40)

if __name__ == "__main__":
    analyze_mutations()
