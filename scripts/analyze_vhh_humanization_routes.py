import json
import os

# Paths
slice_ids_path = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\out\slice_ids\slice_3_vhh_design.txt"
meta_models_path = r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\thera_sabdab\out\antibody_meta_models.json"

def classify_vhh_routes():
    if not os.path.exists(slice_ids_path) or not os.path.exists(meta_models_path):
        print("Required files missing.")
        return

    with open(slice_ids_path, 'r') as f:
        slice_ids = [line.strip() for line in f if line.strip()]

    with open(meta_models_path, 'r') as f:
        meta_list = json.load(f)

    # Classification buckets
    route_a_camelid_humanized = []  # Alpaca/Camelid -> Humanized
    route_b_human_vh_sd = []        # Natural Human / Fully Human Single Domain
    route_c_chimeric = []           # Chimeric (Llama V + Human C)
    unknown = []

    for m in meta_list:
        ab_id = m['antibody_id']
        if ab_id not in slice_ids:
            continue

        genetics = m.get('genetics', {})
        origin_mode = genetics.get('human_origin_mode', '')
        genetics_raw = genetics.get('genetics_raw', '') or ""
        
        # Logic for Route A (Alpaca -> Humanized)
        if origin_mode == 'engineered_humanisation' or 'humanised' in genetics_raw.lower():
            if 'chimeric' in genetics_raw.lower():
                # Some are both, prioritize humanized for this analysis
                route_a_camelid_humanized.append(ab_id)
            else:
                route_a_camelid_humanized.append(ab_id)
        
        # Logic for Route B (Fully Human)
        elif origin_mode == 'natural_human_repertoire' or 'human' in genetics_raw.lower() or 'genetically human' in genetics_raw.lower():
            route_b_human_vh_sd.append(ab_id)
        
        # Logic for Route C (Chimeric)
        elif 'chimeric' in genetics_raw.lower():
            route_c_chimeric.append(ab_id)
        
        else:
            unknown.append(ab_id)

    # Summary
    total = len(slice_ids)
    print("=" * 50)
    print("VHH / Single Domain Humanization Route Analysis")
    print("=" * 50)
    print(f"Total VHH in Slice 3: {total}")
    print(f"\n1. Route A: Camelid-Derived Humanized ()")
    print(f"   Count: {len(route_a_camelid_humanized)}")
    print(f"   Example IDs: {', '.join(route_a_camelid_humanized[:5])}...")
    
    print(f"\n2. Route B: Human VH-Derived / Fully Human ( VH )")
    print(f"   Count: {len(route_b_human_vh_sd)}")
    print(f"   IDs: {', '.join(route_b_human_vh_sd)}")
    
    print(f"\n3. Route C: Chimeric / Mixed ()")
    print(f"   Count: {len(route_c_chimeric)}")
    print(f"   IDs: {', '.join(route_c_chimeric)}")
    
    print(f"\n4. Unknown / Other")
    print(f"   Count: {len(unknown)}")
    print(f"   IDs: {', '.join(unknown)}")
    print("=" * 50)

if __name__ == "__main__":
    classify_vhh_routes()
