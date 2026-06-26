import pandas as pd
import numpy as np

IDC_EXCEL = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\media-1.xlsx'
MASTER_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada_master_136_curated.csv'
ADC_DB_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\adc_immunogenicity_database.csv'
PENDING_ANTIBODIES_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\pure_antibodies_pending_research.csv'

def categorize_and_export():
    master_df = pd.read_csv(MASTER_CSV)
    master_names = set(master_df['antibody_name'].astype(str).str.lower().str.strip())
    
    idc_df = pd.read_excel(IDC_EXCEL, sheet_name='Clinical Trial')
    inn_col = "Molecule Assessed for ADA INN Name"
    ada_col = "Frequency of ADA+ patients"
    trade_col = "Therapeutic Assessed for ADA Trade name"
    disease_col = "Disease Indication Description"
    
    idc_df['therapeutic_lower'] = idc_df[inn_col].astype(str).str.lower().str.strip()
    idc_df['IDC_ADA_pct'] = pd.to_numeric(idc_df[ada_col].replace(['Not reported', 'Unknown', 'N/A', ''], np.nan), errors='coerce')
    
    idc_grouped = idc_df.groupby('therapeutic_lower').agg({
        inn_col: 'first',
        trade_col: lambda x: ', '.join(x.dropna().unique()),
        disease_col: lambda x: ', '.join(x.dropna().unique()),
        'IDC_ADA_pct': 'max'
    }).reset_index(drop=True)
    
    missing_df = idc_grouped[~idc_grouped[inn_col].astype(str).str.lower().str.strip().isin(master_names)].copy()
    
    # Keyword based categorization
    adc_keywords = ['vedotin', 'emtansine', 'ozogamicin', 'difitox', 'pasudotox', 'govitecan', 'deruxtecan', 'tox']
    non_ab_keywords = ['alfa', 'idase', 'human', 'factor', 'cept', 'pegvaliase']
    
    adcs = []
    pure_abs = []
    non_abs = []
    
    for _, row in missing_df.iterrows():
        name = row[inn_col]
        name_lower = str(name).lower()
        
        if any(kw in name_lower for kw in adc_keywords):
            adcs.append(row)
        elif any(kw in name_lower for kw in non_ab_keywords):
            non_abs.append(row)
        else:
            pure_abs.append(row)
            
    adc_df = pd.DataFrame(adcs)
    pure_ab_df = pd.DataFrame(pure_abs)
    non_ab_df = pd.DataFrame(non_abs)
    
    # Save ADC database
    if not adc_df.empty:
        adc_df.to_csv(ADC_DB_CSV, index=False)
        print(f"Created ADC database with {len(adc_df)} entries at: {ADC_DB_CSV}")
        
    # Save Pure Antibodies pending verification
    if not pure_ab_df.empty:
        pure_ab_df['Verification_Status'] = 'Pending Manual Verification (FDA Label)'
        pure_ab_df.to_csv(PENDING_ANTIBODIES_CSV, index=False)
        print(f"Created Pending Pure Antibodies list with {len(pure_ab_df)} entries at: {PENDING_ANTIBODIES_CSV}")
        
    print(f"Filtered out {len(non_ab_df)} Non-Antibody molecules (Enzymes/Traps).")

if __name__ == "__main__":
    categorize_and_export()
