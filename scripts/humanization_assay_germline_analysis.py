import pandas as pd
import json
from pathlib import Path
import sys
from tqdm import tqdm
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Existing numbering tool
from core.numbering.imgt_anarcii import imgt_number_anarcii
from core.vhh_humanization import split_regions

def get_vh_germlines():
    """Load pre-numbered human VH germlines."""
    path = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "vh_numbered" / "human_vh_numbered_and_split.json"
    with open(path, 'r') as f:
        data = json.load(f)
    germs = {}
    for entry in data['results']:
        gid = entry['id'].split('|')[1] if '|' in entry['id'] else entry['id']
        # Concat FR1-3
        regs = entry.get('regions', {})
        fr_concat = regs.get('FR1', '') + regs.get('FR2', '') + regs.get('FR3', '')
        if fr_concat:
            germs[gid] = fr_concat
    return germs

def get_vl_germlines():
    """Segment Human VK/VL germlines."""
    vk_path = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "IGKV_aa.json"
    vl_path = PROJECT_ROOT / "data" / "germlines" / "human_ig_aa" / "IGLV_aa.json"
    
    germs = {}
    for p in [vk_path, vl_path]:
        with open(p, 'r') as f:
            data = json.load(f)
        print(f"Segmenting {len(data['entries'])} {data['sequence_type']} germlines...")
        for entry in tqdm(data['entries']):
            seq = entry['sequence_aa']
            gid = entry['id']
            try:
                # We use accuracy mode here because it's only ~250 sequences
                rows = imgt_number_anarcii(seq)
                regs = split_regions(rows)
                fr_concat = regs.get('FR1', '') + regs.get('FR2', '') + regs.get('FR3', '')
                if fr_concat:
                    germs[gid] = fr_concat
            except:
                continue
    return germs

def compute_identity(q, g):
    if not q or not g: return 0.0
    L = max(len(q), len(g))
    matches = sum(1 for i in range(min(len(q), len(g))) if q[i] == g[i])
    return (matches / L) * 100.0

def main():
    # 1. Prepare Germlines
    gh = get_vh_germlines()
    gl = get_vl_germlines()
    
    # 2. Load Antibodies
    df_path = PROJECT_ROOT / "data" / "humanization_assay" / "thera_human_igG_segmented.xlsx"
    df = pd.read_excel(df_path)
    
    results = []
    print(f"Comparing {len(df)} antibodies...")
    for _, row in tqdm(df.iterrows(), total=len(df)):
        name = row['Name']
        
        # VH Match
        vh_fr = str(row.get('VH_FR1','')) + str(row.get('VH_FR2','')) + str(row.get('VH_FR3',''))
        bvh_id, bvh_score = "None", 0.0
        for gid, gseq in gh.items():
            s = compute_identity(vh_fr, gseq)
            if s > bvh_score:
                bvh_score, bvh_id = s, gid
        
        # VL Match
        vl_fr = str(row.get('VL_FR1','')) + str(row.get('VL_FR2','')) + str(row.get('VL_FR3',''))
        bvl_id, bvl_score = "None", 0.0
        for gid, gseq in gl.items():
            s = compute_identity(vl_fr, gseq)
            if s > bvl_score:
                bvl_score, bvl_id = s, gid
        
        results.append({
            'Name': name,
            'Best_VH_Germline': bvh_id,
            'VH_FR_Identity': round(bvh_score, 2),
            'Best_VL_Germline': bvl_id,
            'VL_FR_Identity': round(bvl_score, 2)
        })
    
    res_df = pd.DataFrame(results)
    final_df = df.merge(res_df, on='Name', how='left')
    
    out_path = PROJECT_ROOT / "data" / "humanization_assay" / "thera_human_igG_germline_analysis.xlsx"
    final_df.to_excel(out_path, index=False)
    print(f"Saved to {out_path}")

if __name__ == "__main__":
    main()
