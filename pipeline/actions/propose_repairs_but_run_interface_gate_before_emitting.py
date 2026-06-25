"""
Action: propose_repairs_but_run_interface_gate_before_emitting

Source: kb/20_rules/cmc_fix_rules.yaml (RULE_CMC_030_INTERFACE_ADJACENT_GATE)

Reads:
  - cmc.liabilities (interface-adjacent)
  - interface.flags
  - variants (proposed repairs)

Writes:
  - variants[].interface_gate_result

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Run interface gate check on proposed repairs for interface-adjacent liabilities.
    """
    patch = {}
    
    # TODO: Implement interface gate check
    # For now, return empty patch (stub)
    
    return patch
