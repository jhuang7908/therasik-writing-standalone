import json
import pandas as pd
import os

# Paths
germline_jsonl = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\germlines\vhh_v1\vhh_germline_assets_clean.jsonl"
slice3_parquet = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\features\germline_match_slice_3_vhh_design.parquet"

def analyze_camelid_vs_human():
    # Load Camelid germlines
    camelid_refs = []
    with open(germline_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            l = json.loads(line)
            if any(s in l['sequence_id'] for s in ['Vicugna', 'Lama', 'Camelus']):
                camelid_refs.append({
                    'id': l['sequence_id'],
                    'seq': l['segments']['FR1'] + l['segments']['FR2'] + l['segments']['FR3']
                })
    
    # Load Slice 3
    df = pd.read_parquet(slice3_parquet)
    
    print(f"{'Antibody ID':<15} {'Best Camelid %':<15} {'Human Global %':<15} {'Gap':<10}")
    print("-" * 55)
    
    for _, row in df.iterrows():
        query = row['vh_fr1_fr3']
        if not query: continue
        
        max_camelid_score = 0
        for ref in camelid_refs:
            cseq = ref['seq']
            # Simple alignment-free comparison if lengths match, else naive
            matches = sum(1 for a, b in zip(query, cseq) if a == b)
            score = matches / max(len(query), len(cseq))
            if score > max_camelid_score:
                max_camelid_score = score
        
        human_score = row['vh_identity_global']
        gap = max_camelid_score - human_score
        
        # Only show those with high camelid score or small gap
        if max_camelid_score > 0.80:
            print(f"{row['antibody_id']:<15} {max_camelid_score:<15.4f} {human_score:<15.4f} {gap:<10.4f}")

if __name__ == "__main__":
    analyze_camelid_vs_human()
