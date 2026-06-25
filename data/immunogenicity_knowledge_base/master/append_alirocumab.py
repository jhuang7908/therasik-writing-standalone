import pandas as pd
import numpy as np

master_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\immunogenicity_knowledge_base\master\ada_master_245_curated.csv'
master_df = pd.read_csv(master_path)

found_data = [
    {
        'antibody_name': 'Alirocumab',
        'discovery_source': 'transgenic_animal',
        'target': 'PCSK9',
        'clinical_phase': 'Approved',
        'indication_text': 'Hyperlipidemia',
        'ada_first_pct': 5.1,
        'ada_value_display': '5.1% (~1% NAb)',
        'evidence_source': 'ClinicalTrials_Literature (Search)',
        'assay_method': 'Unknown',
        'verify_status': 'WEB_SEARCH_VERIFIED',
        'ada_has_text_evidence': True
    }
]

new_df = pd.DataFrame(found_data)
for col in master_df.columns:
    if col not in new_df.columns:
        new_df[col] = np.nan
new_df = new_df[master_df.columns]

updated_master = pd.concat([master_df, new_df], ignore_index=True)
updated_master.to_csv(master_path, index=False)
print(f"Appended {len(found_data)} found entries. Master size now: {len(updated_master)}")
