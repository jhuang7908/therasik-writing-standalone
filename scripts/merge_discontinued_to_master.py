import pandas as pd
import shutil

MASTER_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada_master_136_curated.csv'
BACKUP_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada_master_curated_BACKUP_preMerge.csv'
DISC_CSV = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_negative_library_by_phase.csv'

def merge_discontinued_to_master():
    print(f"Creating backup of master database to {BACKUP_CSV}...")
    shutil.copy2(MASTER_CSV, BACKUP_CSV)
    
    # Load Master
    master_df = pd.read_csv(MASTER_CSV)
    original_master_count = len(master_df)
    print(f"Loaded Master DB: {original_master_count} entries.")
    
    # Load Discontinued
    disc_df = pd.read_csv(DISC_CSV)
    
    # Filter only those that have a populated ADA value (successfully researched)
    disc_verified = disc_df[disc_df['ada_first_pct'].notna()].copy()
    print(f"Found {len(disc_verified)} verified entries in Discontinued DB.")
    
    # Align columns
    # Master has 'phase_highest_global', discontinued has 'phase_bucket'
    if 'phase_bucket' in disc_verified.columns:
        disc_verified['phase_highest_global'] = disc_verified['phase_bucket'].str.replace('_discontinued', '', regex=False)
        
    # Append the verified discontinued antibodies
    # Identify which ones are not already in master
    master_antibodies = set(master_df['antibody_name'].str.lower())
    new_entries = disc_verified[~disc_verified['antibody_name'].str.lower().isin(master_antibodies)]
    print(f"Identified {len(new_entries)} completely new antibodies to merge.")
    
    # Concat
    merged_df = pd.concat([master_df, new_entries], ignore_index=True)
    
    # Save back
    merged_df.to_csv(MASTER_CSV, index=False)
    print(f"Merged successfully. Master DB now contains {len(merged_df)} entries.")

if __name__ == "__main__":
    merge_discontinued_to_master()
