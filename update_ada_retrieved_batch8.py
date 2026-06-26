import pandas as pd

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

updates = {
    'Bapineuzumab': {
        'ada_value': '0% antibapineuzumab antibodies in single-ascending-dose study',
        'ada_value_display': '0.0%',
        'ada_first_pct': 0.0,
        'nab_pct': 'Not reported',
        'dose_mg': '0.5-5 mg/kg single ascending IV dose',
        'dose_freq': 'Single dose in phase 1 study',
        'route_curated': 'Intravenous',
        'assay_platform': 'Validated ELISA for bapineuzumab and antibapineuzumab antibodies',
        'pk_efficacy_impact': 'No antibapineuzumab antibodies found in tested patients; phase 3 efficacy negative for clinical endpoints',
        'evidence_source': 'Phase 1 single ascending dose study; PMC full text',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC3715117/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC3715117/',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'PK/immunogenicity: no antibapineuzumab antibodies were found in any patients tested',
        'verify_note': 'The prior 36% value was not supported by the retrieved phase 3 or phase 1 sources; numeric field set from explicit phase 1 immunogenicity text.'
    },
    'Camidanlumab': {
        'ada_value': '2/117 confirmed positive post-dose ADA responses (1.7%)',
        'ada_value_display': '1.7%',
        'ada_first_pct': 1.7,
        'nab_pct': 'Not reported',
        'dose_mg': '45 ug/kg for cycles 1-2, then 30 ug/kg',
        'dose_freq': 'Every 3 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'Screening assay, confirmation assay, and titer assessment',
        'pk_efficacy_impact': 'No ADA-specific PK or efficacy impact stated in retrieved EudraCT result page',
        'evidence_source': 'EU Clinical Trials Register ADCT-301-201 results',
        'citation_urls': 'https://www.clinicaltrialsregister.eu/ctr-search/trial/2018-002556-32/results',
        'ada_source_url_primary': 'https://www.clinicaltrialsregister.eu/ctr-search/trial/2018-002556-32/results',
        'ada_source_type_curated': 'clinical_trial_registry',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Secondary endpoint: Number of Participants With Confirmed Positive Anti-Drug Antibody Responses Post Dose; 117 analyzed; value 2',
        'verify_note': '2/117 equals 1.7%; prior 13.6% appears to correspond to a non-ADA safety count in the same results page.'
    },
    'Epratuzumab': {
        'ada_value': 'No evidence of HAHA immunogenicity in initial SLE study',
        'ada_value_display': '0.0%',
        'ada_first_pct': 0.0,
        'nab_pct': 'Not reported',
        'dose_mg': '360 mg/m2',
        'dose_freq': 'Every other week for 4 doses',
        'route_curated': 'Intravenous',
        'assay_platform': 'Competitive ELISA HAHA assay',
        'pk_efficacy_impact': 'HAHA values stayed below assay sensitivity or were not increased from baseline',
        'evidence_source': 'Arthritis Research & Therapy initial epratuzumab SLE clinical trial',
        'citation_urls': 'https://arthritis-research.biomedcentral.com/articles/10.1186/ar1942',
        'ada_source_url_primary': 'https://arthritis-research.biomedcentral.com/articles/10.1186/ar1942',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Pharmacokinetics and immunogenicity: HAHA analysis gave no evidence of immunogenicity',
        'verify_note': 'Retrieved EMBODY phase 3 article did not provide a numeric 1.0% ADA value; retained only directly supported HAHA finding from full text.'
    },
    'Bebtelovimab': {
        'ada_value': 'ADA incidence not stated in retrieved FDA EUA fact sheet',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '175 mg',
        'dose_freq': 'Single dose',
        'route_curated': 'Intravenous injection',
        'assay_platform': 'Not stated in retrieved FDA EUA fact sheet',
        'pk_efficacy_impact': 'Not stated; EUA fact sheet provides PK and viral neutralization data but no ADA incidence',
        'evidence_source': 'FDA EUA Fact Sheet for Healthcare Providers / Bebtelovimab',
        'citation_urls': 'https://www.fda.gov/media/156152/download',
        'ada_source_url_primary': 'https://www.fda.gov/media/156152/download',
        'ada_source_type_curated': 'regulatory_eua_fact_sheet',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Clinical Pharmacology and Clinical Studies sections reviewed; no immunogenicity/ADA incidence section found in retrieved fact sheet',
        'verify_note': 'Prior 3.5% value was not supported by the FDA EUA fact sheet retrieved in this batch.'
    },
    'Etesevimab': {
        'ada_value': 'ADA incidence not stated in retrieved FDA EUA documents',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '1,400 mg with bamlanivimab 700 mg',
        'dose_freq': 'Single dose',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved FDA EUA documents',
        'pk_efficacy_impact': 'Not stated; retrieved 5.3% value refers to treatment-emergent viral variants, not anti-drug antibodies',
        'evidence_source': 'FDA EUA memoranda/fact sheet for bamlanivimab plus etesevimab',
        'citation_urls': 'https://www.fda.gov/media/151973/download; https://www.fda.gov/media/174886/download',
        'ada_source_url_primary': 'https://www.fda.gov/media/151973/download',
        'ada_source_type_curated': 'regulatory_eua_fact_sheet',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Antiviral Resistance section: 5.3% is treatment-emergent variants in BLAZE-1, not ADA; no ADA incidence stated',
        'verify_note': 'Corrected a likely field-confusion error: 5.3% was not an ADA rate.'
    }
}

for col in set().union(*(entry.keys() for entry in updates.values())):
    if col not in df.columns:
        df[col] = pd.NA
    df[col] = df[col].astype('object')

for name, data in updates.items():
    mask = df['antibody_name'].fillna('').astype(str).str.casefold() == name.casefold()
    if mask.any():
        for col, val in data.items():
            df.loc[mask, col] = val
        print(f'Updated {name}')
    else:
        print(f'MISSING {name}')

df.to_csv(ada_path, index=False)
