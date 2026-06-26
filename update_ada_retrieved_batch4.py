import pandas as pd
import numpy as np

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

updates = {
    'Cetuximab': {
        'ada_value': '<5.0%',
        'nab_pct': 'Not specified',
        'dose_mg': '400 mg/m2 (loading), 250 mg/m2 (maintenance)',
        'dose_freq': 'Weekly',
        'route_curated': 'Intravenous',
        'assay_platform': 'ELISA',
        'evidence_source': 'FDA Label / Erbitux',
        'citation_urls': 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=8bc6397e-4bd8-4d37-a007-a327e4da34d9'
    },
    'Panitumumab': {
        'ada_value': '5.2% (monotherapy), 3.2% (with chemo)',
        'nab_pct': '18.9% (monotherapy), 14.9% (with chemo) (of ADA+)',
        'dose_mg': '6 mg/kg',
        'dose_freq': 'Every 2 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'ECL bridging immunoassay',
        'pk_efficacy_impact': 'No identified clinically significant effect on PK following monotherapy',
        'evidence_source': 'FDA Label / Vectibix',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/125147s213lbl.pdf'
    },
    'Omalizumab': {
        'ada_value': '<0.1%',
        'nab_pct': 'Not specified',
        'dose_mg': '75-600 mg',
        'dose_freq': 'Every 2 or 4 weeks',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'ELISA',
        'evidence_source': 'FDA Label / Xolair',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2021/103976s5238lbl.pdf'
    },
    'Ranibizumab': {
        'ada_value': '1.0-9.0%',
        'nab_pct': 'Not specified',
        'dose_mg': '0.3 mg or 0.5 mg',
        'dose_freq': 'Monthly',
        'route_curated': 'Intravitreal',
        'assay_platform': 'Immunoassay',
        'pk_efficacy_impact': 'Clinical significance unclear; some patients with highest levels had iritis or vitritis',
        'evidence_source': 'FDA Label / Lucentis',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2014/125156s105lbl.pdf'
    },
    'Denosumab': {
        'ada_value': '<1.0%',
        'nab_pct': '0.0%',
        'dose_mg': '60 mg',
        'dose_freq': 'Every 6 months',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'ECL bridging immunoassay',
        'pk_efficacy_impact': 'No evidence of altered PK, toxicity, or clinical response',
        'evidence_source': 'FDA Label / Prolia',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/125320s216lbl.pdf'
    },
    'Golimumab': {
        'ada_value': '4.0% (RA/PsA/AS)',
        'nab_pct': 'Majority of ADA+',
        'dose_mg': '50 mg',
        'dose_freq': 'Monthly',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'ELISA',
        'pk_efficacy_impact': 'Small number of positive patients limits definitive conclusions',
        'evidence_source': 'FDA Label / Simponi',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2011/125289s0064lbl.pdf'
    }
}

for name, data in updates.items():
    mask = df['antibody_name'].str.lower() == name.lower()
    if mask.any():
        for col, val in data.items():
            df.loc[mask, col] = val
        print(f'Updated {name}')
    else:
        print(f'Warning: {name} not found in CSV')

df.to_csv(ada_path, index=False)
