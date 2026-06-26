import json
import pandas as pd
import os

# Paths
vhh_library_path = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\germlines\vhh_v1\vhh_special_fr_templates_v1.jsonl"
slice3_parquet = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\features\germline_match_slice_3_vhh_design.parquet"
meta_path = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\out\antibody_meta_models.json"

def analyze_vhh_strategies_v2():
    # 1. Load VHH-specific libraries (Native & Engineered)
    vhh_templates = []
    with open(vhh_library_path, 'r', encoding='utf-8') as f:
        for line in f:
            l = json.loads(line)
            source_id = l.get('source_sequence_id', '')
            is_human = 'Homo' in source_id or 'human' in source_id.lower()
            vhh_templates.append({
                'id': l['fr_id'],
                'seq': l['fr_sequence'],
                'origin': 'Human' if is_human else 'Camelid',
                'hallmark': l.get('vhh_hallmark', {}).get('label', 'unknown')
            })
    
    # 2. Load Slice 3 data
    df = pd.read_parquet(slice3_parquet)
    
    # 3. Load Metadata for Origin/Genetics info
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta_list = json.load(f)
    meta_map = {m['antibody_id']: m for m in meta_list}

    results = []
    
    print(f"{'Antibody ID':<15} | {'Best VHH Lib Match':<30} | {'Origin':<8} | {'Strategy'}")
    print("-" * 80)

    for _, row in df.iterrows():
        ab_id = row['antibody_id']
        query_seq = row['vh_fr1_fr3']
        if not query_seq: continue
        
        # Match against VHH-specific library
        best_match = None
        max_score = 0
        for temp in vhh_templates:
            ref_seq = temp['seq']
            # Align sequences (assuming they are reasonably aligned as FR1-FR3)
            matches = sum(1 for a, b in zip(query_seq, ref_seq) if a == b)
            score = matches / max(len(query_seq), len(ref_seq))
            if score > max_score:
                max_score = score
                best_match = temp
        
        # Classification Logic
        meta = meta_map.get(ab_id, {})
        genetics = meta.get('genetics', {})
        origin_mode = genetics.get('human_origin_mode', '')
        genetics_raw = genetics.get('genetics_raw', '') or ""
        
        strategy = "Unknown"
        if best_match:
            if best_match['origin'] == 'Human':
                # Rule: Human VH-derived VHH = Back-mutation Strategy
                strategy = "Back-mutation (BM)"
            else:
                # Rule: Camelid-derived + High humanization = Surface Resurfacing (SR)
                # If identity to human global is high (>85%) but best match is camelid
                if row['vh_identity_global'] > 0.85:
                    strategy = "Surface Resurfacing (SR)"
                else:
                    strategy = "Conservative VHH"

        print(f"{ab_id:<15} | {best_match['id'][:30]:<30} | {best_match['origin']:<8} | {strategy}")
        
        results.append({
            'antibody_id': ab_id,
            'best_lib_match': best_match['id'] if best_match else None,
            'lib_origin': best_match['origin'] if best_match else None,
            'strategy': strategy,
            'lib_identity': max_score,
            'global_h_identity': row['vh_identity_global']
        })

    # Summary
    bm_count = sum(1 for r in results if r['strategy'] == "Back-mutation (BM)")
    sr_count = sum(1 for r in results if r['strategy'] == "Surface Resurfacing (SR)")
    cons_count = sum(1 for r in results if r['strategy'] == "Conservative VHH")
    
    print("\n" + "="*30)
    print("VHH Strategy Summary")
    print("="*30)
    print(f"Back-mutation (BM) [Human VH-derived]: {bm_count}")
    print(f"Surface Resurfacing (SR) [Camelid-derived]: {sr_count}")
    print(f"Conservative / Native VHH: {cons_count}")
    print("="*30)

if __name__ == "__main__":
    analyze_vhh_strategies_v2()
