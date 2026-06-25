"""
Action: propose_cdr_repairs_only_if_high_risk_or_glyco_motif

Source: kb/20_rules/cmc_fix_rules.yaml (RULE_CMC_040_CDR_LIABILITIES_CONSERVATIVE_AND_WARN)

Reads:
  - cmc.liabilities (CDR)
  - cmc.liabilities[].risk
  - cmc.liabilities[].type

Writes:
  - variants (CDR repairs, only high-risk or glycosylation)

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Propose CDR repairs only for high-risk liabilities or glycosylation motifs.
    """
    patch = {}
    
    # TODO: Implement CDR repair filtering
    # For now, return empty patch (stub)
    
    return patch
