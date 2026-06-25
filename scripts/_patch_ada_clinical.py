
import pandas as pd
CSV_PATH = "data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv"

def patch_data():
    df = pd.read_csv(CSV_PATH)
    
    # Donanemab
    mask = df['antibody_name'].str.contains('Donanemab', case=False, na=False)
    df.loc[mask, 'assay_method'] = 'ECL Bridging'
    df.loc[mask, 'trial_duration_weeks'] = 76
    
    # Nipocalimab
    mask = df['antibody_name'].str.contains('Nipocalimab', case=False, na=False)
    df.loc[mask, 'assay_method'] = 'Bridging ELISA'
    df.loc[mask, 'trial_duration_weeks'] = 24
    
    # Epcoritamab
    mask = df['antibody_name'].str.contains('Epcoritamab', case=False, na=False)
    df.loc[mask, 'assay_method'] = 'ECL Bridging'
    df.loc[mask, 'trial_duration_weeks'] = 24 # Median follow-up ~10 months, but primary is earlier
    
    df.to_csv(CSV_PATH, index=False)
    print("Patched Donanemab, Nipocalimab, Epcoritamab")

if __name__ == "__main__":
    patch_data()
