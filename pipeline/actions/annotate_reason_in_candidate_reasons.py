"""
Action: annotate_reason_in_candidate_reasons

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_040_PROTEINA_REQUIREMENT_VH3_BIAS)

Reads:
  - scaffold.candidates[].proteinA_bias_score

Writes:
  - scaffold.candidates[].reasons (appended)

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Annotate candidate reasons with Protein A bias explanation.
    """
    patch = {}
    
    # TODO: Implement reason annotation
    # For now, return empty patch (stub)
    
    return patch
