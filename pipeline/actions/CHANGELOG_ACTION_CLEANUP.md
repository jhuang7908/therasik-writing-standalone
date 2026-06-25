# Action Registry Cleanup Changelog

## Summary

Completed action naming cleanup and rule synchronization to ensure all action names conform to `[a-z0-9_]+` standard for pharmaceutical-grade auditability.

## Changes Made

### 1. Directory Structure
- ✅ Moved rules directory: `kb/03_rules/` → `kb/20_rules/`
- ✅ Updated all action file path references from `kb/03_rules/` to `kb/20_rules/`

### 2. Action Name Cleanup in Rules

#### Removed Conditional Actions
- ❌ Deleted: `"if_only_anchor_works: propose_anchor_mutation_with_affinity_risk_flag"`
  - **Reason**: Conditional logic should be in rules, not action names
  - **Solution**: Rules now directly call `propose_anchor_mutation_with_affinity_risk_flag` when appropriate

#### Renamed Actions (Illegal Characters Removed)
- `"annotate_liabilities_with_region(FR/CDR) and interface_adjacency"` 
  → `"annotate_liabilities_with_region_and_interface_adjacency"`

- `"for_each_liability: propose_repair_mutations_from_policy"`
  → `"propose_repair_mutations_from_policy"`

- `"if_gate_fail: suppress_and_emit_refusal"`
  → `"suppress_and_emit_refusal"`

- `"prefer_non-paratope and non-anchor positions (if available)"`
  → `"prefer_non_paratope_and_non_anchor_positions"`

- `"prefer_N->Q unless N is structurally protected"`
  → `"propose_glyco_fix_n_to_q"`

- `"else S/T->A as alternative"`
  → `"propose_glyco_fix_st_to_a"`

- `"emit_topN_override: 3"`
  → `"emit_topn"` (with `scaffold.selection.topn_override: 3` in decision.set)

- `"include_j_region_family:J6_in_candidate_pool_or_promote_if_present"`
  → `"include_j_region_family_j6_in_candidate_pool_or_promote_if_present"`

- `"add_reason_tag: long_cdr3_support"`
  → `"add_reason_tag_long_cdr3_support"`

- `"score_each_candidate.cdr_length_compatibility"`
  → `"score_each_candidate_cdr_length_compatibility"`

- `"score_each_candidate.structural_motif_compatibility"`
  → `"score_each_candidate_structural_motif_compatibility"`

- `"score_each_candidate.fr_identity"`
  → `"score_each_candidate_fr_identity"`

- `"score_each_candidate.stability_prior"`
  → `"score_each_candidate_stability_prior"`

- `"score_each_candidate.developability_prior"`
  → `"score_each_candidate_developability_prior"`

#### Lowercase Conversions
- `"select_minimal_anchor_disrupting_mutations_in_FR"` → `"select_minimal_anchor_disrupting_mutations_in_fr"`
- `"apply_family_bias_prefer_VH3"` → `"apply_family_bias_prefer_vh3"`
- `"lower_gate_and_keep_best_effort_topN"` → `"lower_gate_and_keep_best_effort_topn"`
- `"emit_topN"` → `"emit_topn"`

### 3. Action Files Created/Renamed

#### New Files Created
- `propose_glyco_fix_n_to_q.py`
- `propose_glyco_fix_st_to_a.py`
- `prefer_non_paratope_and_non_anchor_positions.py`
- `emit_topn.py` (replaces `emit_topN.py` and `emit_topN_override.py`)
- `include_j_region_family_j6_in_candidate_pool_or_promote_if_present.py`
- `add_reason_tag_long_cdr3_support.py`

#### Files Renamed
- `select_minimal_anchor_disrupting_mutations_in_FR.py` → `select_minimal_anchor_disrupting_mutations_in_fr.py`
- `apply_family_bias_prefer_VH3.py` → `apply_family_bias_prefer_vh3.py`
- `lower_gate_and_keep_best_effort_topN.py` → `lower_gate_and_keep_best_effort_topn.py`

#### Old Files Archived (renamed with `_old.py` suffix)
- `if_only_anchor_works_propose_anchor_mutation_with_affinity_risk_flag_old.py`
- `prefer_non_paratope_and_non_anchor_positions_if_available_old.py`
- `prefer_N_to_Q_unless_N_is_structurally_protected_old.py`
- `else_S_T_to_A_as_alternative_old.py`
- `emit_topN_old.py`
- `emit_topN_override_old.py`
- `include_j_region_family_J6_in_candidate_pool_or_promote_if_present_old.py`

### 4. Registry Updates
- ✅ Removed all illegal action keys (containing `:`, `(`, `)`, `->`, `/`, `-`, uppercase letters)
- ✅ Added all new cleaned action keys
- ✅ Updated all import statements to match new file names
- ✅ Total actions in registry: **44**

### 5. Validation & Testing

#### Created Validation Script
- ✅ `tools/validate_actions.py`
  - Extracts actions from `kb/20_rules/*.yaml`
  - Validates action names conform to `[a-z0-9_]+`
  - Checks for missing/orphan actions
  - Exit code 0 if all validations pass

#### Created Smoke Tests
- ✅ `tests/test_action_registry_smoke.py`
  - Tests ACTION_REGISTRY import
  - Tests run_actions() function
  - Tests action naming standard compliance
  - All 6 tests passing ✅

### 6. Documentation Updates
- ✅ Updated `pipeline/actions/README.md`
  - Fixed all path references: `kb/03_rules/` → `kb/20_rules/`
  - Updated all action names to cleaned versions
  - Added validation section

## Validation Results

### ✅ Validation Script Output
```
================================================================================
Action Registry Validation Report
================================================================================

Rules directory: D:\InSynBio-AI-Research\Antibody_Engineer_Suite\kb\20_rules
Actions found in rules: 44
Actions in registry: 44

✅ All validations passed!

All 44 actions are valid and referenced.
================================================================================
```

### ✅ Smoke Tests
```
tests/test_action_registry_smoke.py::test_action_registry_import PASSED
tests/test_action_registry_smoke.py::test_action_registry_has_actions PASSED
tests/test_action_registry_smoke.py::test_run_actions_basic PASSED
tests/test_action_registry_smoke.py::test_run_actions_multiple PASSED
tests/test_action_registry_smoke.py::test_run_actions_invalid_action PASSED
tests/test_action_registry_smoke.py::test_action_naming_standard PASSED

============================== 6 passed in 0.10s ==============================
```

## Final Action List (44 actions)

All actions now conform to `[a-z0-9_]+` standard:

1. add_binding_risk_flag
2. add_reason_tag_long_cdr3_support
3. annotate_epitopes_with_regions_and_interface_adjacency
4. annotate_liabilities_with_region_and_interface_adjacency
5. annotate_reason_in_candidate_reasons
6. apply_family_bias_prefer_vh3
7. apply_region_severity_multiplier
8. approximate_region_by_imgt_boundaries
9. assemble_variants_from_cmc_repairs
10. assemble_variants_from_epitope_mutations
11. attach_rank_reasons_per_candidate
12. attach_rule_trace_and_param_ids
13. compute_cdr_length_profile_from_input
14. emit_topn
15. extract_variable_domain_best_effort
16. filter_out_missing_critical_fields
17. flag_missing_metadata_and_apply_derank
18. include_j_region_family_j6_in_candidate_pool_or_promote_if_present
19. keep_top_k_variants_by_burden_reduction
20. load_scaffold_candidates_from_library
21. lower_gate_and_keep_best_effort_topn
22. prefer_non_paratope_and_non_anchor_positions
23. propose_anchor_mutation_with_affinity_risk_flag
24. propose_cdr_repairs_only_if_high_risk_or_glyco_motif
25. propose_glyco_fix_n_to_q
26. propose_glyco_fix_st_to_a
27. propose_minimal_non_anchor_mutations_first
28. propose_neighbor_noncritical_substitution_to_reduce_motif_context
29. propose_repair_mutations_from_policy
30. propose_repairs_but_run_interface_gate_before_emitting
31. rank_by_identity_with_disclaimer
32. rank_candidates_by_weighted_sum
33. rank_cdr_epitopes_by_allele_coverage_and_strength
34. rank_repairs_by_conservativeness
35. renumber_primary_imgt
36. run_interface_gate
37. score_each_candidate_cdr_length_compatibility
38. score_each_candidate_developability_prior
39. score_each_candidate_fr_identity
40. score_each_candidate_stability_prior
41. score_each_candidate_structural_motif_compatibility
42. select_minimal_anchor_disrupting_mutations_in_fr
43. suppress_and_emit_refusal
44. validate_candidate_metadata_fields

## Files Changed

### Rules Files (kb/20_rules/)
- `input_qc_rules.yaml` - No action name changes needed
- `immuno_deimmunization_rules.yaml` - Fixed action names, fixed YAML syntax
- `cmc_fix_rules.yaml` - Fixed multiple action names
- `germline_selection_rules.yaml` - Fixed action names, added topn_override field

### Action Files (pipeline/actions/)
- Created: 6 new action files
- Renamed: 3 action files (uppercase → lowercase)
- Updated: All 44 action files (path references updated)

### Core Files
- `pipeline/actions/registry.py` - Complete rewrite with cleaned action names
- `pipeline/actions/README.md` - Updated paths and action names
- `tools/validate_actions.py` - New validation script
- `tests/test_action_registry_smoke.py` - New smoke tests

## Compliance Status

✅ **All action names conform to `[a-z0-9_]+` standard**
✅ **All actions referenced in rules exist in registry**
✅ **No orphan actions (all registry actions are referenced)**
✅ **All validation tests passing**
✅ **All smoke tests passing**

## Next Steps

1. Implement actual logic in action stubs (currently all return empty patches)
2. Add unit tests for individual actions
3. Integrate with rule execution engine
4. Add field validation against `kb/01_fields/fields_dictionary.yaml`










