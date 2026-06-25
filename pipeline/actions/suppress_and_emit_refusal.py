"""
Action: suppress_and_emit_refusal

Source: kb/20_rules/cmc_fix_rules.yaml (RULE_CMC_030_INTERFACE_ADJACENT_GATE)

Reads:
  - variants[].interface_gate_result (failed)

Writes:
  - variants (removed failed repairs)
  - report.refusals

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Suppress failed repairs and emit refusal reasons.
    """
    patch = {}
    
    # TODO: Implement refusal emission
    # For now, return empty patch (stub)
    
    return patch
