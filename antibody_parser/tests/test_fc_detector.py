"""
Tests for Fc region detection functionality
"""
import pytest
from fc_detector import FcDetector
from cleaner import clean_sequence


detector = FcDetector()


def test_fc_detect_human():
    seq = (
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYGMSWVRQAPGKGLEWVSAISGSGGSTYY"
        "ADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAR"
        "ASTKGPSVFPLAPSSKSTSGGTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTQTYICNVNHKPSNTKVDKKVEPKSC"
        "DKTHTCPPCPAPELLGGPSVFLFPPKPKDTLMISRTPEVTCVVVDVSHEDPEVKFNWYV"
    )
    cleaned = clean_sequence(seq)
    result = detector.detect(cleaned)

    assert result["present"] is True
    assert result["species"] == "human_igg1" or "human" in result["species"]
    assert result["confidence"] > 0.5
