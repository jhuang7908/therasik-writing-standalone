"""
（Scaffolds Loader）

，LRUIO
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Any, Optional

# 
from core.utils.config_loader import get_config_lazy as get_config


class ScaffoldLoadError(RuntimeError):
    """"""
    pass


@lru_cache(maxsize=1)
def load_alpaca_vhh_scaffolds() -> List[Dict[str, Any]]:
    """
    VHH scaffold
    
    Returns:
        List[Dict]: scaffold，scaffold_id, n_members, member_ids, consensus
    
    Raises:
        ScaffoldLoadError: 
    """
    cfg = get_config()
    path = cfg.paths.alpaca_scaffolds
    
    if not path.exists():
        raise ScaffoldLoadError(f"scaffold: {path}")
    
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise ScaffoldLoadError(f"scaffold: {e}") from e


@lru_cache(maxsize=1)
def load_human_vh3_scaffolds() -> List[Dict[str, Any]]:
    """
    Human VH3 scaffold
    
    Returns:
        List[Dict]: scaffold
    
    Raises:
        ScaffoldLoadError: 
    """
    cfg = get_config()
    path = cfg.paths.human_scaffolds
    
    if not path.exists():
        raise ScaffoldLoadError(f"Human VH3 scaffold: {path}")
    
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise ScaffoldLoadError(f"Human VH3 scaffold: {e}") from e


@lru_cache(maxsize=1)
def load_clinical_vhh_templates() -> List[Dict[str, Any]]:
    """
     42  VHH  (V2.2 Primary Selector)
    """
    path = Path(__file__).resolve().parents[1] / "data" / "vhh_clinical_39_union" / "vhh42_templates_cache.json"
    if not path.exists():
        return []
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"VHH: {e}")
        return []

@lru_cache(maxsize=1)
def load_clinical_germline_anchors() -> Dict[str, Any]:
    """ germline ADA """
    path = Path(__file__).resolve().parents[1] / "config" / "clinical_germline_anchors.json"
    if not path.exists():
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f).get("anchors", {})
    except Exception:
        return {}

@lru_cache(maxsize=1)
def load_fr3_packing_rule() -> Dict[str, Any]:
    """ FR3 Packing """
    path = Path(__file__).resolve().parents[1] / "data" / "vhh_clinical_39_union" / "vhh_fr3_packing_rule.json"
    if not path.exists():
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

@lru_cache(maxsize=1)
def load_human_vhh_safe_templates() -> List[Dict[str, Any]]:
    """
    [DEPRECATED in V5.0 of VHH_HUMANIZATION_DESIGN_STANDARD — 2026-05-16]

    Loads the 90 synthetic VH3-SAFE templates. In V5.0 of the VHH humanization
    standard, this library is DEPRECATED:
      - Real clinical VHH (n=42, vhh42_templates_cache.json) is the only authorized
        template source.
      - Synthetic VH3-SAFE templates do not reflect real human B-cell repertoire
        and have created repeated developability mismatches.

    By default this loader returns an EMPTY list, breaking the V4.0 fallback path
    in select_human_templates(). The loader can be re-enabled for archival/debug
    purposes via environment variable:

        export ABENGINECORE_ALLOW_VH3_SAFE_LEGACY=1

    Re-enabling it does NOT change the V5.0 standard — the production pipeline
    in vhh_humanization.py will not consume the returned templates unless an
    explicit owner override is added.

    Returns:
        List[Dict]: empty list (V5.0 default) or legacy templates (debug override).

    Raises:
        ScaffoldLoadError: only if legacy override is set and the file is broken.
    """
    import os
    if os.environ.get("ABENGINECORE_ALLOW_VH3_SAFE_LEGACY") != "1":
        import logging
        logging.getLogger(__name__).warning(
            "load_human_vhh_safe_templates() returned [] — VH3-SAFE library "
            "is DEPRECATED in VHH humanization V5.0 (2026-05-16). Set "
            "ABENGINECORE_ALLOW_VH3_SAFE_LEGACY=1 to load for debug only."
        )
        return []

    cfg = get_config()
    path = cfg.paths.human_templates

    if not path.exists():
        raise ScaffoldLoadError(f"Human VHH-SAFE: {path}")

    try:
        with open(path, encoding='utf-8') as f:
            templates = json.load(f)

        # developability defaults (legacy debug only)
        for template in templates:
            if 'developability' not in template:
                template['developability'] = {
                    'score': 0.5,
                    'liabilities': [],
                    'fr2_risk': 0.5,
                    'fr3_risk': 0.5,
                    'notes': 'Not scored',
                }

        return templates
    except Exception as e:
        raise ScaffoldLoadError(f"Human VHH-SAFE: {e}") from e


@lru_cache(maxsize=1)
def load_alignment_matrix() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    ，
    
    Returns:
        Dict:  {alpaca_scaffold_id: {human_template_id: {scores...}}}
    
    Raises:
        ScaffoldLoadError: 
    """
    cfg = get_config()
    path = cfg.paths.alignment_file
    
    if not path.exists():
        raise ScaffoldLoadError(f": {path}")
    
    try:
        with open(path, encoding='utf-8') as f:
            alignments = json.load(f)
        
        # ：alpaca_scaffold -> human_template -> scores
        index = {}
        for align in alignments:
            alpaca_id = align.get('alpaca_scaffold', '')
            human_id = align.get('human_template', '')
            
            if not alpaca_id or not human_id:
                continue
            
            if alpaca_id not in index:
                index[alpaca_id] = {}
            
            index[alpaca_id][human_id] = {
                'framework_identity': align.get('framework_identity', 0),
                'framework_similarity': align.get('framework_similarity', 0),
                'fr1_identity': align.get('fr1_identity', 0),
                'fr2_identity': align.get('fr2_identity', 0),
                'fr3_identity': align.get('fr3_identity', 0),
                'fr2_hydrophobicity_mismatch': align.get('fr2_hydrophobicity_mismatch', 0),
                'vhh_hallmark_score': align.get('vhh_hallmark_score', 0),
            }
        
        return index
    except Exception as e:
        raise ScaffoldLoadError(f": {e}") from e


def clear_cache():
    """（/）"""
    load_alpaca_vhh_scaffolds.cache_clear()
    load_human_vh3_scaffolds.cache_clear()
    load_human_vhh_safe_templates.cache_clear()
    load_alignment_matrix.cache_clear()

