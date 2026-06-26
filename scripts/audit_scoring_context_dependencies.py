#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


 stage1_select_scaffold ：
- framework_identity 
- canonical_proxy 
- vhh_hallmark 
- 
- 
"""

from __future__ import annotations

import argparse
import ast
import inspect
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def analyze_function_dependencies(func_source: str, func_name: str) -> Dict[str, Any]:
    """
    
    
    Args:
        func_source: 
        func_name: 
    
    Returns:
        
    """
    tree = ast.parse(func_source)
    
    dependencies = {
        "imports": [],
        "function_calls": [],
        "variable_reads": set(),
        "variable_writes": set(),
        "conditions": [],
    }
    
    for node in ast.walk(tree):
        #  import
        if isinstance(node, ast.Import):
            for alias in node.names:
                dependencies["imports"].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                dependencies["imports"].append(f"{module}.{alias.name}")
        
        # 
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                dependencies["function_calls"].append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                dependencies["function_calls"].append(node.func.attr)
        
        # 
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            dependencies["variable_reads"].add(node.id)
        
        # 
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            dependencies["variable_writes"].add(node.id)
        
        # 
        if isinstance(node, ast.If):
            if isinstance(node.test, ast.Compare):
                left = ast.unparse(node.test.left) if hasattr(ast, 'unparse') else str(node.test.left)
                dependencies["conditions"].append(left)
    
    dependencies["variable_reads"] = sorted(list(dependencies["variable_reads"]))
    dependencies["variable_writes"] = sorted(list(dependencies["variable_writes"]))
    
    return dependencies


def audit_scoring_context_dependencies() -> str:
    """
    
    
    Returns:
        Markdown 
    """
    lines = []
    lines.append("# ")
    lines.append("")
    lines.append(" `stage1_select_scaffold` 。")
    lines.append("")
    
    #  stage12_germline_selection.py
    stage12_path = PROJECT_ROOT / "scripts" / "stage12_germline_selection.py"
    if not stage12_path.exists():
        lines.append("❌ ****: `scripts/stage12_germline_selection.py` ")
        return "\n".join(lines)
    
    with open(stage12_path, "r", encoding="utf-8") as f:
        stage12_source = f.read()
    
    #  stage1_select_scaffold 
    lines.append("## 1. Framework Identity ")
    lines.append("")
    lines.append("### ")
    lines.append("")
    lines.append("1. ****:")
    lines.append("   - `query_seq`: ")
    lines.append("   - `scaffold_library`: scaffold ")
    lines.append("   - `mask_regions`: （: CDR1, CDR2, CDR3）")
    lines.append("")
    lines.append("2. ****:")
    lines.append("   -  query  scaffold  IMGT （`run_anarcii_imgt`）")
    lines.append("   - （`target_pos_map`, `scaffold_pos_map`）")
    lines.append("   -  FR （ CDR ）")
    lines.append("   - `framework_identity = total_match / total_positions`")
    lines.append("")
    lines.append("3. ****:")
    lines.append("   - `core.segmentation.anarcii_adapter.run_anarcii_imgt`")
    lines.append("")
    
    lines.append("## 2. Canonical Proxy ")
    lines.append("")
    lines.append("### ")
    lines.append("")
    lines.append("1. ** 1: scaffold_entry **")
    lines.append("   -  `scaffold_entry.get('canonical_proxy_cdr1')`")
    lines.append("   -  `scaffold_entry.get('canonical_proxy_cdr2')`")
    lines.append("   - ，")
    lines.append("")
    lines.append("2. ** 2: germline_record **")
    lines.append("   -  `scaffold_entry.member_ids`  sequence_id")
    lines.append("   -  `germline_assets` ")
    lines.append("   - :")
    lines.append("     - : `{prefix}|Homo`")
    lines.append("     - : `{prefix}` ()")
    lines.append("   -  `germline_record.get('canonical_proxy_cdr1/cdr2')` ")
    lines.append("")
    lines.append("3. ****:")
    lines.append("   - `core.germline_assets_loader.load_all_clean_germline_assets(include_canonical_proxy=True, version=germline_db)`")
    lines.append("   -  `germline_db` （`v1_clean`  `vhh_v1`）")
    lines.append("")
    lines.append("4. ****:")
    lines.append("   - `core.scoring.canonical_proxy.apply_canonical_proxy_to_score(candidate, canonical_proxy_config)`")
    lines.append("   - : `agg_mode='min'`, `weight=0.10`, `floor_if_missing=0.0`")
    lines.append("")
    
    lines.append("## 3. VHH Hallmark ")
    lines.append("")
    lines.append("### ")
    lines.append("")
    lines.append("- ****: `germline_db == 'vhh_v1'`")
    lines.append("- ****: `vhh_hallmark_weight` ( 0.15)")
    lines.append("")
    lines.append("### ")
    lines.append("")
    lines.append("1. ** 1: scaffold_entry **")
    lines.append("   -  `scaffold_entry.get('vhh_hallmark')`")
    lines.append("   -  `vhh_hallmark_config['enabled'] == True`，")
    lines.append("")
    lines.append("2. ** 2: germline_record **")
    lines.append("   -  `germline_record.get('vhh_hallmark')` ")
    lines.append("   -  `vhh_hallmark_config['enabled'] == True` ")
    lines.append("")
    lines.append("3. ****:")
    lines.append("   -  canonical_proxy ")
    lines.append("   -  `germline_db='vhh_v1'` ")
    lines.append("")
    
    lines.append("## 4. ")
    lines.append("")
    lines.append("### Total Score ")
    lines.append("")
    lines.append("```python")
    lines.append("# ")
    lines.append("w_id = 0.75")
    lines.append("w_proxy = 0.10")
    lines.append("w_hallmark = 0.15")
    lines.append("")
    lines.append("# Fixed （hallmark  0）")
    lines.append("total_score_fixed = (")
    lines.append("    framework_identity * w_id +")
    lines.append("    canonical_proxy_agg * w_proxy +")
    lines.append("    vhh_hallmark_score * w_hallmark")
    lines.append(")")
    lines.append("")
    lines.append("# Norm （hallmark ）")
    lines.append("if hallmark_available == 0:")
    lines.append("    w_id_norm = w_id / (w_id + w_proxy)  # 0.75 / 0.85 ≈ 0.8824")
    lines.append("    w_proxy_norm = w_proxy / (w_id + w_proxy)  # 0.10 / 0.85 ≈ 0.1176")
    lines.append("    total_score_norm = (")
    lines.append("        framework_identity * w_id_norm +")
    lines.append("        canonical_proxy_agg * w_proxy_norm")
    lines.append("    )")
    lines.append("else:")
    lines.append("    total_score_norm = total_score_fixed")
    lines.append("```")
    lines.append("")
    
    lines.append("### ")
    lines.append("")
    lines.append("|  |  |  |  |")
    lines.append("|------|---------|---------|---------|")
    lines.append("| framework_identity | query_seq, scaffold_library, IMGT | - |  |")
    lines.append("| canonical_proxy | germline_assets  scaffold_entry | - | floor_if_missing=0.0 |")
    lines.append("| vhh_hallmark | germline_db='vhh_v1' | scaffold_entry  germline_record | 0 |")
    lines.append("")
    
    lines.append("## 5. ")
    lines.append("")
    lines.append("### v1_clean ")
    lines.append("")
    lines.append("- **germline_db**: `v1_clean`")
    lines.append("- **canonical_proxy**: ✅ （ 0.10）")
    lines.append("- **vhh_hallmark**: ❌ （`vhh_hallmark_config['enabled'] = False`）")
    lines.append("- ****: `data/germlines/v1_clean/`")
    lines.append("")
    
    lines.append("### vhh_v1 ")
    lines.append("")
    lines.append("- **germline_db**: `vhh_v1`")
    lines.append("- **canonical_proxy**: ✅ （ 0.10）")
    lines.append("- **vhh_hallmark**: ✅ （ 0.15，）")
    lines.append("- ****: `data/germlines/vhh_v1/`")
    lines.append("- ****:")
    lines.append("  -  manifest.json  scaffold_library")
    lines.append("  -  `use_special_fr_templates` ")
    lines.append("")
    
    lines.append("## 6. ")
    lines.append("")
    lines.append("```")
    lines.append("query_seq")
    lines.append("  ↓")
    lines.append("run_anarcii_imgt() → target_pos_map")
    lines.append("  ↓")
    lines.append("scaffold_library")
    lines.append("  ↓")
    lines.append("for each scaffold:")
    lines.append("  run_anarcii_imgt() → scaffold_pos_map")
    lines.append("  ↓")
    lines.append("  FR position comparison → framework_identity")
    lines.append("  ↓")
    lines.append("  [ canonical_proxy]")
    lines.append("    ├─ scaffold_entry (1)")
    lines.append("    └─ germline_record (2)")
    lines.append("  ↓")
    lines.append("  apply_canonical_proxy_to_score() → canonical_proxy_agg")
    lines.append("  ↓")
    lines.append("  [ vhh_hallmark] ( vhh_v1 )")
    lines.append("    ├─ scaffold_entry (1)")
    lines.append("    └─ germline_record (2)")
    lines.append("  ↓")
    lines.append("  calculate_scores() → total_score_fixed, total_score_norm")
    lines.append("  ↓")
    lines.append("  sort by total_score → ranked_top10")
    lines.append("```")
    lines.append("")
    
    lines.append("## 7. ")
    lines.append("")
    lines.append("### ")
    lines.append("")
    lines.append("1. ✅ **germline_assets **")
    lines.append("   - ，canonical_proxy  vhh_hallmark  germline_record ")
    lines.append("   -  scaffold_entry （）")
    lines.append("")
    lines.append("2. ✅ **scaffold_entry **")
    lines.append("   -  vhh_scaffold_library_v1.jsonl， `canonical_proxy_cdr1/cdr2`  `vhh_hallmark`")
    lines.append("   -  human_vh3_scaffolds.json，")
    lines.append("")
    lines.append("3. ✅ **germline_db **")
    lines.append("   - `v1_clean`:  vhh_hallmark")
    lines.append("   - `vhh_v1`:  vhh_hallmark")
    lines.append("")
    
    lines.append("### ")
    lines.append("")
    lines.append("1. ⚠️  **member_ids **")
    lines.append("   -  scaffold_entry  canonical_proxy/vhh_hallmark")
    lines.append("   -  member_ids  germline_record")
    lines.append("   - ，")
    lines.append("")
    lines.append("2. ⚠️  ****")
    lines.append("   - Case B (human_vh3_scaffolds)  vhh_hallmark")
    lines.append("   -  `total_score_norm` ")
    lines.append("   - `total_score_fixed` ")
    lines.append("")
    
    lines.append("## 8. ")
    lines.append("")
    lines.append("### ")
    lines.append("")
    lines.append("1. **Framework Identity**:")
    lines.append("   - : query_seq, scaffold_library, IMGT")
    lines.append("   - : ✅ ，")
    lines.append("")
    lines.append("2. **Canonical Proxy**:")
    lines.append("   - : germline_assets  scaffold_entry")
    lines.append("   - : ⚠️ ， scaffold_entry ")
    lines.append("")
    lines.append("3. **VHH Hallmark**:")
    lines.append("   - : germline_db='vhh_v1', germline_assets  scaffold_entry")
    lines.append("   - : ⚠️ ， vhh_v1 ")
    lines.append("")
    lines.append("### ")
    lines.append("")
    lines.append("- **Fixed **: （0）")
    lines.append("- **Norm **:  hallmark ，")
    lines.append("")
    
    lines.append("## 9. ")
    lines.append("")
    lines.append("1. ****:  scaffold_entry  canonical_proxy  vhh_hallmark ")
    lines.append("2. ****:  `total_score_norm` ，`total_score_fixed` ")
    lines.append("3. ****:  germline_assets ，（ scaffold_entry）")
    lines.append("4. ****:  vhh_v1  scaffold_entry  VHH ")
    lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description=""
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "output" / "scoring_context_audit.md",
        help=" Markdown ",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("")
    print("=" * 80)
    print()
    
    # 
    report = audit_scoring_context_dependencies()
    
    # 
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"✅ : {args.output}")
    print()
    print("=" * 80)
    print("✅ ！")
    print("=" * 80)


if __name__ == "__main__":
    main()










