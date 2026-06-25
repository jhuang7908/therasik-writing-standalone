"""
Action: annotate_epitopes_with_regions_and_interface_adjacency

Source: kb/20_rules/immuno_deimmunization_rules.yaml (RULE_IMMUNO_020_LOCATE_EPITOPE_REGION)

Reads:
  - immuno.epitopes
  - segmentation.regions
  - interface.flags

Writes:
  - immuno.epitopes[].region
  - immuno.epitopes[].interface_adjacent

Does NOT:
  - make decisions
  - access filesystem
"""


def action(context: dict) -> dict:
    """
    Annotate each epitope with its region (FR/CDR) and whether it's interface-adjacent.
    """
    patch = {}
    
    # TODO: Implement epitope region and interface adjacency annotation
    # For now, return empty patch (stub)
    
    return patch
