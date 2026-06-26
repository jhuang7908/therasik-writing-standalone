#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 +  + Excel

：
-  IMGT/Kabat （ anarcii）
- （Hallmark/Vernier/）
-  Excel（ sheet：ResidueMap / FunctionalSites / QC）
"""

import sys
import argparse
import json
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import pandas as pd
    import yaml
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("⚠️  Warning: pandas/yaml ， Excel ", file=sys.stderr)

from core.numbering.dual_map import build_dual_map, resolve_functional_sites_on_sequence, DualMapError
from core.numbering.anarcii_adapter import get_engine_info
from tools.trim_variable_domain import trim_variable_domain
from tools.sequence_cleaner import clean_sequence_comprehensive, normalize_input_sequence
from core.features.annotate import annotate_features, export_feature_matrix


def load_sequence_from_fasta(fasta_path: Path) -> Tuple[str, str]:
    """
    Load sequence from FASTA file.
    
    Returns:
        (raw_content, cleaned_sequence)
        raw_content: 
        cleaned_sequence: 
    """
    with open(fasta_path, 'r', encoding='utf-8') as f:
        raw_content = f.read
    
    lines = [line.strip for line in raw_content.splitlines if line.strip]
    if not lines:
        raise ValueError("Empty FASTA file")
    
    # Skip header lines (starting with >)
    seq_lines = [line for line in lines if not line.startswith('>')]
    sequence = ''.join(seq_lines)
    
    cleaned_sequence = sequence.upper.replace(' ', '').replace('\n', '').replace('*', '')
    
    return raw_content, cleaned_sequence


def calculate_dual_map_qc(dual_map: List[Dict[str, Any]], sequence: str) -> Dict[str, Any]:
    """
    dual_mapQC
    
    Returns:
        Dict:
        - aa_mismatch_count: 
        - imgt_gap_count: IMGT gap
        - kabat_gap_count: Kabat gap
        - kabat_insertion_count: Kabat
        - nontrivial_examples_count: 
    """
    aa_mismatch_count = 0
    imgt_gap_count = 0
    kabat_gap_count = 0
    kabat_insertion_count = 0
    nontrivial_examples = []
    
    for entry in dual_map:
        seq_idx = entry["seq_idx"]
        aa = entry["aa"]
        imgt_pos = entry.get("imgt_pos")
        kabat_pos = entry.get("kabat_pos")
        flags = entry.get("flags", [])
        
        # Check AA mismatch (should not happen, but check anyway)
        if seq_idx < len(sequence) and aa != sequence[seq_idx]:
            aa_mismatch_count += 1
        
        # Count gaps
        if "imgt_gap" in flags:
            imgt_gap_count += 1
        if "kabat_gap" in flags:
            kabat_gap_count += 1
        
        # Count insertions
        if kabat_pos and re.search(r'[A-Z]$', kabat_pos):
            kabat_insertion_count += 1
        
        # Collect nontrivial examples (imgt_pos != kabat_pos or insertion/gap)
        is_nontrivial = False
        if imgt_pos and kabat_pos:
            # Check if positions are different (numeric or with insertion)
            imgt_num = re.sub(r'[A-Z]$', '', str(imgt_pos))
            kabat_num = re.sub(r'[A-Z]$', '', str(kabat_pos))
            if imgt_num != kabat_num:
                is_nontrivial = True
            elif imgt_pos != kabat_pos:  # Same number but different insertion codes
                is_nontrivial = True
        elif imgt_pos or kabat_pos:  # One is None (gap)
            is_nontrivial = True
        
        if is_nontrivial and len(nontrivial_examples) < 20:
            nontrivial_examples.append({
                "seq_idx": seq_idx,
                "aa": aa,
                "imgt_pos": imgt_pos,
                "kabat_pos": kabat_pos,
                "flags": flags
            })
    
    return {
        "aa_mismatch_count": aa_mismatch_count,
        "imgt_gap_count": imgt_gap_count,
        "kabat_gap_count": kabat_gap_count,
        "kabat_insertion_count": kabat_insertion_count,
        "nontrivial_examples_count": len(nontrivial_examples),
        "nontrivial_examples": nontrivial_examples
    }


def build_imgt_numbering_dict(dual_map: List[Dict[str, Any]]) -> Dict[str, str]:
    """IMGT：position -> aa"""
    result = {}
    for entry in dual_map:
        imgt_pos = entry.get("imgt_pos")
        if imgt_pos:
            result[str(imgt_pos)] = entry["aa"]
    return result


def build_kabat_numbering_dict(dual_map: List[Dict[str, Any]]) -> Dict[str, str]:
    """Kabat：position -> aa"""
    result = {}
    for entry in dual_map:
        kabat_pos = entry.get("kabat_pos")
        if kabat_pos:
            result[str(kabat_pos)] = entry["aa"]
    return result


def generate_markdown_report(
    output_json: Dict[str, Any],
    sequence: str,
    qc_data: Dict[str, Any],
    resolved_sites: Dict[str, Any],
    conflicts: List[Dict[str, Any]]
) -> str:
    """
    Markdown
    
    Args:
        output_json: JSON
        sequence: 
        qc_data: QC
        resolved_sites: 
        conflicts: 
    
    Returns:
        Markdown
    """
    from datetime import datetime
    
    lines = []
    lines.append("# 7D12 VHH  + ")
    lines.append("")
    lines.append(f"****: {datetime.now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"****: {len(sequence)} aa")
    lines.append("")
    
    # 
    lines.append("## 1. ")
    lines.append("")
    lines.append(f"- **sequence_hash**: `{output_json['sequence_hash']}`")
    lines.append(f"- **numbering_engine**: {output_json['numbering_engine']['name']} v{output_json['numbering_engine']['version']}")
    lines.append(f"- **schemes**: {', '.join(output_json['numbering_engine']['schemes'])}")
    lines.append(f"- **status**: {output_json['status']}")
    lines.append(f"- **chain_type**: {output_json.get('chain_type', 'N/A')}")
    lines.append("")
    
    # QC
    lines.append("## 2. Dual Map QC ")
    lines.append("")
    lines.append("|  |  |")
    lines.append("|------|-----|")
    lines.append(f"| aa_mismatch_count | {qc_data['aa_mismatch_count']} |")
    lines.append(f"| imgt_gap_count | {qc_data['imgt_gap_count']} |")
    lines.append(f"| kabat_gap_count | {qc_data['kabat_gap_count']} |")
    lines.append(f"| kabat_insertion_count | {qc_data['kabat_insertion_count']} |")
    lines.append(f"| nontrivial_examples_count | {qc_data['nontrivial_examples_count']} |")
    lines.append("")
    
    # 
    if qc_data.get("nontrivial_examples"):
        lines.append("### 2.1 （20）")
        lines.append("")
        lines.append("| SeqIdx | AA | IMGT | Kabat | Flags |")
        lines.append("|--------|----|----|----|----|")
        for example in qc_data["nontrivial_examples"][:20]:
            flags_str = ", ".join(example.get("flags", [])) if example.get("flags") else ""
            lines.append(f"| {example['seq_idx']} | {example['aa']} | {example['imgt_pos'] or ''} | {example['kabat_pos'] or ''} | {flags_str} |")
        lines.append("")
    
    # 
    lines.append("## 3. ")
    lines.append("")
    
    # role
    sites_by_role = defaultdict(list)
    for site_id, site_info in resolved_sites.items:
        role = site_info.get("role", "unknown")
        sites_by_role[role].append(site_info)
    
    for role, sites in sites_by_role.items:
        lines.append(f"### 3.{len(lines) - lines.index('## 3. ')} {role.upper} ")
        lines.append("")
        full_count = sum(1 for s in sites if s.get("mapping_status") == "full")
        partial_count = sum(1 for s in sites if s.get("mapping_status") == "partial")
        conflict_count = sum(1 for s in sites if s.get("mapping_status") == "conflict")
        
        lines.append(f"- ****: {len(sites)}")
        lines.append(f"- **Full matches**: {full_count}")
        lines.append(f"- **Partial matches**: {partial_count}")
        lines.append(f"- **Conflicts**: {conflict_count}")
        lines.append("")
    
    # 
    lines.append("## 4. ")
    lines.append("")
    lines.append("| SiteID | Role | IMGT Positions | Kabat Positions | Status | Residues Count |")
    lines.append("|--------|------|----------------|------------------|--------|----------------|")
    
    for site_id, site_info in sorted(resolved_sites.items):
        role = site_info.get("role", "")
        imgt_pos = ", ".join(str(p) for p in site_info.get("imgt_positions", []))
        kabat_pos = ", ".join(str(p) for p in site_info.get("kabat_positions", []))
        status = site_info.get("mapping_status", "")
        residues_count = len(site_info.get("resolved_residues", []))
        
        lines.append(f"| {site_id} | {role} | {imgt_pos} | {kabat_pos} | {status} | {residues_count} |")
    
    lines.append("")
    
    # 
    if conflicts:
        lines.append("## 5. ")
        lines.append("")
        lines.append("| SiteID | Description |")
        lines.append("|--------|-------------|")
        for conflict in conflicts:
            site_id = conflict.get("site_id", "")
            desc = conflict.get("description", "")
            lines.append(f"| {site_id} | {desc} |")
        lines.append("")
    
    # 
    lines.append("## 6. ")
    lines.append("")
    lines.append("```")
    lines.append(sequence)
    lines.append("```")
    lines.append("")
    
    return "\n".join(lines)


def main:
    """"""
    parser = argparse.ArgumentParser(
        description=" +  + Excel",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--fasta',
        type=str,
        required=True,
        help='FASTA'
    )
    parser.add_argument(
        '--sites',
        type=str,
        default='kb/10_parameters/functional_sites.yaml',
        help='YAML'
    )
    parser.add_argument(
        '--out_json',
        type=str,
        required=True,
        help='JSON'
    )
    parser.add_argument(
        '--out_xlsx',
        type=str,
        required=True,
        help='Excel'
    )
    parser.add_argument(
        '--out_md',
        type=str,
        default=None,
        help='Markdown'
    )
    
    args = parser.parse_args
    
    # 
    fasta_path = Path(args.fasta)
    if not fasta_path.exists:
        print(f"❌ ERROR: FASTA: {fasta_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        raw_content, initial_sequence = load_sequence_from_fasta(fasta_path)
    except Exception as e:
        print(f"❌ ERROR: FASTA: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not initial_sequence:
        print(f"❌ ERROR: ", file=sys.stderr)
        sys.exit(1)
    
    print(f"📂 : {len(initial_sequence)} aa")
    
    # （，）
    # ：，QA
    print("🧹 ...")
    try:
        cleaned_input, cleaning_log = normalize_input_sequence(raw_content)
        print(f"✅ ")
        print(f"  - : {len(cleaned_input)} aa")
        if cleaning_log.get("invalid_count", 0) > 0:
            print(f"  - : {cleaning_log['invalid_count']} ")
        if cleaning_log.get("x_count", 0) > 0:
            print(f"  - (X): {cleaning_log['x_count']} ")
    except Exception as e:
        print(f"❌ ERROR: : {e}", file=sys.stderr)
        sys.exit(1)
    
    # Variable Domain Trimming
    print("✂️  ...")
    try:
        trimmed_sequence, variable_domain_metadata = trim_variable_domain(cleaned_input)
        sequence = trimmed_sequence  # 
        print(f"✅ ")
        print(f"  - : {variable_domain_metadata['original_length']} aa")
        print(f"  - : {variable_domain_metadata['variable_domain_length']} aa")
        print(f"  - : {variable_domain_metadata['trimmed_constant_region']}")
    except Exception as e:
        print(f"⚠️  WARNING: : {e}，", file=sys.stderr)
        # ，，
        variable_domain_metadata = {
            "detected": False,
            "trimmed_constant_region": False,
            "original_length": len(cleaned_input),
            "variable_domain_length": len(cleaned_input),
            "v_start": 0,
            "v_end": len(cleaned_input),
            "detection_method": "anarcii_auto_trim_failed"
        }
        sequence = cleaned_input
    
    # hash
    sequence_hash = hashlib.sha256(sequence.encode).hexdigest
    
    # 
    engine_info = get_engine_info
    
    # 
    print("🔢 ANARCII...")
    try:
        dual_map, status, chain_type = build_dual_map(sequence)
    except DualMapError as e:
        print(f"❌ ERROR: : {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"✅ ，: {status}")
    
    # QC
    print("📊 QC...")
    qc_data = calculate_dual_map_qc(dual_map, sequence)
    
    # aa_mismatch_count
    if qc_data["aa_mismatch_count"] != 0:
        print(f"❌ ERROR:  != 0: {qc_data['aa_mismatch_count']}", file=sys.stderr)
        sys.exit(1)
    
    # nontrivial_examples
    if qc_data["nontrivial_examples_count"] == 0:
        print("⚠️  WARNING: nontrivial_examples_count == 0，", file=sys.stderr)
        # /gap0，
        if qc_data["imgt_gap_count"] == 0 and qc_data["kabat_gap_count"] == 0 and qc_data["kabat_insertion_count"] == 0:
            print("⚠️  WARNING: gapinsertion0，nontrivial_examples0，", file=sys.stderr)
            # SUSPICIOUS
            status = "SUSPICIOUS"
    
    # 
    imgt_numbering = build_imgt_numbering_dict(dual_map)
    kabat_numbering = build_kabat_numbering_dict(dual_map)
    
    # 
    sites_path = Path(args.sites)
    if not sites_path.exists:
        print(f"⚠️  WARNING: : {sites_path}，", file=sys.stderr)
        functional_sites = []
        resolved_sites = {}
        conflicts = []
    else:
        print("📋 ...")
        with open(sites_path, 'r', encoding='utf-8') as f:
            sites_data = yaml.safe_load(f)
        functional_sites = sites_data.get('functional_sites', [])
        
        # 
        print("🔍 ...")
        resolved_sites, conflicts = resolve_functional_sites_on_sequence(dual_map, functional_sites, chain_type)
        print(f"✅ ， {len(resolved_sites)} ")
    
    # （，QA）
    print("📋 QA...")
    comprehensive_cleaning_result = clean_sequence_comprehensive(
        raw_content,
        dual_map_status=status,
        chain_type=chain_type,
        variable_domain_metadata=variable_domain_metadata  # V
    )
    
    # STOP
    if comprehensive_cleaning_result.get("stop_reason"):
        print(f"❌ ERROR: STOP: {comprehensive_cleaning_result['stop_reason']}", file=sys.stderr)
        print(f"   QA: {comprehensive_cleaning_result['qa_flags']}", file=sys.stderr)
        sys.exit(1)
    
    # JSON
    output_json = {
        "sequence_hash": sequence_hash,
        "numbering_engine": engine_info,
        "imgt_numbering": imgt_numbering,
        "kabat_numbering": kabat_numbering,
        "dual_map": dual_map,
        "dual_map_qc": qc_data,
        "status": status,
        "chain_type": chain_type,
        # 
        "cleaned_input_sequence": comprehensive_cleaning_result.get("cleaned_input_sequence", cleaned_input),
        "variable_domain": comprehensive_cleaning_result.get("variable_domain", variable_domain_metadata),
        "variable_domain_sequence": comprehensive_cleaning_result.get("variable_domain_sequence", sequence),
        "extra_domains": comprehensive_cleaning_result.get("extra_domains", []),  # V
        "cleaning_log": comprehensive_cleaning_result.get("cleaning_log", cleaning_log),
        "qa_flags": comprehensive_cleaning_result.get("qa_flags", []),
        "stop_reason": comprehensive_cleaning_result.get("stop_reason"),
        "warn_reason": comprehensive_cleaning_result.get("warn_reason"),  # 
        "warn_reasons": comprehensive_cleaning_result.get("warn_reasons", []),  # WARN
        "tool_versions": comprehensive_cleaning_result.get("tool_versions", engine_info),
        "functional_sites": {
            "resolved_sites": resolved_sites,
            "conflicts": conflicts
        }
    }
    
    # JSON
    json_path = Path(args.out_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output_json, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON: {json_path}")
    
    # （Excel）
    annotated_features = None
    print("🏷️  ...")
    try:
        chain_name = "VH" if chain_type == "H" else ("VL" if chain_type in ["K", "L"] else "UNKNOWN")
        annotated_features = annotate_features(output_json, chain_name)
        
        # JSON
        features_json_path = json_path.parent / f"{json_path.stem.replace('_dualmap', '')}_features.json"
        with open(features_json_path, 'w', encoding='utf-8') as f:
            json.dump(annotated_features, f, indent=2, ensure_ascii=False)
        print(f"✅ JSON: {features_json_path}")
    except Exception as e:
        print(f"⚠️  WARNING: : {e}", file=sys.stderr)
        annotated_features = None
    
    # Excel
    if not PANDAS_AVAILABLE:
        print("⚠️  WARNING: pandas，Excel", file=sys.stderr)
    else:
        print("📊 Excel...")
        xlsx_path = Path(args.out_xlsx)
        xlsx_path.parent.mkdir(parents=True, exist_ok=True)
        
        with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
            # Sheet 1: ResidueMap
            residue_data = []
            for entry in dual_map:
                flags_str = ", ".join(entry.get("flags", [])) if entry.get("flags") else ""
                residue_data.append({
                    "SeqIdx": entry["seq_idx"],
                    "AA": entry["aa"],
                    "IMGT": entry.get("imgt_pos") or "",
                    "Kabat": entry.get("kabat_pos") or "",
                    "Flags": flags_str
                })
            df_residue = pd.DataFrame(residue_data)
            df_residue.to_excel(writer, sheet_name='ResidueMap', index=False)
            
            # Sheet 2: FunctionalSites
            sites_data_list = []
            for site_id, site_info in resolved_sites.items:
                role = site_info.get("role", "")
                imgt_positions = site_info.get("imgt_positions", [])
                kabat_positions = site_info.get("kabat_positions", [])
                mapping_status = site_info.get("mapping_status", "")
                resolved_residues = site_info.get("resolved_residues", [])
                
                # 
                if resolved_residues:
                    first_residue = resolved_residues[0]
                    seq_idx = first_residue.get("seq_idx", "")
                    aa = first_residue.get("aa", "")
                    imgt_pos = first_residue.get("imgt_pos", "")
                    kabat_pos = first_residue.get("kabat_pos", "")
                else:
                    seq_idx = ""
                    aa = ""
                    imgt_pos = ""
                    kabat_pos = ""
                
                # 
                site_conflicts = [c for c in conflicts if c.get("site_id") == site_id]
                conflicts_str = "; ".join([c.get("description", "") for c in site_conflicts]) if site_conflicts else ""
                
                sites_data_list.append({
                    "SiteID": site_id,
                    "Role": role,
                    "AA": aa,
                    "SeqIdx": seq_idx,
                    "IMGT": imgt_pos,
                    "Kabat": kabat_pos,
                    "MappingStatus": mapping_status,
                    "Notes": site_info.get("notes", ""),
                    "Conflicts": conflicts_str
                })
            
            df_sites = pd.DataFrame(sites_data_list)
            df_sites.to_excel(writer, sheet_name='FunctionalSites', index=False)
            
            # Sheet 3: QC
            qc_data_list = [{
                "Engine": engine_info.get("name", ""),
                "Version": engine_info.get("version", ""),
                "Hash": sequence_hash[:16],
                "Mismatch": qc_data["aa_mismatch_count"],
                "IMGT_Gap": qc_data["imgt_gap_count"],
                "Kabat_Gap": qc_data["kabat_gap_count"],
                "Kabat_Insertion": qc_data["kabat_insertion_count"],
                "Nontrivial_Examples": qc_data["nontrivial_examples_count"],
                "Status": status
            }]
            df_qc = pd.DataFrame(qc_data_list)
            df_qc.to_excel(writer, sheet_name='QC', index=False)
            
            # Sheet 4: FeatureTags
            if annotated_features is not None:
                try:
                    df_features = export_feature_matrix(annotated_features)
                    df_features.to_excel(writer, sheet_name='FeatureTags', index=False)
                    print(f"✅ FeatureTags sheet")
                except Exception as e:
                    print(f"⚠️  WARNING: FeatureTags sheet: {e}", file=sys.stderr)
        
        print(f"✅ Excel: {xlsx_path}")
    
    # Markdown
    if args.out_md:
        print("📝 Markdown...")
        md_path = Path(args.out_md)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        
        md_content = generate_markdown_report(output_json, sequence, qc_data, resolved_sites, conflicts)
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"✅ Markdown: {md_path}")
    
    print("\n" + "=" * 80)
    print("✅ ！")
    print("=" * 80)
    print(f"\n:")
    print(f"  - JSON: {json_path}")
    if PANDAS_AVAILABLE:
        print(f"  - Excel: {xlsx_path}")
    if args.out_md:
        print(f"  - Markdown: {md_path}")
    print(f"\n:")
    print(f"  - sequence_hash: {sequence_hash[:16]}...")
    print(f"  - numbering_engine: {engine_info.get('name')} v{engine_info.get('version')}")
    print(f"  - aa_mismatch_count: {qc_data['aa_mismatch_count']}")
    print(f"  - imgt_gap_count: {qc_data['imgt_gap_count']}")
    print(f"  - kabat_gap_count: {qc_data['kabat_gap_count']}")
    print(f"  - kabat_insertion_count: {qc_data['kabat_insertion_count']}")
    print(f"  - nontrivial_examples_count: {qc_data['nontrivial_examples_count']}")
    print(f"  - status: {status}")
    
    if qc_data["nontrivial_examples"]:
        print(f"\n5:")
        for i, example in enumerate(qc_data["nontrivial_examples"][:5], 1):
            print(f"  {i}. SeqIdx={example['seq_idx']}, AA={example['aa']}, IMGT={example['imgt_pos']}, Kabat={example['kabat_pos']}")
    
    # SUSPICIOUS，exit non-zero
    if status == "SUSPICIOUS":
        print("\n⚠️  WARNING: SUSPICIOUS，1", file=sys.stderr)
        sys.exit(1)
    
    return 0


if __name__ == "__main__":
    sys.exit(main)
