#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pandas as pd
from pathlib import Path
import re
from typing import Dict, List, Any, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from core.numbering.anarcii_adapter import number_sequence
except ImportError:
    print("CRITICAL: core.numbering.anarcii_adapter not found!")
    sys.exit(1)

# IMGT Boundaries (VH and VL)
IMGT_CDR1 = (27, 38)
IMGT_CDR2 = (56, 65)
IMGT_CDR3 = (105, 117)

def parse_imgt_label(label: str) -> int:
    """Extract integer position from IMGT label (e.g., '37A' -> 37)."""
    if not label: return 0
    m = re.match(r"^(\d+)", str(label))
    return int(m.group(1)) if m else 0

def segment_sequence(seq: str) -> Dict[str, str]:
    """Use ANARCII to number and segment a sequence into FR/CDR regions."""
    if not seq or pd.isna(seq) or str(seq).lower() in ['nan', 'none']:
        return {r: "" for r in ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]}
    
    try:
        _, residue_table = number_sequence(str(seq), scheme="imgt")
    except Exception as e:
        print(f"  [ERROR] ANARCII failed: {e}")
        return {r: "ERROR" for r in ["FR1", "CDR1", "FR2", "CDR2", "FR3", "CDR3", "FR4"]}

    regions = {"FR1": [], "CDR1": [], "FR2": [], "CDR2": [], "FR3": [], "CDR3": [], "FR4": []}
    
    for res in residue_table:
        label = res.get("position_label")
        aa = res.get("aa", "")
        if label is None: continue
        
        pos = parse_imgt_label(label)
        
        if 1 <= pos <= 26:
            regions["FR1"].append(aa)
        elif IMGT_CDR1[0] <= pos <= IMGT_CDR1[1]:
            regions["CDR1"].append(aa)
        elif 39 <= pos <= 55:
            regions["FR2"].append(aa)
        elif IMGT_CDR2[0] <= pos <= IMGT_CDR2[1]:
            regions["CDR2"].append(aa)
        elif 66 <= pos <= 104:
            regions["FR3"].append(aa)
        elif IMGT_CDR3[0] <= pos <= IMGT_CDR3[1]:
            regions["CDR3"].append(aa)
        elif 118 <= pos <= 128:
            regions["FR4"].append(aa)
            
    return {k: "".join(v) for k, v in regions.items()}

def main():
    input_file = PROJECT_ROOT / "data" / "thera_sabdab" / "out" / "thera_standard_human_igG.xlsx"
    output_dir = PROJECT_ROOT / "data" / "humanization_assay"
    output_file = output_dir / "thera_human_igG_segmented.xlsx"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📖 Loading filtered IgG antibodies: {input_file}")
    df = pd.read_excel(input_file)
    print(f"✅ Loaded {len(df)} records.")

    # Copy original file to the new directory as well
    df.to_excel(output_dir / "thera_standard_human_igG.xlsx", index=False)
    print(f"💾 Copied original to {output_dir / 'thera_standard_human_igG.xlsx'}")

    segmented_data = []
    
    print("\n🧬 Running ANARCII segmentation...")
    for idx, row in df.iterrows():
        ab_id = row.get("Name") or row.get("INN")
        print(f"[{idx+1}/{len(df)}] Segmenting {ab_id}...")
        
        # Heavy Chain
        h_seq = row.get("VH")
        h_regions = segment_sequence(h_seq)
        
        # Light Chain
        l_seq = row.get("VL")
        l_regions = segment_sequence(l_seq)
        
        # Combine
        combined_row = row.to_dict()
        for k, v in h_regions.items():
            combined_row[f"VH_{k}"] = v
        for k, v in l_regions.items():
            combined_row[f"VL_{k}"] = v
            
        segmented_data.append(combined_row)

    out_df = pd.DataFrame(segmented_data)
    out_df.to_excel(output_file, index=False)
    print(f"\n✅ All done! Segmented library saved to: {output_file}")

if __name__ == "__main__":
    main()
