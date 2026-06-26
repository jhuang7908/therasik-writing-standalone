import json
import numpy as np
from pathlib import Path
import sys

ROOT = Path("d:/InSynBio-AI-Research/Antibody_Engineer_Suite")
sys.path.insert(0, str(ROOT))

def get_stats(values):
    if not values:
        return {}
    return {
        "n": len(values),
        "mean": round(float(np.mean(values)), 4),
        "p5": round(float(np.percentile(values, 5)), 4),
        "p25": round(float(np.percentile(values, 25)), 4),
        "p50": round(float(np.percentile(values, 50)), 4),
        "p75": round(float(np.percentile(values, 75)), 4),
        "p95": round(float(np.percentile(values, 95)), 4),
    }

def main():
    atlas_path = ROOT / "data" / "vhh_design_atlas_v3.json"
    data = json.loads(atlas_path.read_text(encoding="utf-8"))
    
    # 1. Clinical-26 (Unique Clinical Humanized VHH)
    clin_seqs = []
    hash_to_seq = {}
    for r in data:
        if r.get('category') == 'Clinical_VHH' and r.get('sequence'):
            s = r['sequence']
            if s not in hash_to_seq:
                hash_to_seq[s] = True
                clin_seqs.append(s)
    clin_seqs = clin_seqs[:26]
    
    # 2. Atlas-24 (Engineered Human VH)
    eng_vh_seqs = list({r['sequence'] for r in data if r.get('category') == 'Engineered_Human_VH' and r.get('sequence')})
    eng_vh_seqs = eng_vh_seqs[:24]

    print(f"Loaded {len(clin_seqs)} Clinical VHH sequences.")
    print(f"Loaded {len(eng_vh_seqs)} Engineered VH sequences.")

    try:
        from abnativ.model.scoring_functions import abnativ_scoring
        from Bio.Seq import Seq
        from Bio.SeqRecord import SeqRecord
    except ImportError:
        print("Please run in anarcii env")
        sys.exit(1)

    def score_group(seqs, name):
        deltas = []
        vh_scores = []
        vhh_scores = []
        for i, seq in enumerate(seqs):
            rec = [SeqRecord(Seq(seq), id=f"seq_{i}")]
            df_vh, _ = abnativ_scoring(
                model_type="VH",
                seq_records=rec,
                batch_size=1,
                mean_score_only=True,
                do_align=True,
                is_VHH=False,
                verbose=False,
                run_parall_al=False,
            )
            df_vhh, _ = abnativ_scoring(
                model_type="VHH",
                seq_records=rec,
                batch_size=1,
                mean_score_only=True,
                do_align=True,
                is_VHH=True,
                verbose=False,
                run_parall_al=False,
            )
            vh = float(df_vh.iloc[0]["AbNatiV VH Score"])
            vhh = float(df_vhh.iloc[0]["AbNatiV VHH Score"])
            deltas.append(vhh - vh)
            vh_scores.append(vh)
            vhh_scores.append(vhh)
            print(f"  {name} {i+1}/{len(seqs)}: VH={vh:.3f} VHH={vhh:.3f} Δ={vhh-vh:.3f}")
        
        print(f"\n--- {name} Results ---")
        print("VH:   ", get_stats(vh_scores))
        print("VHH:  ", get_stats(vhh_scores))
        print("Delta:", get_stats(deltas))

    score_group(clin_seqs, "Clinical-26 VHH")
    score_group(eng_vh_seqs, "Atlas-24 Engineered VH")

if __name__ == "__main__":
    main()
