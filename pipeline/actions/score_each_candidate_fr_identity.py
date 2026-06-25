"""
Action: score_each_candidate.fr_identity

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_030_SCORE_FR_IDENTITY_AND_PRIORS)

Reads:
  - scaffold.candidates
  - humanness.fr_identity
  - segmentation.regions

Writes:
  - scaffold.candidates[].fr_identity_score

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Score each candidate by FR identity with input sequence.
    """
    patch = {}
    
    # TODO: Implement FR identity scoring
    # For now, return empty patch (stub)
    
    return patch
