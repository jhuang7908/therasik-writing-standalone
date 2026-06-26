import pandas as pd
import json
import yaml
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MASTER_TABLE = PROJECT_ROOT / "data" / "slice3_vhh_paper_grade_master_table_plus_cdr3_features.csv"
POSITION_SETS_YAML = PROJECT_ROOT / "core" / "data" / "position_sets" / "imgt_position_sets.yaml"
OUTPUT_REPORT = PROJECT_ROOT / "reports" / "slice3_vhh_decision_tree_recommendations.csv"

def load_position_sets():
    with open(POSITION_SETS_YAML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data['imgt_position_sets']

def recommend_strategy(row):
    """
    Implements Step 3 of the VHH Decision Tree.
    """
    h2 = str(row.get('h2_north', 'unknown'))
    identity = row.get('vh_identity_global', 0)
    cdr3_len = row.get('cdr3_len_check', 0)
    mut_hallmark = row.get('mut_hallmark', 0)
    mut_vernier = row.get('mut_vernier_anchor', 0)
    gp_frac = row.get('cdr3_gp_frac', 0)
    net_charge = row.get('cdr3_net_charge_est', 0)

    reasons = []
    
    # 1. Prioritize BM
    if h2 == "H2-9-1":
        if identity >= 0.90:
            reasons.append("H2-9-1 + High Identity (>=0.90)")
            return "BM", "; ".join(reasons)
        if cdr3_len <= 13:
            reasons.append("H2-9-1 + Short CDR3 (<=13)")
            return "BM", "; ".join(reasons)
        if mut_hallmark <= 1 and mut_vernier <= 1:
            reasons.append("H2-9-1 + Low Structural Burden")
            return "BM", "; ".join(reasons)
        
        # If none of above but still H2-9-1, still lean BM but maybe weaker
        reasons.append("H2-9-1 default preference")
        return "BM", "; ".join(reasons)

    # 2. Prioritize SR
    if h2 == "H2-10-1" or h2 == "unknown":
        if cdr3_len >= 14:
            reasons.append(f"{h2} + Long CDR3 ({cdr3_len})")
        if gp_frac > 0.2: # Heuristic for flexible
            reasons.append("High Gly/Pro frac in CDR3")
        if identity < 0.90:
            reasons.append(f"Lower Global Identity ({identity:.2f})")
        
        if reasons:
            return "SR", "; ".join(reasons)
        else:
            return "SR", f"{h2} default preference"

    return "Native", "Default fallback"

def main():
    if not MASTER_TABLE.exists():
        print(f"Error: {MASTER_TABLE} not found.")
        return

    df = pd.read_csv(MASTER_TABLE)
    pos_sets = load_position_sets()

    # Apply Recommendation Logic
    recommendations = []
    for _, row in df.iterrows():
        strat, reason = recommend_strategy(row)
        recommendations.append({
            "antibody_id": row['antibody_id'],
            "h2_north": row['h2_north'],
            "cdr3_len": row['cdr3_len_check'],
            "identity": row['vh_identity_global'],
            "current_strategy": row['strategy'],
            "recommended_strategy": strat,
            "recommendation_reason": reason
        })

    results_df = pd.DataFrame(recommendations)
    results_df.to_csv(OUTPUT_REPORT, index=False)
    print(f"Decision tree recommendations saved to {OUTPUT_REPORT}")

    # Summary of changes
    changes = results_df[results_df['current_strategy'] != results_df['recommended_strategy']]
    print(f"\nDiscrepancy with existing strategy: {len(changes)} / {len(results_df)}")
    if not changes.empty:
        print(changes[['antibody_id', 'current_strategy', 'recommended_strategy', 'recommendation_reason']].to_markdown())

if __name__ == "__main__":
    main()
