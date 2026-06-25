"""
Action: emit_topN_override: 3

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_090_EMIT_TOPN_WITH_REASONS_AND_TRACE, alternative)

Reads:
  - scaffold.candidates (ranked)
  - scaffold.candidates[].total_score

Writes:
  - scaffold.candidates (filtered to Top-3)
  - scaffold.selected_id

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Emit Top-3 candidates (override default Top-N) for customer readability.
    """
    patch = {}
    
    # TODO: Implement Top-3 emission override
    # For now, return empty patch (stub)
    
    return patch
