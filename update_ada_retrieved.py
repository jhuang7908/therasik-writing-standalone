import pandas as pd
import numpy as np

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

updates = {
    'Avelumab': {
        'ada_value': '16.0-19.0%',
        'nab_pct': '78.0-97.0% (of ADA+)',
        'dose_mg': '10 mg/kg',
        'dose_freq': 'Every 2 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'ECL bridging immunoassay',
        'pk_efficacy_impact': '15% higher clearance in ADA+; no clinical impact',
        'evidence_source': 'DailyMed / FDA Label',
        'citation_urls': 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=5cd725a1-2fa4-408a-a651-57a7b84b2118'
    },
    'Alirocumab': {
        'ada_value': '5.5%',
        'nab_pct': '0.5%',
        'dose_mg': '75 mg or 150 mg',
        'dose_freq': 'Every 2 weeks',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'ECL bridging immunoassay',
        'pk_efficacy_impact': 'Attenuation in LDL-C efficacy in some ADA+; higher injection site reactions',
        'evidence_source': 'Sanofi / FDA Label',
        'citation_urls': 'https://products.sanofi.us/Praluent/praluent.html'
    },
    'Brentuximab vedotin': {
        'ada_value': '37.0%',
        'nab_pct': '62.0% (of ADA+)',
        'dose_mg': '1.8 mg/kg',
        'dose_freq': 'Every 3 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'ECL bridging immunoassay',
        'pk_efficacy_impact': 'Higher incidence of infusion-related reactions in persistent ADA+',
        'evidence_source': 'DailyMed / FDA Label',
        'citation_urls': 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=3904f8dd-1aef-3490-e48f-bd55f32ed67f'
    },
    'Belantamab mafodotin': {
        'ada_value': '3.0%',
        'nab_pct': '0.4%',
        'dose_mg': '2.5 mg/kg',
        'dose_freq': 'Every 3 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'ECL bridging immunoassay',
        'evidence_source': 'FDA Label',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761440s000lbl.pdf'
    },
    'Adebrelimab': {
        'dose_mg': '1200 mg (flat) or 20 mg/kg',
        'dose_freq': 'Every 3 weeks',
        'route_curated': 'Intravenous',
        'pk_efficacy_impact': '16-22% reduction in exposure (AUC/Ctrough) in ADA+',
        'evidence_source': 'PMC / PopPK Study',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11247113/'
    },
    'Evolocumab': {
        'ada_value': '0.3%',
        'nab_pct': '0.0%',
        'dose_mg': '140 mg or 420 mg',
        'dose_freq': 'Every 2 weeks or Monthly',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'ECL bridging immunoassay',
        'pk_efficacy_impact': 'No impact on PK, clinical response, or safety',
        'evidence_source': 'DailyMed / FDA Label',
        'citation_urls': 'https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=709338ae-ab8f-44a9-b7d5-abaabec3493a'
    },
    'Ixekizumab': {
        'ada_value': '9.0-22.0%',
        'nab_pct': '2.0%',
        'dose_mg': '160 mg (induction), 80 mg (maintenance)',
        'dose_freq': 'Every 2 or 4 weeks',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'ECL bridging immunoassay',
        'pk_efficacy_impact': 'Loss of efficacy and reduced drug concentration in ADA+',
        'evidence_source': 'FDA Label',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2016/125521s000lbl.pdf'
    },
    'Secukinumab': {
        'ada_value': '<1.0%',
        'nab_pct': '0.03%',
        'dose_mg': '150 mg or 300 mg',
        'dose_freq': 'Every 4 weeks',
        'route_curated': 'Subcutaneous or Intravenous',
        'assay_platform': 'ECL bridging immunoassay',
        'pk_efficacy_impact': 'Unknown impact due to low occurrence',
        'evidence_source': 'DailyMed / FDA Label',
        'citation_urls': 'https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=77c4b13e-7df3-42d4-81db-3d0cddb7f67a'
    },
    'Ustekinumab': {
        'ada_value': '2.9-12.4%',
        'nab_pct': 'Majority of ADA+',
        'dose_mg': '45 mg or 90 mg',
        'dose_freq': 'Every 8 or 12 weeks (SC)',
        'route_curated': 'Subcutaneous or Intravenous',
        'assay_platform': 'ECL bridging immunoassay',
        'pk_efficacy_impact': 'Reduced serum concentrations and reduced efficacy in ADA+',
        'evidence_source': 'FDA Label',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/125261s171,761044s019lbl.pdf'
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
