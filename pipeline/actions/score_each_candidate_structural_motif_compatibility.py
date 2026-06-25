"""
Action: score_each_candidate.structural_motif_compatibility

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_020_SCORE_CDR_LENGTH_AND_MOTIF_COMPATIBILITY)

Reads:
  - scaffold.candidates
  - segmentation.regions

Writes:
  - scaffold.candidates[].structural_motif_compatibility_score

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Score each candidate by structural motif compatibility.
    """
    patch = {}
    
    # TODO: Implement structural motif compatibility scoring
    # For now, return empty patch (stub)
    
    return patch
