"""
Configuration modules.
"""

# 
# ：，，
import importlib.util
from pathlib import Path

_parent_dir = Path(__file__).resolve().parent.parent
config_path = _parent_dir / "config.py"

if config_path.exists():
    spec = importlib.util.spec_from_file_location("core_config_module", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    
    # 
    get_config = config_module.get_config
    Config = config_module.Config
    
    # CFG
    def _get_cfg():
        return get_config()
    
    CFG = property(lambda self: _get_cfg())
    
    __all__ = ["get_config", "Config"]
else:
    __all__ = []

