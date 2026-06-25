"""
Template ID Display Normalization
ID：template_id
"""

import re
from typing import Optional


def normalize_template_id_display(template_id: Optional[str]) -> str:
    """
    ID
    
    ：
    -  IMGT ：IGHV1-46*01、IGKV2-28*01
    -  *xx， 2 （ *01），
    -  "-"  "*" 
    - ，
    
    Args:
        template_id: ID
    
    Returns:
        ID
    """
    if not template_id or not isinstance(template_id, str):
        return str(template_id) if template_id is not None else ""
    
    # ，（）
    if "*" in template_id:
        return template_id
    
    # IMGT ：+-*
    # ：IGHV1-46*01、IGKV2-28*01
    
    # 1：， IMGT （+-）
    # ：IGHV1-4601 -> IGHV1-46*01
    # ：IGKV2-2801 -> IGKV2-28*01
    # ： +-+
    imgt_with_allele_pattern = r'^([A-Z]+[0-9]+-[0-9]+)([0-9]{2})$'
    match = re.match(imgt_with_allele_pattern, template_id)
    
    if match:
        # ，
        prefix = match.group(1)  # ：IGHV1-46
        suffix = match.group(2)   # ：01
        return f"{prefix}*{suffix}"
    
    # ，
    return template_id

