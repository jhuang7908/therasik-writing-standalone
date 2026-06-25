"""
Action: validate_candidate_metadata_fields

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_010_BUILD_CANDIDATE_SET_AND_VALIDATE_METADATA)

Reads:
  - scaffold.candidates

Writes:
  - scaffold.candidates[].metadata_complete
  - scaffold.candidates[].missing_fields

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Validate that scaffold candidates have required metadata fields.
    """
    patch = {}
    
    # TODO: Implement metadata field validation
    # For now, return empty patch (stub)
    
    return patch
