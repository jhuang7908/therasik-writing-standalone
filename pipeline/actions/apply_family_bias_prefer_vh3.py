"""
Action: apply_family_bias_prefer_vh3

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_040_PROTEINA_REQUIREMENT_VH3_BIAS)

Reads:
  - scaffold.candidates
  - scaffold.candidates[].family
  - process.requires_proteinA

Writes:
  - scaffold.candidates[].proteinA_bias_score

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Apply VH3 family bias when Protein A is required.
    """
    patch = {}
    
    # TODO: Implement VH3 family bias application
    # For now, return empty patch (stub)
    
    return patch
