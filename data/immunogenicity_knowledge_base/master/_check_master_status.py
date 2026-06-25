
import pandas as pd
import os

master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_245_curated.csv'

def check_status():
    if not os.path.exists(master_path):
        print(f"File not found: {master_path}")
        return

    df = pd.read_csv(master_path)
    total = len(df)
    
    has_ada = df['ada_first_pct'].notnull().sum()
    missing_ada = df['ada_first_pct'].isnull().sum()
    
    has_vh = df['vh_seq'].notnull().sum()
    has_vl = df['vl_seq'].notnull().sum()
    
    has_both_seq = ((df['vh_seq'].notnull()) & (df['vl_seq'].notnull())).sum()
    
    has_source = df['evidence_source'].notnull().sum()
    
    print(f"Total entries: {total}")
    print(f"Entries with ADA data: {has_ada} ({has_ada/total*100:.1f}%)")
    print(f"Entries missing ADA data: {missing_ada}")
    print(f"Entries with both VH/VL sequences: {has_both_seq} ({has_both_seq/total*100:.1f}%)")
    print(f"Entries with evidence source: {has_source} ({has_source/total*100:.1f}%)")
    
    # List some antibodies missing ADA data
    if missing_ada > 0:
        print("\nTop antibodies missing ADA data (sample):")
        print(df[df['ada_first_pct'].isnull()]['antibody_name'].head(20).tolist())

    # Check for potential 'hallucinations' or placeholders
    placeholders = df[df['evidence_source'].str.contains('placeholder', case=False, na=False)]
    if not placeholders.empty:
        print(f"\nFound {len(placeholders)} entries with 'placeholder' in evidence source.")

if __name__ == "__main__":
    check_status()
