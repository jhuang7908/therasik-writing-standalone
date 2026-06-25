"""
MVP Developer Report Generator (Markdown)

Generates simplified developer report for MVP pipeline results.
"""

from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


def generate_dev_report(
    mapping_result: Dict[str, Any],
    step1a_candidates: List[Dict[str, Any]],
    step1b_candidates: List[Dict[str, Any]],
    gate_decision: Dict[str, Any],
    step2_variants: List[Dict[str, Any]],
    output_path: Path
):
    """
    Generate MVP developer report in Markdown format
    
    Args:
        mapping_result: Original mapping result
        step1a_candidates: Step1-A candidates
        step1b_candidates: Step1-B candidates
        gate_decision: Gate decision results
        step2_variants: Step2 variants
        output_path: Output file path
    """
    lines = []
    
    # Header
    lines.append("# 7D12 VHH MVP Pipeline v0.1 - Developer Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 1. Input & Cleaning Summary
    lines.append("## 1. Input & Cleaning Summary")
    lines.append("")
    variable_domain = mapping_result.get("variable_domain", {})
    
    # Fix A: Variable Domain Length - read from v_length or variable_domain_length, fallback to sequence length
    v_length = variable_domain.get('v_length') or variable_domain.get('variable_domain_length')
    if v_length is None:
        variable_domain_sequence = mapping_result.get("variable_domain_sequence", "")
        if not variable_domain_sequence:
            # Rebuild from dual_map if needed
            dual_map = mapping_result.get("dual_map", [])
            variable_domain_sequence = "".join(entry.get("aa", "") for entry in dual_map if entry.get("aa") and entry.get("aa") != "-")
        v_length = len(variable_domain_sequence) if variable_domain_sequence else 0
    
    lines.append(f"- **Variable Domain Length:** {v_length} aa")
    
    # Add v_start/v_end if available
    v_start = variable_domain.get('v_start')
    v_end = variable_domain.get('v_end')
    if v_start is not None or v_end is not None:
        v_start_str = str(v_start) if v_start is not None else "N/A"
        v_end_str = str(v_end) if v_end is not None else "N/A"
        lines.append(f"- **Variable Domain Range:** {v_start_str} - {v_end_str}")
    
    lines.append(f"- **Sequence Hash:** {mapping_result.get('sequence_hash', 'N/A')[:16]}...")
    lines.append(f"- **Numbering Engine:** {mapping_result.get('numbering_engine', {}).get('name', 'N/A')}")
    lines.append(f"- **Chain Type:** {mapping_result.get('chain_type', 'N/A')}")
    lines.append("")
    
    # 2. Step1-A (EPS) Candidates Summary
    lines.append("## 2. Step1-A (EPS) Candidates Summary")
    lines.append("")
    if step1a_candidates:
        lines.append("| Candidate ID | Template ID | FR Identity | Vernier Identity | Hallmark Status | Mutations |")
        lines.append("|--------------|-------------|-------------|------------------|-----------------|-----------|")
        for cand in step1a_candidates:
            lines.append(
                f"| {cand.get('candidate_id', 'N/A')} | {cand.get('template_id', 'N/A')} | "
                f"{cand.get('fr_identity_total', 0.0):.3f} | {cand.get('vernier_identity', 0.0):.3f} | "
                f"{cand.get('hallmark_status', 'N/A')} | {len(cand.get('mutation_list', []))} |"
            )
    else:
        lines.append("*No EPS candidates generated.*")
    lines.append("")
    
    # 3. Step1-B (Cluster) Candidates Summary
    lines.append("## 3. Step1-B (Cluster) Candidates Summary")
    lines.append("")
    if step1b_candidates:
        lines.append("| Candidate ID | Cluster ID | Cluster Size | FR Distance | Vernier Distance | Hallmark Status | Mutations |")
        lines.append("|--------------|------------|--------------|-------------|------------------|-----------------|-----------|")
        for cand in step1b_candidates:
            lines.append(
                f"| {cand.get('candidate_id', 'N/A')} | {cand.get('cluster_id', 'N/A')} | "
                f"{cand.get('cluster_size', 0)} | {cand.get('fr_distance_total', 0.0):.3f} | "
                f"{cand.get('vernier_distance', 0.0):.3f} | {cand.get('hallmark_status', 'N/A')} | "
                f"{len(cand.get('mutation_list', []))} |"
            )
    else:
        lines.append("*No Cluster candidates generated.*")
    lines.append("")
    
    # 4. Gate Decision
    lines.append("## 4. Gate Decision")
    lines.append("")
    pass_a = gate_decision.get("pass_A")
    pass_b = gate_decision.get("pass_B")
    rejected = gate_decision.get("rejected", [])
    stats = gate_decision.get("stats", {})
    
    lines.append("### Pass A (EPS Route)")
    if pass_a:
        lines.append(f"- **Candidate ID:** {pass_a.get('candidate_id', 'N/A')}")
        lines.append(f"- **Template ID:** {pass_a.get('template_id', 'N/A')}")
        lines.append(f"- **FR Identity:** {pass_a.get('fr_identity_total', 0.0):.3f}")
        lines.append(f"- **Vernier Identity:** {pass_a.get('vernier_identity', 0.0):.3f}")
        lines.append(f"- **Hallmark Status:** {pass_a.get('hallmark_status', 'N/A')}")
        lines.append(f"- **Mutations:** {len(pass_a.get('mutation_list', []))}")
    else:
        lines.append("*No candidate passed Gate A.*")
    lines.append("")
    
    lines.append("### Pass B (Cluster Route)")
    if pass_b:
        lines.append(f"- **Candidate ID:** {pass_b.get('candidate_id', 'N/A')}")
        lines.append(f"- **Cluster ID:** {pass_b.get('cluster_id', 'N/A')}")
        lines.append(f"- **FR Distance:** {pass_b.get('fr_distance_total', 0.0):.3f}")
        lines.append(f"- **Vernier Distance:** {pass_b.get('vernier_distance', 0.0):.3f}")
        lines.append(f"- **Hallmark Status:** {pass_b.get('hallmark_status', 'N/A')}")
        lines.append(f"- **Mutations:** {len(pass_b.get('mutation_list', []))}")
    else:
        lines.append("*No candidate passed Gate B.*")
    lines.append("")
    
    lines.append("### Gate Statistics")
    lines.append("")
    lines.append("**Eligible Candidates (passed hard conditions):**")
    eligible_a = stats.get('passed_a_count', 0)  # This is the count of candidates that passed gate (not rejected)
    eligible_b = stats.get('passed_b_count', 0)
    lines.append(f"- **Eligible A (EPS Route):** {eligible_a}")
    lines.append(f"- **Eligible B (Cluster Route):** {eligible_b}")
    lines.append("")
    lines.append("**Selected Candidates (final selection):**")
    selected_a = 1 if pass_a else 0
    selected_b = 1 if pass_b else 0
    lines.append(f"- **Selected A:** {selected_a} (from {eligible_a} eligible)")
    lines.append(f"- **Selected B:** {selected_b} (from {eligible_b} eligible)")
    lines.append("")
    lines.append(f"- **Rejected:** {stats.get('rejected_count', 0)}")
    lines.append("")
    
    if rejected:
        lines.append("### Rejected Candidates")
        for rej in rejected[:5]:  # Show first 5
            lines.append(f"- **{rej.get('candidate_id', 'N/A')}** ({rej.get('route', 'N/A')}): {', '.join(rej.get('reject_reasons', [])[:2])}")
        if len(rejected) > 5:
            lines.append(f"*... and {len(rejected) - 5} more rejected candidates.*")
    lines.append("")
    
    # 5. Step2 Variants
    lines.append("## 5. Step2 Variants")
    lines.append("")
    if step2_variants:
        # Fix C: Check for route convergence
        a_plus_variant = next((v for v in step2_variants if v.get("route_variant") == "A_PLUS"), None)
        b_plus_conservative = next((v for v in step2_variants if v.get("route_variant") == "BPLUS_CONSERVATIVE"), None)
        
        convergence_note = False
        if a_plus_variant and b_plus_conservative:
            a_plus_seq = a_plus_variant.get("sequence_v_region", "")
            b_plus_seq = b_plus_conservative.get("sequence_v_region", "")
            if a_plus_seq and b_plus_seq and a_plus_seq == b_plus_seq:
                convergence_note = True
        
        if convergence_note:
            lines.append("> **Note:** A_PLUS and BPLUS_CONSERVATIVE sequences are identical. This indicates route convergence under minimal repair strategy (allowed scenario).")
            lines.append("")
        
        for variant in step2_variants:
            variant_type = variant.get("route_variant", "N/A")
            lines.append(f"### {variant_type}")
            lines.append(f"- **Variant ID:** {variant.get('variant_id', 'N/A')}")
            lines.append(f"- **Parent:** {variant.get('parent_candidate_id', 'N/A')}")
            lines.append(f"- **Changed Positions:** {len(variant.get('changed_positions', []))} IMGT positions")
            lines.append(f"- **Mutations:** {len(variant.get('mutation_list', []))}")
            if variant.get('changed_positions'):
                lines.append(f"- **IMGT Positions:** {', '.join(map(str, variant.get('changed_positions', [])[:10]))}")
            lines.append("")
    else:
        lines.append("*No Step2 variants generated.*")
    lines.append("")
    
    # 6. Next Steps (Non-MVP)
    lines.append("## 6. Next Steps (Non-MVP)")
    lines.append("")
    lines.append("The following features are **not included** in MVP v0.1:")
    lines.append("")
    lines.append("- **CMC Analysis:** Deamidation, oxidation, isomerization risk assessment")
    lines.append("- **Immunogenicity Prediction:** MHC-II epitope prediction and T-cell activation risk")
    lines.append("- **Affinity Optimization:** CDR engineering and paratope refinement")
    lines.append("- **Structural Modeling:** 3D structure prediction and validation")
    lines.append("- **Developability Scoring:** Aggregation, solubility, stability predictions")
    lines.append("")
    lines.append("These features can be added in future pipeline versions based on project requirements.")
    lines.append("")
    
    # Footer
    lines.append("---")
    lines.append("")
    lines.append("*Report generated by 7D12 VHH MVP Pipeline v0.1*")
    
    # Write file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

