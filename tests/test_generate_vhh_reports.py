#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VHH Classic Panel
"""

import json
import re
from pathlib import Path

import pytest

# 
PROJECT_ROOT = Path(__file__).resolve.parents[1]
import sys
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_vhh_reports_from_panel_json import (
    generate_client_cro_report,
    generate_developer_audit_report,
    load_panel_json,
    sort_variants_for_client,
)


@pytest.fixture
def sample_panel_json(tmp_path):
    """Classic Panel JSON"""
    json_data = {
        "gate": {
            "version": "v1",
            "pass_level": "pass",
            "flags": [],
            "metrics": {
                "cdr3_len": 12,
                "total_cys_count": 1,
                "best_fr_identity": 0.7875,
                "best_fr_identity_scaffold_id": "IGHV3-66*01",
            },
        },
        "classic_panel": [
            {
                "scaffold_id": "IGHV3-23*01",
                "j_region_id": "IGHJ4",
                "sequence_final": "EVQLLESGGGLVQPGGSLRLSCAASGFWYNHMSWVRQAPGKEREWVAAITADSGSTYYADSVKGRFTISRDDSKNTVYLQMNSLRAEDTAVYYCAAGGVGWPYFDYWGQGTLVTVSS",
                "sequence_grafted_pre_mutation": "EVQLLESGGGLVQPGGSLRLSCAASGFWYNHMSWVRQAPGKGLEWVSAITADSGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAAGGVGWPYFDYWGQGTLVTVSS",
                "mutations": [
                    {
                        "rule_id": "HALLMARK_FR2_44",
                        "numbering": {"kabat": 44, "imgt": "44"},
                        "from_aa": "G",
                        "to_aa": "E",
                        "rationale": "Query position 44 has E",
                        "evidence_level": "rule_based",
                        "layer": "A",
                        "risk_level": "low",
                        "purpose": "Maintain VHH hydrophilic FR2 interface",
                        "trigger_explanation": "Query Kabat 44: E | Scaffold Kabat 44: G",
                    }
                ],
                "mutation_summary": {
                    "hallmark_applied": True,
                    "vernier_applied": True,
                    "n_mutations_total": 1,
                    "vernier_backfill_count": 0,
                },
                "canonical_risk_level": "low",
                "canonical_rationale": "CDR1 match; CDR2 match; risk=low",
                "qa": {
                    "cdr_integrity_ok": True,
                    "numbering_consistency_ok": True,
                },
                "provenance": {
                    "scaffold_sha256": "test_scaffold_hash",
                    "j_region_sha256": "test_j_hash",
                    "pipeline_version": "v1.0",
                },
            },
            {
                "scaffold_id": "IGHV3-23*01",
                "j_region_id": "IGHJ6",
                "sequence_final": "EVQLLESGGGLVQPGGSLRLSCAASGFWYNHMSWVRQAPGKEREWVAAITADSGSTYYADSVKGRFTISRDDSKNTVYLQMNSLRAEDTAVYYCAAGGVGWPYFDYWGQGTTVTVSS",
                "sequence_grafted_pre_mutation": "EVQLLESGGGLVQPGGSLRLSCAASGFWYNHMSWVRQAPGKGLEWVSAITADSGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAAGGVGWPYFDYWGQGTTVTVSS",
                "mutations": [],
                "mutation_summary": {
                    "hallmark_applied": False,
                    "vernier_applied": False,
                    "n_mutations_total": 0,
                    "vernier_backfill_count": 0,
                },
                "canonical_risk_level": "medium",
                "canonical_rationale": "CDR1 mismatch",
                "qa": {
                    "cdr_integrity_ok": True,
                    "numbering_consistency_ok": True,
                },
                "provenance": {
                    "scaffold_sha256": "test_scaffold_hash",
                    "j_region_sha256": "test_j_hash_2",
                    "pipeline_version": "v1.0",
                },
            },
        ],
        "cdr_features": {
            "cdr1_seq": "GFWYNH",
            "cdr2_seq": "ITADSGST",
            "cdr1_len": 6,
            "cdr2_len": 8,
            "cdr1_proxy_class": "L6",
            "cdr2_proxy_class": "L8",
        },
        "canonical_compatibility": {
            "IGHV3-23*01": {
                "cdr1_len_match": False,
                "cdr2_len_match": True,
                "risk_level": "low",
                "rationale": "CDR1 mismatch; CDR2 match",
            }
        },
        "canonical_profiles": {
            "IGHV3-23*01": {
                "canonical_system": "Chothia",
                "cdr1_len": 8,
                "cdr1_class": "C1",
                "cdr2_len": 8,
                "cdr2_class": "C3",
            }
        },
        "rulebook_summary": {
            "rulebook_version": "v1.0",
            "mode": "mvp",
            "triggered_rules": ["HALLMARK_FR2_44", "VERNIER_TUNING"],
            "disabled_high_risk_rules": [
                {
                    "rule_id": "VERNIER_ANCHOR",
                    "layer": "B",
                    "risk_level": "medium",
                    "reason": "Not enabled in mvp mode",
                }
            ],
        },
        "pipeline_version": "v1.0",
        "timestamp": "2025-12-20T10:00:00",
    }
    
    json_path = tmp_path / "test_panel.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    
    return json_path


def test_load_panel_json(sample_panel_json):
    """JSON"""
    data = load_panel_json(sample_panel_json)
    assert "classic_panel" in data
    assert len(data["classic_panel"]) == 2


def test_sort_variants_for_client(sample_panel_json):
    """variants"""
    data = load_panel_json(sample_panel_json)
    variants = data["classic_panel"]
    sorted_variants = sort_variants_for_client(variants)
    
    # canonical_risk_levellow
    assert sorted_variants[0]["canonical_risk_level"] == "low"
    assert sorted_variants[1]["canonical_risk_level"] == "medium"


def test_generate_client_cro_report(sample_panel_json, tmp_path):
    """Client CRO Report"""
    data = load_panel_json(sample_panel_json)
    output_dir = tmp_path / "reports"
    
    report_path = generate_client_cro_report(data, output_dir, "TEST")
    
    assert report_path.exists
    content = report_path.read_text(encoding="utf-8")
    
    # 
    assert "" in content or "Decision Summary" in content
    assert "" in content or "Query Overview" in content
    assert "" in content or "Canonical Compatibility" in content
    assert "" in content or "Humanization Results Table" in content
    
    # 
    sensitive_keywords = ["sha256", "mutations_rules", "core/", "tests/", "byte-level", "unit test"]
    content_lower = content.lower
    for keyword in sensitive_keywords:
        assert keyword not in content_lower, f": {keyword}"
    
    # CDR
    assert "GFWYNH" in content  # CDR1
    assert "ITADSGST" in content  # CDR2


def test_generate_developer_audit_report(sample_panel_json, tmp_path):
    """Developer Audit Report"""
    data = load_panel_json(sample_panel_json)
    output_dir = tmp_path / "reports"
    
    report_path = generate_developer_audit_report(data, output_dir, "TEST")
    
    assert report_path.exists
    content = report_path.read_text(encoding="utf-8")
    
    # 
    assert "Hallmark" in content
    assert "Vernier" in content
    assert "SHA256" in content or "sha256" in content
    
    # 
    assert "" in content or "Mutation Log" in content
    assert "HALLMARK_FR2_44" in content
    
    # provenance
    assert "test_scaffold_hash" in content or "SHA256" in content


def test_client_report_no_technical_details(sample_panel_json, tmp_path):
    """"""
    data = load_panel_json(sample_panel_json)
    output_dir = tmp_path / "reports"
    
    report_path = generate_client_cro_report(data, output_dir, "TEST")
    content = report_path.read_text(encoding="utf-8").lower
    
    # 
    forbidden = [
        "sha256",
        "mutations_rules",
        "core/",
        "tests/",
        "byte-level",
        "unit test",
        "pytest",
        "import",
        "def ",
    ]
    
    for keyword in forbidden:
        assert keyword not in content, f": {keyword}"


def test_developer_report_contains_required_sections(sample_panel_json, tmp_path):
    """"""
    data = load_panel_json(sample_panel_json)
    output_dir = tmp_path / "reports"
    
    report_path = generate_developer_audit_report(data, output_dir, "TEST")
    content = report_path.read_text(encoding="utf-8")
    
    # 
    required_sections = [
        "",
        "",
        "",
        "Hallmark",
        "Vernier",
        "",
        "Canonical",
    ]
    
    for section in required_sections:
        assert section in content, f": {section}"


def test_reports_cdr_consistency(sample_panel_json, tmp_path):
    """CDRJSON"""
    data = load_panel_json(sample_panel_json)
    output_dir = tmp_path / "reports"
    
    client_report = generate_client_cro_report(data, output_dir, "TEST")
    dev_report = generate_developer_audit_report(data, output_dir, "TEST")
    
    client_content = client_report.read_text(encoding="utf-8")
    dev_content = dev_report.read_text(encoding="utf-8")
    
    # CDR1
    cdr1_seq = data["cdr_features"]["cdr1_seq"]
    assert cdr1_seq in client_content
    assert cdr1_seq in dev_content
    
    # CDR2
    cdr2_seq = data["cdr_features"]["cdr2_seq"]
    assert cdr2_seq in client_content
    assert cdr2_seq in dev_content
    
    # CDR
    cdr1_len = str(data["cdr_features"]["cdr1_len"])
    cdr2_len = str(data["cdr_features"]["cdr2_len"])
    assert cdr1_len in client_content
    assert cdr2_len in client_content
    assert cdr1_len in dev_content
    assert cdr2_len in dev_content


def test_variant_count_consistency(sample_panel_json, tmp_path):
    """variantJSON"""
    data = load_panel_json(sample_panel_json)
    output_dir = tmp_path / "reports"
    
    client_report = generate_client_cro_report(data, output_dir, "TEST")
    dev_report = generate_developer_audit_report(data, output_dir, "TEST")
    
    client_content = client_report.read_text(encoding="utf-8")
    dev_content = dev_report.read_text(encoding="utf-8")
    
    # variant（scaffold_id × j_region_id）
    variant_count = len(data["classic_panel"])
    
    # ，
    scaffold_count = client_content.count("IGHV3-23*01")
    assert scaffold_count >= variant_count, "variant"
    
    # ，
    section_count = dev_content.count("### 4.")
    assert section_count == variant_count, "variant"

