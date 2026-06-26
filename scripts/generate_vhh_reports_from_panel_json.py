#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VHH Classic Panel 

 Classic Panel JSON ：
1. Client CRO Report（）：、
2. Developer Audit Report（）：、
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# 
# ============================================================================

RISK_LEVEL_ORDER = {"low": 0, "medium": 1, "high": 2}


def load_panel_json(json_path: Path) -> Dict[str, Any]:
    """Classic Panel JSON"""
    if not json_path.exists():
        raise FileNotFoundError(f"JSON: {json_path}")
    
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    
    # 
    if "classic_panel" not in data:
        raise ValueError("JSON 'classic_panel' ")
    
    if len(data["classic_panel"]) != 8:
        print(f"[WARN] 8variant，{len(data['classic_panel'])}")
    
    return data


def calculate_sha256(sequence: str) -> str:
    """SHA256"""
    return hashlib.sha256(sequence.encode("utf-8")).hexdigest()


def sort_variants_for_client(variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    variants
    
    ：
    1. canonical_risk_level: low → medium → high
    2. mutation_count: 
    """
    def sort_key(v: Dict[str, Any]) -> Tuple[int, int]:
        risk = v.get("canonical_risk_level", "high")
        risk_order = RISK_LEVEL_ORDER.get(risk, 99)
        mut_count = v.get("mutation_summary", {}).get("n_mutations_total", 999)
        return (risk_order, mut_count)
    
    return sorted(variants, key=sort_key)


def get_canonical_risk_explanation(risk_level: str) -> str:
    """canonical"""
    explanations = {
        "low": "CDR1CDR2，。",
        "medium": "CDR1CDR2，。",
        "high": "CDR1CDR2，。",
    }
    return explanations.get(risk_level, "。")


# ============================================================================
# Client CRO Report 
# ============================================================================

def generate_client_cro_report(data: Dict[str, Any], output_dir: Path, project_name: str = "7D12") -> Path:
    """Client CRO Report（）"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    lines = []
    
    # 
    lines.append(f"# {project_name} VHH Classic Panel （）\n")
    lines.append(f"**：** {datetime.now().strftime('%Y%m%d')}\n")
    lines.append("---\n\n")
    
    # 0. Pre-flight Quality Gate
    lines.append("## 0. Pre-flight Quality Gate\n\n")
    
    preflight_checks = data.get("preflight_checks", {})
    cys_check = preflight_checks.get("vhh_cys_check", {})
    
    if cys_check:
        status = cys_check.get("status", "unknown")
        severity = cys_check.get("severity", "unknown")
        core_pair_present = cys_check.get("core_pair_present", False)
        extra_cys = cys_check.get("extra_cys_positions", {})
        has_extra_cys = len(extra_cys.get("imgt", [])) > 0 or len(extra_cys.get("kabat", [])) > 0
        
        # Core disulfide pair
        if core_pair_present:
            lines.append("**Core disulfide pair**: PASS\n")
        else:
            lines.append("**Core disulfide pair**: FAIL\n")
            lines.append("\n，/VHH。\n")
        
        # Extra cysteines
        if has_extra_cys:
            lines.append("**Extra cysteines**: DETECTED (Warning)\n")
        else:
            lines.append("**Extra cysteines**: NONE\n")
        
        # ，
        messages = cys_check.get("messages", [])
        if messages:
            first_msg = messages[0]
            if first_msg.get("code") == "VHH_CYS_CORE_PAIR_MISSING":
                lines.append(f"\n****: {first_msg.get('text_zh', first_msg.get('text_en', ''))}\n")
    else:
        lines.append("**Core disulfide pair**: N/A\n")
        lines.append("**Extra cysteines**: N/A\n")
    
    lines.append("\n---\n\n")
    
    # 1. Decision Summary
    lines.append("## 1. （Decision Summary）\n\n")
    
    variants = data.get("classic_panel", [])
    sorted_variants = sort_variants_for_client(variants)
    
    if sorted_variants:
        top1 = sorted_variants[0]
        top2 = sorted_variants[1] if len(sorted_variants) > 1 else None
        
        lines.append("###  Top 1\n\n")
        lines.append(f"**Scaffold**: {top1.get('scaffold_id', 'N/A')}\n")
        lines.append(f"**J Region**: {top1.get('j_region_id', 'N/A')}\n")
        lines.append(f"**Canonical**: {top1.get('canonical_risk_level', 'N/A').upper()}\n")
        lines.append(f"****: {top1.get('mutation_summary', {}).get('n_mutations_total', 0)}\n")
        lines.append(f"****: ")
        
        # 
        reasons = []
        if top1.get("canonical_risk_level") == "low":
            reasons.append("")
        if top1.get("mutation_summary", {}).get("hallmark_applied"):
            reasons.append("VHH")
        if top1.get("mutation_summary", {}).get("vernier_applied"):
            reasons.append("CDR")
        
        if reasons:
            lines.append("；".join(reasons) + "。\n\n")
        else:
            lines.append("。\n\n")
        
        if top2:
            lines.append("###  Top 2\n\n")
            lines.append(f"**Scaffold**: {top2.get('scaffold_id', 'N/A')}\n")
            lines.append(f"**J Region**: {top2.get('j_region_id', 'N/A')}\n")
            lines.append(f"**Canonical**: {top2.get('canonical_risk_level', 'N/A').upper()}\n")
            lines.append(f"****: {top2.get('mutation_summary', {}).get('n_mutations_total', 0)}\n")
            lines.append(f"****: ，。\n\n")
    
    lines.append("---\n\n")
    
    # 2. Query Overview
    lines.append("## 2. （Query Overview）\n\n")
    
    cdr_features = data.get("cdr_features", {})
    if cdr_features:
        lines.append(f"**CDR1**: {cdr_features.get('cdr1_seq', 'N/A')}\n")
        lines.append(f"**CDR1**: {cdr_features.get('cdr1_len', 'N/A')} aa\n")
        lines.append(f"**CDR2**: {cdr_features.get('cdr2_seq', 'N/A')}\n")
        lines.append(f"**CDR2**: {cdr_features.get('cdr2_len', 'N/A')} aa\n")
        
        cdr3_len = data.get("gate", {}).get("metrics", {}).get("cdr3_len", "N/A")
        lines.append(f"**CDR3**: {cdr3_len} aa\n")
        
        # VHH-like
        total_cys = data.get("gate", {}).get("metrics", {}).get("total_cys_count", 0)
        if total_cys <= 2:
            lines.append("**VHH**: VHH（Cys）\n")
        else:
            lines.append(f"**VHH**: Cys{total_cys}，\n")
    
    lines.append("\n---\n\n")
    
    # 3. Canonical Compatibility
    lines.append("## 3. （Canonical Compatibility）\n\n")
    lines.append("| Scaffold | Canonical |  |\n")
    lines.append("|----------|---------------|------|\n")
    
    canonical_compat = data.get("canonical_compatibility", {})
    for scaffold_id in sorted(canonical_compat.keys()):
        compat = canonical_compat[scaffold_id]
        risk = compat.get("risk_level", "unknown")
        explanation = get_canonical_risk_explanation(risk)
        risk_display = risk.upper() if risk != "unknown" else "N/A"
        lines.append(f"| {scaffold_id} | {risk_display} | {explanation} |\n")
    
    lines.append("\n---\n\n")
    
    # 4. Humanization Results Table
    lines.append("## 4. （Humanization Results Table）\n\n")
    lines.append("| Scaffold | J Region |  | Hallmark | Vernier | Canonical |  |\n")
    lines.append("|----------|----------|--------|----------|---------|---------------|----------|\n")
    
    for idx, variant in enumerate(sorted_variants, 1):
        scaffold_id = variant.get("scaffold_id", "N/A")
        j_region = variant.get("j_region_id", "N/A")
        mut_summary = variant.get("mutation_summary", {})
        mut_count = mut_summary.get("n_mutations_total", 0)
        hallmark = "Y" if mut_summary.get("hallmark_applied") else "N"
        vernier = "Y" if mut_summary.get("vernier_applied") else "N"
        canonical_risk = variant.get("canonical_risk_level", "N/A").upper()
        
        lines.append(f"| {scaffold_id} | {j_region} | {mut_count} | {hallmark} | {vernier} | {canonical_risk} | #{idx} |\n")
    
    lines.append("\n---\n\n")
    
    # 5. Mutation Summary
    lines.append("## 5. （Mutation Summary）\n\n")
    
    # variants
    total_hallmark = sum(1 for v in variants if v.get("mutation_summary", {}).get("hallmark_applied"))
    total_vernier = sum(1 for v in variants if v.get("mutation_summary", {}).get("vernier_applied"))
    
    lines.append(f"**Hallmark**: {total_hallmark}/8 variant\n")
    lines.append("  - ：VHHFR2，\n")
    lines.append("  - ：FR24445（Kabat）\n\n")
    
    lines.append(f"**Vernier**: {total_vernier}/8 variant\n")
    lines.append("  - ：CDR，\n")
    lines.append("  - ：\n\n")
    
    lines.append("---\n\n")
    
    # 6. Boundary Statement
    lines.append("## 6. （Boundary Statement）\n\n")
    lines.append("****：\n\n")
    lines.append("，in silico。\n\n")
    lines.append("- \n")
    lines.append("- 、（SPR/BLI）\n")
    lines.append("- \n")
    lines.append("- ，\n\n")
    
    # 
    report_path = output_dir / f"{project_name}_VHH_Client_CRO_Report.md"
    content = "".join(lines)
    
    # 
    sensitive_keywords = ["sha256", "mutations_rules", "core/", "tests/", "byte-level", "unit test"]
    content_lower = content.lower()
    for keyword in sensitive_keywords:
        if keyword in content_lower:
            raise ValueError(f": {keyword}")
    
    report_path.write_text(content, encoding="utf-8")
    print(f"[INFO] Client CRO Report generated: {report_path}")
    
    return report_path


# ============================================================================
# Developer Audit Report 
# ============================================================================

def generate_developer_audit_report(data: Dict[str, Any], output_dir: Path, project_name: str = "7D12") -> Path:
    """Developer Audit Report（）"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    lines = []
    
    # 
    lines.append(f"# {project_name} VHH Classic Panel （）\n")
    lines.append(f"**：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"**：** Classic Panel JSON\n")
    lines.append("---\n\n")
    
    # 0. P0 | VHH_CYS_PREFLIGHT_CHECK (Non-bypassable)
    lines.append("## 0. P0 | VHH_CYS_PREFLIGHT_CHECK (Non-bypassable)\n\n")
    
    preflight_checks = data.get("preflight_checks", {})
    cys_check = preflight_checks.get("vhh_cys_check", {})
    
    if cys_check:
        status = cys_check.get("status", "unknown")
        severity = cys_check.get("severity", "unknown")
        action = cys_check.get("action", "unknown")
        core_pair_present = cys_check.get("core_pair_present", False)
        core_pair_positions = cys_check.get("core_pair_positions", {})
        detected_cys = cys_check.get("detected_cys_positions", {})
        extra_cys = cys_check.get("extra_cys_positions", {})
        messages = cys_check.get("messages", [])
        
        lines.append(f"**Status**: {status.upper()}\n")
        lines.append(f"**Severity**: {severity.upper()}\n")
        lines.append(f"**Action**: {action.upper()}\n")
        lines.append(f"**Core Pair Present**: {core_pair_present}\n\n")
        
        # 
        lines.append("**Core Pair Positions**:\n\n")
        lines.append("| Scheme | Position 1 | Position 2 |\n")
        lines.append("|--------|-----------|------------|\n")
        imgt_pos = core_pair_positions.get("imgt", [None, None])
        kabat_pos = core_pair_positions.get("kabat", [None, None])
        aho_pos = core_pair_positions.get("aho", [None, None])
        lines.append(f"| IMGT | {imgt_pos[0] if imgt_pos[0] is not None else 'unmapped'} | {imgt_pos[1] if imgt_pos[1] is not None else 'unmapped'} |\n")
        lines.append(f"| Kabat | {kabat_pos[0] if kabat_pos[0] is not None else 'unmapped'} | {kabat_pos[1] if kabat_pos[1] is not None else 'unmapped'} |\n")
        lines.append(f"| AHo | {aho_pos[0] if aho_pos[0] is not None else 'unmapped'} | {aho_pos[1] if aho_pos[1] is not None else 'unmapped'} |\n\n")
        
        # Detected Cys positions
        lines.append("**Detected Cys Positions**:\n\n")
        lines.append(f"- IMGT: {detected_cys.get('imgt', [])}\n")
        lines.append(f"- Kabat: {detected_cys.get('kabat', [])}\n")
        lines.append(f"- AHo: {detected_cys.get('aho', [])}\n\n")
        
        # Extra Cys positions
        lines.append("**Extra Cys Positions**:\n\n")
        lines.append(f"- IMGT: {extra_cys.get('imgt', [])}\n")
        lines.append(f"- Kabat: {extra_cys.get('kabat', [])}\n")
        lines.append(f"- AHo: {extra_cys.get('aho', [])}\n\n")
        
        # 
        lines.append("****:\n\n")
        lines.append("- ：IMGT 23  104（Kabat23104）\n")
        lines.append("-  → status=fail, action=abort\n")
        lines.append("- Cys（≥3） → status=pass, severity=warning\n")
        lines.append("- 2Cys → status=pass, severity=info\n\n")
        
        # Action=abort
        if action == "abort":
            lines.append("**Action=abort **:\n\n")
            for msg in messages:
                if msg.get("code") in ("VHH_CYS_CORE_PAIR_MISSING", "VHH_CYS_SEQUENCE_EXTRACTION_FAILED", "VHH_CYS_SEQUENCE_EMPTY"):
                    lines.append(f"- {msg.get('code')}: {msg.get('text_en', '')}\n")
            lines.append("\n")
        
        # Policy
        policy = cys_check.get("policy", {})
        lines.append("**Policy**:\n\n")
        lines.append(f"- Extra Cys Handling: {policy.get('extra_cys_handling', 'N/A')}\n")
        lines.append(f"- Auto Mutate Extra Cys: {policy.get('auto_mutate_extra_cys', False)}\n\n")
    else:
        lines.append("**Preflight check not available**\n\n")
    
    lines.append("---\n\n")
    
    # 1. Run Metadata & Provenance
    lines.append("## 1. （Run Metadata & Provenance）\n\n")
    
    lines.append(f"**JSON**: {datetime.now().isoformat()}\n")
    lines.append(f"**Pipeline**: {data.get('pipeline_version', 'N/A')}\n")
    lines.append(f"**JSON**: {data.get('timestamp', 'N/A')}\n\n")
    
    # provenance
    variants = data.get("classic_panel", [])
    if variants:
        first_variant = variants[0]
        provenance = first_variant.get("provenance", {})
        if provenance:
            lines.append("**Scaffold SHA256**:\n")
            lines.append(f"- {provenance.get('scaffold_sha256', 'N/A')}\n\n")
            lines.append("**J Region SHA256**:\n")
            # J regionSHA256
            j_sha256s = {}
            for v in variants:
                prov = v.get("provenance", {})
                j_id = v.get("j_region_id", "N/A")
                j_sha = prov.get("j_region_sha256", "N/A")
                if j_sha != "N/A":
                    j_sha256s[j_id] = j_sha
            
            for j_id, j_sha in j_sha256s.items():
                lines.append(f"- {j_id}: {j_sha}\n")
            lines.append("\n")
    
    lines.append("---\n\n")
    
    # 2. Numbering & Boundary Proof
    lines.append("## 2. （Numbering & Boundary Proof）\n\n")
    
    cdr_features = data.get("cdr_features", {})
    if cdr_features:
        lines.append("**CDR**:\n\n")
        lines.append(f"- CDR1: {cdr_features.get('cdr1_seq', 'N/A')}\n")
        lines.append(f"- CDR1: {cdr_features.get('cdr1_len', 'N/A')} aa\n")
        lines.append(f"- CDR2: {cdr_features.get('cdr2_seq', 'N/A')}\n")
        lines.append(f"- CDR2: {cdr_features.get('cdr2_len', 'N/A')} aa\n")
        lines.append(f"- CDR1 Proxy Class: {cdr_features.get('cdr1_proxy_class', 'N/A')}\n")
        lines.append(f"- CDR2 Proxy Class: {cdr_features.get('cdr2_proxy_class', 'N/A')}\n\n")
    
    gate_metrics = data.get("gate", {}).get("metrics", {})
    if gate_metrics:
        lines.append(f"**CDR3**: {gate_metrics.get('cdr3_len', 'N/A')} aa\n\n")
    
    # QA
    lines.append("**QA**:\n\n")
    qa_ok_count = 0
    for v in variants:
        qa = v.get("qa", {})
        if qa.get("cdr_integrity_ok") and qa.get("numbering_consistency_ok"):
            qa_ok_count += 1
    
    lines.append(f"- CDR: {qa_ok_count}/8 variants\n")
    lines.append(f"- : {qa_ok_count}/8 variants\n\n")
    
    lines.append("---\n\n")
    
    # 3. Rules Applied
    lines.append("## 3. （Rules Applied）\n\n")
    
    rulebook_summary = data.get("rulebook_summary", {})
    if rulebook_summary:
        lines.append(f"**Rulebook**: {rulebook_summary.get('rulebook_version', 'N/A')}\n")
        lines.append(f"****: {rulebook_summary.get('mode', 'N/A')}\n\n")
        
        triggered = rulebook_summary.get("triggered_rules", [])
        lines.append("****:\n")
        for rule_id in triggered:
            lines.append(f"- {rule_id}\n")
        lines.append("\n")
        
        disabled = rulebook_summary.get("disabled_high_risk_rules", [])
        if disabled:
            lines.append("****:\n")
            for rule in disabled:
                lines.append(f"- {rule.get('rule_id', 'N/A')} (Layer {rule.get('layer', 'N/A')}, Risk: {rule.get('risk_level', 'N/A')}): {rule.get('reason', 'N/A')}\n")
            lines.append("\n")
    
    # Hallmark
    lines.append("### 3.1 Hallmark（FR2 44/45）\n\n")
    lines.append("****:\n\n")
    lines.append("- ****: 4445（Kabat）MVP\n")
    lines.append("- **44**: query44EQ，scaffoldE，E（G44E）\n")
    lines.append("- **45**: query45R，scaffoldR，R（L45R）\n")
    lines.append("- ****: 37, 47, 49（，V2）\n")
    lines.append("- ****: VHHFR2，\n\n")
    
    # Vernier
    lines.append("### 3.2 Vernier（）\n\n")
    lines.append("****: 27-30, 49, 71, 73, 78, 93, 94（Kabat）\n\n")
    lines.append("****:\n\n")
    lines.append("- ****: queryscaffold，CDR\n")
    lines.append("- ****: scaffoldquery，CDR\n")
    lines.append("- ****:\n")
    lines.append("  - Vernier-Tuning（）: MVP\n")
    lines.append("  - Vernier-Anchor（）: expert\n\n")
    
    lines.append("---\n\n")
    
    # 4. Per-Variant Full Mutation Log
    lines.append("## 4. Variant（Per-Variant Full Mutation Log）\n\n")
    
    for idx, variant in enumerate(variants, 1):
        scaffold_id = variant.get("scaffold_id", "N/A")
        j_region = variant.get("j_region_id", "N/A")
        
        lines.append(f"### 4.{idx} {scaffold_id} × {j_region}\n\n")
        
        # 
        lines.append("****:\n\n")
        lines.append("```\n")
        lines.append(f"Grafted (pre-mutation): {variant.get('sequence_grafted_pre_mutation', 'N/A')}\n")
        lines.append(f"Final (post-mutation):  {variant.get('sequence_final', 'N/A')}\n")
        lines.append("```\n\n")
        
        # 
        mutations = variant.get("mutations", [])
        lines.append(f"**** ({len(mutations)}):\n\n")
        
        if mutations:
            lines.append("| ID | (Kabat) | From | To |  |  |  |  |\n")
            lines.append("|--------|-------------|------|-----|------|------|------|----------|\n")
            
            for mut in mutations:
                rule_id = mut.get("rule_id", "N/A")
                numbering = mut.get("numbering", {})
                kabat_pos = numbering.get("kabat", "N/A")
                from_aa = mut.get("from_aa", "N/A")
                to_aa = mut.get("to_aa", "N/A")
                layer = mut.get("layer", "N/A")
                risk = mut.get("risk_level", "N/A")
                purpose = mut.get("purpose", "N/A")
                trigger = mut.get("trigger_explanation", "N/A")
                
                # trigger
                if len(trigger) > 80:
                    trigger = trigger[:77] + "..."
                
                lines.append(f"| {rule_id} | {kabat_pos} | {from_aa} | {to_aa} | {layer} | {risk} | {purpose[:30]}... | {trigger} |\n")
        else:
            lines.append("（none）\n")
        
        lines.append("\n")
        
        # Mutation Summary
        mut_summary = variant.get("mutation_summary", {})
        lines.append("****:\n")
        lines.append(f"- Hallmark: {mut_summary.get('hallmark_applied', False)}\n")
        lines.append(f"- Vernier: {mut_summary.get('vernier_applied', False)}\n")
        lines.append(f"- : {mut_summary.get('n_mutations_total', 0)}\n")
        lines.append(f"- Vernier: {mut_summary.get('vernier_backfill_count', 0)}\n\n")
        
        # QA
        qa = variant.get("qa", {})
        lines.append("**QA**:\n")
        lines.append(f"- CDR: {'✓' if qa.get('cdr_integrity_ok') else '✗'}\n")
        lines.append(f"- : {'✓' if qa.get('numbering_consistency_ok') else '✗'}\n\n")
        
        # Canonical
        canonical_risk = variant.get("canonical_risk_level", "N/A")
        canonical_rationale = variant.get("canonical_rationale", "N/A")
        lines.append("**Canonical**:\n")
        lines.append(f"- : {canonical_risk}\n")
        lines.append(f"- : {canonical_rationale}\n\n")
        
        lines.append("---\n\n")
    
    # 5. Canonical Layer Proof
    lines.append("## 5. Canonical（Canonical Layer Proof）\n\n")
    
    lines.append("****: canonical，sequence_final\n\n")
    
    # varianthash
    lines.append("****:\n\n")
    lines.append("| Variant | sequence_final SHA256 |  |\n")
    lines.append("|---------|----------------------|------|\n")
    
    for variant in variants:
        scaffold_id = variant.get("scaffold_id", "N/A")
        j_region = variant.get("j_region_id", "N/A")
        seq_final = variant.get("sequence_final", "")
        
        if seq_final:
            seq_hash = calculate_sha256(seq_final)
            lines.append(f"| {scaffold_id} × {j_region} | {seq_hash} | ✓ |\n")
        else:
            lines.append(f"| {scaffold_id} × {j_region} | N/A | ✗ |\n")
    
    lines.append("\n")
    lines.append("****: canonical，sequence_finalmutations。\n\n")
    
    # 
    report_path = output_dir / f"{project_name}_VHH_Developer_Audit_Report.md"
    content = "".join(lines)
    
    # 
    required_keywords = ["Hallmark", "Vernier"]
    content_lower = content.lower()
    for keyword in required_keywords:
        if keyword.lower() not in content_lower:
            raise ValueError(f": {keyword}")
    
    report_path.write_text(content, encoding="utf-8")
    print(f"[INFO] Developer Audit Report generated: {report_path}")
    
    return report_path


# ============================================================================
# 
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Classic Panel JSON")
    parser.add_argument(
        "--panel-json",
        type=str,
        required=True,
        help="Classic Panel JSON"
    )
    parser.add_argument(
        "--outdir",
        type=str,
        required=True,
        help=""
    )
    parser.add_argument(
        "--project-name",
        type=str,
        default="7D12",
        help="（: 7D12）"
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="PDF（pandoc）"
    )
    
    args = parser.parse_args()
    
    # 
    json_path = Path(args.panel_json)
    if not json_path.is_absolute():
        # ，/mnt/data/
        if (PROJECT_ROOT / "mnt" / "data" / json_path.name).exists():
            json_path = PROJECT_ROOT / "mnt" / "data" / json_path.name
        elif (PROJECT_ROOT / json_path).exists():
            json_path = PROJECT_ROOT / json_path
        elif json_path.exists():
            json_path = json_path.resolve()
    
    output_dir = Path(args.outdir)
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    
    # JSON
    print(f"[INFO] JSON: {json_path}")
    data = load_panel_json(json_path)
    
    # 
    print(f"[INFO] : {output_dir}")
    client_report = generate_client_cro_report(data, output_dir, args.project_name)
    dev_report = generate_developer_audit_report(data, output_dir, args.project_name)
    
    # PDF（）
    if args.pdf:
        try:
            import subprocess
            for report_path in [client_report, dev_report]:
                pdf_path = report_path.with_suffix(".pdf")
                cmd = ["pandoc", str(report_path), "-o", str(pdf_path)]
                subprocess.run(cmd, check=True)
                print(f"[INFO] PDF generated: {pdf_path}")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"[WARN] PDF: {e}")
    
    print("\n[SUCCESS] ！")
    print(f"  - Client CRO Report: {client_report}")
    print(f"  - Developer Audit Report: {dev_report}")


if __name__ == "__main__":
    main()

