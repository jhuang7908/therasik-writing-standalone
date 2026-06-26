#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate test Thera-SAbDab data for Step 4.
Creates:
1. thera_export.xlsx - Therapeutics metadata with VH/VL sequences
2. thera_canonical.tsv - Canonical tool output (4-column minimal contract)
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Sample therapeutic antibodies with VH/VL sequences
THERAPEUTICS_DATA = [
    {
        "Name": "Rituximab",
        "INN": "rituximab",
        "VH": "QVQLVQSGAEVKKPGASVKVSCKASGYTFTSYWINWVRQAPGQGLEWMGIIYPGDSDTRYSPSFQGQVTISADKSISTAYLQWSSLKASDTAMYYCAR",
        "VL": "DIQMTQSPSSLSASVGDRVTITCRASQDVNTAVAWYQQKPGKAPKLLIYSASFLYSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQHYTTPPTFGQGTKVEIK"
    },
    {
        "Name": "Trastuzumab",
        "INN": "trastuzumab",
        "VH": "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAR",
        "VL": "DIQMTQSPSSLSASVGDRVTITCRASQDVNTAVAWYQQKPGKAPKLLIYSASFLYSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQHYTTPPTFGQGTKVEIK"
    },
    {
        "Name": "Bevacizumab",
        "INN": "bevacizumab",
        "VH": "QVQLVQSGAEVKKPGASVKVSCKASGYTFTSYWINWVRQAPGQGLEWMGIIYPGDSDTRYSPSFQGQVTISADKSISTAYLQWSSLKASDTAMYYCAR",
        "VL": "EIVLTQSPGTLSLSPGERATLSCRASQSVSSSYLAWYQQKPGQAPRLLIYGASSRATGIPDRFSGSGSGTDFTLTISRLEPEDFAVYYCQQYGSSPWTFGQGTKVEIK"
    },
    {
        "Name": "Adalimumab",
        "INN": "adalimumab",
        "VH": "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAR",
        "VL": "DIQMTQSPSSLSASVGDRVTITCRASQDVNTAVAWYQQKPGKAPKLLIYSASFLYSGVPSRFSGSGSGTDFTLTISSLQPEDFATYYCQQHYTTPPTFGQGTKVEIK"
    },
    {
        "Name": "Cetuximab",
        "INN": "cetuximab",
        "VH": "QVQLVQSGAEVKKPGASVKVSCKASGYTFTSYWINWVRQAPGQGLEWMGIIYPGDSDTRYSPSFQGQVTISADKSISTAYLQWSSLKASDTAMYYCAR",
        "VL": "EIVLTQSPGTLSLSPGERATLSCRASQSVSSSYLAWYQQKPGQAPRLLIYGASSRATGIPDRFSGSGSGTDFTLTISRLEPEDFAVYYCQQYGSSPWTFGQGTKVEIK"
    }
]

def generate_thera_export_xlsx(output_path: Path):
    """Generate Thera-SAbDab export XLSX file with VH/VL sequences."""
    df = pd.DataFrame(THERAPEUTICS_DATA)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False, engine='openpyxl')
    print(f"✅ Generated {len(df)} therapeutics -> {output_path}")

def generate_thera_canonical_tsv(output_path: Path):
    """
    Generate canonical TSV for therapeutics (4-column minimal contract).
    Each therapeutic gets H1/H2/L1/L2/L3 canonical classes.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    lines = ["id\tcdr\tclass\tconfidence"]
    
    # Test canonical classes (simplified)
    test_classes = {
        "H1": ["H1-13-1", "H1-13-2", "H1-13-3", "H1-13-4"],
        "H2": ["H2-10-1", "H2-10-2", "H2-10-3"],
        "L1": ["L1-11-1", "L1-11-2", "L1-11-3"],
        "L2": ["L2-7-1", "L2-7-2", "L2-7-3"],
        "L3": ["L3-9-1", "L3-9-2", "L3-10-1"],
    }
    
    for idx, thera in enumerate(THERAPEUTICS_DATA):
        thera_id = thera["Name"].lower().replace(" ", "_")
        
        # VH CDRs (H1, H2)
        for cdr in ["H1", "H2"]:
            class_idx = hash(thera_id + cdr) % len(test_classes[cdr])
            class_name = test_classes[cdr][class_idx]
            confidence = "0.88"
            lines.append(f"{thera_id}\t{cdr}\t{class_name}\t{confidence}")
        
        # VL CDRs (L1, L2, L3)
        for cdr in ["L1", "L2", "L3"]:
            class_idx = hash(thera_id + cdr) % len(test_classes[cdr])
            class_name = test_classes[cdr][class_idx]
            confidence = "0.88" if cdr != "L3" else "0.75"  # L3 lower confidence
            lines.append(f"{thera_id}\t{cdr}\t{class_name}\t{confidence}")
    
    output_path.write_text("\n".join(lines) + "\n", encoding='utf-8')
    print(f"✅ Generated {len(THERAPEUTICS_DATA)} therapeutics, {len(lines)-1} total rows -> {output_path}")

def main():
    out_dir = PROJECT_ROOT / "data" / "thera_sabdab"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    thera_xlsx = out_dir / "thera_export.xlsx"
    thera_tsv = out_dir / "thera_canonical.tsv"
    
    generate_thera_export_xlsx(thera_xlsx)
    generate_thera_canonical_tsv(thera_tsv)
    
    print("\n[SUCCESS] Test Thera-SAbDab data generated.")
    print(f"⚠️  NOTE: These are TEST data. Replace with actual Thera-SAbDab export for production.")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
