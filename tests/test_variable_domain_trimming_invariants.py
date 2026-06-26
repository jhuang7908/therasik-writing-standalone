"""
Test variable domain trimming invariants

 variable domain trimming  schema/invariant ，
。
， pipeline、action  runtime 。
"""

import pytest
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_dualmap_json(json_path: Path) -> Dict[str, Any]:
    """Load dualmap JSON file without any runtime dependencies."""
    if not json_path.exists:
        pytest.skip(f"JSON file not found: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


def test_variable_domain_field_present:
    """
    ： JSON  variable_domain 
    
     schema 。
    """
    json_path = project_root / "reports" / "mapping" / "pd1_6jbt_mouse_vh_dualmap.json"
    data = load_dualmap_json(json_path)
    
    assert "variable_domain" in data, (
        "Output JSON must contain 'variable_domain' field"
    )


def test_variable_domain_detected_field:
    """
    ：variable_domain.detected 
    
     schema 。
    """
    json_path = project_root / "reports" / "mapping" / "pd1_6jbt_mouse_vh_dualmap.json"
    data = load_dualmap_json(json_path)
    
    variable_domain = data.get("variable_domain", {})
    
    assert "detected" in variable_domain, (
        "variable_domain must contain 'detected' field"
    )
    
    assert isinstance(variable_domain["detected"], bool), (
        f"variable_domain.detected must be boolean, got {type(variable_domain['detected']).__name__}"
    )


def test_variable_domain_trimmed_constant_region_field:
    """
    ：variable_domain.trimmed_constant_region 
    
     schema 。
    """
    json_path = project_root / "reports" / "mapping" / "pd1_6jbt_mouse_vh_dualmap.json"
    data = load_dualmap_json(json_path)
    
    variable_domain = data.get("variable_domain", {})
    
    assert "trimmed_constant_region" in variable_domain, (
        "variable_domain must contain 'trimmed_constant_region' field"
    )
    
    assert isinstance(variable_domain["trimmed_constant_region"], bool), (
        f"variable_domain.trimmed_constant_region must be boolean, "
        f"got {type(variable_domain.get('trimmed_constant_region')).__name__}"
    )


def test_imgt_position_max_limit:
    """
    ： IMGT  128
    
     schema ，。
    """
    json_path = project_root / "reports" / "mapping" / "pd1_6jbt_mouse_vh_dualmap.json"
    data = load_dualmap_json(json_path)
    
    imgt_numbering = data.get("imgt_numbering", {})
    
    if not imgt_numbering:
        pytest.skip("No IMGT numbering found in JSON")
    
    # Extract numeric positions (remove insertion codes like "82C")
    max_position = 0
    for pos_str in imgt_numbering.keys:
        try:
            # Remove insertion codes (e.g., "82C" -> "82")
            pos_num = int(''.join(filter(str.isdigit, pos_str)))
            max_position = max(max_position, pos_num)
        except (ValueError, TypeError):
            continue
    
    assert max_position <= 128, (
        f"Maximum IMGT position ({max_position}) exceeds variable domain limit (128). "
        f"This may indicate constant region was not trimmed."
    )


def test_constant_region_not_numbered:
    """
    ：，
    
     schema 。
     variable_domain.trimmed_constant_region  IMGT 。
    """
    json_path = project_root / "reports" / "mapping" / "pd1_6jbt_mouse_vh_dualmap.json"
    data = load_dualmap_json(json_path)
    
    variable_domain = data.get("variable_domain", {})
    trimmed = variable_domain.get("trimmed_constant_region", False)
    
    if not trimmed:
        pytest.skip("No constant region was trimmed, skipping this test")
    
    imgt_numbering = data.get("imgt_numbering", {})
    
    # If constant region was trimmed, max IMGT position should be <= 128
    max_position = 0
    for pos_str in imgt_numbering.keys:
        try:
            pos_num = int(''.join(filter(str.isdigit, pos_str)))
            max_position = max(max_position, pos_num)
        except (ValueError, TypeError):
            continue
    
    assert max_position <= 128, (
        f"Constant region was trimmed but max IMGT position ({max_position}) > 128. "
        f"This indicates constant region may still be numbered."
    )


def test_variable_domain_indices_present:
    """
    ： trimmed_constant_region  true， v_start  v_end
    
     schema 。
    """
    json_path = project_root / "reports" / "mapping" / "pd1_6jbt_mouse_vh_dualmap.json"
    data = load_dualmap_json(json_path)
    
    variable_domain = data.get("variable_domain", {})
    trimmed = variable_domain.get("trimmed_constant_region", False)
    
    if not trimmed:
        pytest.skip("No constant region was trimmed, skipping index validation")
    
    assert "v_start" in variable_domain, (
        "variable_domain must contain 'v_start' when constant region is trimmed"
    )
    
    assert "v_end" in variable_domain, (
        "variable_domain must contain 'v_end' when constant region is trimmed"
    )
    
    assert isinstance(variable_domain["v_start"], int), (
        f"variable_domain.v_start must be integer, got {type(variable_domain['v_start']).__name__}"
    )
    
    assert isinstance(variable_domain["v_end"], int), (
        f"variable_domain.v_end must be integer, got {type(variable_domain['v_end']).__name__}"
    )
    
    assert variable_domain["v_start"] >= 0, (
        f"variable_domain.v_start must be >= 0, got {variable_domain['v_start']}"
    )
    
    assert variable_domain["v_end"] > variable_domain["v_start"], (
        f"variable_domain.v_end ({variable_domain['v_end']}) must be > v_start ({variable_domain['v_start']})"
    )


def test_detection_method_present:
    """
    ：variable_domain  detection_method 
    
     schema 。
    """
    json_path = project_root / "reports" / "mapping" / "pd1_6jbt_mouse_vh_dualmap.json"
    data = load_dualmap_json(json_path)
    
    variable_domain = data.get("variable_domain", {})
    
    # detection_method is recommended but not strictly required
    if "detection_method" in variable_domain:
        assert isinstance(variable_domain["detection_method"], str), (
            f"variable_domain.detection_method must be string if present, "
            f"got {type(variable_domain['detection_method']).__name__}"
        )


def test_dual_map_only_variable_domain:
    """
    ：dual_map 
    
     schema 。
     variable_domain ，dual_map  seq_idx 。
    """
    json_path = project_root / "reports" / "mapping" / "pd1_6jbt_mouse_vh_dualmap.json"
    data = load_dualmap_json(json_path)
    
    variable_domain = data.get("variable_domain", {})
    dual_map = data.get("dual_map", [])
    
    if not dual_map:
        pytest.skip("No dual_map found in JSON")
    
    start_idx = variable_domain.get("v_start")
    end_idx = variable_domain.get("v_end")
    
    if start_idx is None or end_idx is None:
        pytest.skip("Variable domain indices not provided, cannot validate dual_map range")
    
    out_of_range = []
    for entry in dual_map:
        seq_idx = entry.get("seq_idx")
        if seq_idx is not None:
            if seq_idx < start_idx or seq_idx >= end_idx:
                out_of_range.append({
                    "seq_idx": seq_idx,
                    "imgt_pos": entry.get("imgt_pos"),
                    "kabat_pos": entry.get("kabat_pos")
                })
    
    assert len(out_of_range) == 0, (
        f"dual_map contains residues outside variable domain range [{start_idx}, {end_idx}): {out_of_range}"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])








