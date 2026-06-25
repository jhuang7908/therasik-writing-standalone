# Action Registry v1

**Action Registry is a mechanical execution layer, not a decision layer.**

This directory contains all action implementations for the rule execution system. Actions are pure functions that execute decisions made by rules in `kb/20_rules/`.

## Architecture

- **Rules** (in `kb/20_rules/`) make decisions based on triggers
- **Actions** (in `pipeline/actions/`) execute what rules decide
- Actions are **pure functions**: `context: dict -> patch: dict`
- Actions do **NOT** make decisions (no if/else logic)
- Actions only read/write fields defined in `kb/01_fields/fields_dictionary.yaml`
- **Action naming standard**: All action names must conform to `[a-z0-9_]+` (lowercase letters, digits, underscores only)

## Action List

### Input QC Actions

| Action Name | Source Rule | Reads | Writes |
|------------|-------------|-------|--------|
| `extract_variable_domain_best_effort` | RULE_QC_030 | `input.sequence.aa`, `qc.sequence.has_*` | `input.sequence.aa` (extracted), `qc.sequence.*` |
| `renumber_primary_imgt` | RULE_QC_030 | `input.sequence.aa` | `numbering.imgt.map`, `qc.numbering_status` |
| `approximate_region_by_imgt_boundaries` | RULE_IMMUNO_020 (alt), RULE_CMC_010 (alt) | `numbering.imgt.map` | `segmentation.regions` (approximated) |

### Immunogenicity Actions

| Action Name | Source Rule | Reads | Writes |
|------------|-------------|-------|--------|
| `annotate_epitopes_with_regions_and_interface_adjacency` | RULE_IMMUNO_020 | `immuno.epitopes`, `segmentation.regions`, `interface.flags` | `immuno.epitopes[].region`, `immuno.epitopes[].interface_adjacent` |
| `select_minimal_anchor_disrupting_mutations_in_fr` | RULE_IMMUNO_030 | `immuno.epitopes` (FR), `segmentation.regions` | `variants` (FR mutations) |
| `rank_cdr_epitopes_by_allele_coverage_and_strength` | RULE_IMMUNO_040 | `immuno.epitopes` (CDR), `immuno.metrics` | `immuno.epitopes` (reordered) |
| `propose_minimal_non_anchor_mutations_first` | RULE_IMMUNO_040 | `immuno.epitopes` (CDR), `segmentation.regions` | `variants` (non-anchor mutations) |
| `propose_anchor_mutation_with_affinity_risk_flag` | RULE_IMMUNO_040 | `immuno.epitopes` (CDR) | `variants` (anchor mutations with risk flag) |
| `assemble_variants_from_epitope_mutations` | RULE_IMMUNO_050 | `variants` (individual), `immuno.epitopes` | `variants` (assembled) |
| `attach_rule_trace_and_param_ids` | RULE_IMMUNO_050, RULE_CMC_090, RULE_GL_090 | (context) | `report.trace.*` |
| `keep_top_k_variants_by_burden_reduction` | RULE_IMMUNO_050 (alt) | `variants`, `immuno.metrics` | `variants` (filtered) |

### CMC Actions

| Action Name | Source Rule | Reads | Writes |
|------------|-------------|-------|--------|
| `annotate_liabilities_with_region_and_interface_adjacency` | RULE_CMC_010 | `cmc.liabilities`, `segmentation.regions`, `interface.flags` | `cmc.liabilities[].region`, `cmc.liabilities[].interface_adjacent` |
| `apply_region_severity_multiplier` | RULE_CMC_010 | `cmc.liabilities[].risk`, `cmc.liabilities[].region` | `cmc.liabilities[].adjusted_risk` |
| `propose_repair_mutations_from_policy` | RULE_CMC_020 | `cmc.liabilities` | `variants` (repair mutations) |
| `rank_repairs_by_conservativeness` | RULE_CMC_020 | `variants` (repairs) | `variants` (reordered) |
| `propose_repairs_but_run_interface_gate_before_emitting` | RULE_CMC_030 | `cmc.liabilities` (interface-adjacent), `variants` | `variants[].interface_gate_result` |
| `suppress_and_emit_refusal` | RULE_CMC_030 | `variants[].interface_gate_result` | `variants` (filtered), `report.refusals` |
| `propose_neighbor_noncritical_substitution_to_reduce_motif_context` | RULE_CMC_030 (alt) | `cmc.liabilities`, `interface.flags` | `variants` (second-order repairs) |
| `propose_cdr_repairs_only_if_high_risk_or_glyco_motif` | RULE_CMC_040 | `cmc.liabilities` (CDR) | `variants` (filtered CDR repairs) |
| `prefer_non_paratope_and_non_anchor_positions` | RULE_CMC_040 | `cmc.liabilities` (CDR), `variants` | `variants` (prioritized) |
| `add_binding_risk_flag` | RULE_CMC_040 | `variants` (CDR repairs) | `variants[].binding_risk_flag` |
| `propose_glyco_fix_n_to_q` | RULE_CMC_050 | `cmc.liabilities` (glyco) | `variants` (N->Q mutations) |
| `propose_glyco_fix_st_to_a` | RULE_CMC_050 | `cmc.liabilities` (glyco) | `variants` (S/T->A mutations) |
| `run_interface_gate` | RULE_CMC_050 | `variants` (glyco repairs), `interface.flags` | `variants[].interface_gate_result` |
| `assemble_variants_from_cmc_repairs` | RULE_CMC_090 | `variants` (individual repairs) | `variants` (assembled) |

### Germline/Scaffold Actions

| Action Name | Source Rule | Reads | Writes |
|------------|-------------|-------|--------|
| `load_scaffold_candidates_from_library` | RULE_GL_010 | `scaffold.library` | `scaffold.candidates` |
| `validate_candidate_metadata_fields` | RULE_GL_010 | `scaffold.candidates` | `scaffold.candidates[].metadata_complete` |
| `flag_missing_metadata_and_apply_derank` | RULE_GL_010 | `scaffold.candidates[].metadata_complete` | `scaffold.candidates[].deranked` |
| `filter_out_missing_critical_fields` | RULE_GL_010 (alt) | `scaffold.candidates[].missing_fields` | `scaffold.candidates` (filtered) |
| `compute_cdr_length_profile_from_input` | RULE_GL_020 | `segmentation.regions` | `segmentation.cdr_length_profile` |
| `score_each_candidate_cdr_length_compatibility` | RULE_GL_020 | `scaffold.candidates`, `segmentation.cdr_length_profile` | `scaffold.candidates[].cdr_length_compatibility_score` |
| `score_each_candidate_structural_motif_compatibility` | RULE_GL_020 | `scaffold.candidates`, `segmentation.regions` | `scaffold.candidates[].structural_motif_compatibility_score` |
| `score_each_candidate_fr_identity` | RULE_GL_030 | `scaffold.candidates`, `humanness.fr_identity` | `scaffold.candidates[].fr_identity_score` |
| `score_each_candidate_stability_prior` | RULE_GL_030 | `scaffold.candidates[].stability_prior` | `scaffold.candidates[].stability_prior_score` |
| `score_each_candidate_developability_prior` | RULE_GL_030 | `scaffold.candidates[].developability_prior` | `scaffold.candidates[].developability_prior_score` |
| `apply_family_bias_prefer_vh3` | RULE_GL_040 | `scaffold.candidates[].family`, `process.requires_proteinA` | `scaffold.candidates[].proteinA_bias_score` |
| `annotate_reason_in_candidate_reasons` | RULE_GL_040 | `scaffold.candidates[].proteinA_bias_score` | `scaffold.candidates[].reasons` |
| `include_j_region_family_j6_in_candidate_pool_or_promote_if_present` | RULE_GL_050 | `scaffold.candidates`, `segmentation.cdr3_length` | `scaffold.candidates` (J6 included/promoted) |
| `add_reason_tag_long_cdr3_support` | RULE_GL_050 | `scaffold.candidates` (J6) | `scaffold.candidates[].reasons` |
| `rank_candidates_by_weighted_sum` | RULE_GL_090 | `scaffold.candidates` (all scores) | `scaffold.candidates` (ranked), `scaffold.candidates[].total_score` |
| `emit_topn` | RULE_GL_090 | `scaffold.candidates` (ranked), `scaffold.selection.topn_override` (optional) | `scaffold.candidates` (Top-N), `scaffold.selected_id` |
| `attach_rank_reasons_per_candidate` | RULE_GL_090 | `scaffold.candidates` (ranked) | `scaffold.candidates[].rank_reasons` |
| `lower_gate_and_keep_best_effort_topn` | RULE_GL_020 (alt) | `scaffold.candidates` | `scaffold.candidates` (relaxed), `scaffold.candidates[].best_effort_flag` |
| `rank_by_identity_with_disclaimer` | RULE_GL_030 (alt) | `scaffold.candidates[].fr_identity_score` | `scaffold.candidates` (ranked), `report.disclaimer` |

## Usage

```python
from pipeline.actions import run_actions, ACTION_REGISTRY

# Execute a sequence of actions
context = {...}  # Your context dict
actions = ["extract_variable_domain_best_effort", "renumber_primary_imgt"]
result = run_actions(context, actions)

# Or call individual actions
action_func = ACTION_REGISTRY["extract_variable_domain_best_effort"]
patch = action_func(context)
```

## Field Reference

All fields must be defined in `kb/01_fields/fields_dictionary.yaml`. Actions must not:
- Create new fields
- Use field name variants
- Access filesystem
- Make decisions (if/else logic)

## Validation

Run validation script to ensure all actions are properly registered:
```bash
python tools/validate_actions.py
```

## Status

All actions are currently **stubs** (empty implementations). They define the interface and field contracts but require implementation.










