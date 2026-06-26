import pandas as pd
import numpy as np

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

updates = {
    'Pembrolizumab': {
        'ada_value': '2.1%',
        'nab_pct': '0.5%',
        'dose_mg': '200 mg or 400 mg',
        'dose_freq': 'Every 3 or 6 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'ECL bridging immunoassay',
        'pk_efficacy_impact': 'No identified clinically significant effects on PK or risk of infusion reactions',
        'evidence_source': 'FDA Label / Keytruda',
        'citation_urls': 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=9333c79b-d487-4538-a9f0-71b91a02b287'
    },
    'Nivolumab': {
        'ada_value': '11.2-12.7%',
        'nab_pct': '0.7-0.8%',
        'dose_mg': '240 mg or 480 mg',
        'dose_freq': 'Every 2 or 4 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'ECL bridging immunoassay',
        'evidence_source': 'FDA Label / Opdivo / JITC',
        'citation_urls': 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=f570b9c4-6846-4de2-abfa-4d0a4ae4e394'
    },
    'Ipilimumab': {
        'ada_value': '1.1-4.9%',
        'nab_pct': '0.0%',
        'dose_mg': '3 mg/kg',
        'dose_freq': 'Every 3 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'ECL bridging immunoassay',
        'evidence_source': 'FDA Label / Yervoy / JITC',
        'citation_urls': 'https://packageinserts.bms.com/pi/pi_yervoy.pdf'
    },
    'Atezolizumab': {
        'ada_value': '30.0-48.0%',
        'nab_pct': 'Not reported',
        'dose_mg': '840 mg, 1200 mg, or 1680 mg',
        'dose_freq': 'Every 2, 3, or 4 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'ECL bridging immunoassay',
        'pk_efficacy_impact': 'Higher ADA rates did not substantially affect treatment efficacy in most patients',
        'evidence_source': 'FDA Label / Tecentriq / JITC',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/761034s053lbl.pdf'
    },
    'Durvalumab': {
        'ada_value': '3.0%',
        'nab_pct': '0.5%',
        'dose_mg': '10 mg/kg or 1500 mg',
        'dose_freq': 'Every 2 or 4 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'ECL bridging immunoassay',
        'pk_efficacy_impact': 'No clinically relevant effect on PK or safety',
        'evidence_source': 'FDA Label / Imfinzi',
        'citation_urls': 'https://ce.mayo.edu/sites/default/files/IMFINZI%C2%AE%20%28durvalumab%29%20US%20Prescribing%20Information.pdf'
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
