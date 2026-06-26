"""
Fallback
"""

import pytest
from core.utils.fallback import (
    mark_fallback,
    is_fallback,
    get_fallback_info
)


class TestFallbackUtils:
    """fallback"""
    
    def test_mark_fallback(self):
        """fallback"""
        obj = {"template_id": "TEST_001"}
        mark_fallback(
            obj,
            reason="ANARCII numbering failed",
            ftype="numbering",
            severity="warning"
        )
        assert obj["fallback"] is True
        assert obj["fallback_reason"] == "ANARCII numbering failed"
        assert obj["fallback_type"] == "numbering"
        assert obj["fallback_severity"] == "warning"
    
    def test_is_fallback(self):
        """fallback"""
        obj1 = {"fallback": True}
        obj2 = {"fallback": False}
        obj3 = {}
        
        assert is_fallback(obj1) is True
        assert is_fallback(obj2) is False
        assert is_fallback(obj3) is False
    
    def test_get_fallback_info(self):
        """fallback"""
        obj = {
            "fallback": True,
            "fallback_reason": "Test reason",
            "fallback_type": "numbering",
            "fallback_severity": "warning"
        }
        info = get_fallback_info(obj)
        assert info is not None
        assert info["fallback"] is True
        assert info["reason"] == "Test reason"
        assert info["type"] == "numbering"
        assert info["severity"] == "warning"
    
    def test_get_fallback_info_not_fallback(self):
        """fallback"""
        obj = {"fallback": False}
        info = get_fallback_info(obj)
        assert info is None


















