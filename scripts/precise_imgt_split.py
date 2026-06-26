#!/usr/bin/env python3
"""
IMGT（ALB8）
"""
import json
from pathlib import Path

# ALB8（VHH）
# : EVQLVESGGGLVQPGNSLRLSCAASGFTFSSFGMSWVRQAPGKQREGVSSISGSGSDTLYADSVKGRFTISRDNAKTTLYLQMNSLRPEDTAVYYCTIGGSLSRSSQGTLVTVSST

def precise_split_alb8(sequence: str) -> dict:
    """ALB8"""
    seq = sequence.upper()
    
    # VHH
    # ：WVRQ（FR2）
    wvrq_pos = seq.find("WVRQ")
    if wvrq_pos == -1:
        wvrq_pos = seq.find("WFRQ")
    
    if wvrq_pos != -1:
        # WVRQ
        # FR1: 1  WVRQ12
        fr1_end = max(26, wvrq_pos - 12)
        # CDR1: FR1WVRQ
        cdr1_start = fr1_end + 1
        cdr1_end = wvrq_pos - 1
        # FR2: WVRQ10WVRQ15
        fr2_start = wvrq_pos - 10
        fr2_end = wvrq_pos + 15
        # CDR2: FR2
        cdr2_start = fr2_end + 1
        cdr2_end = cdr2_start + 10
        # FR3: CDR212
        fr3_start = cdr2_end + 1
        fr3_end = len(seq) - 12
        # CDR3: FR3
        cdr3_start = fr3_end + 1
        cdr3_end = len(seq)
    else:
        # 
        fr1_end = 26
        cdr1_start = 27
        cdr1_end = 38
        fr2_start = 39
        fr2_end = 55
        cdr2_start = 56
        cdr2_end = 65
        fr3_start = 66
        fr3_end = 104
        cdr3_start = 105
        cdr3_end = len(seq)
    
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
    
    # FR2hallmark（IMGT）
    # FR2IMGT 39-55
    # IMGT 37FR22，44FR25，45FR26，47FR28
    fr2_imgt_start = 39  # FR2IMGT
    fr2_seq_start = fr2_start
    
    hallmark_positions = {}
    for imgt_pos in [37, 44, 45, 47]:
        # FR2
        offset_from_fr2 = imgt_pos - fr2_imgt_start
        seq_pos = fr2_seq_start + offset_from_fr2
        
        if 1 <= seq_pos <= len(seq):
            hallmark_positions[imgt_pos] = {
                "sequence_position": seq_pos,
                "residue": seq[seq_pos-1],
                "typical": {"37": "F", "44": "Q", "45": "R", "47": "G"}.get(str(imgt_pos), "?"),
                "is_typical": seq[seq_pos-1] == {"37": "F", "44": "Q", "45": "R", "47": "G"}.get(str(imgt_pos), "")
            }
    
    return {
        "regions": regions,
        "hallmark_positions": hallmark_positions,
        "method": "precise_based_on_wvrq",
        "note": "WVRQVHH"
    }

def main():
    """"""
    print("=" * 60)
    print("IMGT")
    print("=" * 60)
    
    # 
    fasta_file = Path("projects/anti_HSA_VHH/input/anti_hsa_vhh_alb8_partial_hallmark.fasta")
    with open(fasta_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        sequence = ""
        for line in lines:
            if not line.startswith('>'):
                sequence += line.strip()
    
    print(f"\n: {len(sequence)} aa")
    print(f": {sequence}\n")
    
    # 
    result = precise_split_alb8(sequence)
    
    print(":")
    print("-" * 60)
    for region_name, region_info in result['regions'].items():
        print(f"\n{region_name}:")
        print(f"  : {region_info['start']}-{region_info['end']}")
        print(f"  : {region_info['length']} aa")
        print(f"  : {region_info['sequence']}")
    
    print("\n" + "=" * 60)
    print("Hallmark（FR2）:")
    print("-" * 60)
    for pos, info in sorted(result['hallmark_positions'].items()):
        status = "✅" if info['is_typical'] else "⚠️"
        print(f"IMGT{pos}:")
        print(f"  : {info['sequence_position']}")
        print(f"  : {info['residue']} (: {info['typical']}) {status}")
    
    # 
    output_file = Path("projects/anti_HSA_VHH/precise_numbering_split.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "sequence": sequence,
            "sequence_length": len(sequence),
            "split_result": result
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ : {output_file}")
    
    # 
    report_file = Path("projects/anti_HSA_VHH/IMGT.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# IMGT\n\n")
        f.write(f"****: {len(sequence)} aa\n")
        f.write(f"****: 2025-12-17\n\n")
        f.write("---\n\n")
        
        f.write("## \n\n")
        f.write("|  |  |  |  |\n")
        f.write("|------|----------|------|------|\n")
        
        for region_name, region_info in result['regions'].items():
            seq_display = region_info['sequence']
            f.write(f"| **{region_name}** | {region_info['start']}-{region_info['end']} | {region_info['length']} aa | `{seq_display}` |\n")
        
        f.write("\n## Hallmark（IMGT）\n\n")
        f.write("| IMGT |  |  |  |  |\n")
        f.write("|----------|----------|------|----------|------|\n")
        
        for pos, info in sorted(result['hallmark_positions'].items()):
            status = "✅ " if info['is_typical'] else "⚠️ "
            f.write(f"| {pos} | {info['sequence_position']} | {info['residue']} | {info['typical']} | {status} |\n")
        
        f.write(f"\n⚠️  {result['note']}\n")
        f.write("\n****: ，IMGTanarcii。\n")
    
    print(f"✅ : {report_file}")

if __name__ == '__main__':
    main()
