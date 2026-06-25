"""
（）

，
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Optional

_CONFIG_MODULE_NAME = 'core_config_module'
_config_cache: Optional[object] = None


def get_config_lazy():
    """
    （）
    
    Returns:
        Config
    
    Raises:
        ImportError: config.py
    """
    global _config_cache
    
    # ，
    if _config_cache is not None:
        return _config_cache
    
    # sys.modules
    if _CONFIG_MODULE_NAME in sys.modules:
        config_module = sys.modules[_CONFIG_MODULE_NAME]
        _config_cache = config_module.get_config()
        return _config_cache
    
    # （config.pycore）
    config_path = Path(__file__).resolve().parents[1] / "config.py"
    if not config_path.exists():
        raise ImportError(f"config.py not found at {config_path}")
    
    try:
        spec = importlib.util.spec_from_file_location(_CONFIG_MODULE_NAME, config_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed to create spec for {config_path}")
        
        config_module = importlib.util.module_from_spec(spec)
        sys.modules[_CONFIG_MODULE_NAME] = config_module
        spec.loader.exec_module(config_module)
        
        _config_cache = config_module.get_config()
        return _config_cache
    except Exception as e:
        raise ImportError(f"Failed to load config module: {e}") from e


def clear_config_cache():
    """（）"""
    global _config_cache
    _config_cache = None
    if _CONFIG_MODULE_NAME in sys.modules:
        del sys.modules[_CONFIG_MODULE_NAME]

