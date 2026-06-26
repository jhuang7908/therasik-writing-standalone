#!/usr/bin/env python3
"""
 ABARCII Kabat 
（ VH 71, VH 94）
"""

import pandas as pd
from anarcii import Anarcii
from pathlib import Path

def verify_single_sequence(name, seq, chain='H'):
    engine = Anarcii()
    # 
    engine.number([(name, seq)])
    # 
    numbering = engine.to_scheme('kabat')[name]['numbering']
    
    # 
    results = {}
    if chain == 'H':
        targets = [71, 94, 92] # 92  Cys, 94  Arg
    else:
        targets = [71, 49]
        
    for target in targets:
        aa = 'X'
        for (pos, ins), res in numbering:
            if pos == target and ins.strip() == '':
                aa = res
                break
        results[f"{chain}_{target}"] = aa
        
    return results

def main():
    # 
    samples = [
        ("Nivolumab_VH", "QVQLVESGGGVVQPGRSLRLDCKASGITFSNSGMHWVRQAPGKGLEWVAVIWYDGSKRYYADSVKGRFTISRDNSKNTLFLQMNSLRAEDTAVYYCATNDDYWGQGTLVTVSS", "H"),
        ("Nivolumab_VL", "EIVLTQSPATLSLSPGERATLSCRASQSVSSYLAWYQQKPGQAPRLLIYDASNRATGIPARFSGSGSGTDFTLTISSLEPEDFAVYYCQQSSNWPRTFGQGTKVEIK", "L"),
    ]
    
    print("="*50)
    print("ABARCII Kabat ")
    print("="*50)
    
    for name, seq, chain in samples:
        res = verify_single_sequence(name, seq, chain)
        print(f"\n: {name}")
        for k, v in res.items():
            print(f"  - Kabat {k}: {v}")
            
        # 
        if chain == 'H':
            if res['H_92'] == 'C':
                print("  [PASS] H_92 (Cys) ")
            if res['H_94'] in ['R', 'S', 'T', 'K', 'A']:
                print(f"  [PASS] H_94 ({res['H_94']})  CDR3 ，")
        elif chain == 'L':
            if res['L_71'] == 'F':
                print("  [PASS] L_71 (Phe) IMGT 80  Kabat 71 ")

    print("\n: ， Kabat  Vernier Zone 。")

if __name__ == "__main__":
    main()
