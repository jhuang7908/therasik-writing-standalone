#!/usr/bin/env python3
"""
Hallmark：37，
"""
from pathlib import Path

def create_partial_hallmark_sequence():
    """hallmark"""
    
    # 
    fasta_file = Path("projects/anti_HSA_VHH/input/anti_hsa_vhh_alb8_only.fasta")
    with open(fasta_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        sequence = ""
        header = ""
        for line in lines:
            if line.startswith('>'):
                header = line.strip()
            else:
                sequence += line.strip()
    
    print(":")
    print(f"  {sequence}")
    print(f"  : {len(sequence)} aa\n")
    
    # ，hallmark（）
    # 37: 37 (V) - （）
    # 44: 44 (G) - Q
    # 45: 45 (L) - R
    # 47: 47 (W) - G
    
    # 
    seq_list = list(sequence)
    
    mutations = []
    
    # 44: G → Q
    if seq_list[43] == 'G':  # 0-based，4443
        seq_list[43] = 'Q'
        mutations.append(("44", "G", "Q", "，"))
    
    # 45: L → R
    if seq_list[44] == 'L':  # 0-based，4544
        seq_list[44] = 'R'
        mutations.append(("45", "L", "R", "，"))
    
    # 47: W → G
    if seq_list[46] == 'W':  # 0-based，4746
        seq_list[46] = 'G'
        mutations.append(("47", "W", "G", "，"))
    
    optimized_sequence = ''.join(seq_list)
    
    print(":")
    print(f"  {optimized_sequence}\n")
    
    print(":")
    for pos, from_aa, to_aa, role in mutations:
        print(f"  {pos}: {from_aa} → {to_aa} ({role})")
    
    print(f"\n:")
    print(f"  37: {seq_list[36]} (V，)")
    
    # FASTA
    output_file = Path("projects/anti_HSA_VHH/input/anti_hsa_vhh_alb8_partial_hallmark.fasta")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    new_header = ">Anti_HSA_VHH_ALB8_partial_hallmark|source:ALB8_with_partial_hallmark|patent_expired:WO2004041865|hallmark_optimized:44,45,47|hallmark_kept:37"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"{new_header}\n")
        f.write(f"{optimized_sequence}\n")
    
    print(f"\n✅ : {output_file}")
    
    # 
    doc_file = Path("projects/anti_HSA_VHH/Hallmark.md")
    with open(doc_file, 'w', encoding='utf-8') as f:
        f.write("# Hallmark\n\n")
        f.write("****: 2025-12-17\n\n")
        f.write("---\n\n")
        f.write("## \n\n")
        f.write("，Hallmark：\n\n")
        f.write("### Hallmark\n\n")
        f.write("- **37 (V)**: V\n")
        f.write("  - : （5/7）\n")
        f.write("  - CDR1（6.5 AA），\n")
        f.write("  - VF，\n\n")
        f.write("### Hallmark\n\n")
        for pos, from_aa, to_aa, role in mutations:
            f.write(f"- **{pos} ({from_aa} → {to_aa})**: {role}\n")
        f.write("\n## \n\n")
        f.write("|  |  |  |  |  |\n")
        f.write("|------|------|--------|------|----------|\n")
        f.write("| 37 | V | **V** () |  |  |\n")
        for pos, from_aa, to_aa, role in mutations:
            if pos == "44":
                f.write(f"| {pos} | {from_aa} | **{to_aa}** | {role} |  |\n")
            elif pos == "45":
                f.write(f"| {pos} | {from_aa} | **{to_aa}** | {role} |  |\n")
            else:
                f.write(f"| {pos} | {from_aa} | **{to_aa}** | {role} |  |\n")
        f.write("\n## \n\n")
        f.write("### \n\n")
        f.write("- ✅ **Q44**: FR2，\n")
        f.write("- ✅ **R45**: ，\n")
        f.write("- ✅ **G47**: ，\n\n")
        f.write("### \n\n")
        f.write("- ✅ **37V**: \n")
        f.write("- ✅ **44/45/47**: FR2\n\n")
        f.write("### \n\n")
        f.write("|  |  |\n")
        f.write("|------|----------|\n")
        f.write("|  | ⬆️⬆️⬆️  |\n")
        f.write("|  | ⬆️⬆️⬆️  |\n")
        f.write("|  | ⬆️⬆️  |\n")
        f.write("|  | ⬆️⬆️  |\n")
        f.write("|  | ➡️  |\n\n")
        f.write("## \n\n")
        f.write("：\n\n")
        f.write("```bash\n")
        f.write("python app/run_vhh_cli.py \\\n")
        f.write("    --fasta projects/anti_HSA_VHH/input/anti_hsa_vhh_alb8_partial_hallmark.fasta \\\n")
        f.write("    --source alpaca \\\n")
        f.write("    --strategy balanced \\\n")
        f.write("    --out projects/anti_HSA_VHH/output/result_alb8_partial_hallmark.json\n")
        f.write("```\n\n")
        f.write("---\n\n")
        f.write("****: `anti_hsa_vhh_alb8_partial_hallmark.fasta`\n")
    
    print(f"✅ : {doc_file}")
    
    return {
        "original_sequence": sequence,
        "optimized_sequence": optimized_sequence,
        "mutations": mutations,
        "kept_positions": [("37", "V", "")],
        "output_file": str(output_file)
    }

if __name__ == '__main__':
    result = create_partial_hallmark_sequence()
    print("\n" + "=" * 60)
    print("Hallmark！")
    print("=" * 60)
