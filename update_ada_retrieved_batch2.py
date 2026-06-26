import pandas as pd
import numpy as np

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

updates = {
    'Adalimumab': {
        'ada_value': '5.0% (RA), 12.0% (monotherapy)',
        'nab_pct': 'Majority of ADA+',
        'dose_mg': '40 mg',
        'dose_freq': 'Every 2 weeks',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'ELISA',
        'pk_efficacy_impact': 'Lower ACR 20 response in ADA+; MTX reduces ADA incidence',
        'evidence_source': 'FDA Label / Humira',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2002/adalabb123102LB.htm'
    },
    'Infliximab': {
        'ada_value': '10.0% (RA/CD), 15.0% (PsA)',
        'nab_pct': 'Not specified (EIA used)',
        'dose_mg': '5 mg/kg',
        'dose_freq': 'Weeks 0, 2, 6, then Every 8 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'EIA / ECLIA',
        'pk_efficacy_impact': 'Higher clearance, reduced efficacy, and higher infusion reactions in ADA+',
        'evidence_source': 'FDA Label / Remicade',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2021/103772s5401lbl.pdf'
    },
    'Etanercept': {
        'ada_value': '6.0%',
        'nab_pct': '0.0%',
        'dose_mg': '50 mg',
        'dose_freq': 'Weekly',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'ELISA',
        'pk_efficacy_impact': 'No apparent correlation to clinical response or adverse events',
        'evidence_source': 'FDA Label / Enbrel',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2022/103795s5591lbl.pdf'
    },
    'Rituximab': {
        'ada_value': '1.1% (NHL), 23.0% (GPA/MPA)',
        'nab_pct': 'Not specified (ELISA used)',
        'dose_mg': '375 mg/m2',
        'dose_freq': 'Weekly for 4 weeks (NHL)',
        'route_curated': 'Intravenous',
        'assay_platform': 'ELISA',
        'pk_efficacy_impact': 'Clinical relevance unclear',
        'evidence_source': 'FDA Label / Ruxience',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2019/761103s000lbl.pdf'
    },
    'Trastuzumab': {
        'ada_value': '0.1%',
        'nab_pct': '0.0%',
        'dose_mg': '4 mg/kg (loading), 2 mg/kg (maintenance)',
        'dose_freq': 'Weekly',
        'route_curated': 'Intravenous',
        'assay_platform': 'HAHA assay',
        'pk_efficacy_impact': 'No allergic manifestations in the one positive patient',
        'evidence_source': 'FDA Label / Herceptin',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2002/trasgen082802lb.pdf'
    },
    'Bevacizumab': {
        'ada_value': '0.6%',
        'nab_pct': '21.0% (of ADA+)',
        'dose_mg': '5-15 mg/kg',
        'dose_freq': 'Every 2-3 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'ECL / ELISA',
        'pk_efficacy_impact': 'Clinical significance unknown',
        'evidence_source': 'FDA Label / Mvasi',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/761028s011lbl.pdf'
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
