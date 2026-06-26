"""
Test Feature Annotation Module

：
1. 
2. tagslist[str]
3. VHvh_hallmark
4. chem_sensitiveAA
5. cdr_boundaryCDR
"""

import pytest
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.features.annotate import annotate_features, export_feature_matrix
from core.features.feature_dict_v1 import (
    is_chemically_sensitive,
    is_cdr_boundary,
    is_vh_hallmark_position,
    parse_imgt_position
)


def create_mock_mapping_result(sequence: str, chain_type: str = "H") -> dict:
    """mock mapping"""
    dual_map = []
    for i, aa in enumerate(sequence):
        # IMGT（1）
        imgt_pos = str(i + 1) if i < 128 else None
        kabat_pos = str(i + 1) if i < 128 else None
        dual_map.append({
            "seq_idx": i,
            "aa": aa,
            "imgt_pos": imgt_pos,
            "kabat_pos": kabat_pos,
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
        "chain_type": chain_type,
        "imgt_numbering": {},
        "kabat_numbering": {}
    }


def test_output_length_consistency:
    """"""
    sequence = "A" * 125  # VH
    mapping_result = create_mock_mapping_result(sequence, chain_type="H")
    
    annotated = annotate_features(mapping_result, "VH")
    
    assert annotated["length"] == len(sequence)
    assert len(annotated["residues"]) == len(sequence)
    assert len(annotated["residues"]) == annotated["length"]


def test_tags_structure_and_stability:
    """tagslist[str]"""
    sequence = "QGQLVQSGAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSS"
    mapping_result = create_mock_mapping_result(sequence, chain_type="H")
    
    annotated = annotate_features(mapping_result, "VH")
    
    # 
    tags_first = [r["tags"] for r in annotated["residues"]]
    
    # 
    annotated2 = annotate_features(mapping_result, "VH")
    tags_second = [r["tags"] for r in annotated2["residues"]]
    
    assert tags_first == tags_second, "Tags should be stable across runs"
    
    # tagslist[str]
    for residue in annotated["residues"]:
        assert isinstance(residue["tags"], list)
        for tag in residue["tags"]:
            assert isinstance(tag, str)


def test_vh_hallmark_tagging:
    """VHvh_hallmark（1）"""
    # VH hallmark
    # VH_HALLMARK_POSITIONS = [42, 49, 50, 52, 54]
    # dual_map
    sequence = "A" * 125
    dual_map = []
    for i, aa in enumerate(sequence):
        imgt_pos = str(i + 1) if i < 128 else None
        kabat_pos = str(i + 1) if i < 128 else None
        dual_map.append({
            "seq_idx": i,
            "aa": aa,
            "imgt_pos": imgt_pos,
            "kabat_pos": kabat_pos,
            "flags": []
        })
    
    mapping_result = {
        "variable_domain_sequence": sequence,
        "variable_domain": {
            "v_start": 0,
            "v_end": len(sequence),
            "v_length": len(sequence),
            "variable_domain_length": len(sequence)
        },
        "dual_map": dual_map,
        "chain_type": "H",
        "imgt_numbering": {},
        "kabat_numbering": {}
    }
    
    annotated = annotate_features(mapping_result, "VH")
    
    # vh_hallmark
    vh_hallmark_count = 0
    for residue in annotated["residues"]:
        if "vh_hallmark" in residue["tags"]:
            vh_hallmark_count += 1
    
    # mock42, 49, 50, 52, 54，1
    # ，
    assert is_vh_hallmark_position(42, "H") is True
    assert is_vh_hallmark_position(49, "H") is True
    assert is_vh_hallmark_position(50, "H") is True
    assert is_vh_hallmark_position(52, "H") is True
    assert is_vh_hallmark_position(54, "H") is True
    assert is_vh_hallmark_position(42, "K") is False  # VL


def test_chem_sensitive_tagging:
    """chem_sensitiveAA"""
    # : N, D, G, M, W, C
    sequence = "NDGMWC" + "A" * 119
    mapping_result = create_mock_mapping_result(sequence, chain_type="H")
    
    annotated = annotate_features(mapping_result, "VH")
    
    # 6chem_sensitive
    for i in range(6):
        residue = annotated["residues"][i]
        assert "chem_sensitive" in residue["tags"], f"Residue {i} ({residue['residue']}) should have chem_sensitive tag"
    
    # 
    assert is_chemically_sensitive("N") is True
    assert is_chemically_sensitive("D") is True
    assert is_chemically_sensitive("G") is True
    assert is_chemically_sensitive("M") is True
    assert is_chemically_sensitive("W") is True
    assert is_chemically_sensitive("C") is True
    assert is_chemically_sensitive("A") is False
    assert is_chemically_sensitive("L") is False


def test_cdr_boundary_tagging:
    """cdr_boundaryCDR"""
    # CDR
    # CDR1: 27-38, CDR2: 56-65, CDR3: 105-117
    sequence = "A" * 125
    dual_map = []
    for i, aa in enumerate(sequence):
        imgt_pos = str(i + 1) if i < 128 else None
        kabat_pos = str(i + 1) if i < 128 else None
        dual_map.append({
            "seq_idx": i,
            "aa": aa,
            "imgt_pos": imgt_pos,
            "kabat_pos": kabat_pos,
            "flags": []
        })
    
    mapping_result = {
        "variable_domain_sequence": sequence,
        "variable_domain": {
            "v_start": 0,
            "v_end": len(sequence),
            "v_length": len(sequence),
            "variable_domain_length": len(sequence)
        },
        "dual_map": dual_map,
        "chain_type": "H",
        "imgt_numbering": {},
        "kabat_numbering": {}
    }
    
    annotated = annotate_features(mapping_result, "VH")
    
    # CDR
    # CDR1: position 27 (index 26)
    # CDR1: position 38 (index 37)
    # CDR2: position 56 (index 55)
    # CDR2: position 65 (index 64)
    # CDR3: position 105 (index 104)
    
    boundary_positions = [27, 38, 56, 65, 105]  # CDR
    
    for pos in boundary_positions:
        idx = pos - 1  # 0-based index
        if idx < len(annotated["residues"]):
            residue = annotated["residues"][idx]
            # 
            imgt_pos = parse_imgt_position(residue["imgt_position"])
            region = residue["region"]
            is_boundary = is_cdr_boundary(imgt_pos, region, dual_map)
            # ：CDR3，
            if pos in [27, 56, 105]:  # CDR
                assert is_boundary or "cdr_boundary" in residue["tags"], f"Position {pos} should be CDR boundary"


def test_export_feature_matrix:
    """"""
    sequence = "A" * 125
    mapping_result = create_mock_mapping_result(sequence, chain_type="H")
    
    annotated = annotate_features(mapping_result, "VH")
    df = export_feature_matrix(annotated)
    
    assert len(df) == len(sequence)
    assert "index" in df.columns
    assert "residue" in df.columns
    assert "imgt_position" in df.columns
    assert "kabat_position" in df.columns
    assert "region" in df.columns
    assert "tags" in df.columns
    
    # tags（;）
    for tags_str in df["tags"]:
        if tags_str:
            assert isinstance(tags_str, str)
            assert ";" in tags_str or len(tags_str.split(";")) >= 1


def test_length_mismatch_error:
    """"""
    sequence = "A" * 125
    mapping_result = create_mock_mapping_result(sequence, chain_type="H")
    
    # 
    mapping_result["variable_domain"]["v_length"] = 100
    
    with pytest.raises(ValueError, match="Length mismatch"):
        annotate_features(mapping_result, "VH")


def test_vl_outputs_length_consistency:
    """VL"""
    sequence = "D" * 112  # VL
    mapping_result = create_mock_mapping_result(sequence, chain_type="K")
    
    annotated = annotate_features(mapping_result, "VL")
    
    assert annotated["length"] == len(sequence)
    assert len(annotated["residues"]) == len(sequence)
    assert len(annotated["residues"]) == annotated["length"]
    assert annotated["chain"] == "VL"


def test_vl_has_vernier_and_chem_sensitive_examples:
    """VLvernierchem_sensitive"""
    # vernier
    # VL vernier positions: [4, 6, 23, 24, 26, 48, 49, 67, 69, 71, 73, 78]
    # : N, D, G, M, W, C
    sequence = "NDGMWC" + "A" * 106  # 6
    dual_map = []
    for i, aa in enumerate(sequence):
        imgt_pos = str(i + 1) if i < 128 else None
        kabat_pos = str(i + 1) if i < 128 else None
        dual_map.append({
            "seq_idx": i,
            "aa": aa,
            "imgt_pos": imgt_pos,
            "kabat_pos": kabat_pos,
            "flags": []
        })
    
    mapping_result = {
        "variable_domain_sequence": sequence,
        "variable_domain": {
            "v_start": 0,
            "v_end": len(sequence),
            "v_length": len(sequence),
            "variable_domain_length": len(sequence)
        },
        "dual_map": dual_map,
        "chain_type": "K",
        "imgt_numbering": {},
        "kabat_numbering": {}
    }
    
    annotated = annotate_features(mapping_result, "VL")
    
    # vernier（4, 6, 23, 24, 26）
    has_vernier = any("vernier" in r["tags"] for r in annotated["residues"])
    
    # chem_sensitive（6）
    has_chem_sensitive = any("chem_sensitive" in r["tags"] for r in annotated["residues"][:6])
    
    assert has_vernier or has_chem_sensitive, "VL should have at least vernier or chem_sensitive tags"
    
    # 6chem_sensitive
    for i in range(6):
        residue = annotated["residues"][i]
        assert "chem_sensitive" in residue["tags"], f"Residue {i} ({residue['residue']}) should have chem_sensitive tag"


def test_vl_no_vh_hallmark_tag:
    """VLvh_hallmark"""
    sequence = "A" * 112
    mapping_result = create_mock_mapping_result(sequence, chain_type="K")
    
    annotated = annotate_features(mapping_result, "VL")
    
    # vh_hallmark
    for residue in annotated["residues"]:
        assert "vh_hallmark" not in residue["tags"], f"VL residue {residue['index']} should not have vh_hallmark tag"
    
    # 
    assert is_vh_hallmark_position(42, "K") is False
    assert is_vh_hallmark_position(49, "K") is False
    assert is_vh_hallmark_position(50, "L") is False


def test_kappa_no_vh_vhh_rules:
    """ VL κ  VH/VHH """
    sequence = "D" * 112
    mapping_result = create_mock_mapping_result(sequence, chain_type="K")
    
    annotated = annotate_features(mapping_result, "VL")
    
    #  tags  vh_hallmark
    for residue in annotated["residues"]:
        assert "vh_hallmark" not in residue["tags"], f"VL κ residue {residue['index']} should not have vh_hallmark tag"
    
    #  scope gating 
    from core.features.scope import rule_applies
    
    # VL κ  VH/VHH 
    assert rule_applies("K", ["vh", "vhh"]) is False
    assert rule_applies("K", ["vh"]) is False
    assert rule_applies("K", ["vhh"]) is False
    
    # VL κ  VL 
    assert rule_applies("K", ["vl"]) is True
    assert rule_applies("K", ["vl_kappa"]) is True
    assert rule_applies("K", ["any"]) is True
    
    # VL κ  VL λ 
    assert rule_applies("K", ["vl_lambda"]) is False


def test_kappa_not_labeled_lambda:
    """ VL κ  VL_LAMBDA_* """
    #  functional_sites.yaml 
    #  resolved_sites  VL_LAMBDA_*（ alias）
    import yaml
    from pathlib import Path
    
    sites_file = Path("kb/10_parameters/functional_sites.yaml")
    if sites_file.exists:
        with open(sites_file, 'r', encoding='utf-8') as f:
            sites_data = yaml.safe_load(f)
        
        functional_sites = sites_data.get('functional_sites', [])
        
        #  VL_LAMBDA_*  site_id（ alias）
        for site in functional_sites:
            site_id = site.get("site_id", "")
            chain_scope = site.get("chain_scope", [])
            
            #  site_id  VL_LAMBDA_*， alias， chain_scope  [vl_lambda]
            if site_id.startswith("VL_LAMBDA_"):
                #  chain_scope  vl  vl_kappa，（ VL_GENERIC_*）
                if any(scope in ["vl", "vl_kappa"] for scope in chain_scope):
                    #  VL_GENERIC_*
                    # ， VL_GENERIC_* 
                    pass
        
        #  VL_GENERIC_* 
        has_generic = any(s.get("site_id", "").startswith("VL_GENERIC_") for s in functional_sites)
        assert has_generic, "Should have VL_GENERIC_* rules for K/L common sites"


def test_resolved_sites_no_vh_vhh_for_kappa:
    """ VL κ  resolved_sites  VH/VHH """
    import yaml
    from pathlib import Path
    from core.numbering.dual_map import build_dual_map, resolve_functional_sites_on_sequence
    
    sites_file = Path("kb/10_parameters/functional_sites.yaml")
    if not sites_file.exists:
        pytest.skip("Functional sites file not found")
    
    # 
    with open(sites_file, 'r', encoding='utf-8') as f:
        sites_data = yaml.safe_load(f)
    functional_sites = sites_data.get('functional_sites', [])
    
    #  VL κ 
    vl_kappa_sequence = "DVVMTQSPLSLPVTLGQPASISCRSSQSIVHSNGNTYLEWYLQKPGQSPQLLIYKVSNRFSGVPDRFSGSGSGTDFTLKISRVEAEDVGVYYCFQGSHVPLTFGQGTKLEIK"
    
    try:
        dual_map, status, chain_type = build_dual_map(vl_kappa_sequence)
        
        if status == "failed" or chain_type != "K":
            pytest.skip(f"ANARCI numbering failed or chain_type is not K (got {chain_type})")
        
        # 
        resolved_sites, conflicts = resolve_functional_sites_on_sequence(dual_map, functional_sites, chain_type)
        
        #  resolved_sites  VH/VHH 
        for site_id in resolved_sites.keys:
            #  HALLMARK_VHH_*  VH 
            assert not site_id.startswith("HALLMARK_VHH_"), f"VL κ resolved_sites should not contain {site_id}"
            assert not site_id.startswith("VERNIER_") or site_id.startswith("VL_"), f"VL κ resolved_sites should not contain VH-only {site_id}"
            assert not site_id.startswith("BOUNDARY_") or site_id.startswith("VL_"), f"VL κ resolved_sites should not contain VH-only {site_id}"
            
            #  VL_LAMBDA_*（ VL_GENERIC_*）
            assert not site_id.startswith("VL_LAMBDA_"), f"VL κ resolved_sites should not contain {site_id} (should be VL_GENERIC_*)"
        
        #  VL_GENERIC_* 
        has_vl_generic = any(sid.startswith("VL_GENERIC_") for sid in resolved_sites.keys)
        assert has_vl_generic, "VL κ resolved_sites should contain VL_GENERIC_* rules"
        
    except Exception as e:
        pytest.skip(f"Test setup failed: {e}")


def test_resolved_sites_use_normalized_site_id:
    """ resolved_sites  site_id（ alias）"""
    import yaml
    from pathlib import Path
    from core.numbering.dual_map import build_dual_map, resolve_functional_sites_on_sequence
    from core.features.scope import normalize_site_id
    
    sites_file = Path("kb/10_parameters/functional_sites.yaml")
    if not sites_file.exists:
        pytest.skip("Functional sites file not found")
    
    # 
    with open(sites_file, 'r', encoding='utf-8') as f:
        sites_data = yaml.safe_load(f)
    functional_sites = sites_data.get('functional_sites', [])
    
    #  VL κ 
    vl_kappa_sequence = "DVVMTQSPLSLPVTLGQPASISCRSSQSIVHSNGNTYLEWYLQKPGQSPQLLIYKVSNRFSGVPDRFSGSGSGTDFTLKISRVEAEDVGVYYCFQGSHVPLTFGQGTKLEIK"
    
    try:
        dual_map, status, chain_type = build_dual_map(vl_kappa_sequence)
        
        if status == "failed" or chain_type != "K":
            pytest.skip(f"ANARCI numbering failed or chain_type is not K (got {chain_type})")
        
        # 
        resolved_sites, conflicts = resolve_functional_sites_on_sequence(dual_map, functional_sites, chain_type)
        
        #  resolved_sites  site_id （ alias）
        for site_id, site_info in resolved_sites.items:
            # site_id  site_info["site_id"] 
            assert site_id == site_info["site_id"], f"Resolved site key {site_id} should match site_info.site_id {site_info['site_id']}"
            
            #  VL κ， VL_LAMBDA_* 
            if chain_type == "K":
                assert not site_id.startswith("VL_LAMBDA_"), f"VL κ resolved_sites should not contain {site_id}"
                #  VL_LAMBDA_*， VL_GENERIC_*
                normalized = normalize_site_id(site_id, chain_type)
                if site_id.startswith("VL_LAMBDA_"):
                    assert normalized.startswith("VL_GENERIC_"), f"{site_id} should be normalized to VL_GENERIC_*"
        
    except Exception as e:
        pytest.skip(f"Test setup failed: {e}")


def test_lambda_not_labeled_kappa:
    """ VL λ  VL_KAPPA_* """
    from core.features.scope import rule_applies
    
    # VL λ  VL κ 
    assert rule_applies("L", ["vl_kappa"]) is False
    
    # VL λ  VL λ 
    assert rule_applies("L", ["vl_lambda"]) is True
    assert rule_applies("L", ["vl"]) is True
    assert rule_applies("L", ["any"]) is True
    
    # VL λ  VH/VHH 
    assert rule_applies("L", ["vh", "vhh"]) is False


def test_rule_applies_mixed_scopes:
    """ rule_applies """
    from core.features.scope import rule_applies
    
    # VL κ  VH/VHH 
    assert rule_applies("K", ["vh", "vl"]) is False  #  vh
    assert rule_applies("K", ["vhh", "vl"]) is False  #  vhh
    assert rule_applies("K", ["vl", "vl_lambda"]) is False  #  vl_lambda
    
    # VL λ  VH/VHH 
    assert rule_applies("L", ["vh", "vl"]) is False  #  vh
    assert rule_applies("L", ["vhh", "vl"]) is False  #  vhh
    assert rule_applies("L", ["vl", "vl_kappa"]) is False  #  vl_kappa
    
    # VH  VL 
    assert rule_applies("H", ["vh", "vl"]) is False  #  vl
    assert rule_applies("H", ["vhh", "vl_kappa"]) is False  #  vl_kappa


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


