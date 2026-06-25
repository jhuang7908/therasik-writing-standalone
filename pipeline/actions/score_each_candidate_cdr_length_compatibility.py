"""
Action: score_each_candidate.cdr_length_compatibility

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_020_SCORE_CDR_LENGTH_AND_MOTIF_COMPATIBILITY)

Reads:
  - scaffold.candidates
  - scaffold.candidates[].cdr_length_profile
  - segmentation.cdr_length_profile

Writes:
  - scaffold.candidates[].cdr_length_compatibility_score

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Score each candidate by CDR length compatibility with input.
    """
    patch = {}
    
    # TODO: Implement CDR length compatibility scoring
    # For now, return empty patch (stub)
    
    return patch
