import yaml
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from core.position_sets.load_imgt_position_sets import (
    get_surface_plasticity_v1, 
    flatten_nd_dependent_all_v2_lite
)

def build_strict_surface_set():
    original_set = get_surface_plasticity_v1()
    nd_all = flatten_nd_dependent_all_v2_lite()
    
    strict_set = original_set - nd_all
    removed = original_set & nd_all
    
    output_data = {
        "surface_plasticity_positions_v1_strict": sorted(list(strict_set)),
        "audit": {
            "original_count": len(original_set),
            "removed_count": len(removed),
            "removed_positions": sorted(list(removed)),
            "reason": "excluded ND-dependent v2-lite positions to avoid structural disruption during resurfacing"
        }
    }
    
    output_path = PROJECT_ROOT / "output" / "surface_plasticity_positions_v1_strict.yaml"
    os.makedirs(output_path.parent, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(output_data, f, sort_keys=False, default_flow_style=False)
    
    print(f"Strict surface set saved to {output_path}")
    print(f"Removed {len(removed)} positions: {sorted(list(removed))}")

if __name__ == "__main__":
    build_strict_surface_set()
