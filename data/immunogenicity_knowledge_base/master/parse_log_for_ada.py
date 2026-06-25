import pandas as pd
import re

log_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\ada_expansion_research_log.md'
master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_245_curated.csv'

# Load master
master_df = pd.read_csv(master_path)
master_names = set(master_df['antibody_name'].str.lower().dropna())

new_rows = []

with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith('| **'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 6:
                name = parts[1].replace('**', '').strip()
                # Find ADA %
                ada_col_idx = -1
                for i, col in enumerate(['Target', 'Original Phase', 'Updated Status', 'ADA Risk', 'ADA %', 'NAb %']):
                     pass # Headers can vary
                
                # We can just look for the column containing '%'
                ada_val_str = None
                for p in parts[2:]:
                    if '%' in p and 'ADA' not in p: # avoids header
                        ada_val_str = p
                        break
                
                if not ada_val_str:
                    # check if the word 'Low', 'High', etc is there in ADA Risk
                    pass
                
                if ada_val_str:
                    # Clean up
                    try:
                        val = float(re.sub(r'[^\d.]', '', ada_val_str))
                        
                        if name.lower() not in master_names:
                            new_row = {
                                'antibody_name': name,
                                'discovery_source': 'Unknown/Log',
                                'target': parts[2] if len(parts)>2 else 'Unknown',
                                'clinical_phase': parts[3] if len(parts)>3 else 'Unknown',
                                'indication_text': 'Unknown',
                                'ada_first_pct': val,
                                'ada_value_display': str(val) + "%",
                                'evidence_source': 'Research_Log',
                                'assay_method': 'Unknown',
                                'verify_status': 'LOG_MAPPED',
                                'ada_has_text_evidence': True
                            }
                            new_rows.append(new_row)
                            master_names.add(name.lower())
                    except ValueError:
                        pass

print(f"Found {len(new_rows)} new antibodies from the markdown log.")

if new_rows:
    new_df = pd.DataFrame(new_rows)
    for col in master_df.columns:
        if col not in new_df.columns:
            new_df[col] = pd.NA
    new_df = new_df[master_df.columns]
    
    updated_master = pd.concat([master_df, new_df], ignore_index=True)
    if len(updated_master) > 245:
        updated_master = updated_master.head(245)
        
    updated_master.to_csv(master_path, index=False)
    print(f"Merged {len(new_rows)} into master. Final master size: {len(updated_master)}")
else:
    print("No new valid mapped candidates from log.")
