"""
Action: score_each_candidate.developability_prior

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_030_SCORE_FR_IDENTITY_AND_PRIORS)

Reads:
  - scaffold.candidates
  - scaffold.candidates[].developability_prior

Writes:
  - scaffold.candidates[].developability_prior_score

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Score each candidate using developability prior (if available).
    """
    patch = {}
    
    # TODO: Implement developability prior scoring
    # For now, return empty patch (stub)
    
    return patch
