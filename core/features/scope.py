"""
Chain Scope Gating Module

，。
"""

from typing import List, Optional, Union, Dict


def rule_applies(chain_type: str, chain_scope: Union[List[str], str, None]) -> bool:
    """
    
    
    Args:
        chain_type:  ("H", "K", "L")
        chain_scope: ，：
            - List[str]:  ["vh", "vhh"], ["vl", "vl_kappa"], ["vl_lambda"]
            - str: （）
            - None: （）
    
    Returns:
        True
    
    ：
    - chain_type == "H":  vh / vhh / any / vh_vhh（ vl / vl_kappa / vl_lambda）
    - chain_type == "K":  vl / vl_kappa / any（ vh / vhh / vl_lambda）
    - chain_type == "L":  vl / vl_lambda / any（ vh / vhh / vl_kappa）
    """
    if chain_scope is None:
        return True
    
    #  chain_scope 
    if isinstance(chain_scope, str):
        chain_scope = [chain_scope]
    
    if not isinstance(chain_scope, list) or len(chain_scope) == 0:
        # ，
        return True
    
    #  "any"（）
    if "any" in chain_scope:
        return True
    
    #  chain_type 
    if chain_type == "H":
        # VH/VHH:  vh, vhh, vh_vhh（ vl / vl_kappa / vl_lambda）
        allowed_scopes = ["vh", "vhh", "vh_vhh"]
        forbidden_scopes = ["vl", "vl_kappa", "vl_lambda"]
        
        # ，False
        if any(scope in forbidden_scopes for scope in chain_scope):
            return False
        
        # 
        return any(scope in allowed_scopes for scope in chain_scope)
    
    elif chain_type == "K":
        # VL κ:  vl, vl_kappa（ vh/vhh/vl_lambda）
        allowed_scopes = ["vl", "vl_kappa"]
        forbidden_scopes = ["vh", "vhh", "vl_lambda"]
        
        # ，False
        if any(scope in forbidden_scopes for scope in chain_scope):
            return False
        
        # 
        return any(scope in allowed_scopes for scope in chain_scope)
    
    elif chain_type == "L":
        # VL λ:  vl, vl_lambda（ vh/vhh/vl_kappa）
        allowed_scopes = ["vl", "vl_lambda"]
        forbidden_scopes = ["vh", "vhh", "vl_kappa"]
        
        # ，False
        if any(scope in forbidden_scopes for scope in chain_scope):
            return False
        
        # 
        return any(scope in allowed_scopes for scope in chain_scope)
    
    else:
        #  chain_type，
        return False


def normalize_site_id(site_id: str, chain_type: str, aliases_map: Optional[Dict[str, str]] = None) -> str:
    """
     site_id，（alias/deprecated）
    
    Args:
        site_id:  site_id（ alias）
        chain_type:  ("H", "K", "L")
        aliases_map:  alias -> site_id 
    
    Returns:
         site_id（， alias）
    
    ：
    -  site_id  alias（ aliases_map ）， site_id
    - VL_LAMBDA_* (chain_type="K"): ， VL_GENERIC_*
    - ： site_id  VL_LAMBDA_  chain_type="K"， VL_GENERIC_*
    """
    #  alias
    if aliases_map and site_id in aliases_map:
        site_id = aliases_map[site_id]
    
    #  VL_LAMBDA_* -> VL_GENERIC_* （）
    if chain_type == "K" and site_id.startswith("VL_LAMBDA_"):
        #  VL_LAMBDA_*  VL_GENERIC_*
        site_id = site_id.replace("VL_LAMBDA_", "VL_GENERIC_", 1)
    
    #  VL_KAPPA_* -> VL_GENERIC_* （）
    if chain_type == "L" and site_id.startswith("VL_KAPPA_"):
        #  VL_KAPPA_*  VL_GENERIC_*
        site_id = site_id.replace("VL_KAPPA_", "VL_GENERIC_", 1)
    
    return site_id
