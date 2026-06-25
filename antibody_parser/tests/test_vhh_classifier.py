"""
Tests for VHH classifier functionality
"""
import pytest
from v_classifier import VClassifier


classifier = VClassifier()


def test_classify_vhh():
    seq_vhh = (
        "QVQLVESGGGLVQAGGSLRLSCAASGRNYGTSYSMGWYRQAPGKQRELVAARLGGTRYYA"
        "DSVKGRFTISRDNAKNTLYLQMNSLKPEDTAVYYCAAGWVHPNNNWYWGQGTQVTVSS"
    )
    result = classifier.classify(seq_vhh)

    assert result["is_vhh"] is True
    assert result["confidence"] > 0.6


def test_classify_vh():
    seq_vh = (
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYGMSWVRQAPGKGLEWVSAISGSGGSTY"
        "YADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAR"
    )
    result = classifier.classify(seq_vh)

    assert result["is_vhh"] is False
