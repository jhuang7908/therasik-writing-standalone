
import pandas as pd
import numpy as np

master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_245_curated.csv'

def run_authenticity_check():
    df = pd.read_csv(master_path)
    issues = []

    # 1. Check ADA Value Consistency
    for idx, row in df.iterrows():
        name = row['antibody_name']
        display = str(row['ada_value_display'])
        pct = row['ada_first_pct']
        
        if pd.notnull(pct):
            if pct < 0 or pct > 100:
                issues.append(f"CRITICAL: {name} has ADA% out of range: {pct}")
            
            # Simple check if pct is present in display string (basic heuristic)
            if str(int(pct)) not in display and str(pct) not in display and 'No treatment-emergent' not in display:
                 # Check if it's a zero value or specifically handled
                 if pct == 0 and ('0%' in display or 'None' in display or 'No' in display):
                     pass
                 else:
                     issues.append(f"WARNING: {name} ADA% ({pct}) might mismatch display text: '{display}'")

    # 2. Check Sequences
    for idx, row in df.iterrows():
        name = row['antibody_name']
        vh = str(row['vh_seq'])
        vl = str(row['vl_seq'])
        
        if vh != 'nan' and len(vh) < 100:
            issues.append(f"WARNING: {name} VH sequence too short ({len(vh)})")
        if vl != 'nan' and len(vl) < 90:
            issues.append(f"WARNING: {name} VL sequence too short ({len(vl)})")
            
        # Check for non-amino acid characters
        if vh != 'nan' and any(c not in 'ACDEFGHIKLMNPQRSTVWY' for c in vh.upper()):
            issues.append(f"CRITICAL: {name} VH sequence contains invalid characters")
        if vl != 'nan' and any(c not in 'ACDEFGHIKLMNPQRSTVWY' for c in vl.upper()):
            issues.append(f"CRITICAL: {name} VL sequence contains invalid characters")

    # 3. Check for duplicates
    dups = df[df.duplicated(subset=['antibody_name'], keep=False)]
    if not dups.empty:
        issues.append(f"WARNING: Duplicate antibody names found: {dups['antibody_name'].unique().tolist()}")

    # 4. Check for 'UNKNOWN' or placeholders in critical metadata
    for col in ['thera_genetics_class', 'origin', 'evidence_source']:
        unknowns = df[df[col].astype(str).str.contains('UNKNOWN|placeholder|TBD', case=False, na=False)]
        if not unknowns.empty:
            issues.append(f"INFO: {len(unknowns)} entries have '{col}' as UNKNOWN/placeholder")

    # Print Report
    print("--- ADA Database Authenticity Check Report ---")
    if not issues:
        print("No obvious issues found.")
    else:
        for issue in issues:
            print(issue)
    print(f"\nChecked {len(df)} entries.")

if __name__ == "__main__":
    run_authenticity_check()
