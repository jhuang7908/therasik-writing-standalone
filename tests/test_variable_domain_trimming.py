"""
Test variable domain trimming functionality

，：
1. 
2. 
3. 
"""

import pytest
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.trim_variable_domain import trim_variable_domain


def test_trim_vh_with_constant_region:
    """
     VH 
    
     PD1 6JBT Mouse VH ， CH1
    """
    # PD1 6JBT Mouse VH 
    full_sequence = "QGQLVQSGAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSSASTKGPSVFPLAPCSRSTSESTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTKTYTCNVDHKPSNTKVDKRV"
    
    trimmed_seq, metadata = trim_variable_domain(full_sequence)
    
    # 
    assert metadata["detected"] is True
    assert metadata["original_length"] == len(full_sequence)
    assert metadata["variable_domain_length"] == len(trimmed_seq)
    assert metadata["v_start"] == 0
    assert metadata["v_end"] == len(trimmed_seq)
    assert "detection_method" in metadata
    
    # 
    assert len(trimmed_seq) < len(full_sequence), ""
    assert metadata["trimmed_constant_region"] is True, ""
    
    # （ VH  110-130 aa）
    assert 100 <= len(trimmed_seq) <= 140, f" {len(trimmed_seq)} "
    
    # 
    assert trimmed_seq == full_sequence[:len(trimmed_seq)], ""


def test_trim_vl_with_constant_region:
    """
     VL Kappa 
    
     PD1 6JBT Mouse VL Kappa ， CL
    """
    # PD1 6JBT Mouse VL Kappa 
    full_sequence = "DVVMTQSPLSLPVTLGQPASISCRSSQSIVHSNGNTYLEWYLQKPGQSPQLLIYKVSNRFSGVPDRFSGSGSGTDFTLKISRVEAEDVGVYYCFQGSHVPLTFGQGTKLEIKRTVAAPSVFIFPPSDEQLKSGTASVVCLLNNFYPREAKVQWKVDNALQSGNSQESVTEQDSKDSTYSLSSTLTLSKADYEKHKVYACEVTHQGLSSPVTKSFNRGEC"
    
    trimmed_seq, metadata = trim_variable_domain(full_sequence)
    
    # 
    assert metadata["detected"] is True
    assert metadata["original_length"] == len(full_sequence)
    assert metadata["variable_domain_length"] == len(trimmed_seq)
    assert metadata["v_start"] == 0
    assert metadata["v_end"] == len(trimmed_seq)
    
    # 
    assert len(trimmed_seq) < len(full_sequence), ""
    assert metadata["trimmed_constant_region"] is True, ""
    
    # （ VL  100-120 aa）
    assert 90 <= len(trimmed_seq) <= 130, f" {len(trimmed_seq)} "
    
    # 
    assert trimmed_seq == full_sequence[:len(trimmed_seq)], ""


def test_trim_pure_variable_domain:
    """
    
    
    ，trimmed_constant_region  False
    """
    # 7D12 VHH （，）
    pure_vdomain = "QVQLQESGGGLVQAGGSLRLSCAASGRTFSSYAMGWFRQAPGKEREFVAAISSWSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAAKLLGSSGWSPFDYWGQGTLVTVSS"
    
    trimmed_seq, metadata = trim_variable_domain(pure_vdomain)
    
    # 
    assert metadata["detected"] is True
    assert metadata["original_length"] == len(pure_vdomain)
    assert metadata["variable_domain_length"] == len(trimmed_seq)
    
    # 
    # ：，， trimmed_constant_region  False
    assert len(trimmed_seq) == len(pure_vdomain), ""
    # trimmed_constant_region  False


def test_metadata_structure:
    """
    
    
    
    """
    test_sequence = "QGQLVQSGAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSSASTKGPSVFPLAPCSRSTSESTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTKTYTCNVDHKPSNTKVDKRV"
    
    trimmed_seq, metadata = trim_variable_domain(test_sequence)
    
    # 
    required_fields = [
        "detected",
        "trimmed_constant_region",
        "original_length",
        "variable_domain_length",  # 
        "v_length",  # （ STOP ）
        "v_start",
        "v_end",
        "detection_method"
    ]
    
    for field in required_fields:
        assert field in metadata, f": {field}"
    
    # 
    assert isinstance(metadata["detected"], bool)
    assert isinstance(metadata["trimmed_constant_region"], bool)
    assert isinstance(metadata["original_length"], int)
    assert isinstance(metadata["variable_domain_length"], int)
    assert isinstance(metadata["v_length"], int)  # 
    assert isinstance(metadata["v_start"], int)
    assert isinstance(metadata["v_end"], int)
    assert isinstance(metadata["detection_method"], str)
    
    # 
    assert metadata["original_length"] > 0
    assert metadata["variable_domain_length"] > 0
    assert metadata["v_length"] > 0
    assert metadata["v_start"] >= 0
    assert metadata["v_end"] > metadata["v_start"]
    assert metadata["v_end"] <= metadata["original_length"]
    assert metadata["variable_domain_length"] == metadata["v_end"] - metadata["v_start"]
    
    # 
    assert metadata["v_length"] == metadata["variable_domain_length"], \
        "v_length must equal variable_domain_length"


def test_trimming_preserves_sequence_integrity:
    """
    
    
    
    """
    test_sequence = "QGQLVQSGAEVKKPGASVKVSCKASGYTFTDYEMHWVRQAPIHGLEWIGVIESETGGTAYNQKFKGRVTITADKSTSTAYMELSSLRSEDTAVYYCAREGITTVATTYYWYFDVWGQGTTVTVSSASTKGPSVFPLAPCSRSTSESTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTKTYTCNVDHKPSNTKVDKRV"
    
    trimmed_seq, metadata = trim_variable_domain(test_sequence)
    
    # 
    assert trimmed_seq == test_sequence[metadata["v_start"]:metadata["v_end"]], \
        ""
    
    # 
    valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
    assert all(aa in valid_aa for aa in trimmed_seq), ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])








