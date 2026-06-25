"""
Fallback

fallback，fallback
"""

from __future__ import annotations

from typing import Dict, Any, Optional


def mark_fallback(
    obj: Dict[str, Any],
    reason: str,
    ftype: str = "generic",
    severity: str = "warning"
) -> Dict[str, Any]:
    """
    fallback
    
    Args:
        obj: （）
        reason: fallback
        ftype: fallback（"numbering", "template", "scaffold", "generic"）
        severity: （"info", "warning", "error"）
    
    Returns:
        （，）
    
    Example:
        >>> template = {"template_id": "HUMAN_VH3_SCF_01"}
        >>> mark_fallback(template, "ANARCII numbering failed", "numbering", "warning")
        >>> assert template["fallback"] == True
        >>> assert template["fallback_reason"] == "ANARCII numbering failed"
    """
    obj["fallback"] = True
    obj["fallback_reason"] = reason
    obj["fallback_type"] = ftype
    obj["fallback_severity"] = severity
    
    return obj


def is_fallback(obj: Dict[str, Any]) -> bool:
    """
    fallback
    
    Args:
        obj: 
    
    Returns:
        fallback
    """
    return obj.get("fallback", False)


def get_fallback_info(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    fallback
    
    Args:
        obj: 
    
    Returns:
        fallback，fallbackNone
    """
    if not is_fallback(obj):
        return None
    
    return {
        "fallback": True,
        "reason": obj.get("fallback_reason", "Unknown"),
        "type": obj.get("fallback_type", "generic"),
        "severity": obj.get("fallback_severity", "warning"),
    }


















