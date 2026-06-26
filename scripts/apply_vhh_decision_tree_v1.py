import pandas as pd
import json
import yaml
import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from core.position_sets.load_imgt_position_sets import (
    get_imgt_anchors,
    get_vhh_hallmarks,
    get_vernier_anchors,
    get_surface_plasticity_v1,
    get_nd_dependent_v2_lite
)

# Paths
MASTER_TABLE = PROJECT_ROOT / "data" / "slice3_vhh_paper_grade_master_table_plus_cdr3_features.csv"
POSITION_SETS_YAML = PROJECT_ROOT / "core" / "data" / "position_sets" / "imgt_position_sets.yaml"
OUTPUT_REPORT = PROJECT_ROOT / "reports" / "slice3_vhh_decision_tree_recommendations_v2_lite.csv"
STRICT_SURFACE_YAML = PROJECT_ROOT / "output" / "surface_plasticity_positions_v1_strict.yaml"
NUMBERING_PARQUET = PROJECT_ROOT / "data" / "thera_sabdab" / "features" / "anarcii_numbering_slice_3_vhh_design.parquet"
FRAMEWORK_LIB_YAML = PROJECT_ROOT / "core" / "data" / "framework_library" / "vh_frameworks.with_cdr12.canonical_input.yaml"

# Try to import numbering tool
try:
    from core.numbering.imgt_anarcii import imgt_number_anarcii
    HAS_ANARCII = True
except (ImportError, Exception):
    HAS_ANARCII = False

def load_framework_library():
    if not FRAMEWORK_LIB_YAML.exists():
        return {}
    with open(FRAMEWORK_LIB_YAML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    lib = {}
    for fw in data.get('frameworks', []):
        germline = fw.get('germline')
        positions = fw.get('numbering_evidence', {}).get('positions', {})
        # Convert keys to int
        pos_map = {int(k): v for k, v in positions.items()}
        lib[germline] = pos_map
    return lib

def load_strict_surface():
    if not STRICT_SURFACE_YAML.exists():
        return get_surface_plasticity_v1()
    with open(STRICT_SURFACE_YAML, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return set(data.get('surface_plasticity_positions_v1_strict', []))

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
    
    # Load assets
    fw_lib = load_framework_library()
    strict_surface = load_strict_surface()
    anchors = get_imgt_anchors()
    hallmarks = get_vhh_hallmarks()
    vernier = get_vernier_anchors()
    
    # Load query sequences
    df_numbering = pd.read_parquet(NUMBERING_PARQUET) if NUMBERING_PARQUET.exists() else pd.DataFrame()
    query_seqs = dict(zip(df_numbering['antibody_id'], df_numbering['vh_sequence'])) if not df_numbering.empty else {}

    # Apply Logic
    recommendations = []
    smoketest_stats = {
        "processed": 0,
        "non_empty_nd": 0,
        "nd_core_mismatches": [],
        "empty_strict_surface": []
    }

    print(f"Processing {len(df)} records...")

    for _, row in df.iterrows():
        ab_id = row['antibody_id']
        h1_cls = str(row.get('h1_north', 'unknown'))
        h2_cls = str(row.get('h2_north', 'unknown'))
        best_germline = row.get('vh_best_germline_global')
        
        # 1. Strategy recommendation
        strat, reason = recommend_strategy(row)
        
        # 2. ND-dependent sets
        nd_h1 = get_nd_dependent_v2_lite("H1", h1_cls)
        nd_h2 = get_nd_dependent_v2_lite("H2", h2_cls)
        
        core_pos = nd_h1['core'] | nd_h2['core']
        cand_pos = nd_h1['candidate'] | nd_h2['candidate']
        
        if core_pos or cand_pos:
            smoketest_stats["non_empty_nd"] += 1

        # 3. Mismatch analysis
        query_res = {}
        if ab_id in query_seqs and HAS_ANARCII:
            try:
                numbered = imgt_number_anarcii(query_seqs[ab_id])
                query_res = {int(item['pos']): item['aa'] for item in numbered}
            except: pass
        
        tpl_res = fw_lib.get(best_germline, {})
        
        mismatch_core = []
        mismatch_cand = []
        
        for pos in core_pos:
            q_aa = query_res.get(pos)
            t_aa = tpl_res.get(pos)
            if q_aa and t_aa and q_aa != t_aa:
                mismatch_core.append(pos)
        
        for pos in cand_pos:
            q_aa = query_res.get(pos)
            t_aa = tpl_res.get(pos)
            if q_aa and t_aa and q_aa != t_aa:
                mismatch_cand.append(pos)
        
        smoketest_stats["nd_core_mismatches"].append(len(mismatch_core))

        # 4. Back-mutation Tier Plan
        tier0 = core_pos | vernier | anchors
        tier1 = cand_pos | hallmarks
        tier2 = strict_surface
        
        if not tier2:
            smoketest_stats["empty_strict_surface"].append(ab_id)

        recommendations.append({
            "antibody_id": ab_id,
            "h1_north": h1_cls,
            "h2_north": h2_cls,
            "current_strategy": row['strategy'],
            "recommended_strategy": strat,
            "recommendation_reason": reason,
            "nd_core_mismatch_count": len(mismatch_core),
            "nd_candidate_mismatch_count": len(mismatch_cand),
            "nd_mismatch_positions_core": ";".join(map(str, sorted(mismatch_core))),
            "nd_mismatch_positions_candidate": ";".join(map(str, sorted(mismatch_cand))),
            "bm_tier0_positions": ";".join(map(str, sorted(tier0))),
            "bm_tier1_positions": ";".join(map(str, sorted(tier1))),
            "bm_tier2_positions": ";".join(map(str, sorted(tier2))),
            "bm_tier3_note": "No additional positions recommended; requires experimental validation."
        })
        smoketest_stats["processed"] += 1

    results_df = pd.DataFrame(recommendations)
    results_df.to_csv(OUTPUT_REPORT, index=False)
    print(f"Recommendations saved to {OUTPUT_REPORT}")

    # 5. Smoke test report
    smoketest_md = PROJECT_ROOT / "output" / "decision_tree_integration_smoketest.md"
    with open(smoketest_md, 'w', encoding='utf-8') as f:
        f.write("# Decision Tree Integration Smoketest Report (v2-lite)\n\n")
        f.write(f"- **Records processed**: {smoketest_stats['processed']}\n")
        f.write(f"- **Records with non-empty ND sets**: {smoketest_stats['non_empty_nd']}\n")
        f.write(f"- **ND Core Mismatch Distribution**: {pd.Series(smoketest_stats['nd_core_mismatches']).value_counts().to_dict()}\n")
        if smoketest_stats['empty_strict_surface']:
            f.write(f"- **Records with empty strict surface set**: {', '.join(smoketest_stats['empty_strict_surface'])}\n")
        else:
            f.write("- **Records with empty strict surface set**: None\n")
        f.write("\nNote: ND Core mismatches are penalized in template ranking (tier0/tier1 logic).")

    print(f"Smoketest report saved to {smoketest_md}")

if __name__ == "__main__":
    main()
