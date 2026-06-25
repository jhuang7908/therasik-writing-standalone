"""
Action: annotate_liabilities_with_region_and_interface_adjacency

Source: kb/20_rules/cmc_fix_rules.yaml (RULE_CMC_010_CLASSIFY_SEVERITY_WITH_REGION_INTERFACE)

Reads:
  - cmc.liabilities
  - segmentation.regions
  - interface.flags

Writes:
  - cmc.liabilities[].region
  - cmc.liabilities[].interface_adjacent

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Annotate each liability with its region (FR/CDR) and interface adjacency.
    """
    patch = {}
    
    # TODO: Implement liability region and interface adjacency annotation
    # For now, return empty patch (stub)
    
    return patch
