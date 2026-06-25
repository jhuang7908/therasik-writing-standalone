import pandas as pd
import re

candidates_md_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_candidates_to_fill.md'
output_csv_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_batch9_and_10_candidates.csv'

# Parse MD table
candidates = []
with open(candidates_md_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith('| **'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 6:
                name = parts[1].replace('**', '').strip()
                category = parts[2]
                target = parts[3]
                phase = parts[4]
                indication = parts[5]
                candidates.append({
                    'antibody_name': name,
                    'discovery_source': category,
                    'target': target,
                    'clinical_phase': phase,
                    'indication': indication
                })

# Assign scores to sort by clinical phase
def score_phase(p):
    p = str(p).lower()
    if 'approved' in p or 'market' in p or 'emergency' in p: return 5
    if '3' in p or 'iii' in p: return 4
    if '2' in p or 'ii' in p: return 3
    if '1' in p or 'i' in p: return 2
    if p: return 1
    return 0

candidates.sort(key=lambda x: (score_phase(x['clinical_phase']), x['antibody_name']), reverse=True)

# Select top 49 to reach 245
top_49 = candidates[:49]
df_top49 = pd.DataFrame(top_49)
df_top49['ada_pct'] = ''
df_top49['assay'] = ''
df_top49['evidence_source'] = ''

df_top49.to_csv(output_csv_path, index=False)
print(f"Saved {len(top_49)} top candidates to {output_csv_path}")
