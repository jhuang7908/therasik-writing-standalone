#!/usr/bin/env python3
"""
abnumberIMGT
"""
import json
from pathlib import Path
from abnumber import Chain

def number_and_split_with_abnumber(sequence: str):
    """abnumberIMGT"""
    print(f": {len(sequence)} aa")
    print(f": {sequence}\n")
    
    try:
        # abnumber（chain_type，abnumber）
        chain = Chain(sequence, scheme="imgt")
        
        print("✅ abnumber\n")
        print(f": {chain.chain_type}")
        print(f": imgt\n")
        
        # 
        regions = chain.regions
        print(":")
        print("-" * 60)
        
        region_seqs = {}
        for region_name, pos_dict in regions.items():
            if region_name in ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]:
                seq = ''.join([aa for pos, aa in sorted(pos_dict.items(), key=lambda x: x[0].number)])
                region_seqs[region_name] = seq
                print(f"{region_name}: {len(seq)} aa")
                print(f"  : {seq}")
        
        # hallmark
        print("\nHallmark（IMGT）:")
        print("-" * 60)
        
        hallmark_positions = {}
        fr2_positions = regions.get("FR2", {})
        
        for pos_obj, aa in fr2_positions.items():
            pos_num = pos_obj.number
            if pos_num in [37, 44, 45, 47]:
                typical = {37: "F", 44: "Q", 45: "R", 47: "G"}.get(pos_num, "?")
                status = "✅" if aa == typical else "⚠️"
                hallmark_positions[pos_num] = {
                    "imgt_position": pos_num,
                    "imgt_pos_str": str(pos_obj),
                    "residue": aa,
                    "typical": typical,
                    "is_typical": aa == typical
                }
                print(f"IMGT{pos_num} ({pos_obj}): {aa} (: {typical}) {status}")
        
        # 
        all_positions = []
        for region_name, pos_dict in regions.items():
            for pos_obj, aa in pos_dict.items():
                all_positions.append({
                    "imgt_position": pos_obj.number,
                    "imgt_pos_str": str(pos_obj),
                    "region": region_name,
                    "residue": aa
                })
        
        all_positions.sort(key=lambda x: (x["imgt_position"], x["imgt_pos_str"]))
        
        return {
            "sequence": sequence,
            "chain_type": chain.chain_type,
            "scheme": "imgt",
            "regions": region_seqs,
            "hallmark_positions": hallmark_positions,
            "all_positions": all_positions[:50]  # 50
        }
        
    except Exception as e:
        print(f"❌ abnumber: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """"""
    print("=" * 60)
    print("abnumberIMGT")
    print("=" * 60)
    
    # 
    fasta_file = Path("projects/anti_HSA_VHH/input/anti_hsa_vhh_alb8_partial_hallmark.fasta")
    with open(fasta_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        sequence = ""
        for line in lines:
            if not line.startswith('>'):
                sequence += line.strip()
    
    # 
    result = number_and_split_with_abnumber(sequence)
    
    if result:
        # 
        output_file = Path("projects/anti_HSA_VHH/accurate_imgt_numbering.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ : {output_file}")
        
        # 
        report_file = Path("projects/anti_HSA_VHH/IMGT.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# IMGT\n\n")
            f.write(f"****: ALB8 (Hallmark)\n")
            f.write(f"****: {len(sequence)} aa\n")
            f.write(f"****: IMGT\n")
            f.write(f"****: abnumber\n")
            f.write(f"****: 2025-12-17\n\n")
            f.write("---\n\n")
            
            f.write("## ✅ （abnumber）\n\n")
            f.write("|  |  |  |\n")
            f.write("|------|------|------|\n")
            
            for region_name in ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]:
                if region_name in result["regions"]:
                    seq = result["regions"][region_name]
                    f.write(f"| **{region_name}** | {len(seq)} aa | `{seq}` |\n")
            
            f.write("\n## ✅ Hallmark（IMGT）\n\n")
            f.write("| IMGT | IMGT |  |  |  |\n")
            f.write("|----------|----------|------|----------|------|\n")
            
            for pos_num in sorted(result["hallmark_positions"].keys()):
                info = result["hallmark_positions"][pos_num]
                status = "✅ " if info["is_typical"] else "⚠️ "
                f.write(f"| {pos_num} | {info['imgt_pos_str']} | {info['residue']} | {info['typical']} | {status} |\n")
            
            f.write("\n## （50）\n\n")
            f.write("| IMGT | IMGT |  |  |\n")
            f.write("|----------|----------|------|------|\n")
            
            for pos_info in result["all_positions"]:
                f.write(f"| {pos_info['imgt_position']} | {pos_info['imgt_pos_str']} | {pos_info['region']} | {pos_info['residue']} |\n")
        
        print(f"✅ : {report_file}")

if __name__ == '__main__':
    main()
