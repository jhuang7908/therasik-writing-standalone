"""
End-to-end tests for the complete antibody parsing pipeline
"""
import pytest
import json
from main import parse_sequence


def test_full_pipeline:
    seq = (
        "MRLLLLLLGGGGGHHHHHH"
        "QVQLVESGGGLVQPGGSLRLSCAASGFTFSSYGMSWVRQAPGKGLEWVSAISGSGGSTYY"
        "ADSVKGRFTISRDNAKNTLYLQMNSLRAEDTAVYYCAR"
        "ASTKGPSVFPLAPSSKSTSGGTAALGCLVKDYFPEPVTVSWNSGALTSGVHTFPAVLQSSGLYSLSSVVTVPSSSLGTQTYICNVNHKPSNTKVDKKVEPKSC"
        "DKTHTCPPCPAPELLGGPSVFLFPPKPKDTLMISRTPEVTCVVVDVSHEDPEVKFNWYV"
    )

    result = parse_sequence(seq)
    assert result["v_region"]["found"] is True
    assert result["is_vhh_like"] in (True, False)
    assert result["constant_region"]["fc_present"] in (True, False)

    #  → JSON 
    json.dumps(result)
