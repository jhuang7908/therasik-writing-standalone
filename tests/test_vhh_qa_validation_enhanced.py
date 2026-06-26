"""
QA（fallback、、）
"""

import pytest
from core.vhh_qa_validation import validate_vhh_humanization_result


def test_fallback_warning:
    """fallback"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "AAAA", "CDR1": "BBBB", "FR2": "CCCC",
                "CDR2": "DDDD", "FR3": "EEEE", "CDR3": "FFFF", "FR4": "GGGG",
            },
            "humanized_regions": {
                "FR1": "AAAA", "CDR1": "BBBB", "FR2": "CCCC",
                "CDR2": "DDDD", "FR3": "EEEE", "CDR3": "FFFF", "FR4": "GGGG",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "AAAABBBBCCCCDDDDEEEEFFFFGGGG",
            "template": {
                "flags": {
                    "uses_fallback_numbering": True
                }
            }
        },
        "quality_flags": {}
    }
    
    qa_result = validate_vhh_humanization_result(result, strict=True)
    assert qa_result["ok"]  # warning，
    assert len([w for w in qa_result["warnings"] if "fallback" in w.lower]) > 0


def test_mutation_consistency_check:
    """"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "AAAA", "CDR1": "BBBB", "FR2": "CCCC",
                "CDR2": "DDDD", "FR3": "EEEE", "CDR3": "FFFF", "FR4": "GGGG",
            },
            "humanized_regions": {
                "FR1": "AXAA",  # 2
                "CDR1": "BBBB", "FR2": "CCCC",
                "CDR2": "DDDD", "FR3": "EEEE", "CDR3": "FFFF", "FR4": "GGGG",
            }
        },
        "mutations": {
            "list": [
                {
                    "position": 5,  # IMGT5 = FR12（0-based1）
                    "from": "A",
                    "to": "X",
                    "region": "FR1"
                }
            ]
        },
        "best_match": {
            "humanized_sequence": "AXAABBBBCCCCDDDDEEEEFFFFGGGG"
        }
    }
    
    qa_result = validate_vhh_humanization_result(result, strict=True)
    assert qa_result["ok"]
    # 


def test_mutation_inconsistency_error:
    """"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "AAAA", "CDR1": "BBBB", "FR2": "CCCC",
                "CDR2": "DDDD", "FR3": "EEEE", "CDR3": "FFFF", "FR4": "GGGG",
            },
            "humanized_regions": {
                "FR1": "AAAA",  # 
                "CDR1": "BBBB", "FR2": "CCCC",
                "CDR2": "DDDD", "FR3": "EEEE", "CDR3": "FFFF", "FR4": "GGGG",
            }
        },
        "mutations": {
            "list": [
                {
                    "position": 5,
                    "from": "A",
                    "to": "X",
                    "region": "FR1"
                }
            ]
        },
        "best_match": {
            "humanized_sequence": "AAAABBBBCCCCDDDDEEEEFFFFGGGG"
        }
    }
    
    qa_result = validate_vhh_humanization_result(result, strict=True)
    assert not qa_result["ok"]  # 
    assert len([e for e in qa_result["errors"] if "" in e or "" in e]) > 0


def test_sequence_consistency_check:
    """"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "AAAA", "CDR1": "BBBB", "FR2": "CCCC",
                "CDR2": "DDDD", "FR3": "EEEE", "CDR3": "FFFF", "FR4": "GGGG",
            },
            "humanized_regions": {
                "FR1": "AAAA", "CDR1": "BBBB", "FR2": "CCCC",
                "CDR2": "DDDD", "FR3": "EEEE", "CDR3": "FFFF", "FR4": "GGGG",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "AAAABBBBCCCCDDDDEEEEFFFFGGGG"  # 
        }
    }
    
    qa_result = validate_vhh_humanization_result(result, strict=True)
    assert qa_result["ok"]


def test_sequence_inconsistency_error:
    """"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "AAAA", "CDR1": "BBBB", "FR2": "CCCC",
                "CDR2": "DDDD", "FR3": "EEEE", "CDR3": "FFFF", "FR4": "GGGG",
            },
            "humanized_regions": {
                "FR1": "AAAA", "CDR1": "BBBB", "FR2": "CCCC",
                "CDR2": "DDDD", "FR3": "EEEE", "CDR3": "FFFF", "FR4": "GGGG",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "XXXXXXXXXXXX"  # 
        }
    }
    
    qa_result = validate_vhh_humanization_result(result, strict=True)
    # >3，
    if abs(len("XXXXXXXXXXXX") - len("AAAABBBBCCCCDDDDEEEEFFFFGGGG")) > 3:
        assert not qa_result["ok"]
        assert len([e for e in qa_result["errors"] if "" in e or "" in e]) > 0


def test_cdr_difference_detection:
    """CDR"""
    result = {
        "sequence_analysis": {
            "original_regions": {
                "FR1": "AAAA", "CDR1": "BBBB", "FR2": "CCCC",
                "CDR2": "DDDD", "FR3": "EEEE", "CDR3": "FFFF", "FR4": "GGGG",
            },
            "humanized_regions": {
                "FR1": "AAAA", "CDR1": "BXXB",  # CDR1
                "FR2": "CCCC", "CDR2": "DDDD", "FR3": "EEEE", "CDR3": "FFFF", "FR4": "GGGG",
            }
        },
        "mutations": {"list": []},
        "best_match": {
            "humanized_sequence": "AAAABXXBCCCCDDDDEEEEFFFFGGGG"
        }
    }
    
    qa_result = validate_vhh_humanization_result(result, strict=True)
    assert not qa_result["ok"]  # 
    assert len([e for e in qa_result["errors"] if "CDR" in e and "" in e]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

















