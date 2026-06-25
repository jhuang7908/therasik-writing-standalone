#!/usr/bin/env python3
"""
VHHhallmark，hallmark
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple

# VHH Hallmark（IMGT）
HALLMARK_POSITIONS = {
    37: {"typical": "F", "alternative": "Y", "role": "，"},
    44: {"typical": "Q", "alternative": "E", "role": "，"},
    45: {"typical": "R", "alternative": "K", "role": "，"},
    47: {"typical": "G", "alternative": "A", "role": "，"}
}

def analyze_hallmark(sequence: str) -> Dict:
    """hallmark"""
    # ：
    # IMGT
    
    seq = sequence.upper()
    length = len(seq)
    
    # FR2（VHH）
    # FR126，FR227，IMGT
    # ：FR237（IMGT）
    
    # FR2
    # ：...WVRQAPGKEREGV... 
    fr2_start = None
    for i in range(len(seq) - 10):
        if seq[i:i+4] == "WVRQ" or seq[i:i+4] == "WFRQ":
            fr2_start = i - 10  # FR2
            break
    
    if fr2_start is None:
        # ，
        fr2_start = 26  # FR1
    
    hallmark_analysis = {}
    
    # hallmark
    for pos_imgt, info in HALLMARK_POSITIONS.items():
        # （）
        seq_pos = fr2_start + (pos_imgt - 26)  # FR126
        
        if 0 <= seq_pos < length:
            current_aa = seq[seq_pos]
            is_typical = current_aa == info["typical"]
            is_alternative = current_aa == info.get("alternative", "")
            
            hallmark_analysis[pos_imgt] = {
                "sequence_position": seq_pos + 1,  # 1-based
                "current_aa": current_aa,
                "typical_aa": info["typical"],
                "is_typical": is_typical,
                "is_alternative": is_alternative,
                "role": info["role"],
                "needs_mutation": not (is_typical or is_alternative)
            }
        else:
            hallmark_analysis[pos_imgt] = {
                "sequence_position": None,
                "current_aa": None,
                "typical_aa": info["typical"],
                "is_typical": False,
                "needs_mutation": True
            }
    
    # hallmark score
    typical_count = sum(1 for v in hallmark_analysis.values() if v.get("is_typical", False))
    alternative_count = sum(1 for v in hallmark_analysis.values() if v.get("is_alternative", False))
    total_score = typical_count + alternative_count * 0.5
    
    return {
        "hallmark_positions": hallmark_analysis,
        "typical_count": typical_count,
        "alternative_count": alternative_count,
        "total_score": total_score,
        "max_score": 4.0,
        "score_percentage": total_score / 4.0 * 100,
        "needs_optimization": total_score < 3.0
    }

def generate_hallmark_optimization(sequence: str, name: str) -> Dict:
    """hallmark"""
    analysis = analyze_hallmark(sequence)
    
    mutations = []
    optimized_sequence = list(sequence.upper())
    
    for pos_imgt, info in analysis["hallmark_positions"].items():
        if info.get("needs_mutation", False) and info.get("sequence_position"):
            seq_pos = info["sequence_position"] - 1  # 0-based
            current_aa = info["current_aa"]
            target_aa = info["typical_aa"]
            
            if seq_pos < len(optimized_sequence):
                mutations.append({
                    "imgt_position": pos_imgt,
                    "sequence_position": info["sequence_position"],
                    "from": current_aa,
                    "to": target_aa,
                    "role": info["role"],
                    "reason": f"VHH hallmark，{info['role']}"
                })
                
                optimized_sequence[seq_pos] = target_aa
    
    optimized_seq = ''.join(optimized_sequence)
    
    return {
        "original_sequence": sequence,
        "optimized_sequence": optimized_seq,
        "mutations": mutations,
        "mutation_count": len(mutations),
        "hallmark_analysis": analysis,
        "benefits": {
            "expression": "hallmark（）",
            "solubility": "FR2",
            "stability": "hallmark",
            "immunogenicity": "VHH，"
        }
    }

def main():
    """"""
    print("=" * 60)
    print("VHH Hallmark")
    print("=" * 60)
    
    # ALB8
    fasta_file = Path("projects/anti_HSA_VHH/input/anti_hsa_vhh_alb8_only.fasta")
    if not fasta_file.exists():
        print("❌ ALB8")
        return
    
    # 
    with open(fasta_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        sequence = ""
        for line in lines:
            if not line.startswith('>'):
                sequence += line.strip()
    
    if not sequence:
        print("❌ ")
        return
    
    print(f"\n: ALB8 (: {len(sequence)} aa)\n")
    
    # hallmark
    analysis = analyze_hallmark(sequence)
    
    print("Hallmark:")
    print("-" * 60)
    print(f"hallmark: {analysis['typical_count']}/4")
    print(f"hallmark: {analysis['alternative_count']}/4")
    print(f"Hallmark: {analysis['total_score']:.1f}/4.0 ({analysis['score_percentage']:.1f}%)")
    print(f": {'' if analysis['needs_optimization'] else ''}")
    
    print("\n:")
    for pos, info in analysis["hallmark_positions"].items():
        if info.get("sequence_position"):
            status = "✅" if info.get("is_typical") else "⚠️" if info.get("is_alternative") else "❌"
            print(f"  {status} {pos} ({info['sequence_position']}): {info.get('current_aa', '?')} → {info['typical_aa']} ({info['role']})")
    
    # 
    print("\n" + "=" * 60)
    print("Hallmark")
    print("=" * 60)
    
    optimization = generate_hallmark_optimization(sequence, "ALB8")
    
    if optimization["mutations"]:
        print(f"\n {len(optimization['mutations'])} hallmark:\n")
        
        for mut in optimization["mutations"]:
            print(f" {mut['imgt_position']} ({mut['sequence_position']}): {mut['from']} → {mut['to']}")
            print(f"  : {mut['reason']}")
            print(f"  : {mut['role']}\n")
        
        print(":")
        print(f"{optimization['optimized_sequence']}\n")
        
        print(":")
        for benefit, desc in optimization["benefits"].items():
            print(f"  ✅ {benefit}: {desc}")
    else:
        print("\n✅ hallmark，")
    
    # 
    output_file = Path("projects/anti_HSA_VHH/hallmark_optimization.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "analysis": analysis,
            "optimization": optimization
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ : {output_file}")
    
    # FASTA
    if optimization["mutations"]:
        optimized_fasta = Path("projects/anti_HSA_VHH/input/anti_hsa_vhh_alb8_hallmark_optimized.fasta")
        with open(optimized_fasta, 'w', encoding='utf-8') as f:
            f.write(">Anti_HSA_VHH_ALB8_hallmark_optimized|source:ALB8_with_hallmark|patent_expired:WO2004041865\n")
            f.write(f"{optimization['optimized_sequence']}\n")
        
        print(f"✅ : {optimized_fasta}")
        print("\n: ，hallmark")

if __name__ == '__main__':
    main()
