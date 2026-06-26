#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
（ Canonical Proxy ）
"""

import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_dual_report_v3 import generate_client_report
from core.report_blocks.canonical_proxy_background_customer import (
    render_canonical_proxy_background_customer_block,
)


def create_minimal_test_result():
    """ result """
    return {
        "input": {
            "sequence": "EVQLVESGGGLVQPGGSLRLSCAASGRTFSSYAMGWFRQAPGKEREFVAAISWSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAA",
            "target": "EGFR",
            "species": "alpaca",
        },
        "target": "EGFR",
        "best_match": {
            "id": "HUMAN_VH3_SCF_10",
            "template": {
                "template_id": "HUMAN_VH3_SCF_10",
                "source_scaffold": "VH3-30",
            },
            "alignment_scores": {
                "framework_identity": 0.85,
                "fr1_identity": 0.90,
                "fr2_identity": 0.80,
                "fr3_identity": 0.85,
                "combined_score": 0.85,
            },
            "humanized_sequence": "EVQLVESGGGLVQPGGSLRLSCAASGRTFSSYAMGWFRQAPGKEREFVAAISWSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAA",
        },
        "segmentation": {
            "regions": {
                "FR1": "EVQLVESGGGLVQPGGSLRLSCAAS",
                "CDR1": "GRTFSSYAMG",
                "FR2": "WFRQAPGKEREFVAA",
                "CDR2": "ISWSGGSTYYADSVK",
                "FR3": "GRFTISRDNSKNTLYLQMNSLRAEDTAVYYC",
                "CDR3": "AA",
            },
        },
        "segmentation_provenance": {
            "method": "anarcii",
            "version": "1.0",
            "scheme": "imgt",
            "implementation": "core.segmentation.anarcii_adapter",
            "evidence": "ANARCII numbering output",
        },
        "germline_library_provenance": {
            "source": "IMGT",
            "version": "2024-01",
        },
        "germline_numbering": {
            "method": "anarcii",
            "scheme": "imgt",
        },
        "stage1": {
            "selected_scaffold": {
                "scaffold_id": "HUMAN_VH3_SCF_10",
            },
        },
        "mutations": {
            "list": [],
        },
        "cmc": {
            "hotspots": [],
        },
        "immunogenicity": {
            "high_risk_epitopes": [],
        },
        "qa": {
            "version": "v3.5",
            "ok": True,
        },
    }


def main():
    print("=" * 80)
    print("（ Canonical Proxy ）")
    print("=" * 80)
    print()
    
    # 
    test_result = create_minimal_test_result()
    
    # 
    try:
        output_dir = PROJECT_ROOT / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = generate_client_report(
            test_result,
            output_dir,
            project_id="TEST_CLIENT_REPORT",
        )
        
        print(f"✅ : {report_path}")
        print()
        
        # （ Canonical Proxy ）
        report_content = report_path.read_text(encoding="utf-8")
        
        #  Canonical Proxy 
        if "CDR Canonical Proxy" in report_content:
            print("=" * 80)
            print(" Canonical Proxy :")
            print("=" * 80)
            
            lines = report_content.split("\n")
            in_section = False
            section_lines = []
            
            for i, line in enumerate(lines):
                if "## CDR Canonical Proxy" in line:
                    in_section = True
                    # 
                    start_idx = max(0, i - 2)
                    section_lines = lines[start_idx:i+20]
                    break
            
            if section_lines:
                print("\n".join(section_lines))
            else:
                # ，
                for i, line in enumerate(lines):
                    if "Canonical Proxy" in line or "CDR" in line:
                        start = max(0, i - 1)
                        end = min(len(lines), i + 15)
                        print("\n".join(lines[start:end]))
                        break
        else:
            print("⚠️   Canonical Proxy ")
        
        print()
        print("=" * 80)
        print(f": {report_path}")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ : {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())













