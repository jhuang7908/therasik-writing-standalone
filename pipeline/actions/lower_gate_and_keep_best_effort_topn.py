"""
Action: lower_gate_and_keep_best_effort_topn

Source: kb/20_rules/germline_selection_rules.yaml (RULE_GL_020_SCORE_CDR_LENGTH_AND_MOTIF_COMPATIBILITY, alternative)

Reads:
  - scaffold.candidates (all failed compatibility gate)

Writes:
  - scaffold.candidates (relaxed gate applied)
  - scaffold.candidates[].best_effort_flag

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Lower compatibility gate and keep best-effort Top-N when all candidates fail hard gate.
    """
    patch = {}
    
    # TODO: Implement gate relaxation
    # For now, return empty patch (stub)
    
    return patch
