import pandas as pd
import numpy as np
import os

MASTER_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada_master_136_curated.csv'
IDC_MOCK_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\idc_v1_mock.csv'
REPORT_MD = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\reports\IDC_V1_Cross_Validation_Report.md'

def create_mock_idc_data():
    # Since we can't directly download the Excel right now, we create a mock
    # representation of the 142 clinical trial entries based on standard ADA distributions
    # to demonstrate the alignment pipeline.
    master_df = pd.read_csv(MASTER_CSV)
    
    # Take a subset to represent the 142 IDC clinical trials
    idc_candidates = master_df['antibody_name'].dropna().unique()[:142]
    
    idc_data = []
    for name in idc_candidates:
        # Mocking IDC structure based on paper description
        # IDC includes ADA incidence, NAb incidence, PK impact, Safety Impact
        ada_pct = master_df[master_df['antibody_name'] == name]['ada_first_pct'].values
        ada_val = ada_pct[0] if len(ada_pct) > 0 and not np.isnan(ada_pct[0]) else np.nan
        
        # Add slight variation to simulate different trial data sources
        idc_val = ada_val + np.random.normal(0, 1) if not np.isnan(ada_val) else np.nan
        if not np.isnan(idc_val) and idc_val < 0: idc_val = 0.0
            
        idc_data.append({
            'Therapeutic': name,
            'IDC_ADA_Incidence': round(idc_val, 1) if not np.isnan(idc_val) else np.nan,
            'IDC_NAb_Incidence': round(idc_val * 0.2, 1) if not np.isnan(idc_val) else np.nan,
            'Clinical_Impact_PK': np.random.choice(['Yes', 'No', 'Unknown']),
            'Clinical_Impact_Safety': np.random.choice(['Yes', 'No', 'Unknown'])
        })
        
    idc_df = pd.DataFrame(idc_data)
    idc_df.to_csv(IDC_MOCK_CSV, index=False)
    return idc_df

def run_alignment():
    print("Loading Master Database...")
    master_df = pd.read_csv(MASTER_CSV)
    print(f"Master Database loaded: {len(master_df)} entries.")
    
    if not os.path.exists(IDC_MOCK_CSV):
        print("IDC V1 dataset not found. Generating mock subset for pipeline testing...")
        idc_df = create_mock_idc_data()
    else:
        idc_df = pd.read_csv(IDC_MOCK_CSV)
        
    print(f"IDC V1 Database loaded: {len(idc_df)} clinical entries.")
    
    # Merge on therapeutic name
    merged = pd.merge(master_df, idc_df, left_on='antibody_name', right_on='Therapeutic', how='inner')
    print(f"Successfully aligned {len(merged)} overlapping antibodies.")
    
    # Calculate discrepancies
    merged['ADA_Delta'] = abs(merged['ada_first_pct'] - merged['IDC_ADA_Incidence'])
    
    discrepancies = merged[merged['ADA_Delta'] > 5.0]
    perfect_matches = merged[merged['ADA_Delta'] <= 1.0]
    
    # Generate Report
    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("# IDC V1 Database Cross-Validation Report\n\n")
        f.write("## 1. Overview\n")
        f.write(f"- **InSynBio Master Entries:** {len(master_df)}\n")
        f.write(f"- **IDC V1 Clinical Entries:** {len(idc_df)}\n")
        f.write(f"- **Overlapping Therapeutics Aligned:** {len(merged)}\n\n")
        
        f.write("## 2. Validation Metrics\n")
        f.write(f"- **High Concordance (Δ ≤ 1.0%):** {len(perfect_matches)} antibodies\n")
        f.write(f"- **Discrepancies (Δ > 5.0%):** {len(discrepancies)} antibodies\n\n")
        
        f.write("## 3. Discrepancy Analysis (Requires Manual Review)\n")
        f.write("| Antibody | InSynBio ADA % | IDC V1 ADA % | Delta | Clinical Impact (IDC) |\n")
        f.write("|---|---|---|---|---|\n")
        for _, row in discrepancies.iterrows():
            f.write(f"| {row['antibody_name']} | {row['ada_first_pct']} | {row['IDC_ADA_Incidence']} | {round(row['ADA_Delta'],1)} | PK: {row['Clinical_Impact_PK']}, Safety: {row['Clinical_Impact_Safety']} |\n")
            
        f.write("\n## 4. Next Steps\n")
        f.write("- Download the official Supplementary Table S4 from bioRxiv (10.64898/2025.12.08.692993v1).\n")
        f.write("- Replace mock dataset and re-run alignment.\n")
        f.write("- Merge IDC NAb% and Clinical Impact fields into `ada_master_136_curated.csv`.\n")

    print(f"Report generated: {REPORT_MD}")

if __name__ == "__main__":
    run_alignment()
