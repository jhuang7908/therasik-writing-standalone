"""
Action: add_reason_tag_long_cdr3_support

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_050_LONG_CDR3_ADD_J6_CANDIDATES)

Reads:
  - scaffold.candidates (J6 candidates)

Writes:
  - scaffold.candidates[].reasons (appended with "long_cdr3_support")

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Add "long_cdr3_support" reason tag to J6 candidates.
    """
    patch = {}
    
    # TODO: Implement reason tag addition
    # For now, return empty patch (stub)
    
    return patch
