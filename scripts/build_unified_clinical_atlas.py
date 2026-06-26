#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/build_unified_clinical_atlas.py

Build a unified, searchable Clinical Antibody Atlas JSON for the web console.
Combines:
- Metadata (Phase, Format, Target, Genetics)
- Sequences (VH/VL/VHH)
- CMC Metrics (pI, Stability, etc.)
- ADA (Immunogenicity) data
"""

import json
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
META_JSON = PROJECT_ROOT / "data/thera_sabdab/out/antibody_meta_models.json"
SEQ_XLSX = PROJECT_ROOT / "data/thera_sabdab/TheraSAbDab_SeqStruc_OnlineDownload.xlsx"
CMC_CSV = PROJECT_ROOT / "data/humanization_assay/842_combined_assessment.csv"
ADA_CSV = PROJECT_ROOT / "data/immunogenicity_knowledge_base/master/ada_master_328_with_params.csv"
OUT_JSON = PROJECT_ROOT / "api/static/assets/clinical_atlas_unified.json"

def norm_id(s):
    if pd.isna(s): return ""
    return str(s).strip().lower()

def clean_value(value, default=None):
    if pd.isna(value):
        return default
    return value

def main():
    # 1. Load Metadata
    print(f"📖 Loading metadata: {META_JSON}")
    with open(META_JSON, 'r', encoding='utf-8') as f:
        meta_data = json.load(f)
    
    atlas = {}
    for m in meta_data:
        aid = m["antibody_id"]
        atlas[norm_id(aid)] = {
            "id": aid,
            "name": m["name"],
            "phase": m["clinical"]["phase_bucket"],
            "phase_raw": m["clinical"]["phase_raw"],
            "format": m["format"]["format_class"],
            "format_raw": m["format"]["format_raw"],
            "genetics": m["genetics"]["normalized"],
            "targets": m["target"]["targets"],
            "target_raw": m["target"]["target_raw"],
            "isotype": m["fc"]["isotype_primary"],
            "heavy_aa": "",
            "light_aa": "",
            "germline": {
                "vh": "",
                "vl": ""
            },
            "cmc": None,
            "ada": None
        }

    # 2. Load Sequences
    print(f"📖 Loading sequences: {SEQ_XLSX}")
    seq_df = pd.read_excel(SEQ_XLSX, engine='openpyxl')
    for _, row in seq_df.iterrows():
        nid = norm_id(row['Therapeutic'])
        if nid in atlas:
            atlas[nid]["heavy_aa"] = str(row['HeavySequence']) if pd.notna(row['HeavySequence']) else ""
            atlas[nid]["light_aa"] = str(row['LightSequence']) if pd.notna(row['LightSequence']) else ""
            h2 = str(row['HeavySequence(ifbispec)']) if pd.notna(row['HeavySequence(ifbispec)']) else ""
            l2 = str(row['LightSequence(ifbispec)']) if pd.notna(row['LightSequence(ifbispec)']) else ""
            if h2: atlas[nid]["heavy_aa_2"] = h2
            if l2: atlas[nid]["light_aa_2"] = l2

    # 3. Load CMC
    if CMC_CSV.exists():
        print(f"📖 Loading CMC: {CMC_CSV}")
        cmc_df = pd.read_csv(CMC_CSV)
        for _, row in cmc_df.iterrows():
            nid = norm_id(row['antibody_id'])
            if nid in atlas:
                atlas[nid]["cmc"] = {
                    "pI": round(float(row['pI']), 2) if pd.notna(row['pI']) else None,
                    "net_charge_pH7": round(float(row['net_charge_pH7']), 2) if pd.notna(row['net_charge_pH7']) else None,
                    "hydro_patch": round(float(row['hydro_patch_max9']), 2) if 'hydro_patch_max9' in row and pd.notna(row['hydro_patch_max9']) else None,
                    "instability": round(float(row['instability_index']), 2) if 'instability_index' in row and pd.notna(row['instability_index']) else None,
                    "immuno_risk": clean_value(row.get('immuno_risk_level', 'unknown'), 'unknown')
                }

    # 4. Load ADA & Germline from Master
    if ADA_CSV.exists():
        print(f"📖 Loading ADA & Germline: {ADA_CSV}")
        ada_df = pd.read_csv(ADA_CSV)
        for _, row in ada_df.iterrows():
            nid = norm_id(row['antibody_name'])
            if nid in atlas:
                # Update Germline
                atlas[nid]["germline"]["vh"] = str(row['vh_germline']) if pd.notna(row['vh_germline']) else ""
                atlas[nid]["germline"]["vl"] = str(row['vl_germline']) if pd.notna(row['vl_germline']) else ""
                
                # Update ADA
                atlas[nid]["ada"] = {
                    "incidence": clean_value(row.get('ada_value_display', 'N/A'), 'N/A'),
                    "risk_level": clean_value(row.get('immuno_risk_level', 'unknown'), 'unknown'),
                    "tcia_score": round(float(row['immuno_tcia_score']), 2) if pd.notna(row['immuno_tcia_score']) else None,
                    "notes": clean_value(row.get('indication_unified', ''), '')
                }

    # 5. Save Unified JSON
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    final_list = list(atlas.values())
    print(f"💾 Saving {len(final_list)} records to {OUT_JSON}")
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(final_list, f, indent=None, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

    print("✅ Unified Clinical Atlas built successfully.")

if __name__ == "__main__":
    main()
