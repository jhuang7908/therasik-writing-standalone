import pandas as pd
from pathlib import Path
from anarcii import Anarcii
import sys
import os

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

def get_kabat_residues(seq, positions):
    try:
        a = Anarcii(seq_type="antibody", mode="accuracy")
        res = a.number([seq])
        if isinstance(res, dict) and 'Sequence 1' in res:
            v = res['Sequence 1']
            if isinstance(v, dict) and 'numbering' in v and v['numbering']:
                numbering = v['numbering']
                # numbering is [((pos, ins), aa), ...]
                k_dict = {pos: aa for (pos, ins), aa in numbering if ins == " " or ins == ""}
                return {p: k_dict.get(p, "?") for p in positions}
    except Exception as e:
        print(f"Error numbering: {e}")
    return {p: "?" for p in positions}

def main():
    df = pd.read_csv('data/vhh_master_benchmarks_v3.csv')
    seqs = pd.read_csv('data/vhh_master_seq_list.csv')
    df = df.merge(seqs[['id', 'sequence']], on='id')
    
    top_5 = df[df['category'] == 'Autonomous_Human_VH'].sort_values('abnativ_delta', ascending=False).head(5)
    
    # Stealth positions: 35, 50, 89, 94
    # Adaptation positions: 18, 68
    # Hallmark positions: 37, 44, 45, 47
    target_pos = [18, 35, 37, 44, 45, 47, 50, 68, 89, 94]
    
    results = []
    for _, row in top_5.iterrows():
        res_map = get_kabat_residues(row['sequence'], target_pos)
        res_map['id'] = row['id']
        res_map['abnativ_delta'] = row['abnativ_delta']
        results.append(res_map)
    
    res_df = pd.DataFrame(results)
    # Reorder columns
    cols = ['id', 'abnativ_delta'] + target_pos
    print(res_df[cols].to_string(index=False))

if __name__ == "__main__":
    main()
