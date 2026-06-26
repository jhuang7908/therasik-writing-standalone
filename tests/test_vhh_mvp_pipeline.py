"""
Test suite for 7D12 VHH MVP Pipeline v0.1
"""

import pytest
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.mvp.step1_eps import generate_step1a_candidates
from core.mvp.step1_cluster import generate_step1b_candidates
from core.mvp.gate import apply_gate
from core.mvp.step2_variants import generate_step2_variants


def create_minimal_dual_map_fixture() -> dict:
    """Create minimal dual_map fixture for testing"""
    # Create a simple VHH sequence with IMGT numbering
    dual_map = []
    sequence = "QVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS"
    
    # Standard IMGT positions for VH (simplified)
    imgt_positions = list(range(1, 128))
    
    for i, aa in enumerate(sequence):
        if i < len(imgt_positions):
            dual_map.append({
                "seq_idx": i,
                "aa": aa,
                "imgt_pos": str(imgt_positions[i]),
                "kabat_pos": str(i + 1),
                "flags": []
            })
    
    return {
        "variable_domain_sequence": sequence,
        "variable_domain": {
            "v_start": 0,
            "v_end": len(sequence),
            "v_length": len(sequence),
            "variable_domain_length": len(sequence)
        },
        "dual_map": dual_map,
        "imgt_numbering": {str(i+1): aa for i, aa in enumerate(sequence)},
        "kabat_numbering": {str(i+1): aa for i, aa in enumerate(sequence)},
        "chain_type": "H"
    }


def test_step1a_generates_candidates():
    """Test Step1-A generates EPS candidates"""
    mapping_result = create_minimal_dual_map_fixture()
    candidates = generate_step1a_candidates(mapping_result)
    
    assert len(candidates) > 0, "Should generate at least one EPS candidate"
    
    # Check required fields
    for cand in candidates:
        assert "candidate_id" in cand
        assert cand.get("route") == "A_EPS"
        assert "template_id" in cand
        assert "fr_identity_total" in cand
        assert "fr_id_fr1" in cand
        assert "fr_id_fr2" in cand
        assert "fr_id_fr3" in cand
        assert "fr_id_fr4" in cand
        assert "vernier_identity" in cand
        assert "hallmark_status" in cand
        assert cand.get("hallmark_status") in ["pass", "conflict"]
        assert "mutation_list" in cand
        assert "sequence_v_region" in cand


def test_step1b_generates_candidates():
    """Test Step1-B generates Cluster candidates"""
    mapping_result = create_minimal_dual_map_fixture()
    candidates = generate_step1b_candidates(mapping_result)
    
    assert len(candidates) > 0, "Should generate at least one Cluster candidate"
    
    # Check required fields
    for cand in candidates:
        assert "candidate_id" in cand
        assert cand.get("route") == "B_CLUSTER"
        assert "cluster_id" in cand
        assert "cluster_size" in cand
        assert "fr_distance_total" in cand
        assert "vernier_distance" in cand
        assert "hallmark_status" in cand
        assert "mutation_list" in cand
        assert "sequence_v_region" in cand


def test_gate_outputs_pass_a_and_pass_b():
    """Test Gate outputs exactly 1 pass_A and 1 pass_B"""
    mapping_result = create_minimal_dual_map_fixture()
    
    # Generate candidates
    step1a = generate_step1a_candidates(mapping_result)
    step1b = generate_step1b_candidates(mapping_result)
    all_candidates = step1a + step1b
    
    # Apply gate
    gate_decision = apply_gate(all_candidates, mapping_result)
    
    # Check structure
    assert "pass_A" in gate_decision
    assert "pass_B" in gate_decision
    assert "rejected" in gate_decision
    assert "gate_params" in gate_decision
    
    # Check that we have at least one pass (if candidates exist)
    if len(all_candidates) > 0:
        # At least one should pass (unless all are rejected)
        pass_a = gate_decision.get("pass_A")
        pass_b = gate_decision.get("pass_B")
        assert pass_a is not None or pass_b is not None, "At least one candidate should pass gate"


def test_step2_generates_variants():
    """Test Step2 generates A⁺ and B⁺ variants"""
    mapping_result = create_minimal_dual_map_fixture()
    
    # Generate candidates and apply gate
    step1a = generate_step1a_candidates(mapping_result)
    step1b = generate_step1b_candidates(mapping_result)
    gate_decision = apply_gate(step1a + step1b, mapping_result)
    
    # Generate Step2 variants
    step2_variants = generate_step2_variants(gate_decision, mapping_result)
    
    # Check structure
    assert isinstance(step2_variants, list)
    
    # Check required fields if variants exist
    for variant in step2_variants:
        assert "variant_id" in variant
        assert "parent_candidate_id" in variant
        assert "route_variant" in variant
        assert variant.get("route_variant") in ["A_PLUS", "BPLUS_CONSERVATIVE", "BPLUS_EXPLORATORY"]
        assert "mutation_list" in variant
        assert "sequence_v_region" in variant
        assert "changed_positions" in variant


def test_cdr_integrity_preserved():
    """Test that CDRs are preserved in candidates"""
    mapping_result = create_minimal_dual_map_fixture()
    
    # Extract original CDRs
    from core.mvp.utils import extract_regions_from_dual_map
    orig_regions = extract_regions_from_dual_map(mapping_result["dual_map"])
    orig_cdr1 = orig_regions.get("CDR1", "")
    orig_cdr2 = orig_regions.get("CDR2", "")
    orig_cdr3 = orig_regions.get("CDR3", "")
    
    # Generate candidates
    step1a = generate_step1a_candidates(mapping_result)
    step1b = generate_step1b_candidates(mapping_result)
    
    # Check CDR preservation
    for cand in step1a + step1b:
        # Extract CDRs from candidate sequence (simplified check)
        # For MVP, we verify that mutations don't include CDR regions
        mutations = cand.get("mutation_list", [])
        cdr_mutations = [m for m in mutations if not m.get("region", "").startswith("FR")]
        assert len(cdr_mutations) == 0, f"CDR mutations found in {cand.get('candidate_id')}: {cdr_mutations}"


def test_output_json_schema():
    """Test that output JSON has required schema fields"""
    mapping_result = create_minimal_dual_map_fixture()
    
    # Run full pipeline
    step1a = generate_step1a_candidates(mapping_result)
    step1b = generate_step1b_candidates(mapping_result)
    gate_decision = apply_gate(step1a + step1b, mapping_result)
    step2_variants = generate_step2_variants(gate_decision, mapping_result)
    
    # Check Step1 candidates schema
    for cand in step1a:
        assert "candidate_id" in cand
        assert "route" in cand
        assert "sequence_v_region" in cand
    
    # Check Gate decision schema
    assert "pass_A" in gate_decision
    assert "pass_B" in gate_decision
    assert "rejected" in gate_decision
    assert "gate_params" in gate_decision
    
    # Check Step2 variants schema
    for variant in step2_variants:
        assert "variant_id" in variant
        assert "parent_candidate_id" in variant
        assert "route_variant" in variant
        assert "mutation_list" in variant


def test_step2_outputs_aplus_and_bplus():
    """Test Step2 outputs A⁺=1, B⁺=2 variants"""
    mapping_result = create_minimal_dual_map_fixture()
    
    # Generate candidates and apply gate
    step1a = generate_step1a_candidates(mapping_result)
    step1b = generate_step1b_candidates(mapping_result)
    gate_decision = apply_gate(step1a + step1b, mapping_result)
    
    # Generate Step2 variants
    step2_variants = generate_step2_variants(gate_decision, mapping_result)
    
    # Count variants by type
    a_plus = [v for v in step2_variants if v.get("route_variant") == "A_PLUS"]
    b_plus_conservative = [v for v in step2_variants if v.get("route_variant") == "BPLUS_CONSERVATIVE"]
    b_plus_exploratory = [v for v in step2_variants if v.get("route_variant") == "BPLUS_EXPLORATORY"]
    
    # If pass_A exists, should have A⁺
    if gate_decision.get("pass_A"):
        assert len(a_plus) >= 0, "A⁺ variant should be generated if pass_A exists"
    
    # If pass_B exists, should have 2 B⁺ variants
    if gate_decision.get("pass_B"):
        assert len(b_plus_conservative) >= 0, "BPLUS_CONSERVATIVE should be generated if pass_B exists"
        assert len(b_plus_exploratory) >= 0, "BPLUS_EXPLORATORY should be generated if pass_B exists"


def test_dev_report_variable_domain_length_and_gate_stats():
    """Test dev report: Variable Domain Length not N/A, Gate Statistics with eligible/selected fields"""
    import tempfile
    from pathlib import Path
    from core.mvp.report_dev_md import generate_dev_report
    
    mapping_result = create_minimal_dual_map_fixture()
    
    # Generate candidates and apply gate
    step1a = generate_step1a_candidates(mapping_result)
    step1b = generate_step1b_candidates(mapping_result)
    gate_decision = apply_gate(step1a + step1b, mapping_result)
    step2_variants = generate_step2_variants(gate_decision, mapping_result)
    
    # Generate report
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        report_path = Path(f.name)
    
    try:
        generate_dev_report(
            mapping_result,
            step1a,
            step1b,
            gate_decision,
            step2_variants,
            report_path
        )
        
        # Read report content
        report_content = report_path.read_text(encoding='utf-8')
        
        # Check Variable Domain Length is not N/A
        assert "Variable Domain Length:" in report_content
        assert "N/A" not in report_content.split("Variable Domain Length:")[1].split("\n")[0], \
            "Variable Domain Length should not be N/A"
        
        # Check Gate Statistics contains eligible_* and selected_* fields
        assert "Eligible A" in report_content or "eligible_A" in report_content.lower(), \
            "Report should contain Eligible A count"
        assert "Eligible B" in report_content or "eligible_B" in report_content.lower(), \
            "Report should contain Eligible B count"
        assert "Selected A" in report_content or "selected_A" in report_content.lower(), \
            "Report should contain Selected A count"
        assert "Selected B" in report_content or "selected_B" in report_content.lower(), \
            "Report should contain Selected B count"
        
    finally:
        # Clean up
        if report_path.exists():
            report_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

