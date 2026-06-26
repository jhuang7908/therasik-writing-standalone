#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VHH Classic Panel CLI

result JSON（）
：output/vhh_classic_panel.json + output/vhh_classic_panel.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.humanize.vhh_classic_panel import (
    generate_vhh_classic_panel,
    normalize_query_schema,
    VHHClassicPanelError,
)
from core.explain.decision_rationale_builder import _build_canonical_rationale
from core.numbering.dual_numbering import (
    get_dual_numbering,
    build_numbering_maps_json,
    DualNumberingError,
)
from core.numbering.imgt_anarcii import (
    imgt_number_anarcii,
    build_pos_to_aa_map,
    IMGTNumberingError,
)
from core.vhh_humanization import split_regions


def load_query_from_json(json_path: Path) -> Dict[str, Any]:
    """
    JSONquery
    
    Args:
        json_path: JSON
    
    Returns:
        query
    """
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    
    # JSON
    if "segments" in data:
        return data
    elif "regions" in data:
        return {"segments": data["regions"], "numbering_maps": data.get("numbering_maps", {})}
    elif "sequence" in data:
        # ，
        sequence = data["sequence"]
        return build_query_from_sequence(sequence)
    else:
        raise ValueError(f"Unknown JSON format in {json_path}")


def build_query_from_sequence(sequence: str) -> Dict[str, Any]:
    """
    query（）
    
    Args:
        sequence: 
    
    Returns:
        query
    """
    # 1. IMGT
    try:
        imgt_rows = imgt_number_anarcii(sequence)
    except IMGTNumberingError as e:
        raise ValueError(f"IMGT numbering failed: {e}") from e
    
    # 2. 
    segments = split_regions(imgt_rows)
    
    # 3. （IMGT + Kabat）
    try:
        imgt_rows_dual, kabat_rows, mapping = get_dual_numbering(sequence)
        numbering_maps = build_numbering_maps_json(imgt_rows_dual, kabat_rows, mapping)
    except DualNumberingError as e:
        # ，IMGT
        numbering_maps = {
            "imgt": [
                {"pos": str(row.get("pos", "")), "aa": row.get("aa", "")}
                for row in imgt_rows
            ],
        }
    
    return {
        "segments": segments,
        "numbering_maps": numbering_maps,
    }


def generate_markdown_report(result: Dict[str, Any], output_path: Path):
    """
    Markdown
    
    Args:
        result: generate_vhh_classic_panel
        output_path: 
    """
    lines = []
    lines.append("# VHH Classic Panel Humanization Report (Client Report)\n")
    lines.append(f"**Generated**: {result.get('timestamp', 'N/A')}\n")
    lines.append(f"**Pipeline Version**: {result.get('pipeline_version', 'N/A')}\n")
    lines.append("\n")
    lines.append("*Canonical analysis is an explanatory layer for structural compatibility. ")
    lines.append("It does not alter scaffold selection or humanization rules in the Classic Panel.*\n")
    lines.append("\n---\n")
    
    # ========================================================================
    # Gate (Pre-flight Check)
    # ========================================================================
    gate = result.get("gate", {})
    if gate:
        lines.append("## Gate (Pre-flight Check)\n\n")
        
        pass_level = gate.get("pass_level", "unknown")
        pass_level_display = pass_level.upper()
        lines.append(f"**Pass Level**: {pass_level_display}\n\n")
        
        flags = gate.get("flags", [])
        if flags:
            lines.append("**Flags**:\n")
            for flag in flags:
                lines.append(f"- {flag}\n")
            lines.append("\n")
        else:
            lines.append("**Flags**: None\n\n")
        
        metrics = gate.get("metrics", {})
        if metrics:
            lines.append("**Metrics**:\n")
            lines.append(f"- CDR3 Length: {metrics.get('cdr3_len', 'N/A')}\n")
            lines.append(f"- Total Cys Count: {metrics.get('total_cys_count', 'N/A')}\n")
            lines.append(f"- Best FR Identity: {metrics.get('best_fr_identity', 'N/A'):.4f}\n")
            lines.append(f"- Best Scaffold ID: {metrics.get('best_fr_identity_scaffold_id', 'N/A')}\n")
            if metrics.get("length_mismatch", False):
                lines.append("- Length Mismatch: Yes\n")
            lines.append("\n")
        
        recommendations = gate.get("recommendations", {})
        if recommendations:
            lines.append("**Recommendations**:\n")
            suggest_j_region = recommendations.get("suggest_j_region", "N/A")
            lines.append(f"- Suggested J Region: {suggest_j_region}\n")
            
            suggest_scaffold_rank = recommendations.get("suggest_scaffold_rank", [])
            if suggest_scaffold_rank:
                lines.append("- Suggested Scaffold Rank:\n")
                for idx, item in enumerate(suggest_scaffold_rank, 1):
                    scaffold_id = item.get("scaffold_id", "N/A")
                    rationale = item.get("rationale", "N/A")
                    lines.append(f"  {idx}. {scaffold_id} - {rationale}\n")
            lines.append("\n")
        
        lines.append("---\n\n")
    
    # ========================================================================
    # Rulebook Summary (Rulebook v1.0)
    # ========================================================================
    rulebook_summary = result.get("rulebook_summary", {})
    if rulebook_summary:
        lines.append("## Rulebook Summary\n\n")
        
        lines.append(f"**Rulebook Version**: {rulebook_summary.get('rulebook_version', 'N/A')}\n")
        lines.append(f"**Mode**: {rulebook_summary.get('mode', 'N/A').upper()}\n\n")
        
        triggered_rules = rulebook_summary.get("triggered_rules", [])
        if triggered_rules:
            lines.append("**Triggered Rules**:\n")
            for rule_id in triggered_rules:
                lines.append(f"- {rule_id}\n")
            lines.append("\n")
        else:
            lines.append("**Triggered Rules**: None\n\n")
        
        disabled_high_risk = rulebook_summary.get("disabled_high_risk_rules", [])
        if disabled_high_risk:
            lines.append("**Disabled High-Risk Rules** (not enabled in current mode):\n")
            for rule_info in disabled_high_risk:
                rule_id = rule_info.get("rule_id", "N/A")
                layer = rule_info.get("layer", "N/A")
                risk_level = rule_info.get("risk_level", "N/A")
                reason = rule_info.get("reason", "N/A")
                lines.append(f"- **{rule_id}** (Layer {layer}, Risk: {risk_level}): {reason}\n")
            lines.append("\n")
        
        total_mutations = rulebook_summary.get("total_mutations", 0)
        lines.append(f"**Total Mutations Applied**: {total_mutations}\n\n")
        
        lines.append("---\n\n")
    
    # ========================================================================
    # Canonical Risk Overview Table (Client Report - Top)
    # ========================================================================
    canonical_compat = result.get("canonical_compatibility", {})
    
    if canonical_compat:
        lines.append("## Canonical Compatibility Overview\n\n")
        lines.append("| Scaffold | Canonical Risk |\n")
        lines.append("|----------|----------------|\n")
        
        # ：low → medium → high
        risk_order = {"low": 0, "medium": 1, "high": 2}
        sorted_scaffolds = sorted(
            canonical_compat.items(),
            key=lambda x: risk_order.get(x[1].get("risk_level", "unknown").lower(), 99)
        )
        
        for scaffold_id, compat_info in sorted_scaffolds:
            risk_level = compat_info.get("risk_level", "unknown").lower()
            # ：low → Low, medium → Medium, high → High
            risk_display = risk_level.capitalize() if risk_level in ("low", "medium", "high") else risk_level
            
            lines.append(f"| {scaffold_id} | {risk_display} |\n")
        
        lines.append("\n")
        lines.append("*Note: Canonical analysis is an explanatory layer for structural compatibility. ")
        lines.append("It does not alter scaffold selection or humanization rules.*\n")
        lines.append("\n---\n\n")
    
    # ========================================================================
    # Panel Results (Sorted by Canonical Risk)
    # ========================================================================
    classic_panel = result.get("classic_panel", [])
    
    # canonical（，JSON）
    risk_order = {"low": 0, "medium": 1, "high": 2, "unknown": 99}
    classic_panel_sorted = sorted(
        classic_panel,
        key=lambda x: risk_order.get(x.get("canonical_risk_level", "unknown").lower(), 99)
    )
    
    for idx, entry in enumerate(classic_panel_sorted, 1):
        scaffold_id = entry.get("scaffold_id", "N/A")
        j_region_id = entry.get("j_region_id", "N/A")
        
        lines.append(f"## {idx}. {scaffold_id} × {j_region_id}\n")
        
        # Scaffold Selection / Rationale
        lines.append("### Scaffold Selection\n\n")
        lines.append(f"Selected scaffold: **{scaffold_id}** with J region: **{j_region_id}**\n\n")
        
        # Canonical Compatibility (CDR1 / CDR2) - Client-friendly language
        canonical_risk = entry.get("canonical_risk_level", "unknown")
        canonical_rationale_en, canonical_rationale_zh = _build_canonical_rationale(canonical_risk)
        
        lines.append("### Canonical Compatibility (CDR1 / CDR2)\n\n")
        lines.append(f"{canonical_rationale_zh}\n\n")
        
        # 
        lines.append("### Output Sequence\n")
        lines.append("```\n")
        lines.append(f"{entry.get('sequence_final', 'N/A')}\n")
        lines.append("```\n\n")
        
        # 
        mutations = entry.get("mutations", [])
        if mutations:
            lines.append("### Mutations\n")
            lines.append("| Position | From | To | Rule | Rationale |\n")
            lines.append("|----------|------|----|----|-----------|\n")
            
            for mut in mutations:
                numbering = mut.get("numbering", {})
                kabat_pos = numbering.get("kabat", "N/A")
                imgt_pos = numbering.get("imgt", "N/A")
                pos_label = f"Kabat {kabat_pos}" + (f" (IMGT {imgt_pos})" if imgt_pos else "")
                
                # Rulebook v1.0: layerrisk_level
                layer = mut.get("layer", "N/A")
                risk_level = mut.get("risk_level", "N/A")
                rule_id = mut.get("rule_id", "N/A")
                rule_label = f"{rule_id} (Layer {layer}, Risk: {risk_level})"
                
                lines.append(
                    f"| {pos_label} | {mut.get('from_aa', 'N/A')} | "
                    f"{mut.get('to_aa', 'N/A')} | {rule_label} | "
                    f"{mut.get('rationale', 'N/A')} |\n"
                )
        else:
            lines.append("### Mutations\n")
            lines.append("No mutations applied.\n\n")
        
        # 
        mutation_summary = entry.get("mutation_summary", {})
        lines.append("### Mutation Summary\n")
        lines.append(f"- **Hallmark Applied**: {mutation_summary.get('hallmark_applied', False)}\n")
        lines.append(f"- **Vernier Applied**: {mutation_summary.get('vernier_applied', False)}\n")
        lines.append(f"- **Total Mutations**: {mutation_summary.get('n_mutations_total', 0)}\n")
        lines.append(f"- **Vernier Backfill Count**: {mutation_summary.get('vernier_backfill_count', 0)}\n\n")
        
        # Canonical Compatibility (CDR1 / CDR2) - Client-friendly language
        canonical_risk = entry.get("canonical_risk_level", "unknown")
        canonical_rationale_en, canonical_rationale_zh = _build_canonical_rationale(canonical_risk)
        
        lines.append("### Canonical Compatibility (CDR1 / CDR2)\n\n")
        lines.append(f"{canonical_rationale_zh}\n\n")
        
        # QA
        qa = entry.get("qa", {})
        lines.append("### QA\n")
        lines.append(f"- **CDR Integrity**: {'✓' if qa.get('cdr_integrity_ok', False) else '✗'}\n")
        lines.append(f"- **Numbering Consistency**: {'✓' if qa.get('numbering_consistency_ok', False) else '✗'}\n\n")
        
        lines.append("---\n\n")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("".join(lines))


def main():
    parser = argparse.ArgumentParser(
        description="Generate VHH Classic Panel humanization results"
    )
    parser.add_argument(
        "input",
        type=str,
        help="Input: JSON file path or sequence string",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Output directory (default: output)",
    )
    parser.add_argument(
        "--scaffolds",
        type=str,
        nargs="+",
        help="Scaffold IDs to use (default: all)",
    )
    parser.add_argument(
        "--j-regions",
        type=str,
        nargs="+",
        help="J region IDs to use (default: all)",
    )
    parser.add_argument(
        "--sequence",
        action="store_true",
        help="Treat input as sequence string instead of JSON file",
    )
    
    args = parser.parse_args()
    
    # 
    if args.sequence:
        # 
        query = build_query_from_sequence(args.input)
    else:
        # JSON
        json_path = Path(args.input)
        if not json_path.exists():
            print(f"Error: File not found: {json_path}", file=sys.stderr)
            sys.exit(1)
        query = load_query_from_json(json_path)
    
    # panel
    panel_config = {}
    if args.scaffolds:
        panel_config["scaffolds"] = args.scaffolds
    if args.j_regions:
        panel_config["j_regions"] = args.j_regions
    
    # panel
    try:
        result = generate_vhh_classic_panel(query, panel_config)
    except VHHClassicPanelError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # JSON
    json_output = output_dir / "vhh_classic_panel.json"
    with open(json_output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"JSON output: {json_output}")
    
    # Markdown
    md_output = output_dir / "vhh_classic_panel.md"
    generate_markdown_report(result, md_output)
    print(f"Markdown output: {md_output}")


if __name__ == "__main__":
    main()

