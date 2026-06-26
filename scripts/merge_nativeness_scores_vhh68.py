"""
scripts/merge_nativeness_scores_vhh68.py
Merges AbNatiV VHH2 and nanoBERT PLL scores into the main CMC results file.
"""
import json
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parents[1]
VHH_DIR = SUITE_ROOT / "data" / "vhh_structural_union"

CMC_FILE    = VHH_DIR / "vhh68_special_cmc_results.json"
ABNATIV_FILE = VHH_DIR / "abnativ_scores_vhh68.json"
NANOBERT_FILE = VHH_DIR / "nanobert_scores_vhh68.json"

def main():
    cmc = json.loads(CMC_FILE.read_text(encoding="utf-8"))
    abnativ = json.loads(ABNATIV_FILE.read_text(encoding="utf-8"))
    nanobert = json.loads(NANOBERT_FILE.read_text(encoding="utf-8"))

    missing_ab = 0
    missing_nb = 0
    for entry in cmc:
        eid = entry["id"]
        ab_score = abnativ.get(eid)
        nb_score = nanobert.get(eid)

        if ab_score is not None:
            entry["vhh_specific"]["abnativ_vhh_score"] = ab_score
        else:
            missing_ab += 1

        if nb_score is not None:
            entry["vhh_specific"]["nanobert_pll"] = nb_score
        else:
            entry["vhh_specific"]["nanobert_pll"] = None
            missing_nb += 1

    CMC_FILE.write_text(json.dumps(cmc, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Merged {len(cmc)} entries.")
    print(f"  AbNatiV missing: {missing_ab}")
    print(f"  nanoBERT missing: {missing_nb}")
    print(f"Saved to {CMC_FILE}")

    # Print summary table
    print("\n=== AbNatiV VHH2 Score Summary ===")
    scores = [(e["id"], e["vhh_specific"]["abnativ_vhh_score"]) for e in cmc
              if isinstance(e["vhh_specific"].get("abnativ_vhh_score"), float)]
    scores.sort(key=lambda x: x[1], reverse=True)
    print(f"N={len(scores)}, range=[{scores[-1][1]:.3f}, {scores[0][1]:.3f}]")
    print("\nTop 5:")
    for name, s in scores[:5]:
        print(f"  {name:<45} {s:.4f}")
    print("\nBottom 5:")
    for name, s in scores[-5:]:
        print(f"  {name:<45} {s:.4f}")

    print("\n=== nanoBERT PLL Score Summary ===")
    nb_scores = [(e["id"], e["vhh_specific"]["nanobert_pll"]) for e in cmc
                 if isinstance(e["vhh_specific"].get("nanobert_pll"), float)]
    nb_scores.sort(key=lambda x: x[1], reverse=True)
    print(f"N={len(nb_scores)}, range=[{nb_scores[-1][1]:.3f}, {nb_scores[0][1]:.3f}]")
    print("\nTop 5 (highest PLL = most nativeness-consistent):")
    for name, s in nb_scores[:5]:
        print(f"  {name:<45} {s:.4f}")

if __name__ == "__main__":
    main()
