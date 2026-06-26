"""


QA，OK
"""

import pytest
from scripts.generate_egfr_cro_report_cn_enhanced import (
    generate_cro_html_report_cn_enhanced,
    generate_cro_html_report_failed_cn,
)


def test_generate_full_report_only_for_ok_status:
    """：OK"""
    # OK：
    result_ok = {
        "status": "OK",
        "best_match": {
            "humanized_sequence": "TEST_SEQ",
            "template": {"template_id": "TEST_TEMPLATE"}
        },
        "input": {"sequence": "ORIGINAL_SEQ"},
        "cdrs": {},
        "cdr_canonical": {},
    }
    
    # 
    try:
        html = generate_cro_html_report_cn_enhanced(result_ok, "TEST_ID")
        assert html is not None
        assert len(html) > 0
    except ValueError:
        pytest.fail("OK")
    
    # OK_SAFE_MODE：
    result_safe = result_ok.copy
    result_safe["status"] = "OK_SAFE_MODE"
    
    try:
        html = generate_cro_html_report_cn_enhanced(result_safe, "TEST_ID")
        assert html is not None
        assert len(html) > 0
    except ValueError:
        pytest.fail("OK_SAFE_MODE")


def test_generate_full_report_raises_for_failed_qa:
    """：FAILED_QA"""
    result_failed_qa = {
        "status": "FAILED_QA",
        "error": "QA",
        "qa": {
            "ok": False,
            "errors": ["FR4", "CDR"]
        }
    }
    
    # ValueError
    with pytest.raises(ValueError, match=" status=FAILED_QA"):
        generate_cro_html_report_cn_enhanced(result_failed_qa, "TEST_ID")


def test_generate_full_report_raises_for_failed:
    """：FAILED"""
    result_failed = {
        "status": "FAILED",
        "error": ""
    }
    
    # ValueError
    with pytest.raises(ValueError, match=" status=FAILED"):
        generate_cro_html_report_cn_enhanced(result_failed, "TEST_ID")


def test_generate_failure_report_for_failed_qa:
    """：FAILED_QA"""
    result_failed_qa = {
        "status": "FAILED_QA",
        "error": "QA",
        "input": {"sequence": "TEST_SEQ"},
        "qa": {
            "ok": False,
            "errors": ["FR4", "CDR"],
            "warnings": []
        }
    }
    
    html = generate_cro_html_report_failed_cn(result_failed_qa, "TEST_ID", result_failed_qa["qa"])
    
    assert html is not None
    assert len(html) > 0
    assert "QA" in html or "QA" in html
    assert "FR4" in html or "CDR" in html
    assert "" in html and ("" in html or "" in html)


def test_generate_failure_report_for_failed:
    """：FAILED"""
    result_failed = {
        "status": "FAILED",
        "error": ""
    }
    
    html = generate_cro_html_report_failed_cn(result_failed, "TEST_ID")
    
    assert html is not None
    assert len(html) > 0
    assert "" in html or "" in html


def test_failure_report_contains_required_elements:
    """："""
    result_failed_qa = {
        "status": "FAILED_QA",
        "error": "QA",
        "input": {
            "sequence": "QVQLVESGGGLVQVGGSLRLSRALSGFWYNHMGWFRQAPGKEREGVAVITADSGSTTYADSVKGRFTISRDDARNTVYLQMNSLKPEDTAVYYCAAGGVGWPYFDYWGQGTQVTVSS",
            "length": 117
        },
        "qa": {
            "ok": False,
            "errors": [" FR4 （0）- FR4"],
            "warnings": []
        }
    }
    
    html = generate_cro_html_report_failed_cn(result_failed_qa, "TEST_ID", result_failed_qa["qa"])
    
    # 
    assert "" in html or "sequence" in html.lower
    
    # QA
    assert "QA" in html or "" in html
    assert "FR4" in html
    
    # 
    assert ("" in html and "" in html) or ("" in html and "" in html)
    
    # 
    assert "" in html or "" in html or "mAb" in html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

