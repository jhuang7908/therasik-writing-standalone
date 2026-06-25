"""
Action: prefer_non_paratope_and_non_anchor_positions

Source: kb/20_rules/cmc_fix_rules.yaml (RULE_CMC_040_CDR_LIABILITIES_CONSERVATIVE_AND_WARN)

Reads:
  - cmc.liabilities (CDR)
  - variants (CDR repair candidates)

Writes:
  - variants (prioritized to non-paratope/non-anchor positions)

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Prioritize CDR repair mutations to non-paratope and non-anchor positions when available.
    """
    patch = {}
    
    # TODO: Implement position preference for CDR repairs
    # For now, return empty patch (stub)
    
    return patch










