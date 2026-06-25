"""
Action: apply_region_severity_multiplier

Source: kb/20_rules/cmc_fix_rules.yaml (RULE_CMC_010_CLASSIFY_SEVERITY_WITH_REGION_INTERFACE)

Reads:
  - cmc.liabilities[].risk
  - cmc.liabilities[].region
  - cmc.liabilities[].interface_adjacent

Writes:
  - cmc.liabilities[].adjusted_risk

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Apply region-based severity multipliers to liability risk scores.
    """
    patch = {}
    
    # TODO: Implement region severity multiplier application
    # For now, return empty patch (stub)
    
    return patch
