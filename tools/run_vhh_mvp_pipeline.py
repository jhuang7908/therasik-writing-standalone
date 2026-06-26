#!/usr/bin/env python3
"""
7D12 VHH MVP Pipeline v0.1 CLI

One-command execution: Step1 (A+B) → Gate → Step2 (A⁺+B⁺) → Reports
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Dict, Any
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.mvp.step1_eps import generate_step1a_candidates
from core.mvp.step1_cluster import generate_step1b_candidates
from core.mvp.gate import apply_gate
from core.mvp.step2_variants import generate_step2_variants
from core.mvp.report_dev_md import generate_dev_report


def load_dual_map(input_path: str) -> Dict[str, Any]:
    """Load dual map JSON file"""
    with open(input_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Dict[str, Any], output_path: Path):
    """Save data as JSON"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_excel_comparison(
    step1_candidates: list,
    gate_decision: Dict[str, Any],
    step2_variants: list,
    output_path: Path
):
    """Save comparison Excel with multiple sheets"""
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Sheet 1: Step1 Candidates
        if step1_candidates:
            df_step1 = pd.DataFrame(step1_candidates)
            df_step1.to_excel(writer, sheet_name='Step1Candidates', index=False)
        
        # Sheet 2: Gate Decision
        pass_a = gate_decision.get("pass_A")
        pass_b = gate_decision.get("pass_B")
        gate_data = {
            "pass_A_id": [pass_a.get("candidate_id", "None") if pass_a else "None"],
            "pass_B_id": [pass_b.get("candidate_id", "None") if pass_b else "None"],
            "rejected_count": [len(gate_decision.get("rejected", []))]
        }
        df_gate = pd.DataFrame(gate_data)
        df_gate.to_excel(writer, sheet_name='GateDecision', index=False)
        
        # Sheet 3: Step2 Variants
        if step2_variants:
            df_step2 = pd.DataFrame(step2_variants)
            df_step2.to_excel(writer, sheet_name='Step2Variants', index=False)


def main():
    parser = argparse.ArgumentParser(
        description="7D12 VHH MVP Pipeline v0.1: Step1 → Gate → Step2 → Reports"
    )
    parser.add_argument(
        "--input_dualmap",
        type=str,
        required=True,
        help="Path to input dual map JSON file"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="Output directory for results"
    )
    parser.add_argument(
        "--project_name",
        type=str,
        default="EGFR_7D12_VHH",
        help="Project name (default: EGFR_7D12_VHH)"
    )
    parser.add_argument(
        "--eps_db",
        type=str,
        default=None,
        help="Optional path to EPS scaffold database"
    )
    parser.add_argument(
        "--cluster_db",
        type=str,
        default=None,
        help="Optional path to cluster scaffold database"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("7D12 VHH MVP Pipeline v0.1")
    print("=" * 80)
    
    # Step 1: Load input
    print(f"\n[Step 0] Loading input: {args.input_dualmap}")
    mapping_result = load_dual_map(args.input_dualmap)
    print(f"  ✓ Loaded dual map: {len(mapping_result.get('dual_map', []))} residues")
    
    # Step 1-A: Generate EPS candidates
    print(f"\n[Step 1-A] Generating EPS candidates...")
    step1a_candidates = generate_step1a_candidates(mapping_result, args.eps_db)
    print(f"  ✓ Generated {len(step1a_candidates)} EPS candidates")
    
    # Step 1-B: Generate Cluster candidates
    print(f"\n[Step 1-B] Generating Cluster candidates...")
    step1b_candidates = generate_step1b_candidates(mapping_result, args.cluster_db)
    print(f"  ✓ Generated {len(step1b_candidates)} Cluster candidates")
    
    # Combine Step1 candidates
    step1_candidates = step1a_candidates + step1b_candidates
    
    # Gate: Apply quality control
    print(f"\n[Gate] Applying quality control gate...")
    gate_decision = apply_gate(step1_candidates, mapping_result)
    pass_a = gate_decision.get("pass_A")
    pass_b = gate_decision.get("pass_B")
    print(f"  ✓ Pass A: {pass_a.get('candidate_id') if pass_a else 'None'}")
    print(f"  ✓ Pass B: {pass_b.get('candidate_id') if pass_b else 'None'}")
    print(f"  ✓ Rejected: {len(gate_decision.get('rejected', []))} candidates")
    
    # Step 2: Generate variants
    print(f"\n[Step 2] Generating A⁺ and B⁺ variants...")
    step2_variants = generate_step2_variants(gate_decision, mapping_result)
    print(f"  ✓ Generated {len(step2_variants)} variants")
    
    # Save outputs
    print(f"\n[Saving] Writing output files...")
    
    # JSON outputs
    save_json({"candidates": step1_candidates}, output_dir / "step1_candidates.json")
    save_json(gate_decision, output_dir / "gate_decision.json")
    save_json({"variants": step2_variants}, output_dir / "step2_variants.json")
    
    # Excel comparison
    save_excel_comparison(step1_candidates, gate_decision, step2_variants, output_dir / "mvp_comparison.xlsx")
    
    print(f"  ✓ step1_candidates.json")
    print(f"  ✓ gate_decision.json")
    print(f"  ✓ step2_variants.json")
    print(f"  ✓ mvp_comparison.xlsx")
    
    # Generate developer report
    print(f"\n[Report] Generating developer report...")
    report_path = output_dir / f"{args.project_name}_MVP_dev_report.md"
    generate_dev_report(
        mapping_result,
        step1a_candidates,
        step1b_candidates,
        gate_decision,
        step2_variants,
        report_path
    )
    print(f"  ✓ {report_path.name}")
    
    print("\n" + "=" * 80)
    print("MVP Pipeline completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()

