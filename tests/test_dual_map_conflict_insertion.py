"""
Test dual mapping conflict detection with insertion sites

Tests that:
1. Dual map correctly identifies conflicts when insertions occur
2. Functional sites resolution detects conflicts
3. Status is set to conflict/partial when appropriate
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.numbering.dual_map import build_dual_map, resolve_functional_sites_on_sequence, DualMapError


def test_dual_map_with_insertion_conflict():
    """
    Test dual mapping with insertion conflict (Kabat 52A while IMGT has gap).
    
    Uses monkeypatch to simulate ANARCI output with insertion.
    """
    test_sequence = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAA"
    
    # Mock ANARCI output with insertion in Kabat
    # IMGT numbering: standard positions
    # Kabat numbering: has insertion at position 52 (52A)
    mock_imgt_numbering = [
        ((1, ' '), 'E'),
        ((2, ' '), 'V'),
        ((3, ' '), 'Q'),
        ((37, ' '), 'F'),  # Position 37 exists in IMGT
        ((52, ' '), 'S'),  # Position 52 in IMGT
        # ... more positions
    ]
    
    mock_kabat_numbering = [
        ((1, ' '), 'E'),
        ((2, ' '), 'V'),
        ((3, ' '), 'Q'),
        ((37, ' '), 'F'),  # Position 37 exists in Kabat
        ((52, 'A'), 'S'),  # Position 52A in Kabat (insertion!)
        # ... more positions
    ]
    
    def mock_anarcii_number(seq):
        """Mock ANARCII number method."""
        # Return dict format: {key: {"numbering": [...], "chain_type": "H"}}
        return {
            "Sequence": {
                "numbering": mock_imgt_numbering,
                "chain_type": "H",
                "scheme": "imgt"
            }
        }
    
    def mock_anarcii_to_scheme(scheme):
        """Mock ANARCII to_scheme method."""
        if scheme == "kabat":
            return {
                "Sequence": {
                    "numbering": mock_kabat_numbering,
                    "chain_type": "H",
                    "scheme": "kabat"
                }
            }
        else:
            raise ValueError(f"Unknown scheme: {scheme}")
    
    # Mock Anarcii class and its methods
    with patch('core.numbering.dual_map._get_anarcii_obj') as mock_get_obj:
        mock_obj = MagicMock()
        mock_obj.number = MagicMock(side_effect=mock_anarcii_number)
        mock_obj.to_scheme = MagicMock(side_effect=mock_anarcii_to_scheme)
        mock_get_obj.return_value = mock_obj
        dual_map, status, chain_type = build_dual_map(test_sequence)
        
        # Should detect conflict or partial due to insertion
        assert status in ["conflict", "partial"], f"Expected conflict or partial, got {status}"
        
        # Check for insertion flags
        has_insertion = any("kabat_insertion" in entry.get("flags", []) for entry in dual_map)
        assert has_insertion, "Should detect Kabat insertion"


def test_functional_sites_conflict_detection():
    """Test that functional sites resolution detects conflicts."""
    # Create a dual_map with conflict (IMGT gap, Kabat has position)
    dual_map = [
        {"seq_idx": 0, "aa": "E", "imgt_pos": "1", "kabat_pos": "1", "flags": []},
        {"seq_idx": 36, "aa": "F", "imgt_pos": None, "kabat_pos": "37", "flags": ["imgt_gap"]},  # Conflict!
        {"seq_idx": 37, "aa": "Y", "imgt_pos": "38", "kabat_pos": "38", "flags": []},
    ]
    
    functional_sites = [
        {
            "site_id": "HALLMARK_VHH_37_39",
            "role": "hallmark",
            "imgt_positions": [37, 38, 39],
            "kabat_positions": [37, 38, 39],
            "scope": ["vhh"],
            "notes": "Test site"
        }
    ]
    
    resolved_sites, conflicts = resolve_functional_sites_on_sequence(dual_map, functional_sites)
    
    # Should detect conflict
    assert len(conflicts) > 0, "Should detect conflicts"
    assert any(c["site_id"] == "HALLMARK_VHH_37_39" for c in conflicts), "Should have conflict for hallmark site"
    
    # Check conflict structure
    conflict = conflicts[0]
    assert "site_id" in conflict
    assert "missing_scheme" in conflict
    assert "missing_pos" in conflict
    assert "present_scheme" in conflict
    assert "present_pos" in conflict
    assert "description" in conflict


def test_dual_map_status_classification():
    """Test that dual_map_status is correctly classified."""
    test_sequence = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAA"
    
    try:
        dual_map, status, chain_type = build_dual_map(test_sequence)
        
        # Status should be one of the valid values
        assert status in ["full", "partial", "conflict", "failed"], f"Invalid status: {status}"
        
        # If we got a result, it should not be empty
        if status != "failed":
            assert len(dual_map) > 0, "Dual map should not be empty"
            assert len(dual_map) == len(test_sequence), "Dual map length should match sequence length"
        
    except DualMapError as e:
        # If ANARCII is not available, skip test
        pytest.skip(f"ANARCII not available: {e}")


def test_resolve_sites_with_real_sequence():
    """Test resolving functional sites with a real VHH sequence."""
    # Load functional sites
    sites_file = project_root / "kb" / "10_parameters" / "functional_sites.yaml"
    if not sites_file.exists():
        pytest.skip("Functional sites file not found")
    
    import yaml
    with open(sites_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    functional_sites = data.get('functional_sites', [])
    
    # Use a test sequence
    test_sequence = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAA"
    
    try:
        dual_map, status, chain_type = build_dual_map(test_sequence)
        
        if status == "failed":
            pytest.skip("ANARCI numbering failed")
        
        resolved_sites, conflicts = resolve_functional_sites_on_sequence(dual_map, functional_sites)
        
        # Should resolve at least some sites
        assert len(resolved_sites) > 0, "Should resolve at least some functional sites"
        
        # Check that resolved sites have mapping_status
        for site_id, site_info in resolved_sites.items():
            assert "mapping_status" in site_info
            assert site_info["mapping_status"] in ["full", "partial", "conflict"]
        
    except DualMapError as e:
        pytest.skip(f"ANARCII not available: {e}")


def test_numbering_engine_info_in_reports():
    """Test that numbering_engine info is included in mapping reports."""
    from tools.validate_dual_map_consistency import get_numbering_engine_info, validate_sequence
    from tools.analyze_functional_sites_mapping import analyze_functional_sites_mapping
    from pathlib import Path
    
    # Test get_numbering_engine_info
    engine_info = get_numbering_engine_info()
    assert "name" in engine_info, "numbering_engine must have 'name' field"
    assert engine_info["name"] == "anarcii", "numbering_engine.name must be 'anarcii'"
    assert "version" in engine_info, "numbering_engine must have 'version' field"
    # version can be "unknown" if anarci is not installed, that's OK
    assert "scheme_imgt" in engine_info
    assert "scheme_kabat" in engine_info
    
    # Test validate_sequence includes numbering_engine
    test_sequence = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAA"
    try:
        result = validate_sequence("test_seq", test_sequence)
        assert "numbering_engine" in result, "validate_sequence result must include numbering_engine"
        assert result["numbering_engine"]["name"] == "anarcii", "numbering_engine.name must be 'anarcii'"
    except DualMapError:
        pytest.skip("ANARCI not available")
    
    # Test analyze_functional_sites_mapping includes numbering_engine
    sites_file = project_root / "kb" / "10_parameters" / "functional_sites.yaml"
    if sites_file.exists():
        try:
            result = analyze_functional_sites_mapping(sites_file, test_sequence)
            assert "numbering_engine" in result, "analyze_functional_sites_mapping result must include numbering_engine"
            assert result["numbering_engine"]["name"] == "anarcii", "numbering_engine.name must be 'anarcii'"
        except DualMapError:
            pytest.skip("ANARCI not available")










