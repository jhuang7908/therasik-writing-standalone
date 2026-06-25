"""
Action: score_each_candidate.stability_prior

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_030_SCORE_FR_IDENTITY_AND_PRIORS)

Reads:
  - scaffold.candidates
  - scaffold.candidates[].stability_prior

Writes:
  - scaffold.candidates[].stability_prior_score

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Score each candidate using stability prior (if available).
    """
    patch = {}
    
    # TODO: Implement stability prior scoring
    # For now, return empty patch (stub)
    
    return patch
