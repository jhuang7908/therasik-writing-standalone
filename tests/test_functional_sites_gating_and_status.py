"""
Test functional sites gating and status validation

：
- Heavy  VL_LAMBDA_ site
- hallmark/vhh sites  full  scheme_shift， conflict
-  site：resolved_residues  IMGT pos  site.imgt_positions
"""

import pytest
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_heavy_chain_no_vl_lambda_sites:
    """
     Heavy  VL_LAMBDA_ site
    
     egfr_7d12_vhh_dualmap.json ， VL_LAMBDA_* 。
    """
    json_path = project_root / "reports" / "mapping" / "egfr_7d12_vhh_dualmap.json"
    
    if not json_path.exists:
        pytest.skip(f"JSON file not found: {json_path}")
    
    #  JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    chain_type = data.get("chain_type", "")
    resolved_sites = data.get("functional_sites", {}).get("resolved_sites", {})
    
    #  chain_type  H
    assert chain_type == "H", f"Expected chain_type 'H', got '{chain_type}'"
    
    #  VL_LAMBDA_* 
    vl_lambda_sites = [site_id for site_id in resolved_sites.keys if site_id.startswith("VL_LAMBDA_")]
    
    assert len(vl_lambda_sites) == 0, (
        f"Heavy chain (chain_type='H') should not contain VL_LAMBDA_ sites. "
        f"Found: {vl_lambda_sites}"
    )


def test_hallmark_vhh_sites_not_all_conflict:
    """
     hallmark/vhh sites  full  scheme_shift， conflict
    
    /。
    """
    json_path = project_root / "reports" / "mapping" / "egfr_7d12_vhh_dualmap.json"
    
    if not json_path.exists:
        pytest.skip(f"JSON file not found: {json_path}")
    
    #  JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    resolved_sites = data.get("functional_sites", {}).get("resolved_sites", {})
    
    #  hallmark  vhh 
    hallmark_sites = []
    vhh_sites = []
    
    for site_id, site_info in resolved_sites.items:
        role = site_info.get("role", "")
        if role == "hallmark":
            hallmark_sites.append(site_info)
        if "VHH" in site_id.upper or site_id.startswith("HALLMARK_") or site_id.startswith("VERNIER_"):
            vhh_sites.append(site_info)
    
    if not hallmark_sites and not vhh_sites:
        pytest.skip("No hallmark or VHH sites found in JSON")
    
    # 
    all_sites = hallmark_sites + vhh_sites
    status_counts = {}
    for site in all_sites:
        status = site.get("mapping_status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    
    total_sites = len(all_sites)
    conflict_count = status_counts.get("conflict", 0)
    full_count = status_counts.get("full", 0)
    scheme_shift_count = status_counts.get("scheme_shift", 0)
    partial_count = status_counts.get("partial", 0)
    
    # ： conflict（/）
    #  full  scheme_shift
    non_conflict_count = full_count + scheme_shift_count + partial_count
    
    assert non_conflict_count > 0 or total_sites == 0, (
        f"All hallmark/VHH sites are in 'conflict' status. "
        f"Total: {total_sites}, Conflicts: {conflict_count}, "
        f"Full: {full_count}, Scheme_shift: {scheme_shift_count}, Partial: {partial_count}. "
        f"This may indicate a problem with mapping_status logic."
    )


def test_resolved_residues_imgt_pos_in_site_positions:
    """
     site  resolved_residues  IMGT pos  site.imgt_positions
    """
    json_path = project_root / "reports" / "mapping" / "egfr_7d12_vhh_dualmap.json"
    
    if not json_path.exists:
        pytest.skip(f"JSON file not found: {json_path}")
    
    #  JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    resolved_sites = data.get("functional_sites", {}).get("resolved_sites", {})
    
    if not resolved_sites:
        pytest.skip("No resolved_sites in JSON")
    
    #  site 
    for site_id, site_info in resolved_sites.items:
        resolved_residues = site_info.get("resolved_residues", [])
        imgt_positions = site_info.get("imgt_positions", [])
        
        #  imgt_positions 
        expected_imgt_pos_set = set(str(pos) for pos in imgt_positions)
        # 
        for pos in imgt_positions:
            try:
                expected_imgt_pos_set.add(str(int(pos)))
            except (ValueError, TypeError):
                pass
        
        # ：resolved_residues  residue  imgt_pos  imgt_positions 
        for residue in resolved_residues:
            imgt_pos = residue.get("imgt_pos")
            if imgt_pos is not None:
                imgt_pos_str = str(imgt_pos)
                #  expected_imgt_pos_set 
                assert (
                    imgt_pos_str in expected_imgt_pos_set or
                    (imgt_pos_str.isdigit and str(int(imgt_pos_str)) in expected_imgt_pos_set)
                ), (
                    f"Site {site_id}: residue with imgt_pos {imgt_pos} not in site's imgt_positions {imgt_positions}. "
                    f"Expected one of: {expected_imgt_pos_set}"
                )


def test_scheme_shift_detection:
    """
     scheme_shift 
    
     IMGT  Kabat （ 37→32）， scheme_shift。
    """
    json_path = project_root / "reports" / "mapping" / "egfr_7d12_vhh_dualmap.json"
    
    if not json_path.exists:
        pytest.skip(f"JSON file not found: {json_path}")
    
    #  JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    resolved_sites = data.get("functional_sites", {}).get("resolved_sites", {})
    
    if not resolved_sites:
        pytest.skip("No resolved_sites in JSON")
    
    #  scheme_shift 
    scheme_shift_sites = [
        (site_id, site_info) 
        for site_id, site_info in resolved_sites.items 
        if site_info.get("mapping_status") == "scheme_shift"
    ]
    
    #  scheme_shift  resolved_residues 
    for site_id, site_info in scheme_shift_sites:
        resolved_residues = site_info.get("resolved_residues", [])
        
        has_scheme_shift = False
        for residue in resolved_residues:
            imgt_pos = residue.get("imgt_pos")
            kabat_pos = residue.get("kabat_pos")
            
            if imgt_pos and kabat_pos:
                # 
                import re
                imgt_num = re.sub(r'[A-Z]$', '', str(imgt_pos))
                kabat_num = re.sub(r'[A-Z]$', '', str(kabat_pos))
                
                if imgt_num != kabat_num:
                    has_scheme_shift = True
                    break
        
        assert has_scheme_shift, (
            f"Site {site_id} is marked as 'scheme_shift' but no numeric difference found "
            f"between IMGT and Kabat positions in resolved_residues."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])









