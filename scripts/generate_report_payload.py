#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


 result_stage12.json ，：
1. report_payload.json -  JSON （）
2. report_sections.md - /
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def extract_stage1_summary(stage1_data: Dict[str, Any]) -> Dict[str, Any]:
    """ Stage 1 """
    ranked_top10 = stage1_data.get("ranked_top10", [])
    selected = stage1_data.get("selected_scaffold", {})
    
    #  top10 
    top10_table = []
    for item in ranked_top10[:10]:
        top10_table.append({
            "rank": item.get("rank"),
            "scaffold_id": item.get("scaffold_id"),
            "framework_identity": round(item.get("framework_identity", 0), 4),
            "imgt_positions_compared": item.get("imgt_positions_compared", 0),
        })
    
    return {
        "top10_table": top10_table,
        "selected_scaffold": {
            "scaffold_id": selected.get("scaffold_id"),
            "rank": selected.get("rank"),
            "framework_identity": selected.get("framework_identity"),
            "region_counts": selected.get("region_counts", {}),
        }
    }


def extract_stage2_summary(stage2_data: Dict[str, Any]) -> Dict[str, Any]:
    """ Stage 2 """
    strategy_definitions = stage2_data.get("safe_strategy_definitions", {})
    safe_variants = stage2_data.get("safe_variants", {})
    
    # 
    strategies = {}
    for key in ["A", "B", "C"]:
        if key in strategy_definitions:
            strategies[f"SAFE_{key}"] = {
                "name": strategy_definitions[key].get("name"),
                "description": strategy_definitions[key].get("description"),
                "functional_meaning": strategy_definitions[key].get("functional_meaning"),
            }
    
    # 
    variants_summary = {}
    for variant_key in ["SAFE_A", "SAFE_B", "SAFE_C"]:
        if variant_key in safe_variants:
            variant = safe_variants[variant_key]
            variants_summary[variant_key] = {
                "template_id": variant.get("template_id"),
                "framework_full": variant.get("sequence", {}).get("framework_full", ""),
                "fr2": variant.get("sequence", {}).get("fr2", ""),
                "diff_count": len(variant.get("diff_vs_scaffold", [])),
                "actual_mutations": [
                    {
                        "imgt_pos": d.get("imgt_pos"),
                        "kabat_pos": d.get("kabat_pos"),
                        "from": d.get("from"),
                        "to": d.get("to"),
                        "region": d.get("region"),
                    }
                    for d in variant.get("diff_vs_scaffold", [])
                    if d.get("from") != d.get("to")
                ],
                "physiology_explanations": variant.get("physiology_explanations", []),
                "note": variant.get("note"),  #  " SAFE_B " 
            }
    
    #  SAFE_A  SAFE_B 
    seq_a = variants_summary.get("SAFE_A", {}).get("framework_full", "")
    seq_b = variants_summary.get("SAFE_B", {}).get("framework_full", "")
    safe_a_equals_safe_b = (seq_a == seq_b and seq_a != "")
    
    return {
        "strategy_definitions": strategies,
        "variants_summary": variants_summary,
        "safe_a_equals_safe_b": safe_a_equals_safe_b,
        "safe_a_equals_safe_b_reason": "scaffold  SAFE_B （ 44=Q, 47=G）， 37  gap" if safe_a_equals_safe_b else None,
    }


def extract_validation_summary(validation_data: Dict[str, Any]) -> Dict[str, Any]:
    """（ V2 schema）"""
    summary = {}
    
    for obj_key in ["query", "selected_scaffold"]:
        if obj_key not in validation_data:
            continue
        
        obj_val = validation_data[obj_key]
        
        #  V2 schema
        check_c_details = obj_val.get("check_c", {}).get("details", {})
        hallmark_v2 = check_c_details.get("hallmark_positions_v2", {})
        hallmark_old = check_c_details.get("hallmark_positions", {})  # 
        
        summary[obj_key] = {
            "check_a": {
                "pass": obj_val.get("check_a", {}).get("pass", False),
                "imgt_reconstruction_pass": obj_val.get("check_a", {}).get("details", {}).get("imgt_reconstruction", {}).get("pass", False),
                "kabat_reconstruction_pass": obj_val.get("check_a", {}).get("details", {}).get("kabat_reconstruction", {}).get("pass", False),
            },
            "check_b": {
                "pass": obj_val.get("check_b", {}).get("pass", False),
                "total_residues": obj_val.get("check_b", {}).get("details", {}).get("total_residues", 0),
                "checked_residues": obj_val.get("check_b", {}).get("details", {}).get("checked_residues", 0),
                "mismatch_count": len(obj_val.get("check_b", {}).get("details", {}).get("mismatches", [])),
            },
            "check_c": {
                "pass": obj_val.get("check_c", {}).get("pass", False),
                "hallmark_positions": hallmark_old,  # （deprecated）
                "hallmark_positions_v2": hallmark_v2,  # 
            },
        }
    
    return summary


def generate_report_payload(result_json_path: Path, output_dir: Path) -> None:
    """"""
    #  JSON
    with open(result_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    #  project_meta
    project_meta = {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": "stage12.v2",  #  schema 
        "algorithm": data.get("stage1", {}).get("scaffold_alignment_provenance", {}).get("algorithm", "imgt_position_identity"),
        "scheme": data.get("segmentation_provenance", {}).get("scheme", "imgt"),
        "method": data.get("segmentation_provenance", {}).get("method", "anarcii"),
        "package_version": data.get("segmentation_provenance", {}).get("package_version", "unknown"),
    }
    
    #  stage1_summary
    stage1_summary = extract_stage1_summary(data.get("stage1", {}))
    
    #  stage2_summary
    stage2_summary = extract_stage2_summary(data.get("stage2", {}))
    
    #  validation_summary
    validation_summary = extract_validation_summary(data.get("mapping_validation", {}))
    
    #  audit.md
    audit_md_path = output_dir / "audit_stage12.md"
    audit_content = ""
    if audit_md_path.exists():
        with open(audit_md_path, "r", encoding="utf-8") as f:
            audit_content = f.read()
    
    #  payload
    payload = {
        "project_meta": project_meta,
        "stage1_summary": stage1_summary,
        "stage2_summary": stage2_summary,
        "validation_summary": validation_summary,
        "audit": {
            "source": "audit_stage12.md",
            "content": audit_content,
        }
    }
    
    #  report_payload.json
    payload_path = output_dir / "report_payload.json"
    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"✅ report_payload.json : {payload_path}")
    
    #  report_sections.md
    generate_report_sections(payload, output_dir / "report_sections.md")
    
    return payload


def generate_report_sections(payload: Dict[str, Any], output_path: Path) -> None:
    """"""
    sections = []
    
    # 1. Project Meta
    sections.append("# \n")
    meta = payload["project_meta"]
    sections.append(f"- ****: {meta['generated_at']}")
    sections.append(f"- ****: {meta['algorithm']}")
    sections.append(f"- ****: {meta['scheme']}")
    sections.append(f"- ****: {meta['method']}")
    sections.append(f"- ****: {meta['package_version']}")
    sections.append("")
    
    # 2. Stage 1 Summary
    sections.append("# Stage 1: Scaffold \n")
    stage1 = payload["stage1_summary"]
    
    sections.append("## Top 10 Scaffold \n")
    sections.append("| Rank | Scaffold ID | Framework Identity | IMGT Positions Compared |")
    sections.append("|------|-------------|-------------------|------------------------|")
    for item in stage1["top10_table"]:
        sections.append(f"| {item['rank']} | {item['scaffold_id']} | {item['framework_identity']:.4f} | {item['imgt_positions_compared']} |")
    sections.append("")
    
    sections.append("##  Scaffold\n")
    selected = stage1["selected_scaffold"]
    sections.append(f"- **Scaffold ID**: {selected['scaffold_id']}")
    sections.append(f"- **Rank**: {selected['rank']}")
    sections.append(f"- **Framework Identity**: {selected['framework_identity']:.4f}")
    sections.append("")
    sections.append("### \n")
    sections.append("| Region | Match | Total |")
    sections.append("|--------|-------|-------|")
    for region, counts in selected.get("region_counts", {}).items():
        sections.append(f"| {region} | {counts.get('match', 0)} | {counts.get('total', 0)} |")
    sections.append("")
    
    # 3. Stage 2 Summary
    sections.append("# Stage 2: SAFE A/B/C \n")
    stage2 = payload["stage2_summary"]
    
    sections.append("## \n")
    for key, strategy in stage2["strategy_definitions"].items():
        sections.append(f"### {key}\n")
        sections.append(f"- ****: {strategy['name']}")
        sections.append(f"- ****: {strategy['description']}")
        sections.append(f"- ****: {strategy['functional_meaning']}")
        sections.append("")
    
    sections.append("## \n")
    variants = stage2["variants_summary"]
    
    # 
    sections.append("| Variant | Template ID | FR2 Sequence |  |  |")
    sections.append("|---------|-------------|--------------|--------|------------|")
    for key in ["SAFE_A", "SAFE_B", "SAFE_C"]:
        if key in variants:
            v = variants[key]
            sections.append(f"| {key} | {v['template_id']} | {v['fr2']} | {v['diff_count']} | {len(v['actual_mutations'])} |")
    sections.append("")
    
    # SAFE_A = SAFE_B 
    if stage2.get("safe_a_equals_safe_b"):
        sections.append("## ⚠️ \n")
        sections.append(f"**SAFE_A  SAFE_B **\n")
        sections.append(f": {stage2.get('safe_a_equals_safe_b_reason', '')}\n")
        sections.append("")
    
    # 
    for key in ["SAFE_A", "SAFE_B", "SAFE_C"]:
        if key not in variants:
            continue
        
        v = variants[key]
        sections.append(f"### {key} \n")
        
        if v.get("note"):
            sections.append(f"****: {v['note']}\n")
        
        if v["actual_mutations"]:
            sections.append("| IMGT Pos | Kabat Pos | From | To | Region |")
            sections.append("|----------|-----------|------|-----|--------|")
            for mut in v["actual_mutations"]:
                sections.append(f"| {mut.get('imgt_pos', 'N/A')} | {mut.get('kabat_pos', 'N/A')} | {mut.get('from')} | {mut.get('to')} | {mut.get('region', 'N/A')} |")
        else:
            sections.append("*（ scaffold）*")
        sections.append("")
    
    # 4. Validation Summary
    sections.append("# \n")
    validation = payload["validation_summary"]
    
    for obj_key in ["query", "selected_scaffold"]:
        if obj_key not in validation:
            continue
        
        obj_name = "Query" if obj_key == "query" else "Selected Scaffold"
        sections.append(f"## {obj_name}\n")
        
        val = validation[obj_key]
        
        # Check A
        sections.append("### Check A: \n")
        check_a = val["check_a"]
        sections.append(f"- IMGT : {'✅ PASS' if check_a['imgt_reconstruction_pass'] else '❌ FAIL'}")
        sections.append(f"- Kabat : {'✅ PASS' if check_a['kabat_reconstruction_pass'] else '❌ FAIL'}")
        sections.append("")
        
        # Check B
        sections.append("### Check B: \n")
        check_b = val["check_b"]
        sections.append(f"- : {check_b['total_residues']}")
        sections.append(f"- : {check_b['checked_residues']}")
        sections.append(f"- : {check_b['mismatch_count']}")
        sections.append(f"- : {'✅ PASS' if check_b['pass'] else '⚠️ '}")
        sections.append("")
        
        # Check C ( V2 schema)
        sections.append("### Check C: \n")
        check_c = val["check_c"]
        sections.append(f"- : {'✅ PASS' if check_c['pass'] else '❌ FAIL'}\n")
        
        #  V2 schema
        hallmark_v2 = check_c.get("hallmark_positions_v2", {})
        if hallmark_v2:
            sections.append("| Kabat Pos | Kabat Label | Kabat AA | Out-of-Domain | IMGT Label | IMGT AA | Mapping Status |")
            sections.append("|-----------|------------|----------|---------------|------------|---------|----------------|")
            for pos in ["37", "44", "45", "47"]:
                info = hallmark_v2.get(pos, {})
                kabat = info.get("kabat", {})
                imgt = info.get("imgt", {})
                mapping = info.get("mapping", {})
                
                #  Kabat AA
                if kabat.get("out_of_domain", False):
                    kabat_aa_display = f"{kabat.get('aa', 'N/A')} (out-of-domain)"
                elif kabat.get("residue_present"):
                    kabat_aa_display = kabat.get("aa", "N/A")
                else:
                    kabat_aa_display = "gap"
                
                #  IMGT AA
                imgt_aa_display = imgt.get("aa", "gap") if imgt.get("residue_present") else "gap"
                
                # Out-of-domain 
                out_of_domain_display = "✅" if kabat.get("out_of_domain", False) else "❌"
                
                sections.append(
                    f"| {pos} | {kabat.get('label', 'N/A')} | {kabat_aa_display} | {out_of_domain_display} | "
                    f"{imgt.get('label', 'N/A')} | {imgt_aa_display} | {mapping.get('status', 'N/A')} |"
                )
        else:
            # Fallback 
            sections.append("| Kabat Pos | Exists | AA | Mapped IMGT | IMGT AA | Reason |")
            sections.append("|-----------|--------|----|-------------|---------|--------|")
            for pos in ["37", "44", "45", "47"]:
                info = check_c.get("hallmark_positions", {}).get(pos, {})
                sections.append(f"| {pos} | {info.get('exists', False)} | {info.get('aa', 'N/A')} | {info.get('mapped_imgt_label', 'N/A')} | {info.get('mapped_imgt_aa', 'N/A')} | {info.get('reason', 'N/A')} |")
        sections.append("")
    
    # 5. Audit
    sections.append("# \n")
    sections.append(payload["audit"]["content"])
    
    # 
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sections))
    print(f"✅ report_sections.md : {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "output" / "result_stage12.json",
        help=" result_stage12.json ",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=PROJECT_ROOT / "output",
        help="",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("")
    print("=" * 80)
    print()
    
    if not args.input.exists():
        print(f"❌ : {args.input}")
        return
    
    args.out.mkdir(parents=True, exist_ok=True)
    
    try:
        payload = generate_report_payload(args.input, args.out)
        print()
        print("=" * 80)
        print("✅ ！")
        print("=" * 80)
    except Exception as e:
        print(f"\n❌ : {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

