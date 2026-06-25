"""
Action: rank_by_identity_with_disclaimer

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_030_SCORE_FR_IDENTITY_AND_PRIORS, alternative)

Reads:
  - scaffold.candidates
  - scaffold.candidates[].fr_identity_score

Writes:
  - scaffold.candidates (ranked by identity)
  - report.disclaimer (identity-only ranking)

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Rank candidates by FR identity only when priors unavailable, with disclaimer.
    """
    patch = {}
    
    # TODO: Implement identity-only ranking with disclaimer
    # For now, return empty patch (stub)
    
    return patch
