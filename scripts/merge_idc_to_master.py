import pandas as pd
import numpy as np
import os
import shutil

MASTER_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada_master_136_curated.csv'
BACKUP_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada_master_136_curated_BACKUP_preIDC.csv'
IDC_EXCEL = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\media-1.xlsx'

def merge_idc_data():
    print(f"Creating backup of master database to {BACKUP_CSV}...")
    shutil.copy2(MASTER_CSV, BACKUP_CSV)
    
    print("Loading Master Database...")
    master_df = pd.read_csv(MASTER_CSV)
    master_df['antibody_name_lower'] = master_df['antibody_name'].str.lower()
    
    print("Loading IDC V1 Database...")
    idc_df = pd.read_excel(IDC_EXCEL, sheet_name='Clinical Trial')
    
    # Columns of interest from IDC
    therapeutic_col = "Molecule Assessed for ADA INN Name"
    nab_col = "Frequency nADA+ patients reported"
    pk_col = "ADA interpreted to impact PK"
    eff_col = "ADA interpreted to impact Efficacy"
    
    idc_df['therapeutic_lower'] = idc_df[therapeutic_col].astype(str).str.lower()
    
    # Clean up IDC data (replace 'Not reported' with NA)
    idc_df['idc_nab_pct'] = pd.to_numeric(idc_df[nab_col].replace(['Not reported', 'Unknown', 'N/A', ''], np.nan), errors='coerce')
    idc_df['idc_pk_impact'] = idc_df[pk_col].replace(['Not reported', 'Unknown', 'N/A', ''], np.nan)
    idc_df['idc_efficacy_impact'] = idc_df[eff_col].replace(['Not reported', 'Unknown', 'N/A', ''], np.nan)
    
    # Group by therapeutic taking the max for NAb and first valid for PK/Efficacy
    idc_grouped = idc_df.groupby('therapeutic_lower').agg({
        'idc_nab_pct': 'max',
        'idc_pk_impact': lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else np.nan,
        'idc_efficacy_impact': lambda x: x.dropna().iloc[0] if len(x.dropna()) > 0 else np.nan
    }).reset_index()
    
    print(f"Aggregated {len(idc_grouped)} unique therapeutics from IDC.")
    
    # Merge into master
    original_cols = master_df.columns.tolist()
    
    # Drop existing idc columns if they already exist to avoid duplicates
    for col in ['idc_nab_pct', 'idc_pk_impact', 'idc_efficacy_impact']:
        if col in master_df.columns:
            master_df.drop(columns=[col], inplace=True)
            original_cols.remove(col)
            
    merged_df = pd.merge(master_df, idc_grouped, left_on='antibody_name_lower', right_on='therapeutic_lower', how='left')
    
    # Cleanup temp columns
    merged_df.drop(columns=['antibody_name_lower', 'therapeutic_lower'], inplace=True, errors='ignore')
    
    print(f"Master db row count before merge: {len(master_df)}, after merge: {len(merged_df)}")
    
    # Check how many were successfully mapped
    mapped_count = merged_df['idc_nab_pct'].notna() | merged_df['idc_pk_impact'].notna() | merged_df['idc_efficacy_impact'].notna()
    print(f"Successfully enriched {mapped_count.sum()} antibodies with IDC data.")
    
    # Reorder columns to put new ones near ada_first_pct if possible
    final_cols = original_cols.copy()
    if 'antibody_name_lower' in final_cols: final_cols.remove('antibody_name_lower')
    
    # Insert new cols after 'ada_first_pct' if it exists
    if 'ada_first_pct' in final_cols:
        idx = final_cols.index('ada_first_pct') + 1
        final_cols.insert(idx, 'idc_efficacy_impact')
        final_cols.insert(idx, 'idc_pk_impact')
        final_cols.insert(idx, 'idc_nab_pct')
    else:
        final_cols.extend(['idc_nab_pct', 'idc_pk_impact', 'idc_efficacy_impact'])
        
    merged_df = merged_df[final_cols]
    
    # Save back to master
    merged_df.to_csv(MASTER_CSV, index=False)
    print("Master database successfully overwritten and updated.")

if __name__ == "__main__":
    merge_idc_data()
