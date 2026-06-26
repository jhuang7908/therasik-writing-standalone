import pandas as pd
from pathlib import Path
from anarcii import Anarcii
import sys
import collections

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

def get_kabat_numbering(seq):
    try:
        a = Anarcii()
        # Correct pattern based on kabat_utils.py:
        # to_scheme returns the updated results dictionary
        a.number([("seq", seq)])
        res = a.to_scheme("kabat")
        if "seq" in res and res["seq"]:
            # numbering is [((pos, ins), aa), ...)]
            return { (pos, ins.strip()): aa for (pos, ins), aa in res["seq"]["numbering"] if aa != "-" }
    except Exception as e:
        print(f"Error numbering: {e}")
    return None

def main():
    df = pd.read_csv('data/vhh_master_benchmarks_v3.csv')
    seqs = pd.read_csv('data/vhh_master_seq_list.csv')
    df = df.merge(seqs[['id', 'sequence']], on='id')

    # Filter for Delta > 0 in Autonomous or Engineered categories
    gold_df = df[
        ((df['category'] == 'Autonomous_Human_VH') | (df['category'] == 'Engineered_Human_VH')) &
        (df['abnativ_delta'] > 0)
    ]

    print(f"Learning from {len(gold_df)} Gold Standard sequences (Delta > 0) using KABAT scheme...")

    # Positions of interest (Kabat)
    # Hallmark: 37, 44, 45, 47
    # Stealth: 35, 50, 89, 94
    # Adaptation: 18, 68
    # Vernier: 2, 27, 28, 29, 30, 47, 48, 49, 67, 69, 71, 73, 78, 93, 94
    target_pos = [2, 18, 27, 28, 29, 30, 35, 37, 44, 45, 47, 48, 49, 50, 67, 68, 69, 71, 73, 78, 89, 93, 94]

    all_residues = collections.defaultdict(list)

    for _, row in gold_df.iterrows():
        k_dict = get_kabat_numbering(row['sequence'])
        if k_dict:
            for p in target_pos:
                aa = k_dict.get((p, ""), "?")
                all_residues[p].append(aa)

    # Calculate frequencies
    summary = []
    for p in target_pos:
        counts = collections.Counter(all_residues[p])
        total = sum(counts.values())
        top_aa = counts.most_common(3)
        freq_str = ", ".join([f"{aa}:{c/total:.1%}" for aa, c in top_aa if aa != "?"])
        summary.append({
            "Kabat_Pos": p,
            "Top_Residues": freq_str,
            "Diversity": len([aa for aa in counts if aa != "?"])
        })
    summary_df = pd.DataFrame(summary)
    print("\n### Gold Standard Feature Frequency (n=23) - KABAT SCHEME")
    print(summary_df.to_string(index=False))

if __name__ == "__main__":
    main()
