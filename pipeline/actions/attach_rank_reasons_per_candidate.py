"""
Action: attach_rank_reasons_per_candidate

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_090_EMIT_TOPN_WITH_REASONS_AND_TRACE)

Reads:
  - scaffold.candidates (ranked)

Writes:
  - scaffold.candidates[].rank_reasons

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Attach rank reasons to each candidate explaining the ranking.
    """
    patch = {}
    
    # TODO: Implement rank reason attachment
    # For now, return empty patch (stub)
    
    return patch
