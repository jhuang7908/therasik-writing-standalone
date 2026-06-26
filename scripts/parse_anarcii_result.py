#!/usr/bin/env python3
"""
ANARCII，IMGT
"""
import json
from pathlib import Path
from anarcii.pipeline import Anarcii

# IMGT
IMGT_BOUNDARIES = {
    "FR1": (1, 26),
    "CDR1": (27, 38),
    "FR2": (39, 55),
    "CDR2": (56, 65),
    "FR3": (66, 104),
    "CDR3": (105, 117),
    "FR4": (118, 128)
}

def parse_anarcii_numbering(sequence: str):
    """ANARCII"""
    print("=" * 60)
    print("ANARCIIIMGT")
    print("=" * 60)
    
    # ANARCII
    anarcii_instance = Anarcii()
    result = anarcii_instance.number([sequence])
    
    if not result or 'Sequence 1' not in result:
        print("❌ ")
        return None
    
    seq_result = result['Sequence 1']
    numbering = seq_result['numbering']
    chain_type = seq_result['chain_type']
    scheme = seq_result['scheme']
    
    print(f"\n✅ ")
    print(f": {chain_type}")
    print(f": {scheme}")
    print(f": {seq_result.get('score', 'N/A')}\n")
    
    # 
    # numbering: [((, ), ), ...]
    # ' '，
    
    regions = {
        "FR1": [],
        "CDR1": [],
        "FR2": [],
        "CDR2": [],
        "FR3": [],
        "CDR3": [],
        "FR4": []
    }
    
    hallmark_positions = {}

    # ：ANARCII  '-' “ IMGT /”。
    # '-' ； aa != '-' ， sequence_index，
    #  IMGT  ->  。
    seq_idx = 0  # 0-based index into `sequence`
    for (pos_num, ins_code), aa in numbering:
        if aa == '-':
            continue

        if seq_idx >= len(sequence):
            raise ValueError(
                f"ANARCII numbering has more non-gap residues than input sequence length. "
                f"seq_idx={seq_idx}, len(sequence)={len(sequence)}"
            )

        sequence_index = seq_idx
        seq_idx += 1

        # 
        region = None
        for region_name, (start, end) in IMGT_BOUNDARIES.items():
            if start <= pos_num <= end:
                region = region_name
                break
        
        if region:
            regions[region].append({
                "imgt_position": pos_num,
                "insertion": ins_code if ins_code != ' ' else None,
                "residue": aa,
                "sequence_index": sequence_index,  # 0-based
                "sequence_position": sequence_index + 1,  # 1-based
            })
        
        # hallmark
        if pos_num in [37, 44, 45, 47]:
            typical = {37: "F", 44: "Q", 45: "R", 47: "G"}.get(pos_num, "?")
            hallmark_positions[pos_num] = {
                "imgt_position": pos_num,
                "insertion": ins_code if ins_code != ' ' else None,
                "residue": aa,
                "sequence_index": sequence_index,  # 0-based
                "sequence_position": sequence_index + 1,  # 1-based
                "typical": typical,
                "is_typical": aa == typical
            }
    
    # 
    region_seqs = {}
    for region_name, positions in regions.items():
        seq = ''.join([p['residue'] for p in positions])
        region_seqs[region_name] = seq
    
    # 
    print(":")
    print("-" * 60)
    for region_name, seq in region_seqs.items():
        if seq:
            start_pos = regions[region_name][0]['imgt_position'] if regions[region_name] else None
            end_pos = regions[region_name][-1]['imgt_position'] if regions[region_name] else None
            print(f"{region_name}: IMGT {start_pos}-{end_pos} ({len(seq)} aa)")
            print(f"  : {seq}")
    
    print("\nHallmark（IMGT）:")
    print("-" * 60)
    for pos_num in sorted(hallmark_positions.keys()):
        info = hallmark_positions[pos_num]
        status = "✅" if info['is_typical'] else "⚠️"
        pos_str = f"H{pos_num}{info['insertion']}" if info['insertion'] else f"H{pos_num}"
        print(f"IMGT{pos_num} ({pos_str}): {info['residue']} (: {info['typical']}) {status}")
    
    # 
    output_data = {
        "sequence": sequence,
        "chain_type": chain_type,
        "scheme": scheme,
        "score": seq_result.get('score'),
        "regions": region_seqs,
        "region_details": regions,
        "hallmark_positions": hallmark_positions,
        "numbering": []
    }

    # “gap”，
    seq_idx2 = 0
    for (pos_num, ins_code), aa in numbering:
        if aa == '-':
            continue
        output_data["numbering"].append({
            "imgt_position": pos_num,
            "insertion": ins_code if ins_code != ' ' else None,
            "residue": aa,
            "sequence_index": seq_idx2,  # 0-based
            "sequence_position": seq_idx2 + 1,  # 1-based
        })
        seq_idx2 += 1
    
    output_file = Path("projects/anti_HSA_VHH/accurate_anarcii_numbering.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ : {output_file}")
    
    # 
    generate_accurate_report(output_data)
    
    return output_data

def generate_accurate_report(data: dict):
    """"""
    report_file = Path("projects/anti_HSA_VHH/IMGT_ANARCII.md")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# IMGT（ANARCII）\n\n")
        f.write(f"****: ANARCII (GitHub: https://github.com/oxpig/ANARCII)\n")
        f.write(f"****: ALB8 (Hallmark)\n")
        f.write(f"****: {len(data['sequence'])} aa\n")
        f.write(f"****: {data['chain_type']}\n")
        f.write(f"****: {data['scheme']}\n")
        f.write(f"****: {data.get('score', 'N/A')}\n")
        f.write(f"****: 2025-12-17\n\n")
        f.write("---\n\n")
        
        f.write("## ✅ （ANARCII）\n\n")
        f.write("|  | IMGT |  |  |\n")
        f.write("|------|----------|------|------|\n")
        
        for region_name, seq in data['regions'].items():
            if seq and data['region_details'][region_name]:
                start_pos = data['region_details'][region_name][0]['imgt_position']
                end_pos = data['region_details'][region_name][-1]['imgt_position']
                f.write(f"| **{region_name}** | {start_pos}-{end_pos} | {len(seq)} aa | `{seq}` |\n")
        
        f.write("\n## ✅ Hallmark（IMGT）\n\n")
        f.write("| IMGT | IMGT |  |  |  |  |\n")
        f.write("|----------|----------|------|----------|------|\n")
        
        for pos_num in sorted(data['hallmark_positions'].keys()):
            info = data['hallmark_positions'][pos_num]
            pos_str = f"H{pos_num}{info['insertion']}" if info['insertion'] else f"H{pos_num}"
            status = "✅ " if info['is_typical'] else "⚠️ "
            seq_pos = info.get("sequence_position", "-")
            f.write(f"| {pos_num} | {pos_str} | {info['residue']} | {seq_pos} | {info['typical']} | {status} |\n")
        
        f.write("\n## IMGT（50）\n\n")
        f.write("| IMGT | IMGT |  |  |\n")
        f.write("|----------|----------|------|------|\n")
        
        for entry in data['numbering'][:50]:
            pos_str = f"H{entry['imgt_position']}{entry['insertion']}" if entry['insertion'] else f"H{entry['imgt_position']}"
            # 
            region = None
            for region_name, (start, end) in IMGT_BOUNDARIES.items():
                if start <= entry['imgt_position'] <= end:
                    region = region_name
                    break
            f.write(f"| {entry['imgt_position']} | {pos_str} | {entry['residue']} | {region or '-'} |\n")
        
        if len(data['numbering']) > 50:
            f.write(f"\n... ({len(data['numbering'])})\n")
        
        f.write("\n## 📊 \n\n")
        
        # hallmark
        typical_count = sum(1 for info in data['hallmark_positions'].values() if info['is_typical'])
        f.write(f"### Hallmark\n\n")
        f.write(f"- **Hallmark**: {typical_count}/4 ({typical_count/4*100:.0f}%)\n")
        f.write(f"- **44**: {'✅  (Q)' if data['hallmark_positions'].get(44, {}).get('is_typical') else '⚠️ '}\n")
        f.write(f"- **45**: {'✅  (R)' if data['hallmark_positions'].get(45, {}).get('is_typical') else '⚠️ '}\n")
        f.write(f"- **47**: {'✅  (G)' if data['hallmark_positions'].get(47, {}).get('is_typical') else '⚠️ '}\n")
        f.write(f"- **37**: {'✅  (F)' if data['hallmark_positions'].get(37, {}).get('is_typical') else '⚠️  (V，)'}\n")
        
        f.write("\n### \n\n")
        f.write("|  |  |  |  |\n")
        f.write("|------|------|----------|------|\n")
        
        # “”（//）
        typical_ranges = {
            "CDR1": (6, 17),
            "CDR2": (1, 10),
            "CDR3": (3, 25)
        }
        
        for region_name, seq in data['regions'].items():
            if region_name.startswith('CDR') and seq:
                length = len(seq)
                if region_name in typical_ranges:
                    min_len, max_len = typical_ranges[region_name]
                    status = "✅ " if min_len <= length <= max_len else "⚠️ "
                    f.write(f"| {region_name} | {length} aa | {min_len}-{max_len} aa | {status} |\n")
    
    print(f"✅ : {report_file}")

def main():
    """"""
    # 
    fasta_file = Path("projects/anti_HSA_VHH/input/anti_hsa_vhh_alb8_partial_hallmark.fasta")
    with open(fasta_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        sequence = ""
        for line in lines:
            if not line.startswith('>'):
                sequence += line.strip()
    
    # 
    result = parse_anarcii_numbering(sequence)
    
    if result:
        print("\n" + "=" * 60)
        print("✅ ANARCII！")
        print("=" * 60)
        print("\nANARCII，。")

if __name__ == '__main__':
    main()
