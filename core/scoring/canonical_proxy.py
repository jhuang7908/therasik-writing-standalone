#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Canonical Proxy Scoring Module

 canonical_proxy ， scaffold/germline 。
"""

from __future__ import annotations

from typing import Dict, Any, Literal, Optional


def canonical_proxy_agg(
    record_or_features: Dict[str, Any],
    mode: Literal["min", "mean"] = "min",
) -> float:
    """
     CDR canonical 
    
    Args:
        record_or_features: germline  canonical_proxy 
            -  `canonical_proxy_cdr1`  `canonical_proxy_cdr2`，
            -  `proxy_cdr1`  `proxy_cdr2`，
        mode: 
            - "min": （，）
            - "mean": 
    
    Returns:
        canonical_proxy_agg (0.0-1.0)
    """
    #  proxy scores
    proxy_cdr1 = None
    proxy_cdr2 = None
    
    # 1:  canonical_proxy_cdr1/cdr2 
    if "canonical_proxy_cdr1" in record_or_features:
        cdr1_proxy = record_or_features.get("canonical_proxy_cdr1", {})
        if isinstance(cdr1_proxy, dict):
            proxy_cdr1 = cdr1_proxy.get("proxy_score")
    
    if "canonical_proxy_cdr2" in record_or_features:
        cdr2_proxy = record_or_features.get("canonical_proxy_cdr2", {})
        if isinstance(cdr2_proxy, dict):
            proxy_cdr2 = cdr2_proxy.get("proxy_score")
    
    # 2:  proxy_cdr1/cdr2 
    if proxy_cdr1 is None:
        proxy_cdr1 = record_or_features.get("proxy_cdr1")
    if proxy_cdr2 is None:
        proxy_cdr2 = record_or_features.get("proxy_cdr2")
    
    # 
    if proxy_cdr1 is None or proxy_cdr2 is None:
        return 0.0
    
    #  float
    try:
        proxy_cdr1 = float(proxy_cdr1)
        proxy_cdr2 = float(proxy_cdr2)
    except (ValueError, TypeError):
        return 0.0
    
    # 
    if mode == "min":
        return min(proxy_cdr1, proxy_cdr2)
    elif mode == "mean":
        return (proxy_cdr1 + proxy_cdr2) / 2.0
    else:
        raise ValueError(f"Unknown mode: {mode}. Must be 'min' or 'mean'.")


def canonical_proxy_score_breakdown(
    record_or_features: Dict[str, Any],
    mode: Literal["min", "mean"] = "min",
) -> Dict[str, Any]:
    """
     canonical_proxy （）
    
    Args:
        record_or_features: germline  canonical_proxy 
        mode: 
    
    Returns:
        {
            "proxy_cdr1": float,
            "proxy_cdr2": float,
            "proxy_agg": float,
            "agg_mode": str,
            "explanation": str,
        }
    """
    #  proxy scores
    proxy_cdr1 = None
    proxy_cdr2 = None
    
    if "canonical_proxy_cdr1" in record_or_features:
        cdr1_proxy = record_or_features.get("canonical_proxy_cdr1", {})
        if isinstance(cdr1_proxy, dict):
            proxy_cdr1 = cdr1_proxy.get("proxy_score")
    
    if "canonical_proxy_cdr2" in record_or_features:
        cdr2_proxy = record_or_features.get("canonical_proxy_cdr2", {})
        if isinstance(cdr2_proxy, dict):
            proxy_cdr2 = cdr2_proxy.get("proxy_score")
    
    if proxy_cdr1 is None:
        proxy_cdr1 = record_or_features.get("proxy_cdr1", 0.0)
    if proxy_cdr2 is None:
        proxy_cdr2 = record_or_features.get("proxy_cdr2", 0.0)
    
    try:
        proxy_cdr1 = float(proxy_cdr1)
        proxy_cdr2 = float(proxy_cdr2)
    except (ValueError, TypeError):
        proxy_cdr1 = 0.0
        proxy_cdr2 = 0.0
    
    # 
    proxy_agg = canonical_proxy_agg(record_or_features, mode=mode)
    
    # 
    if mode == "min":
        explanation = f"CDR canonical  = min({proxy_cdr1:.4f}, {proxy_cdr2:.4f}) = {proxy_agg:.4f}（： loop /）"
    else:
        explanation = f"CDR canonical  = mean({proxy_cdr1:.4f}, {proxy_cdr2:.4f}) = {proxy_agg:.4f}"
    
    return {
        "proxy_cdr1": round(proxy_cdr1, 4),
        "proxy_cdr2": round(proxy_cdr2, 4),
        "proxy_agg": round(proxy_agg, 4),
        "agg_mode": mode,
        "explanation": explanation,
    }


def apply_canonical_proxy_to_score(
    candidate: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
     canonical_proxy  scaffold 
    
    Args:
        candidate: scaffold ， canonical_proxy 
        config: ，：
            - enabled: bool ( True)
            - agg_mode: "min" | "mean" ( "min")
            - weight: float ( 0.10)
            - floor_if_missing: float ( 0.0)
    
    Returns:
         candidate ，：
            - score_components["canonical_proxy"]: float
            - total_score: 
    """
    # 
    if config is None:
        config = {
            "enabled": True,
            "agg_mode": "min",
            "weight": 0.10,
            "floor_if_missing": 0.0,
        }
    
    enabled = config.get("enabled", True)
    if not enabled:
        return candidate
    
    #  canonical_proxy_agg
    agg_mode = config.get("agg_mode", "min")
    proxy_agg = canonical_proxy_agg(candidate, mode=agg_mode)
    
    # ， floor
    if proxy_agg == 0.0 and config.get("floor_if_missing", 0.0) > 0.0:
        proxy_agg = config["floor_if_missing"]
    
    #  score_components
    if "score_components" not in candidate:
        candidate["score_components"] = {}
    
    #  canonical_proxy 
    candidate["score_components"]["canonical_proxy"] = proxy_agg
    
    # 
    weight = config.get("weight", 0.10)
    old_total_score = candidate.get("total_score", 0.0)
    new_total_score = old_total_score + weight * proxy_agg
    
    candidate["total_score"] = new_total_score
    
    # （）
    if "total_score_old" not in candidate:
        candidate["total_score_old"] = old_total_score
    
    return candidate













