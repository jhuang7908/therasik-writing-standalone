"""
Action: filter_out_missing_critical_fields

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_010_BUILD_CANDIDATE_SET_AND_VALIDATE_METADATA, alternative)

Reads:
  - scaffold.candidates[].missing_fields

Writes:
  - scaffold.candidates (filtered)

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Filter out candidates missing critical metadata fields (strict mode).
    """
    patch = {}
    
    # TODO: Implement critical field filtering
    # For now, return empty patch (stub)
    
    return patch
