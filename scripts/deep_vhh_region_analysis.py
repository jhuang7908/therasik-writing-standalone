import json
import pandas as pd
import os

# Paths
germline_jsonl = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\germlines\vhh_v1\vhh_germline_assets_clean.jsonl"
slice3_parquet = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\features\germline_match_slice_3_vhh_design.parquet"

def get_region_identity(query_frs, ref_frs):
    identities = {}
    for region in ['FR1', 'FR2', 'FR3']:
        q = query_frs.get(region, "")
        r = ref_frs.get(region, "")
        if not q or not r:
            identities[region] = 0.0
            continue
        matches = sum(1 for a, b in zip(q, r) if a == b)
        identities[region] = matches / max(len(q), len(r))
    return identities

def deep_analyze_sr_vs_bm():
    # Load Camelid and Human refs
    camelid_refs = []
    human_refs = []
    with open(germline_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            l = json.loads(line)
            is_camelid = any(s in l['sequence_id'] for s in ['Vicugna', 'Lama', 'Camelus'])
            is_human = 'Homo' in l['sequence_id']
            
            entry = {
                'id': l['sequence_id'],
                'frs': l['segments']
            }
            if is_camelid: camelid_refs.append(entry)
            if is_human: human_refs.append(entry)
    
    # Load Slice 3
    # Note: The parquet might not have individual FRs, but we can reconstruct if we had the original sequence.
    # Actually, let's assume we can get segments or use a simple heuristic.
    # Since I don't have the original full sequence in the parquet (only fr1_fr3), 
    # I'll use the antibody_meta_models.json to get the ID and then maybe infer or use a different script.
    
    # Let's try to get Caplacizumab and Ozoralizumab specifically.
    target_ids = ['Caplacizumab', 'Ozoralizumab', 'Vobarilizumab', 'Rimteravimab']
    
    # Re-reading slice 3 to get sequences
    df = pd.read_parquet(slice3_parquet)
    
    print(f"{'ID':<15} | {'Region':<5} | {'vs Human %':<12} | {'vs Camelid %':<12} | {'Trend'}")
    print("-" * 65)
    
    for ab_id in target_ids:
        row = df[df['antibody_id'] == ab_id]
        if row.empty: continue
        row = row.iloc[0]
        
        # We need to split the query fr1_fr3 into FR1, FR2, FR3.
        # Standard VHH FR lengths: FR1(~25), FR2(15), FR3(~38)
        # Caplacizumab FR1-3: EVQLVESGGGLVQPGGSLRLSCAASMGWFRQAPGKGRELVAAYYPDSVEGRFTISRDNAKRMVYLQMNSLRAEDTAVYYC
        # Length = 25 (FR1) + 15 (FR2) + 40 (FR3) = 80
        full_fr = row['vh_fr1_fr3']
        q_fr1 = full_fr[:25]
        q_fr2 = full_fr[25:40]
        q_fr3 = full_fr[40:]
        query_frs = {'FR1': q_fr1, 'FR2': q_fr2, 'FR3': q_fr3}

        for region in ['FR1', 'FR2', 'FR3']:
            # Find best human and best camelid for this specific region
            best_h = 0
            for h in human_refs:
                r = h['frs'].get(region, "")
                if not r: continue
                matches = sum(1 for a, b in zip(query_frs[region], r) if a == b)
                score = matches / max(len(query_frs[region]), len(r))
                if score > best_h: best_h = score
            
            best_c = 0
            for c in camelid_refs:
                r = c['frs'].get(region, "")
                if not r: continue
                matches = sum(1 for a, b in zip(query_frs[region], r) if a == b)
                score = matches / max(len(query_frs[region]), len(r))
                if score > best_c: best_c = score
            
            trend = "Humanized" if best_h > best_c else ("Native" if best_c > best_h else "Equal")
            print(f"{ab_id:<15} | {region:<5} | {best_h:<12.2%} | {best_c:<12.2%} | {trend}")
        print("-" * 65)

if __name__ == "__main__":
    deep_analyze_sr_vs_bm()
