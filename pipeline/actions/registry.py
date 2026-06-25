"""
Action Registry v1

This registry maps action names (from rule files) to pure functions.
Actions are execution-only: they do NOT make decisions, only execute what rules decide.

All actions must:
- Take context: dict as input
- Return patch: dict as output (fields to update)
- Be pure functions (no side effects)
- Only read/write fields defined in kb/01_fields/fields_dictionary.yaml

Action naming standard: [a-z0-9_]+ only
"""

import copy
from typing import Dict, Callable, List

# Import all action modules
from pipeline.actions.extract_variable_domain_best_effort import action as extract_variable_domain_best_effort
from pipeline.actions.renumber_primary_imgt import action as renumber_primary_imgt
from pipeline.actions.approximate_region_by_imgt_boundaries import action as approximate_region_by_imgt_boundaries
from pipeline.actions.annotate_epitopes_with_regions_and_interface_adjacency import action as annotate_epitopes_with_regions_and_interface_adjacency
from pipeline.actions.select_minimal_anchor_disrupting_mutations_in_fr import action as select_minimal_anchor_disrupting_mutations_in_fr
from pipeline.actions.rank_cdr_epitopes_by_allele_coverage_and_strength import action as rank_cdr_epitopes_by_allele_coverage_and_strength
from pipeline.actions.propose_minimal_non_anchor_mutations_first import action as propose_minimal_non_anchor_mutations_first
from pipeline.actions.propose_anchor_mutation_with_affinity_risk_flag import action as propose_anchor_mutation_with_affinity_risk_flag
from pipeline.actions.assemble_variants_from_epitope_mutations import action as assemble_variants_from_epitope_mutations
from pipeline.actions.attach_rule_trace_and_param_ids import action as attach_rule_trace_and_param_ids
from pipeline.actions.keep_top_k_variants_by_burden_reduction import action as keep_top_k_variants_by_burden_reduction
from pipeline.actions.annotate_liabilities_with_region_and_interface_adjacency import action as annotate_liabilities_with_region_and_interface_adjacency
from pipeline.actions.apply_region_severity_multiplier import action as apply_region_severity_multiplier
from pipeline.actions.propose_repair_mutations_from_policy import action as propose_repair_mutations_from_policy
from pipeline.actions.rank_repairs_by_conservativeness import action as rank_repairs_by_conservativeness
from pipeline.actions.propose_repairs_but_run_interface_gate_before_emitting import action as propose_repairs_but_run_interface_gate_before_emitting
from pipeline.actions.suppress_and_emit_refusal import action as suppress_and_emit_refusal
from pipeline.actions.propose_neighbor_noncritical_substitution_to_reduce_motif_context import action as propose_neighbor_noncritical_substitution_to_reduce_motif_context
from pipeline.actions.propose_cdr_repairs_only_if_high_risk_or_glyco_motif import action as propose_cdr_repairs_only_if_high_risk_or_glyco_motif
from pipeline.actions.prefer_non_paratope_and_non_anchor_positions import action as prefer_non_paratope_and_non_anchor_positions
from pipeline.actions.add_binding_risk_flag import action as add_binding_risk_flag
from pipeline.actions.propose_glyco_fix_n_to_q import action as propose_glyco_fix_n_to_q
from pipeline.actions.propose_glyco_fix_st_to_a import action as propose_glyco_fix_st_to_a
from pipeline.actions.run_interface_gate import action as run_interface_gate
from pipeline.actions.assemble_variants_from_cmc_repairs import action as assemble_variants_from_cmc_repairs
from pipeline.actions.load_scaffold_candidates_from_library import action as load_scaffold_candidates_from_library
from pipeline.actions.validate_candidate_metadata_fields import action as validate_candidate_metadata_fields
from pipeline.actions.flag_missing_metadata_and_apply_derank import action as flag_missing_metadata_and_apply_derank
from pipeline.actions.filter_out_missing_critical_fields import action as filter_out_missing_critical_fields
from pipeline.actions.compute_cdr_length_profile_from_input import action as compute_cdr_length_profile_from_input
from pipeline.actions.score_each_candidate_cdr_length_compatibility import action as score_each_candidate_cdr_length_compatibility
from pipeline.actions.score_each_candidate_structural_motif_compatibility import action as score_each_candidate_structural_motif_compatibility
from pipeline.actions.score_each_candidate_fr_identity import action as score_each_candidate_fr_identity
from pipeline.actions.score_each_candidate_stability_prior import action as score_each_candidate_stability_prior
from pipeline.actions.score_each_candidate_developability_prior import action as score_each_candidate_developability_prior
from pipeline.actions.apply_family_bias_prefer_vh3 import action as apply_family_bias_prefer_vh3
from pipeline.actions.annotate_reason_in_candidate_reasons import action as annotate_reason_in_candidate_reasons
from pipeline.actions.include_j_region_family_j6_in_candidate_pool_or_promote_if_present import action as include_j_region_family_j6_in_candidate_pool_or_promote_if_present
from pipeline.actions.add_reason_tag_long_cdr3_support import action as add_reason_tag_long_cdr3_support
from pipeline.actions.rank_candidates_by_weighted_sum import action as rank_candidates_by_weighted_sum
from pipeline.actions.emit_topn import action as emit_topn
from pipeline.actions.attach_rank_reasons_per_candidate import action as attach_rank_reasons_per_candidate
from pipeline.actions.lower_gate_and_keep_best_effort_topn import action as lower_gate_and_keep_best_effort_topn
from pipeline.actions.rank_by_identity_with_disclaimer import action as rank_by_identity_with_disclaimer


# Action Registry: maps action name (string) to function
# All action names must conform to [a-z0-9_]+ standard
ACTION_REGISTRY: Dict[str, Callable[[dict], dict]] = {
    # Input QC actions
    "extract_variable_domain_best_effort": extract_variable_domain_best_effort,
    "renumber_primary_imgt": renumber_primary_imgt,
    "approximate_region_by_imgt_boundaries": approximate_region_by_imgt_boundaries,
    
    # Immunogenicity actions
    "annotate_epitopes_with_regions_and_interface_adjacency": annotate_epitopes_with_regions_and_interface_adjacency,
    "select_minimal_anchor_disrupting_mutations_in_fr": select_minimal_anchor_disrupting_mutations_in_fr,
    "rank_cdr_epitopes_by_allele_coverage_and_strength": rank_cdr_epitopes_by_allele_coverage_and_strength,
    "propose_minimal_non_anchor_mutations_first": propose_minimal_non_anchor_mutations_first,
    "propose_anchor_mutation_with_affinity_risk_flag": propose_anchor_mutation_with_affinity_risk_flag,
    "assemble_variants_from_epitope_mutations": assemble_variants_from_epitope_mutations,
    "attach_rule_trace_and_param_ids": attach_rule_trace_and_param_ids,
    "keep_top_k_variants_by_burden_reduction": keep_top_k_variants_by_burden_reduction,
    
    # CMC actions
    "annotate_liabilities_with_region_and_interface_adjacency": annotate_liabilities_with_region_and_interface_adjacency,
    "apply_region_severity_multiplier": apply_region_severity_multiplier,
    "propose_repair_mutations_from_policy": propose_repair_mutations_from_policy,
    "rank_repairs_by_conservativeness": rank_repairs_by_conservativeness,
    "propose_repairs_but_run_interface_gate_before_emitting": propose_repairs_but_run_interface_gate_before_emitting,
    "suppress_and_emit_refusal": suppress_and_emit_refusal,
    "propose_neighbor_noncritical_substitution_to_reduce_motif_context": propose_neighbor_noncritical_substitution_to_reduce_motif_context,
    "propose_cdr_repairs_only_if_high_risk_or_glyco_motif": propose_cdr_repairs_only_if_high_risk_or_glyco_motif,
    "prefer_non_paratope_and_non_anchor_positions": prefer_non_paratope_and_non_anchor_positions,
    "add_binding_risk_flag": add_binding_risk_flag,
    "propose_glyco_fix_n_to_q": propose_glyco_fix_n_to_q,
    "propose_glyco_fix_st_to_a": propose_glyco_fix_st_to_a,
    "run_interface_gate": run_interface_gate,
    "assemble_variants_from_cmc_repairs": assemble_variants_from_cmc_repairs,
    
    # Germline/Scaffold actions
    "load_scaffold_candidates_from_library": load_scaffold_candidates_from_library,
    "validate_candidate_metadata_fields": validate_candidate_metadata_fields,
    "flag_missing_metadata_and_apply_derank": flag_missing_metadata_and_apply_derank,
    "filter_out_missing_critical_fields": filter_out_missing_critical_fields,
    "compute_cdr_length_profile_from_input": compute_cdr_length_profile_from_input,
    "score_each_candidate_cdr_length_compatibility": score_each_candidate_cdr_length_compatibility,
    "score_each_candidate_structural_motif_compatibility": score_each_candidate_structural_motif_compatibility,
    "score_each_candidate_fr_identity": score_each_candidate_fr_identity,
    "score_each_candidate_stability_prior": score_each_candidate_stability_prior,
    "score_each_candidate_developability_prior": score_each_candidate_developability_prior,
    "apply_family_bias_prefer_vh3": apply_family_bias_prefer_vh3,
    "annotate_reason_in_candidate_reasons": annotate_reason_in_candidate_reasons,
    "include_j_region_family_j6_in_candidate_pool_or_promote_if_present": include_j_region_family_j6_in_candidate_pool_or_promote_if_present,
    "add_reason_tag_long_cdr3_support": add_reason_tag_long_cdr3_support,
    "rank_candidates_by_weighted_sum": rank_candidates_by_weighted_sum,
    "emit_topn": emit_topn,
    "attach_rank_reasons_per_candidate": attach_rank_reasons_per_candidate,
    "lower_gate_and_keep_best_effort_topn": lower_gate_and_keep_best_effort_topn,
    "rank_by_identity_with_disclaimer": rank_by_identity_with_disclaimer,
}


def run_actions(context: dict, actions: List[str]) -> dict:
    """
    Execute a sequence of actions in order.
    
    Args:
        context: Input context dictionary (will be deep-copied)
        actions: List of action names (strings) to execute
        
    Returns:
        Updated context dictionary with all patches merged
        
    Raises:
        KeyError: If any action name is not found in ACTION_REGISTRY
    """
    # Deep copy to avoid mutating input
    result = copy.deepcopy(context)
    
    for action_name in actions:
        if action_name not in ACTION_REGISTRY:
            raise KeyError(
                f"Action '{action_name}' not found in ACTION_REGISTRY. "
                f"Available actions: {list(ACTION_REGISTRY.keys())}"
            )
        
        # Execute action to get patch
        action_func = ACTION_REGISTRY[action_name]
        patch = action_func(result)
        
        # Merge patch into result (deep merge for nested dicts)
        _deep_merge(result, patch)
    
    return result


def _deep_merge(target: dict, source: dict) -> None:
    """Deep merge source into target."""
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value
