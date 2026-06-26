"""
Scoring Profile
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.utils.config_loader import clear_config_cache, get_config_lazy

def test_scoring_profiles():
    """scoring profiles"""
    clear_config_cache()
    cfg = get_config_lazy()
    
    print("=" * 60)
    print("Scoring Profile Test")
    print("=" * 60)
    
    # weights
    weights = cfg.parameters.get_scoring_weights()
    print(f"\nDefault weights: {weights}")
    
    # scoring
    if cfg.parameters.scoring:
        print(f"\nActive profile: {cfg.parameters.scoring.active_profile}")
        print(f"Available profiles: {list(cfg.parameters.scoring.profiles.keys())}")
        
        # profile
        for profile_name in cfg.parameters.scoring.profiles.keys():
            cfg.parameters.scoring.active_profile = profile_name
            weights = cfg.parameters.get_scoring_weights()
            print(f"\nProfile '{profile_name}' weights: {weights}")
    else:
        print("\n⚠️  Scoring profiles not configured in config.yaml")
        print("   Using legacy scoring_weights instead")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_scoring_profiles()


















