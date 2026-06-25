"""
Action: rank_repairs_by_conservativeness

Source: kb/20_rules/cmc_fix_rules.yaml (RULE_CMC_020_HIGH_RISK_FR_MUST_FIX)

Reads:
  - variants (CMC repair mutations)

Writes:
  - variants (reordered by conservativeness)

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Rank repair mutations by conservativeness (amino acid similarity).
    """
    patch = {}
    
    # TODO: Implement repair ranking by conservativeness
    # For now, return empty patch (stub)
    
    return patch
