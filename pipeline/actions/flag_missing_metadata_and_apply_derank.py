"""
Action: flag_missing_metadata_and_apply_derank

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_010_BUILD_CANDIDATE_SET_AND_VALIDATE_METADATA)

Reads:
  - scaffold.candidates[].metadata_complete
  - scaffold.candidates[].missing_fields

Writes:
  - scaffold.candidates[].deranked
  - scaffold.candidates[].score (adjusted)

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Flag candidates with missing metadata and apply deranking penalty.
    """
    patch = {}
    
    # TODO: Implement metadata deranking
    # For now, return empty patch (stub)
    
    return patch
