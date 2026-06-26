import pandas as pd
import os

MASTER_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada_master_136_curated.csv'
DISC_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_negative_library_by_phase.csv'
COMBINED_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\InSynBio_Combined_ADA_Database.csv'

def compile_full_database():
    print("Loading Master Database (138 curated)...")
    master_df = pd.read_csv(MASTER_CSV)
    
    # Standardize columns for merging
    master_subset = master_df[['antibody_name', 'ada_first_pct', 'target', 'phase_highest_global']].copy()
    master_subset.rename(columns={'phase_highest_global': 'phase'}, inplace=True)
    master_subset['source_db'] = 'Master_Curated'
    
    print("Loading Discontinued Database...")
    disc_df = pd.read_csv(DISC_CSV)
    
    # Filter for entries where we have successfully patched ADA data (not null)
    disc_verified = disc_df[disc_df['ada_first_pct'].notna()].copy()
    print(f"Found {len(disc_verified)} verified ADA entries in Discontinued library.")
    
    disc_subset = disc_verified[['antibody_name', 'ada_first_pct', 'target', 'phase_bucket']].copy()
    disc_subset.rename(columns={'phase_bucket': 'phase'}, inplace=True)
    disc_subset['source_db'] = 'Discontinued_Patched'
    
    # Combine both datasets
    combined_df = pd.concat([master_subset, disc_subset], ignore_index=True)
    
    # Remove duplicates if any antibody exists in both
    combined_df = combined_df.drop_duplicates(subset=['antibody_name'], keep='first')
    
    print(f"\nTotal Compiled InSynBio ADA Database: {len(combined_df)} unique antibodies.")
    
    # Save to disk
    combined_df.to_csv(COMBINED_CSV, index=False)
    print(f"Saved combined database to: {COMBINED_CSV}")
    
    return combined_df

if __name__ == "__main__":
    compile_full_database()
