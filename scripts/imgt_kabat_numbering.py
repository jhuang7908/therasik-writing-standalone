#!/usr/bin/env python3
"""
IMGT/Kabat
anarcii
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys
import os

# anarcii
try:
    from anarci import anarci
    HAS_ANARCI = True
except ImportError:
    HAS_ANARCI = False
    print("⚠️  anarcii，")

# IMGT（VHH）
IMGT_REGIONS = {
    "FR1": (1, 26),
    "CDR1": (27, 38),
    "FR2": (39, 55),
    "CDR2": (56, 65),
    "FR3": (66, 104),
    "CDR3": (105, 117),
    "FR4": (118, 128)
}

# Hallmark（IMGT）
HALLMARK_POSITIONS = [37, 44, 45, 47]

def number_with_anarci(sequence: str, scheme: str = 'imgt') -> Optional[Dict]:
    """anarcii"""
    if not HAS_ANARCI:
        return None
    
    try:
        numbered, alignment_details, hit_tables = anarci(
            [("VHH", sequence)], 
            scheme=scheme,
            output=False
        )
        
        if numbered and numbered[0] and numbered[0][0]:
            numbering = numbered[0][0][0]
            
            # 
            regions = {name: [] for name in IMGT_REGIONS.keys()}
            hallmark = {}
            
            for (chain, pos), aa in numbering:
                if chain == 'H':  # 
                    # 
                    for region_name, (start, end) in IMGT_REGIONS.items():
                        if start <= pos <= end:
                            regions[region_name].append((pos, aa))
                            break
                    
                    # hallmark
                    if pos in HALLMARK_POSITIONS:
                        hallmark[pos] = {
                            "imgt_position": pos,
                            "residue": aa,
                            "sequence_index": None  # 
                        }
            
            # IMGT
            seq_to_imgt = {}
            for idx, ((chain, pos), aa) in enumerate(numbering):
                if chain == 'H':
                    seq_to_imgt[idx] = pos
            
            return {
                "scheme": scheme,
                "numbering": numbering,
                "regions": regions,
                "hallmark": hallmark,
                "sequence_to_imgt": seq_to_imgt,
                "success": True
            }
    except Exception as e:
        print(f"  ⚠️  anarcii: {e}")
        return None

def split_regions_rule_based(sequence: str) -> Dict:
    """（VHH）"""
    seq = sequence.upper()
    length = len(seq)
    
    # VHH
    # WVRQWFRQ（FR2）
    fr2_marker = None
    for i in range(len(seq) - 4):
        if seq[i:i+4] in ["WVRQ", "WFRQ", "WIRQ"]:
            fr2_marker = i
            break
    
    if fr2_marker:
        # 
        fr1_end = max(26, fr2_marker - 12)
        cdr1_start = fr1_end + 1
        cdr1_end = fr2_marker - 1
        fr2_start = fr2_marker - 10
        fr2_end = fr2_marker + 15
        cdr2_start = fr2_end + 1
        cdr2_end = cdr2_start + 10
        fr3_start = cdr2_end + 1
        fr3_end = length - 12
        cdr3_start = fr3_end + 1
        cdr3_end = length
    else:
        # （VHH）
        fr1_end = min(26, length)
        cdr1_start = fr1_end + 1
        cdr1_end = min(38, length)
        fr2_start = cdr1_end + 1
        fr2_end = min(55, length)
        cdr2_start = fr2_end + 1
        cdr2_end = min(65, length)
        fr3_start = cdr2_end + 1
        fr3_end = min(104, length)
        cdr3_start = fr3_end + 1
        cdr3_end = length
    
    regions = {
        "FR1": {
            "start": 1,
            "end": fr1_end,
            "sequence": seq[0:fr1_end],
            "length": fr1_end
        },
        "CDR1": {
            "start": cdr1_start,
            "end": cdr1_end,
            "sequence": seq[cdr1_start-1:cdr1_end],
            "length": cdr1_end - cdr1_start + 1
        },
        "FR2": {
            "start": fr2_start,
            "end": fr2_end,
            "sequence": seq[fr2_start-1:fr2_end],
            "length": fr2_end - fr2_start + 1
        },
        "CDR2": {
            "start": cdr2_start,
            "end": cdr2_end,
            "sequence": seq[cdr2_start-1:cdr2_end],
            "length": cdr2_end - cdr2_start + 1
        },
        "FR3": {
            "start": fr3_start,
            "end": fr3_end,
            "sequence": seq[fr3_start-1:fr3_end],
            "length": fr3_end - fr3_start + 1
        },
        "CDR3": {
            "start": cdr3_start,
            "end": cdr3_end,
            "sequence": seq[cdr3_start-1:cdr3_end],
            "length": cdr3_end - cdr3_start + 1
        }
    }
    
    # hallmark（FR2）
    fr2_seq_pos = fr2_start
    hallmark_estimates = {}
    for imgt_pos in HALLMARK_POSITIONS:
        # IMGT 37FR211，4418，4519，4721
        offset = imgt_pos - 26  # FR2IMGT 39，
        seq_pos = fr2_start + offset - 12  # 
        if 1 <= seq_pos <= length:
            hallmark_estimates[imgt_pos] = {
                "sequence_position": seq_pos,
                "residue": seq[seq_pos-1] if seq_pos <= length else "?",
                "note": "，IMGT"
            }
    
    return {
        "regions": regions,
        "hallmark_estimates": hallmark_estimates,
        "method": "rule_based",
        "note": "VHH，anarcii"
    }

def create_numbering_report(sequence: str, imgt_result: Optional[Dict], rule_result: Dict) -> str:
    """"""
    report = []
    report.append("# IMGT/Kabat\n\n")
    report.append(f"****: {len(sequence)} aa\n")
    report.append(f"****: 2025-12-17\n\n")
    report.append("---\n\n")
    
    if imgt_result and imgt_result.get('success'):
        report.append("## ✅ IMGT（anarcii）\n\n")
        
        # 
        report.append("### （IMGT）\n\n")
        for region_name, positions in imgt_result['regions'].items():
            if positions:
                start_pos = positions[0][0]
                end_pos = positions[-1][0]
                seq = ''.join([aa for _, aa in positions])
                report.append(f"#### {region_name}\n\n")
                report.append(f"- **IMGT**: {start_pos}-{end_pos}\n")
                report.append(f"- ****: {len(positions)} aa\n")
                report.append(f"- ****: `{seq}`\n\n")
        
        # Hallmark
        if imgt_result.get('hallmark'):
            report.append("### Hallmark（IMGT）\n\n")
            report.append("| IMGT |  | （） |\n")
            report.append("|----------|------|------------------|\n")
            for pos, info in sorted(imgt_result['hallmark'].items()):
                typical = {"37": "F", "44": "Q", "45": "R", "47": "G"}.get(str(pos), "?")
                status = "✅" if info['residue'] == typical else "⚠️"
                report.append(f"| {pos} | {info['residue']} (: {typical}) {status} | - |\n")
            report.append("\n")
    else:
        report.append("## ⚠️  IMGT（anarcii）\n\n")
        report.append("anarcii，。\n\n")
    
    # 
    report.append("## （）\n\n")
    report.append("### \n\n")
    report.append("|  |  |  |  |\n")
    report.append("|------|----------|------|------|\n")
    
    for region_name, region_info in rule_result['regions'].items():
        seq_display = region_info['sequence'][:30] + "..." if len(region_info['sequence']) > 30 else region_info['sequence']
        report.append(f"| **{region_name}** | {region_info['start']}-{region_info['end']} | {region_info['length']} aa | `{seq_display}` |\n")
    
    report.append("\n### Hallmark\n\n")
    report.append("| IMGT |  |  |  |\n")
    report.append("|----------|--------------|------|----------|\n")
    
    for pos, info in sorted(rule_result['hallmark_estimates'].items()):
        typical = {"37": "F", "44": "Q", "45": "R", "47": "G"}.get(str(pos), "?")
        status = "✅" if info['residue'] == typical else "⚠️"
        report.append(f"| {pos} | {info['sequence_position']} | {info['residue']} (: {typical}) {status} | {typical} |\n")
    
    report.append(f"\n⚠️  {rule_result['note']}\n\n")
    
    return ''.join(report)

def main():
    """"""
    print("=" * 60)
    print("IMGT/Kabat")
    print("=" * 60)
    
    # 
    fasta_file = Path("projects/anti_HSA_VHH/input/anti_hsa_vhh_alb8_partial_hallmark.fasta")
    if not fasta_file.exists():
        print("❌ ")
        return
    
    with open(fasta_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        sequence = ""
        header = ""
        for line in lines:
            if line.startswith('>'):
                header = line.strip()
            else:
                sequence += line.strip()
    
    if not sequence:
        print("❌ ")
        return
    
    print(f"\n: {header}")
    print(f": {len(sequence)} aa")
    print(f": {sequence}\n")
    
    # anarcii
    print("anarciiIMGT...")
    imgt_result = number_with_anarci(sequence, scheme='imgt')
    
    if imgt_result:
        print("  ✅ IMGT")
    else:
        print("  ⚠️  anarcii，")
    
    # 
    print("\n...")
    rule_result = split_regions_rule_based(sequence)
    print("  ✅ ")
    
    # 
    print("\n:")
    print("-" * 60)
    for region_name, region_info in rule_result['regions'].items():
        print(f"{region_name}: {region_info['start']}-{region_info['end']} ({region_info['length']} aa)")
        print(f"  : {region_info['sequence']}")
    
    print("\nHallmark:")
    print("-" * 60)
    for pos, info in sorted(rule_result['hallmark_estimates'].items()):
        typical = {"37": "F", "44": "Q", "45": "R", "47": "G"}.get(str(pos), "?")
        print(f"IMGT{pos}: {info['sequence_position']}, {info['residue']} (: {typical})")
    
    # 
    output_file = Path("projects/anti_HSA_VHH/numbering_and_split.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    result_data = {
        "sequence": sequence,
        "sequence_length": len(sequence),
        "imgt_numbering": imgt_result,
        "rule_based_split": rule_result
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ : {output_file}")
    
    # 
    report_content = create_numbering_report(sequence, imgt_result, rule_result)
    report_file = Path("projects/anti_HSA_VHH/IMGT_Kabat.md")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"✅ : {report_file}")

if __name__ == '__main__':
    main()
