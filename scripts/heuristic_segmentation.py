import pandas as pd
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def heuristic_segment_vh(seq: str):
    """Approximate VH segmentation based on conserved motifs."""
    # QSQVQLVESGPGLVKPSETLSLTCRVSGDSNRPSYWSWIRQAPGKGPEWIGYIYNSGDTNYNPSLKSRVTISVDTSKNQFSLKLSSVTAADTAVYYCARGAPYCSSSSCYRSGMDVWGQGTTVTVSS
    
    # FR1 - 1 to 26 (approx)
    # Cys at index ~23
    cys1_idx = seq.find('C')
    if cys1_idx == -1: return None
    
    # FR2 start - WIRQ
    fr2_start = seq.find('WIRQ')
    if fr2_start == -1: fr2_start = seq.find('WVRQ')
    
    # FR3 end - YYC
    fr3_end = seq.find('YYC')
    if fr3_end == -1: fr3_end = seq.find('YFC')
    if fr3_end != -1: fr3_end += 3 # skip YYC
    
    # FR4 start - WGQG
    fr4_start = seq.find('WGQG')
    if fr4_start == -1: fr4_start = seq.find('WGKG')
    
    if fr2_start != -1 and fr3_end != -1 and fr4_start != -1:
        return {
            "VH_FR1": seq[:26],
            "VH_CDR1": seq[26:fr2_start],
            "VH_FR2": seq[fr2_start:fr2_start+14],
            "VH_CDR2": seq[fr2_start+14:fr2_start+14+8], # typical IMGT CDR2 is 8
            "VH_FR3": seq[fr2_start+14+8:fr3_end],
            "VH_CDR3": seq[fr3_end:fr4_start],
            "VH_FR4": seq[fr4_start:]
        }
    return None

def heuristic_segment_vl(seq: str):
    """Approximate VL segmentation."""
    # SDISVAPGETARISCGEKSLGSRAVQWYQHRAGQAPSLIIYNNQDRPSGIPERFSGSNSGNTATLTISRVEAGDEADYYCQVWDSGNDHVFGGGTQLTVL
    
    # FR2 start - WYQH
    fr2_start = seq.find('WYQH')
    if fr2_start == -1: fr2_start = seq.find('WYQQ')
    
    # FR3 end - YYC
    fr3_end = seq.find('YYC')
    if fr3_end == -1: fr3_end = seq.find('YFC')
    if fr3_end != -1: fr3_end += 3
    
    # FR4 start - FGGG
    fr4_start = seq.find('FG')
    if fr4_start == -1: fr4_start = seq.find('WG')
    
    if fr2_start != -1 and fr3_end != -1 and fr4_start != -1:
        return {
            "VL_FR1": seq[:fr2_start-12], # approx
            "VL_CDR1": seq[fr2_start-12:fr2_start],
            "VL_FR2": seq[fr2_start:fr2_start+15],
            "VL_CDR2": seq[fr2_start+15:fr2_start+15+3], # IMGT CDR2 VL is often short
            "VL_FR3": seq[fr2_start+18:fr3_end],
            "VL_CDR3": seq[fr3_end:fr4_start],
            "VL_FR4": seq[fr4_start:]
        }
    return None

def main():
    file_path = PROJECT_ROOT / "data" / "humanization_assay" / "thera_human_igG_segmented.xlsx"
    df = pd.read_excel(file_path)
    
    # Targets
    targets = ['Calpurbatug', 'Elipovimab', 'Zinlirvimab']
    
    for idx, row in df.iterrows():
        if row['Name'] == 'Calpurbatug':
            res = heuristic_segment_vh(row['VH'])
            if res:
                for k, v in res.items(): df.at[idx, k] = v
                print(f"Heuristically patched {row['Name']} VH")
        
        if row['Name'] in ['Elipovimab', 'Zinlirvimab']:
            res = heuristic_segment_vl(row['VL'])
            if res:
                for k, v in res.items(): df.at[idx, k] = v
                print(f"Heuristically patched {row['Name']} VL")
                
    df.to_excel(file_path, index=False)
    print(f"Saved updated file to {file_path}")

if __name__ == "__main__":
    main()
