import yaml
import os
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
YAML_PATH = PROJECT_ROOT / "core" / "data" / "position_sets" / "imgt_position_sets.yaml"

def load_yaml():
    if not YAML_PATH.exists():
        print(f"Warning: IMGT position sets YAML not found at {YAML_PATH}")
        return {}
    try:
        with open(YAML_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML: {e}")
        return {}

def get_imgt_anchors():
    data = load_yaml()
    return set(data.get('imgt_position_sets', {}).get('imgt_anchor_positions', []))

def get_vhh_hallmarks():
    data = load_yaml()
    return set(data.get('imgt_position_sets', {}).get('vhh_hallmark_positions', []))

def get_vernier_anchors():
    data = load_yaml()
    return set(data.get('imgt_position_sets', {}).get('vernier_anchor_positions', []))

def get_surface_plasticity_v1():
    data = load_yaml()
    return set(data.get('imgt_position_sets', {}).get('surface_plasticity_positions_v1', []))

def get_nd_dependent_v2_lite(region: str, class_label: str):
    """
    Returns {"core": set[int], "candidate": set[int]}
    """
    data = load_yaml()
    nd_data = data.get('north_dunbrack', {}).get('dependent_positions_v2_lite', {})
    
    # Check region (H1/H2)
    region_data = nd_data.get(region, {})
    class_data = region_data.get(class_label, {})
    
    return {
        "core": set(class_data.get('core', [])),
        "candidate": set(class_data.get('candidate', []))
    }

def flatten_nd_dependent_all_v2_lite():
    """
    Flattens core and candidate positions across all classes in H1 and H2.
    """
    data = load_yaml()
    nd_data = data.get('north_dunbrack', {}).get('dependent_positions_v2_lite', {})
    
    flattened = set()
    for region in ['H1', 'H2']:
        region_data = nd_data.get(region, {})
        for cls_label, sets in region_data.items():
            flattened.update(sets.get('core', []))
            flattened.update(sets.get('candidate', []))
    return flattened
