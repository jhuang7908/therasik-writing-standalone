"""
Tests for functional_sites.yaml schema validation

Tests that:
1. Valid functional_sites.yaml passes validation
2. Missing required fields are detected
3. Duplicate site_ids are detected
4. Invalid position types are detected
5. Invalid role values are detected
"""

import subprocess
import sys
import tempfile
import pytest
from pathlib import Path
import yaml

# Import validation function
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from tools.validate_functional_sites import validate_functional_sites


def test_valid_functional_sites():
    """Test that valid functional_sites.yaml passes validation."""
    sites_file = project_root / "kb" / "10_parameters" / "functional_sites.yaml"
    
    is_valid, errors, report = validate_functional_sites(sites_file)
    
    assert is_valid, f"Valid file should pass validation. Errors: {errors}"
    assert len(errors) == 0
    # Check that VL_LAMBDA_ sites are detected
    assert "vl_lambda_sites" in report
    # Check that VL_LAMBDA_ sites are skipped when no lambda sequences
    if report["vl_lambda_sites"]:
        assert len(report["skipped_sites"]) > 0
        assert all(s["skipped_reason"] == "no_lambda_sequences_provided" for s in report["skipped_sites"])


def test_vl_lambda_sites_with_lambda_sequences():
    """Test that VL_LAMBDA_* sites are not skipped when lambda sequences are provided."""
    sites_file = project_root / "kb" / "10_parameters" / "functional_sites.yaml"
    
    is_valid, errors, report = validate_functional_sites(sites_file, has_lambda_sequences=True)
    
    assert is_valid, f"Valid file should pass validation. Errors: {errors}"
    # When lambda sequences are provided, VL_LAMBDA_* sites should not be skipped
    if report["vl_lambda_sites"]:
        assert len(report["skipped_sites"]) == 0, "VL_LAMBDA_* sites should not be skipped when lambda sequences are provided"


def test_chain_type_validation():
    """Test that chain_type validation works correctly."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites:
  - site_id: "TEST_SITE"
    role: "hallmark"
    chain_type: "INVALID"  # Invalid chain_type
    light_chain_type: null
    imgt_positions: [37, 38]
    kabat_positions: [37, 38]
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


def test_vl_lambda_site_requirements():
    """Test that VL_LAMBDA_* sites must have chain_type='VL' and light_chain_type='lambda'."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites:
  - site_id: "VL_LAMBDA_TEST"
    role: "vernier"
    chain_type: "VHH"  # Wrong chain_type for VL_LAMBDA_*
    light_chain_type: "lambda"
    imgt_positions: [29, 30]
    kabat_positions: [29, 30]
    scope: [vl]
    notes: "Test VL-λ site"
""")
        tmp_file_path = Path(tmp_file.name)
    
    try:
        is_valid, errors, _ = validate_functional_sites(tmp_file_path)
        
        assert not is_valid, "VL_LAMBDA_* site with wrong chain_type should fail validation"
        assert any("must have chain_type='VL'" in error for error in errors)
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()


def test_light_chain_type_validation():
    """Test that light_chain_type validation works correctly."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites:
  - site_id: "TEST_SITE"
    role: "hallmark"
    chain_type: "VHH"
    light_chain_type: "invalid"  # Invalid light_chain_type
    imgt_positions: [37, 38]
    kabat_positions: [37, 38]
    scope: [vhh]
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


def test_validate_functional_sites_script():
    """Test that validation script runs successfully on valid file."""
    script_path = project_root / "tools" / "validate_functional_sites.py"
    sites_file = project_root / "kb" / "10_parameters" / "functional_sites.yaml"
    
    if not sites_file.exists():
        pytest.skip(f"Functional sites file not found: {sites_file}")
    
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        cwd=project_root
    )
    
    assert result.returncode == 0, f"Validation should pass. Output: {result.stdout}\nErrors: {result.stderr}"
    assert "✅ All validations passed!" in result.stdout


def test_missing_required_field():
    """Test that missing required fields are detected."""
    # Create a temporary file with missing field
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites:
  - site_id: "TEST_SITE"
    role: "hallmark"
    imgt_positions: [37, 38]
    # Missing kabat_positions
    scope: [vhh]
    notes: "Test site"
""")
        tmp_file_path = Path(tmp_file.name)
    
    try:
        is_valid, errors, _ = validate_functional_sites(tmp_file_path)
        
        assert not is_valid, "Missing required field should fail validation"
        assert any("kabat_positions" in error.lower() for error in errors)
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()


def test_duplicate_site_id():
    """Test that duplicate site_ids are detected."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites:
  - site_id: "DUPLICATE_ID"
    role: "hallmark"
    imgt_positions: [37, 38]
    kabat_positions: [37, 38]
    scope: [vhh]
    notes: "First site"
  - site_id: "DUPLICATE_ID"
    role: "vernier"
    imgt_positions: [29, 30]
    kabat_positions: [29, 30]
    scope: [vhh]
    notes: "Second site with same ID"
""")
        tmp_file_path = Path(tmp_file.name)
    
    try:
        is_valid, errors, _ = validate_functional_sites(tmp_file_path)
        
        assert not is_valid, "Duplicate site_id should fail validation"
        assert any("duplicate" in error.lower() for error in errors)
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()


def test_invalid_position_type():
    """Test that invalid position types are detected."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites:
  - site_id: "TEST_SITE"
    role: "hallmark"
    imgt_positions: [37, "invalid", 39]  # String instead of int
    kabat_positions: [37, 38, 39]
    scope: [vhh]
    notes: "Test site"
""")
        tmp_file_path = Path(tmp_file.name)
    
    try:
        is_valid, errors, _ = validate_functional_sites(tmp_file_path)
        
        assert not is_valid, "Invalid position type should fail validation"
        assert any("integer" in error.lower() for error in errors)
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()


def test_invalid_role():
    """Test that invalid role values are detected."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites:
  - site_id: "TEST_SITE"
    role: "invalid_role"  # Invalid role
    imgt_positions: [37, 38]
    kabat_positions: [37, 38]
    scope: [vhh]
    notes: "Test site"
""")
        tmp_file_path = Path(tmp_file.name)
    
    try:
        is_valid, errors, _ = validate_functional_sites(tmp_file_path)
        
        assert not is_valid, "Invalid role should fail validation"
        assert any("invalid 'role'" in error.lower() for error in errors)
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()


def test_position_out_of_range():
    """Test that positions out of valid range are detected."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites:
  - site_id: "TEST_SITE"
    role: "hallmark"
    imgt_positions: [200]  # Out of range
    kabat_positions: [37, 38]
    scope: [vhh]
    notes: "Test site"
""")
        tmp_file_path = Path(tmp_file.name)
    
    try:
        is_valid, errors, _ = validate_functional_sites(tmp_file_path)
        
        assert not is_valid, "Position out of range should fail validation"
        assert any("out of valid range" in error.lower() for error in errors)
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()


def test_non_list_positions():
    """Test that positions must be lists."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites:
  - site_id: "TEST_SITE"
    role: "hallmark"
    imgt_positions: 37  # Should be a list
    kabat_positions: [37, 38]
    scope: [vhh]
    notes: "Test site"
""")
        tmp_file_path = Path(tmp_file.name)
    
    try:
        is_valid, errors, _ = validate_functional_sites(tmp_file_path)
        
        assert not is_valid, "Positions must be lists"
        assert any("must be a list" in error.lower() for error in errors)
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()


def test_empty_functional_sites():
    """Test that empty functional_sites list is detected."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as tmp_file:
        tmp_file.write("""functional_sites: []
""")
        tmp_file_path = Path(tmp_file.name)
    
    try:
        is_valid, errors, _ = validate_functional_sites(tmp_file_path)
        
        assert not is_valid, "Empty functional_sites list should fail validation"
        assert any("empty" in error.lower() for error in errors)
    finally:
        if tmp_file_path.exists():
            tmp_file_path.unlink()










