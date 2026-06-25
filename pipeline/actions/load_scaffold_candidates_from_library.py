"""
Action: load_scaffold_candidates_from_library

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_010_BUILD_CANDIDATE_SET_AND_VALIDATE_METADATA)

Reads:
  - scaffold.library

Writes:
  - scaffold.candidates

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Load scaffold candidates from the scaffold library.
    """
    patch = {}
    
    # TODO: Implement scaffold candidate loading
    # For now, return empty patch (stub)
    
    return patch
