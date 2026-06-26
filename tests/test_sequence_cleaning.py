"""
Test sequence cleaning functionality

，：
1. 
2. STOP/WARN
3. QA
4. 
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.sequence_cleaner import (
    normalize_input_sequence,
    perform_length_screening,
    check_x_proportion,
    generate_qa_flags,
    clean_sequence_comprehensive,
    validate_variable_domain_consistency,
    enhance_cleaning_log_with_residues
)


def test_normalize_input_sequence:
    """"""
    # FASTA、、
    raw_input = ">test_sequence\nQGQLVQS GAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSSASTKGPSVFPLAPCSRSTSESTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTKTYTCNVDHKPSNTKVDKRV"
    
    cleaned, log = normalize_input_sequence(raw_input)
    
    # 
    assert len(cleaned) > 0
    assert all(c in "ACDEFGHIKLMNPQRSTVWYX" for c in cleaned)
    assert " " not in cleaned
    assert "\n" not in cleaned
    
    # 
    assert "original_length" in log
    assert "cleaned_length" in log
    assert log["has_fasta_header"] is True
    assert log["fasta_header"] == "test_sequence"


def test_length_screening:
    """"""
    #  - STOP
    should_continue, stop_reason, warn_reason = perform_length_screening("A" * 50)
    assert not should_continue
    assert stop_reason == "too_short"
    
    # 
    should_continue, stop_reason, warn_reason = perform_length_screening("A" * 200)
    assert should_continue
    assert stop_reason is None
    
    #  - WARN
    should_continue, stop_reason, warn_reason = perform_length_screening("A" * 900)
    assert should_continue
    assert warn_reason == "too_long_suspicious_fusion"


def test_check_x_proportion:
    """X"""
    # X - STOP
    seq_with_high_x = "A" * 90 + "X" * 10  # 10% X
    should_continue, stop_reason = check_x_proportion(seq_with_high_x)
    assert not should_continue
    assert "x_proportion_too_high" in stop_reason
    
    # X
    seq_with_low_x = "A" * 95 + "X" * 5  # 5% X
    should_continue, stop_reason = check_x_proportion(seq_with_low_x)
    assert should_continue
    assert stop_reason is None


def test_generate_qa_flags:
    """QA（warn_reasons）"""
    # 
    vdomain_meta = {
        "detected": True,
        "variable_domain_length": 125,
        "v_length": 125,
        "variable_domain_sequence": "A" * 125,
        "v_start": 0,
        "v_end": 125,
        "trimmed_constant_region": False
    }
    
    qa_flags, stop_reason, warn_reasons = generate_qa_flags(
        vdomain_meta, "full", {}, "H", None
    )
    
    assert "CLEAN" in qa_flags
    assert stop_reason is None
    assert isinstance(warn_reasons, list)
    
    # 
    qa_flags, stop_reason, warn_reasons = generate_qa_flags(
        vdomain_meta, "conflict", {}, "H", None
    )
    
    assert "WARN_CONFLICT" in qa_flags
    assert "USABLE_WITH_WARNINGS" in qa_flags
    assert isinstance(warn_reasons, list)
    assert len(warn_reasons) > 0
    
    # V
    extra_domains = [{"v_start": 200, "v_end": 300, "length": 100}]
    qa_flags, stop_reason, warn_reasons = generate_qa_flags(
        vdomain_meta, "full", {}, "H", extra_domains
    )
    
    assert "WARN_MULTI_DOMAIN" in qa_flags
    assert "WARN_MULTI_DOMAIN" in warn_reasons
    
    # V - STOP
    vdomain_meta_failed = {
        "detected": False,
        "variable_domain_length": 0
    }
    
    qa_flags, stop_reason, warn_reasons = generate_qa_flags(
        vdomain_meta_failed, "unknown", {}, None, None
    )
    
    assert "REJECT" in qa_flags
    assert stop_reason is not None


def test_clean_sequence_comprehensive_stop_conditions:
    """STOP"""
    # 
    result = clean_sequence_comprehensive("A" * 50)
    assert result["stop_reason"] is not None
    assert "REJECT" in result["qa_flags"]
    
    # X
    result = clean_sequence_comprehensive("A" * 90 + "X" * 10)
    # ：V，STOP
    # VSTOP


def test_clean_sequence_comprehensive_success:
    """"""
    # VH
    test_seq = "QGQLVQSGAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSSASTKGPSVFPLAPCSRSTSESTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTKTYTCNVDHKPSNTKVDKRV"
    
    result = clean_sequence_comprehensive(
        test_seq,
        dual_map_status="conflict",
        chain_type="H"
    )
    
    # 
    assert "cleaned_input_sequence" in result
    assert "variable_domain" in result
    assert "variable_domain_sequence" in result
    assert "cleaning_log" in result
    assert "qa_flags" in result
    assert "tool_versions" in result
    assert "warn_reasons" in result  # WARN
    assert "extra_domains" in result  # V
    
    # 
    assert result["cleaning_log"]["cleaned_length"] > 0
    
    # V
    if result["variable_domain"].get("detected"):
        assert len(result["variable_domain_sequence"]) > 0
        assert result["variable_domain"]["variable_domain_length"] > 0


def test_field_consistency_constraints:
    """"""
    # 
    vdomain_meta = {
        "detected": True,
        "variable_domain_length": 125,
        "v_length": 125,
        "v_start": 0,
        "v_end": 125,
        "variable_domain_sequence": "A" * 125
    }
    
    is_valid, stop_reason, diagnostic = validate_variable_domain_consistency(
        vdomain_meta, "A" * 125
    )
    
    assert is_valid is True
    assert stop_reason is None
    
    # ：v_length != variable_domain_length
    vdomain_meta_inconsistent1 = {
        "detected": True,
        "variable_domain_length": 125,
        "v_length": 120,  # 
        "v_start": 0,
        "v_end": 125,
        "variable_domain_sequence": "A" * 125
    }
    
    is_valid, stop_reason, diagnostic = validate_variable_domain_consistency(
        vdomain_meta_inconsistent1, "A" * 125
    )
    
    assert is_valid is False
    assert "STOP_INCONSISTENT_BOUNDARIES" in stop_reason
    assert "issues" in diagnostic
    
    # ：v_end - v_start != v_length
    vdomain_meta_inconsistent2 = {
        "detected": True,
        "variable_domain_length": 125,
        "v_length": 125,
        "v_start": 0,
        "v_end": 120,  # 
        "variable_domain_sequence": "A" * 125
    }
    
    is_valid, stop_reason, diagnostic = validate_variable_domain_consistency(
        vdomain_meta_inconsistent2, "A" * 125
    )
    
    assert is_valid is False
    assert "STOP_INCONSISTENT_BOUNDARIES" in stop_reason


def test_warn_reasons_structure:
    """WARN（warn_reasons: List[str]）"""
    test_seq = "QGQLVQSGAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSSASTKGPSVFPLAPCSRSTSESTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTKTYTCNVDHKPSNTKVDKRV"
    
    result = clean_sequence_comprehensive(
        test_seq,
        dual_map_status="conflict",
        chain_type="H"
    )
    
    # warn_reasons
    assert "warn_reasons" in result
    assert isinstance(result["warn_reasons"], list)
    
    # warn_reason
    assert "warn_reason" in result
    if result["warn_reasons"]:
        assert result["warn_reason"] == "; ".join(result["warn_reasons"])


def test_upstream_downstream_logging:
    """/"""
    # N
    seq_with_signal_peptide = "MKLLVVVFCLGVPAQVEQGQLVQSGAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSS"
    
    cleaned, log = normalize_input_sequence(seq_with_signal_peptide)
    
    # V（v_start > 0）
    v_start = 20
    v_end = len(cleaned)
    enhance_cleaning_log_with_residues(log, cleaned, v_start, v_end)
    
    assert "upstream_length" in log
    assert log["upstream_length"] == 20
    assert "upstream_tail_15" in log
    assert len(log["upstream_tail_15"]) <= 15
    
    # C
    seq_with_constant = "QGQLVQSGAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSSASTKGPSVFPLAPCSRSTSESTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTKTYTCNVDHKPSNTKVDKRV"
    
    cleaned2, log2 = normalize_input_sequence(seq_with_constant)
    
    # V（v_end < original_length）
    v_start2 = 0
    v_end2 = 125
    enhance_cleaning_log_with_residues(log2, cleaned2, v_start2, v_end2)
    
    assert "downstream_length" in log2
    assert log2["downstream_length"] > 0
    assert "downstream_head_15" in log2
    assert len(log2["downstream_head_15"]) <= 15


def test_invalid_chars_removal_order:
    """：，"""
    # 、、*、-、X
    raw_input = "QGQLVQS123 GAEVKK*PGAS-VKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSSX"
    
    cleaned, log = normalize_input_sequence(raw_input)
    
    # 
    assert "1" not in cleaned
    assert "2" not in cleaned
    assert "3" not in cleaned
    assert " " not in cleaned
    assert "*" not in cleaned
    assert "-" not in cleaned
    
    # Xx_count
    assert "X" in cleaned  # X
    assert log["x_count"] > 0
    
    # 
    assert log["invalid_count"] > 0
    assert "invalid_chars" in log["removed_chars"]
    assert "invalid_chars" in log["removed_count"]


def test_x_threshold_stop:
    """XSTOP"""
    # >5% XV
    v_seq_high_x = "A" * 90 + "X" * 10  # 10% X
    
    should_continue, stop_reason = check_x_proportion(v_seq_high_x)
    
    assert not should_continue
    assert "x_proportion_too_high" in stop_reason
    
    # 
    # ：V，STOP
    # VSTOP


def test_multi_domain_detection:
    """V"""
    # V（scFv：VH-linker-VL）
    # ：V
    # extra_domains
    
    test_seq = "QGQLVQSGAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSSGGGGSGGGGSGGGGSDVVMTQSPLSLPVTLGQPASISCRSSQSIVHSNGNTYLEWYLQKPGQSPQLLIYKVSNRFSGVPDRFSGSGSGTDFTLKISRVEAEDVGVYYCFQGSHVPLTFGQGTKLEIKRTVAAPSVFIFPPSDEQLKSGTASVVCLLNNFYPREAKVQWKVDNALQSGNSQESVTEQDSKDSTYSLSSTLTLSKADYEKHKVYACEVTHQGLSSPVTKSFNRGEC"
    
    result = clean_sequence_comprehensive(
        test_seq,
        dual_map_status="full",
        chain_type="H"
    )
    
    # extra_domains
    assert "extra_domains" in result
    assert isinstance(result["extra_domains"], list)
    
    # V，
    if len(result["extra_domains"]) > 0:
        extra = result["extra_domains"][0]
        assert "v_start" in extra
        assert "v_end" in extra
        assert "length" in extra
        assert "score" in extra
        assert "sequence" in extra


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])








