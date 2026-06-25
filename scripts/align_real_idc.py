import pandas as pd
import numpy as np

COMBINED_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\InSynBio_Combined_ADA_Database.csv'
IDC_EXCEL = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\media-1.xlsx'
REPORT_MD = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\reports\IDC_V1_Cross_Validation_Report.md'

def run_alignment():
    print("Loading InSynBio Combined Database...")
    insynbio_df = pd.read_csv(COMBINED_CSV)
    insynbio_df['antibody_name_lower'] = insynbio_df['antibody_name'].str.lower()
    print(f"Loaded {len(insynbio_df)} entries from InSynBio database.")
    
    print("Loading IDC V1 Database (media-1.xlsx, Clinical Trial sheet)...")
    idc_df = pd.read_excel(IDC_EXCEL, sheet_name='Clinical Trial')
    
    therapeutic_col = "Molecule Assessed for ADA INN Name"
    ada_col = "Frequency of ADA+ patients"
    nab_col = "Frequency nADA+ patients reported"
    pk_col = "ADA interpreted to impact PK"
    eff_col = "ADA interpreted to impact Efficacy"
    
    print(f"Mapped Columns: Drug='{therapeutic_col}', ADA='{ada_col}'")
    
    idc_df['therapeutic_lower'] = idc_df[therapeutic_col].astype(str).str.lower()
    
    # Handle 'Not reported' and convert to numeric
    idc_df['IDC_ADA_pct'] = pd.to_numeric(idc_df[ada_col].replace(['Not reported', 'Unknown', 'N/A', ''], np.nan), errors='coerce')
    idc_df['IDC_NAb_pct'] = pd.to_numeric(idc_df[nab_col].replace(['Not reported', 'Unknown', 'N/A', ''], np.nan), errors='coerce')
        
    # Merge
    merged = pd.merge(insynbio_df, idc_df, left_on='antibody_name_lower', right_on='therapeutic_lower', how='inner')
    
    # Group by antibody because IDC might have multiple trials per therapeutic
    # We take the max ADA % as the worst-case scenario for safety
    agg_funcs = {
        'antibody_name': 'first',
        'ada_first_pct': 'first',
        'source_db': 'first',
        'IDC_ADA_pct': 'max',
        'IDC_NAb_pct': 'max',
        pk_col: 'first',
        eff_col: 'first'
    }
    
    grouped = merged.groupby('antibody_name_lower').agg(agg_funcs).reset_index(drop=True)
    
    print(f"Successfully aligned {len(grouped)} unique therapeutics.")
    
    # Calculate discrepancies
    grouped['ADA_Delta'] = abs(grouped['ada_first_pct'] - grouped['IDC_ADA_pct'])
    
    discrepancies = grouped[grouped['ADA_Delta'] > 5.0].sort_values('ADA_Delta', ascending=False)
    perfect_matches = grouped[(grouped['ADA_Delta'] <= 1.0) | (grouped['ADA_Delta'].isna())]
    
    # Generate Report
    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("# InSynBio vs IDC V1 - Database Cross-Validation Report\n\n")
        f.write("## 1. Overview\n")
        f.write(f"- **InSynBio Combined Entries:** {len(insynbio_df)}\n")
        f.write(f"- **IDC V1 Clinical Entries (Unique):** {idc_df['therapeutic_lower'].nunique()}\n")
        f.write(f"- **Overlapping Therapeutics Aligned:** {len(grouped)}\n\n")
        
        f.write("## 2. Validation Metrics\n")
        f.write(f"- **High Concordance (Δ ≤ 1.0% or Both NA):** {len(perfect_matches)} antibodies\n")
        f.write(f"- **Discrepancies (Δ > 5.0%):** {len(discrepancies)} antibodies\n\n")
        
        f.write("## 3. Discrepancy Analysis (Requires Manual Review)\n")
        f.write("| Antibody | Source | InSynBio ADA % | IDC V1 ADA % (Max) | Delta | NAb % | PK Impact | Efficacy Impact |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for _, row in discrepancies.iterrows():
            f.write(f"| **{row['antibody_name']}** | {row['source_db']} | {row['ada_first_pct']} | {row['IDC_ADA_pct']} | {round(row['ADA_Delta'],1)} | {row['IDC_NAb_pct']} | {row[pk_col]} | {row[eff_col]} |\n")
            
        f.write("\n## 4. Next Steps\n")
        f.write("- **Data Enrichment**: Merge the newly extracted IDC `NAb %`, `PK Impact`, and `Efficacy Impact` columns directly into `ada_master_136_curated.csv`.\n")
        f.write("- **Discrepancy Resolution**: Review the high-delta items above. In many cases, IDC reports the maximum trial ADA, while InSynBio might track phase-specific or monotherapy ADA.\n")

    print(f"Report generated: {REPORT_MD}")

if __name__ == "__main__":
    run_alignment()
