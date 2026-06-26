"""
Test functional sites resolution strictness

：
- resolved_residues  position 
-  IMGT 
- 
"""

import pytest
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.numbering.dual_map import resolve_functional_sites_on_sequence


def test_functional_sites_resolution_strictness:
    """
    
    
     egfr_7d12_vhh_dualmap.json ， site  resolved_residues
     position 。
    """
    json_path = project_root / "reports" / "mapping" / "egfr_7d12_vhh_dualmap.json"
    
    if not json_path.exists:
        pytest.skip(f"JSON file not found: {json_path}")
    
    #  JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    dual_map = data.get("dual_map", [])
    resolved_sites = data.get("functional_sites", {}).get("resolved_sites", {})
    
    if not resolved_sites:
        pytest.skip("No resolved_sites in JSON")
    
    #  site 
    for site_id, site_info in resolved_sites.items:
        resolved_residues = site_info.get("resolved_residues", [])
        resolved_imgt_positions = set(
            str(pos) for pos in site_info.get("resolved_imgt_positions", [])
        )
        resolved_kabat_positions = set(
            str(pos) for pos in site_info.get("resolved_kabat_positions", [])
        )
        
        #  1: resolved_residues  residue  imgt_pos  resolved_imgt_positions 
        actual_imgt_pos_set = set(
            str(r["imgt_pos"]) for r in resolved_residues 
            if r.get("imgt_pos") is not None
        )
        
        assert actual_imgt_pos_set.issubset(resolved_imgt_positions), (
            f"Site {site_id}: resolved_residues contains IMGT positions not in resolved_imgt_positions. "
            f"Actual: {actual_imgt_pos_set}, Expected subset of: {resolved_imgt_positions}"
        )
        
        #  2: resolved_residues  residue  kabat_pos  resolved_kabat_positions 
        actual_kabat_pos_set = set(
            str(r["kabat_pos"]) for r in resolved_residues 
            if r.get("kabat_pos") is not None
        )
        
        assert actual_kabat_pos_set.issubset(resolved_kabat_positions), (
            f"Site {site_id}: resolved_residues contains Kabat positions not in resolved_kabat_positions. "
            f"Actual: {actual_kabat_pos_set}, Expected subset of: {resolved_kabat_positions}"
        )
        
        #  3: resolved_residues  resolved_imgt_positions 
        # ( IMGT ， IMGT position  residue)
        assert len(resolved_residues) == len(resolved_imgt_positions), (
            f"Site {site_id}: resolved_residues count ({len(resolved_residues)}) "
            f"should equal resolved_imgt_positions count ({len(resolved_imgt_positions)}) "
            f"when using IMGT as primary anchor"
        )
        
        #  4:  resolved_imgt_position  residue
        imgt_pos_to_residue = {
            str(r["imgt_pos"]): r 
            for r in resolved_residues 
            if r.get("imgt_pos") is not None
        }
        
        for imgt_pos in resolved_imgt_positions:
            assert imgt_pos in imgt_pos_to_residue, (
                f"Site {site_id}: resolved_imgt_position {imgt_pos} has no corresponding residue in resolved_residues"
            )


def test_functional_sites_imgt_primary_anchor:
    """
     IMGT 
    
    ：
    - resolved_residues  IMGT positions  residues
    - resolved_kabat_positions  resolved_residues ，
    """
    json_path = project_root / "reports" / "mapping" / "egfr_7d12_vhh_dualmap.json"
    
    if not json_path.exists:
        pytest.skip(f"JSON file not found: {json_path}")
    
    #  JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    dual_map = data.get("dual_map", [])
    resolved_sites = data.get("functional_sites", {}).get("resolved_sites", {})
    
    if not resolved_sites:
        pytest.skip("No resolved_sites in JSON")
    
    #  IMGT position -> seq_idx 
    imgt_to_seq_idx = {}
    for entry in dual_map:
        if entry.get("imgt_pos"):
            imgt_to_seq_idx[str(entry["imgt_pos"])] = entry["seq_idx"]
            # Also add integer version
            try:
                int_pos = int(entry["imgt_pos"])
                if str(int_pos) not in imgt_to_seq_idx:
                    imgt_to_seq_idx[str(int_pos)] = entry["seq_idx"]
            except ValueError:
                pass
    
    #  site  IMGT 
    for site_id, site_info in resolved_sites.items:
        resolved_residues = site_info.get("resolved_residues", [])
        resolved_imgt_positions = site_info.get("resolved_imgt_positions", [])
        resolved_kabat_positions = site_info.get("resolved_kabat_positions", [])
        
        # ：resolved_residues  residue  resolved_imgt_position
        for residue in resolved_residues:
            imgt_pos = residue.get("imgt_pos")
            assert imgt_pos is not None, (
                f"Site {site_id}: residue at seq_idx {residue.get('seq_idx')} has no imgt_pos"
            )
            
            imgt_pos_str = str(imgt_pos)
            #  resolved_imgt_positions 
            assert (
                imgt_pos_str in resolved_imgt_positions or 
                str(int(imgt_pos)) in resolved_imgt_positions if imgt_pos_str.isdigit else False
            ), (
                f"Site {site_id}: residue with imgt_pos {imgt_pos} not in resolved_imgt_positions {resolved_imgt_positions}"
            )
        
        # ：resolved_kabat_positions  resolved_residues  None  kabat_pos
        expected_kabat_positions = set(
            str(r["kabat_pos"]) for r in resolved_residues 
            if r.get("kabat_pos") is not None
        )
        actual_kabat_positions = set(str(pos) for pos in resolved_kabat_positions)
        
        assert expected_kabat_positions == actual_kabat_positions, (
            f"Site {site_id}: resolved_kabat_positions should be extracted from resolved_residues. "
            f"Expected: {expected_kabat_positions}, Actual: {actual_kabat_positions}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])









