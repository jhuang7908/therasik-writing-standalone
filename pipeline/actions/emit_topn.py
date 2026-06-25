"""
Action: emit_topn

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_090_EMIT_TOPN_WITH_REASONS_AND_TRACE)

Action: emit_topn

Reads:
  - scaffold.candidates (ranked)
  - scaffold.candidates[].total_score
  - scaffold.selection.topn_override (optional, if set overrides default)

Writes:
  - scaffold.candidates (filtered to Top-N)
  - scaffold.selected_id

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Emit Top-N candidates. If scaffold.selection.topn_override is set, use that value instead of default.
    """
    patch = {}
    
    # TODO: Implement Top-N emission with override support
    # For now, return empty patch (stub)
    
    return patch
