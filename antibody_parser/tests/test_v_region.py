"""
Tests for V region finding functionality
"""
import pytest
from cleaner import clean_sequence
from v_finder import VRegionFinder


finder = VRegionFinder()


# --- Test Case 1: Normal VH -----------------------------------


def test_v_region_normal_vh():
    seq = (
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYGMSWVRQAPGKGLEWVSAISGSGGSTYY"
        "ADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAR"
    )
    cleaned = clean_sequence(seq)
    result = finder.find_v_region(cleaned)

    assert result["found"] is True
    assert result["confidence"] > 0.5
    assert len(result["sequence"]) > 80


# --- Test Case 2: VHH sequence --------------------------------


def test_v_region_vhh():
    seq = (
        "QVQLVESGGGLVQAGGSLRLSCAASGRNYGTSYSMGWYRQAPGKQRELVAARLGGTRYYA"
        "DSVKGRFTISRDNAKNTLYLQMNSLKPEDTAVYYCAAGWVHPNNNWYWGQGTQVTVSS"
    )
    cleaned = clean_sequence(seq)
    result = finder.find_v_region(cleaned)

    assert result["found"] is True
    assert result["confidence"] > 0.6
    assert result["sequence"].startswith("QVQL")


# --- Test Case 3: Noisy input with tags & signal peptide -------


def test_v_region_dirty_input():
    seq = (
        "MRLLLLLLLLLLLLLRSGGHHHHHHGSSGGSGSGSGG"
        "QVQLVESGGGLVQPGGSLRLSCAASGFTFSSYGM"
    )
    cleaned = clean_sequence(seq)
    result = finder.find_v_region(cleaned)

    assert result["found"] is True
    assert "QVQL" in result["sequence"]
    assert result["start"] > 0  # must skip garbage


# --- Test Case 4: Truncated V region ----------------------------


def test_v_region_truncated():
    seq = "SGGGLVQPGGSLRLSCAASGFTFSSYGM"
    cleaned = clean_sequence(seq)
    result = finder.find_v_region(cleaned)

    assert result["found"] is True
    assert len(result["sequence"]) > 20
