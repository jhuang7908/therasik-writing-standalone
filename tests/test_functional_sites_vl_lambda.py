"""
Tests for VL-λ (lambda light chain) functional sites support

Tests that:
1. VL_LAMBDA_* sites are allowed in functional_sites.yaml
2. VL_LAMBDA_* sites are skipped from mapping_status if no λ sequences provided
3. chain_type and light_chain_type fields are validated correctly
"""

import sys
import tempfile
import pytest
from pathlib import Path
import yaml

# Import validation function
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from tools.validate_functional_sites import validate_functional_sites


def test_vl_lambda_sites_allowed():
    """Test that VL_LAMBDA_* sites are allowed in functional_sites.yaml."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites:
  - site_id: "VL_LAMBDA_VERNIER_29_30"
    role: "vernier"
    chain_type: "VL"
    light_chain_type: "lambda"
    imgt_positions: [29, 30]
    kabat_positions: [29, 30]
    imgt_anchor_positions: [29, 30]
    needs_calibration: true
    scope: [vl]
    notes: "VL-λ vernier zone"
""")
        tmp_file_path = Path(tmp_file.name)
    
    try:
        is_valid, errors, report = validate_functional_sites(tmp_file_path)
        
        assert is_valid, f"VL_LAMBDA_* sites should be allowed. Errors: {errors}"
        assert len(errors) == 0
        assert "VL_LAMBDA_VERNIER_29_30" in report["vl_lambda_sites"]
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()


def test_vl_lambda_sites_skipped_without_lambda_sequences():
    """Test that VL_LAMBDA_* sites are skipped if no λ sequences provided."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites:
  - site_id: "VL_LAMBDA_VERNIER_29_30"
    role: "vernier"
    chain_type: "VL"
    light_chain_type: "lambda"
    imgt_positions: [29, 30]
    kabat_positions: [29, 30]
    scope: [vl]
    notes: "VL-λ vernier zone"
""")
        tmp_file_path = Path(tmp_file.name)
    
    try:
        # Without lambda sequences
        is_valid, errors, report = validate_functional_sites(tmp_file_path, has_lambda_sequences=False)
        
        assert is_valid
        assert len(report["skipped_sites"]) > 0
        assert any(s["skipped_reason"] == "no_lambda_sequences_provided" for s in report["skipped_sites"])
        
        # With lambda sequences
        is_valid2, errors2, report2 = validate_functional_sites(tmp_file_path, has_lambda_sequences=True)
        
        assert is_valid2
        assert len(report2["skipped_sites"]) == 0  # Should not be skipped if λ sequences provided
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()


def test_chain_type_validation():
    """Test that chain_type field is validated correctly."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites:
  - site_id: "TEST_SITE"
    role: "vernier"
    chain_type: "INVALID"  # Invalid chain_type
    light_chain_type: null
    imgt_positions: [29, 30]
    kabat_positions: [29, 30]
    scope: [vhh]
    notes: "Test site"
""")
        tmp_file_path = Path(tmp_file.name)
    
    try:
        is_valid, errors, _ = validate_functional_sites(tmp_file_path)
        
        assert not is_valid, "Invalid chain_type should fail validation"
        assert any("invalid 'chain_type'" in error.lower() for error in errors)
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()


def test_light_chain_type_validation():
    """Test that light_chain_type field is validated correctly."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites:
  - site_id: "TEST_SITE"
    role: "vernier"
    chain_type: "VL"
    light_chain_type: "invalid"  # Invalid light_chain_type
    imgt_positions: [29, 30]
    kabat_positions: [29, 30]
    scope: [vl]
    notes: "Test site"
""")
        tmp_file_path = Path(tmp_file.name)
    
    try:
        is_valid, errors, _ = validate_functional_sites(tmp_file_path)
        
        assert not is_valid, "Invalid light_chain_type should fail validation"
        assert any("invalid 'light_chain_type'" in error.lower() for error in errors)
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()


def test_imgt_anchor_positions_validation():
    """Test that imgt_anchor_positions field is validated correctly."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites:
  - site_id: "VL_LAMBDA_TEST"
    role: "vernier"
    chain_type: "VL"
    light_chain_type: "lambda"
    imgt_positions: [29, 30]
    kabat_positions: [29, 30]
    imgt_anchor_positions: "invalid"  # Should be a list
    scope: [vl]
    notes: "Test site"
""")
        tmp_file_path = Path(tmp_file.name)
    
    try:
        is_valid, errors, _ = validate_functional_sites(tmp_file_path)
        
        assert not is_valid, "imgt_anchor_positions must be a list"
        assert any("imgt_anchor_positions" in error.lower() and "list" in error.lower() for error in errors)
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()


def test_needs_calibration_validation():
    """Test that needs_calibration field is validated correctly."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites:
  - site_id: "VL_LAMBDA_TEST"
    role: "vernier"
    chain_type: "VL"
    light_chain_type: "lambda"
    imgt_positions: [29, 30]
    kabat_positions: [29, 30]
    needs_calibration: "yes"  # Should be boolean
    scope: [vl]
    notes: "Test site"
""")
        tmp_file_path = Path(tmp_file.name)
    
    try:
        is_valid, errors, _ = validate_functional_sites(tmp_file_path)
        
        assert not is_valid, "needs_calibration must be a boolean"
        assert any("needs_calibration" in error.lower() and "boolean" in error.lower() for error in errors)
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()
