"""
Utility functions and helpers.
"""

from .fallback import mark_fallback, is_fallback, get_fallback_info
from .config_loader import get_config_lazy, clear_config_cache

__all__ = [
    "mark_fallback", "is_fallback", "get_fallback_info",
    "get_config_lazy", "clear_config_cache"
]

