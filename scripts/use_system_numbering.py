#!/usr/bin/env python3
"""
IMGT
"""
import sys
from pathlib import Path

# 
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from scripts.anarci_abnumber_adapter import annotate_chain
    HAS_ADAPTER = True
except ImportError as e:
    HAS_ADAPTER = False
    print(f"⚠️  : {e}")

def main():
    """"""
    print("=" * 60)
    print("IMGT")
    print("=" * 60)
    
    if not HAS_ADAPTER:
        print("❌ ")
        return
    
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
    print("IMGT...")
    try:
        annotation = annotate_chain(sequence, scheme="imgt", chain_type_hint="H")
        
        print(f"  ✅ ")
        print(f"  : {annotation.scheme}")
        print(f"  : {annotation.chain_type}")
        print(f"  V: {annotation.v_length}")
        
        # 
        print("\n:")
        print("-" * 60)
        for region_name, region_seq in annotation.regions_seq.items():
            if region_name.startswith(('FR', 'CDR')):
                print(f"{region_name}: {len(region_seq)} aa")
                print(f"  : {region_seq}")
        
        # hallmark
        print("\nHallmark（IMGT）:")
        print("-" * 60)
        hallmark_imgt = {37: "F", 44: "Q", 45: "R", 47: "G"}
        
        for pos_record in annotation.positions:
            if pos_record.region.startswith('FR2') and pos_record.pos:
                # IMGT
                try:
                    pos_num = int(pos_record.pos.replace('H', '').replace('A', '').replace('B', '').replace('C', ''))
                    if pos_num in hallmark_imgt:
                        typical = hallmark_imgt[pos_num]
                        status = "✅" if pos_record.aa == typical else "⚠️"
                        print(f"IMGT{pos_num} ({pos_record.pos}): {pos_record.aa} (: {typical}) {status}")
                except:
                    pass
        
        # 
        import json
        output_file = Path("projects/anti_HSA_VHH/system_numbering_result.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "sequence": sequence,
                "scheme": annotation.scheme,
                "chain_type": annotation.chain_type,
                "v_length": annotation.v_length,
                "regions": annotation.regions_seq,
                "positions": [
                    {
                        "idx": p.idx,
                        "pos": p.pos,
                        "region": p.region,
                        "aa": p.aa
                    }
                    for p in annotation.positions
                ]
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ : {output_file}")
        
        # 
        report_file = Path("projects/anti_HSA_VHH/IMGT.md")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# IMGT\n\n")
            f.write(f"****: {len(sequence)} aa\n")
            f.write(f"****: {annotation.scheme}\n")
            f.write(f"****: {annotation.chain_type}\n")
            f.write(f"**V**: {annotation.v_length} aa\n")
            f.write(f"****: 2025-12-17\n\n")
            f.write("---\n\n")
            
            f.write("## \n\n")
            f.write("|  |  |  |\n")
            f.write("|------|------|------|\n")
            
            for region_name, region_seq in annotation.regions_seq.items():
                if region_name.startswith(('FR', 'CDR')):
                    f.write(f"| **{region_name}** | {len(region_seq)} aa | `{region_seq}` |\n")
            
            f.write("\n## Hallmark（IMGT）\n\n")
            f.write("| IMGT | IMGT |  |  |  |\n")
            f.write("|----------|----------|------|----------|------|\n")
            
            hallmark_imgt = {37: "F", 44: "Q", 45: "R", 47: "G"}
            found_hallmarks = {}
            
            for pos_record in annotation.positions:
                if pos_record.pos:
                    try:
                        pos_num = int(pos_record.pos.replace('H', '').replace('A', '').replace('B', '').replace('C', ''))
                        if pos_num in hallmark_imgt:
                            typical = hallmark_imgt[pos_num]
                            status = "✅ " if pos_record.aa == typical else "⚠️ "
                            found_hallmarks[pos_num] = {
                                "pos": pos_record.pos,
                                "aa": pos_record.aa,
                                "typical": typical,
                                "status": status
                            }
                    except:
                        pass
            
            for pos_num in sorted(found_hallmarks.keys()):
                info = found_hallmarks[pos_num]
                f.write(f"| {pos_num} | {info['pos']} | {info['aa']} | {info['typical']} | {info['status']} |\n")
            
            f.write("\n## \n\n")
            f.write("|  | IMGT |  |  |\n")
            f.write("|------|----------|------|------|\n")
            
            for pos_record in annotation.positions[:50]:  # 50
                f.write(f"| {pos_record.idx} | {pos_record.pos or '-'} | {pos_record.region} | {pos_record.aa} |\n")
            
            if len(annotation.positions) > 50:
                f.write(f"\n... ({len(annotation.positions)})\n")
        
        print(f"✅ : {report_file}")
        
    except Exception as e:
        print(f"  ❌ : {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
