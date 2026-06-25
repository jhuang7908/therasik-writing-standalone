"""
ADC Design Engine — CLI Entry Point & Integration Test
======================================================
Run three demonstration queries covering solid tumor, liquid tumor,
and autoimmune disease to validate the full decision pipeline.

Usage
-----
    conda activate anarcii
    python -m core.adc_design.run_adc_design
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.adc_design.adc_decision_engine import ADCDesignEngine
from core.adc_design.adc_design_report import ADCDesignReport

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output" / "adc_design"


def run_demo():
    engine = ADCDesignEngine()

    print("=" * 70)
    print("InSynBio ADC Intelligent Design Engine — Integration Test")
    print("=" * 70)

    print("\n[INFO] Supported diseases:")
    for cat, subtypes in engine.get_supported_diseases().items():
        print(f"  {cat}: {', '.join(subtypes[:5])}{'...' if len(subtypes) > 5 else ''}")

    test_cases = [
        {
            "label": "Case 1: HER2+ Breast Cancer (Solid Tumor)",
            "disease_type": "solid_tumor",
            "disease_subtype": "breast_HER2_pos",
            "cmc_priority": "high",
            "fto_concern": "moderate",
        },
        {
            "label": "Case 2: DLBCL (Liquid Tumor)",
            "disease_type": "liquid_tumor",
            "disease_subtype": "dlbcl",
            "cmc_priority": "moderate",
            "fto_concern": "moderate",
        },
        {
            "label": "Case 3: NSCLC with EGFR Mutation",
            "disease_type": "solid_tumor",
            "disease_subtype": "nsclc_egfr_mutant",
            "cmc_priority": "moderate",
            "fto_concern": "high",
        },
    ]

    for tc in test_cases:
        label = tc.pop("label")
        print(f"\n{'─' * 60}")
        print(f"  {label}")
        print(f"{'─' * 60}")

        proposals = engine.recommend(**tc, top_n=5)

        if not proposals:
            print("  [WARN] No proposals generated.")
            continue

        for p in proposals:
            score_str = f"{p.score_total * 100:.1f}%"
            warn_flag = " ⚠" if p.safety_warnings else ""
            print(
                f"  #{p.rank}  {p.target_antigen:12s} + {p.payload_name:15s} "
                f"| DAR {p.dar_range[0]:.1f}-{p.dar_range[1]:.1f} "
                f"| Bystander: {'Y' if p.bystander_effect else 'N'} "
                f"| {p.conjugation_method:30s} "
                f"| Score: {score_str}{warn_flag}"
            )
            if p.precedent_programs:
                print(f"       Precedents: {', '.join(p.precedent_programs[:3])}")
            if p.fto_alerts:
                print(f"       FTO: {p.fto_alerts[0]}")

        query_params = {
            **tc,
            "label": label,
        }
        report = ADCDesignReport(proposals, query_params)

        safe_name = label.replace(" ", "_").replace(":", "").replace("(", "").replace(")", "").lower()
        md_path = report.write_markdown(OUTPUT_DIR / f"{safe_name}.md")
        json_path = report.write_json(OUTPUT_DIR / f"{safe_name}.json")
        print(f"  [OK] Reports: {md_path.name}, {json_path.name}")

    print(f"\n{'=' * 70}")
    print(f"All reports written to: {OUTPUT_DIR}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    run_demo()
