#!/usr/bin/env python3
"""
anarcii 2.0.5APIIMGT
"""
import json
from pathlib import Path
from anarcii.pipeline import Anarcii

def number_with_anarcii_v2(sequence: str):
    """anarcii 2.0.5"""
    print(f": {len(sequence)} aa")
    print(f": {sequence}\n")
    
    try:
        # anarcii 2.0.5API
        anarcii_instance = Anarcii()
        result = anarcii_instance.number([sequence], scheme="imgt")
        
        print("✅ anarcii 2.0.5\n")
        
        # 
        if result and len(result) > 0:
            numbering = result[0]
            
            print(":")
            print("-" * 60)
            
            # 
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
            
            for entry in numbering:
                # anarcii 2.0.5
                print(f"Entry: {entry}")
            
            return {
                "sequence": sequence,
                "numbering": numbering,
                "success": True
            }
        else:
            print("⚠️  ")
            return None
            
    except Exception as e:
        print(f"❌ anarcii 2.0.5: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """"""
    print("=" * 60)
    print("anarcii 2.0.5IMGT")
    print("=" * 60)
    
    # 
    fasta_file = Path("projects/anti_HSA_VHH/input/anti_hsa_vhh_alb8_partial_hallmark.fasta")
    with open(fasta_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        sequence = ""
        for line in lines:
            if not line.startswith('>'):
                sequence += line.strip()
    
    result = number_with_anarcii_v2(sequence)
    
    if result:
        print(f"\n✅ ")

if __name__ == '__main__':
    main()
