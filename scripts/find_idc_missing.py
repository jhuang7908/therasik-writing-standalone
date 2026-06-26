import pandas as pd
import numpy as np

MASTER_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada_master_136_curated.csv'
IDC_EXCEL = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\media-1.xlsx'
OUTPUT_REPORT = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\reports\IDC_Missing_From_InSynBio_Report.md'

def find_missing():
    print("Loading Master DB...")
    master_df = pd.read_csv(MASTER_CSV)
    master_names = set(master_df['antibody_name'].astype(str).str.lower().str.strip())
    
    print("Loading IDC DB...")
    idc_df = pd.read_excel(IDC_EXCEL, sheet_name='Clinical Trial')
    
    inn_col = "Molecule Assessed for ADA INN Name"
    ada_col = "Frequency of ADA+ patients"
    trade_col = "Therapeutic Assessed for ADA Trade name"
    disease_col = "Disease Indication Description"
    
    # Process IDC Data
    idc_df['therapeutic_lower'] = idc_df[inn_col].astype(str).str.lower().str.strip()
    
    # Replace not reported
    idc_df['IDC_ADA_pct'] = pd.to_numeric(idc_df[ada_col].replace(['Not reported', 'Unknown', 'N/A', ''], np.nan), errors='coerce')
    
    # Group by INN to get unique antibodies and their max ADA and typical indication
    idc_grouped = idc_df.groupby('therapeutic_lower').agg({
        inn_col: 'first',
        trade_col: lambda x: ', '.join(x.dropna().unique()),
        disease_col: lambda x: ', '.join(x.dropna().unique()),
        'IDC_ADA_pct': 'max'
    }).reset_index(drop=True)
    
    # Find the missing ones
    missing_from_master = idc_grouped[~idc_grouped[inn_col].astype(str).str.lower().str.strip().isin(master_names)].copy()
    
    # Sort by ADA percent descending
    missing_from_master.sort_values(by='IDC_ADA_pct', ascending=False, inplace=True, na_position='last')
    
    print(f"Total unique in IDC: {len(idc_grouped)}")
    print(f"Total missing from our Master: {len(missing_from_master)}")
    
    # Generate report
    with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
        f.write("# IDC Antibodies Missing from InSynBio 147-Panel\n\n")
        f.write(f"We identified **{len(missing_from_master)}** unique therapeutics present in the IDC V1 database that are currently missing from our 147-antibody master panel.\n\n")
        
        f.write("## Top Missing Candidates (Sorted by Max ADA %)\n")
        f.write("| INN Name | Trade Name | Max ADA % | Disease Indication |\n")
        f.write("|---|---|---|---|\n")
        for _, row in missing_from_master.iterrows():
            inn = row[inn_col]
            trade = row[trade_col] if pd.notna(row[trade_col]) else "N/A"
            ada = row['IDC_ADA_pct'] if pd.notna(row['IDC_ADA_pct']) else "Unknown"
            disease = row[disease_col] if pd.notna(row[disease_col]) else "N/A"
            # truncate long disease strings
            if len(str(disease)) > 50:
                disease = str(disease)[:47] + "..."
            f.write(f"| {inn} | {trade} | {ada} | {disease} |\n")
            
    print(f"Report saved to {OUTPUT_REPORT}")

if __name__ == "__main__":
    find_missing()
