"""
Action: propose_minimal_non_anchor_mutations_first

Source: kb/20_rules/immuno_deimmunization_rules.yaml (RULE_IMMUNO_040_CDR_STRONG_EPITOPE_MINIMAL_MUTATE_AND_WARN)

Reads:
  - immuno.epitopes (CDR, ranked)
  - immuno.epitopes[].anchor_positions
  - segmentation.regions

Writes:
  - variants (non-anchor mutations for CDR epitopes)

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Propose minimal mutations that avoid anchor positions in CDR epitopes.
    """
    patch = {}
    
    # TODO: Implement non-anchor mutation proposal for CDR epitopes
    # For now, return empty patch (stub)
    
    return patch
