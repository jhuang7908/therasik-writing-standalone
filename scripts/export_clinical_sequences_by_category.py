#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/export_clinical_sequences_by_category.py

Export clinical antibody sequences (1143 database) categorized by:
- Phase (Approved, Phase III, etc.)
- Format (Whole mAb, VHH, ADC, etc.)
- Genetics (Human, Humanized, Chimeric, etc.)

Excludes pet antibody atlas data from public export.
"""

import os
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
META_JSON = PROJECT_ROOT / "data/thera_sabdab/out/antibody_meta_models.json"
SEQ_XLSX = PROJECT_ROOT / "data/thera_sabdab/TheraSAbDab_SeqStruc_OnlineDownload.xlsx"
OUT_DIR = PROJECT_ROOT / "data/clinical_exports"

def main():
    # 1. Load Metadata (Normalized categories)
    print(f"📖 Loading metadata: {META_JSON}")
    with open(META_JSON, 'r', encoding='utf-8') as f:
        meta_data = json.load(f)
    
    meta_df = pd.DataFrame([
        {
            "antibody_id": m["antibody_id"],
            "phase": m["clinical"]["phase_bucket"],
            "format": m["format"]["format_class"],
            "genetics": m["genetics"]["normalized"],
            "target": m["target"]["target_raw"]
        }
        for m in meta_data
    ])

    # 2. Load Sequences
    print(f"📖 Loading sequences: {SEQ_XLSX}")
    seq_df = pd.read_excel(SEQ_XLSX, engine='openpyxl')
    
    # Clean sequence data
    seq_df = seq_df[['Therapeutic', 'HeavySequence', 'LightSequence']].copy()
    seq_df.columns = ['antibody_id', 'heavy_aa', 'light_aa']
    
    # 3. Join
    merged = pd.merge(meta_df, seq_df, on='antibody_id', how='inner')
    print(f"✅ Merged {len(merged)} records with sequences.")

    # 4. Create Export Directory
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 5. Export by Category
    categories = {
        "phase": "Phase",
        "format": "Format",
        "genetics": "Genetics"
    }

    for cat_key, cat_name in categories.items():
        cat_dir = OUT_DIR / cat_key
        cat_dir.mkdir(exist_ok=True)
        
        print(f"\n📦 Exporting by {cat_name}...")
        groups = merged.groupby(cat_key)
        
        for val, group in groups:
            safe_val = str(val).replace("/", "_").replace(" ", "_").lower()
            out_file = cat_dir / f"clinical_abs_{cat_key}_{safe_val}.csv"
            
            # Export CSV
            group.to_csv(out_file, index=False)
            
            # Also export a summary FASTA for each group
            fasta_file = cat_dir / f"clinical_abs_{cat_key}_{safe_val}.fasta"
            with open(fasta_file, 'w', encoding='utf-8') as f:
                for _, row in group.iterrows():
                    name = row['antibody_id']
                    if pd.notna(row['heavy_aa']) and str(row['heavy_aa']).strip():
                        f.write(f">{name}_VH | {cat_name}:{val}\n{row['heavy_aa']}\n")
                    if pd.notna(row['light_aa']) and str(row['light_aa']).strip():
                        f.write(f">{name}_VL | {cat_name}:{val}\n{row['light_aa']}\n")
            
            print(f"  - {val}: {len(group)} entries -> {out_file.name}")

    print(f"\n✅ All exports completed in {OUT_DIR}")

if __name__ == "__main__":
    main()
