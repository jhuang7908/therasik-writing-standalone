"""
Action: attach_rule_trace_and_param_ids

Source: 
  - kb/20_rules/immuno_deimmunization_rules.yaml (RULE_IMMUNO_050_BUILD_DEIMMU_VARIANTS_AND_TRACE)
  - kb/20_rules/cmc_fix_rules.yaml (RULE_CMC_090_BUILD_VARIANTS_AND_MIN_VALIDATION)
  - kb/20_rules/germline_selection_rules.yaml (RULE_GL_090_EMIT_TOPN_WITH_REASONS_AND_TRACE)

Reads:
  - (context from rule execution)

Writes:
  - report.trace.rules_fired
  - report.trace.params_used

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Attach rule IDs and parameter IDs to report.trace for auditability.
    """
    patch = {}
    
    # TODO: Implement trace attachment
    # For now, return empty patch (stub)
    
    return patch
