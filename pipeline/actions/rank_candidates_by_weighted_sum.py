"""
Action: rank_candidates_by_weighted_sum

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_090_EMIT_TOPN_WITH_REASONS_AND_TRACE)

Reads:
  - scaffold.candidates (with all scores)
  - scaffold.candidates[].cdr_length_compatibility_score
  - scaffold.candidates[].structural_motif_compatibility_score
  - scaffold.candidates[].fr_identity_score
  - scaffold.candidates[].stability_prior_score
  - scaffold.candidates[].developability_prior_score
  - scaffold.candidates[].proteinA_bias_score

Writes:
  - scaffold.candidates (reordered by weighted sum)
  - scaffold.candidates[].total_score

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Rank candidates by weighted sum of all compatibility and prior scores.
    """
    patch = {}
    
    # TODO: Implement weighted sum ranking
    # For now, return empty patch (stub)
    
    return patch
