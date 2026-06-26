import pandas as pd

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

updates = {
    'Gimsilumab': {
        'ada_value': 'ADA incidence not stated in retrieved BREATHE COVID-19 trial article',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '400 mg Day 1; 200 mg Day 8',
        'dose_freq': 'Two IV doses one week apart',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved article',
        'pk_efficacy_impact': 'BREATHE trial reports no mortality or key clinical outcome benefit; ADA incidence not reported in retrieved main text',
        'evidence_source': 'BREATHE randomized COVID-19 pneumonia trial; PMC full text',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9873114/; https://pubmed.ncbi.nlm.nih.gov/35290169/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9873114/',
        'ada_source_pmids': '35290169',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Methods/results reviewed; article reports dosing, safety, and efficacy endpoints but no immunogenicity/ADA incidence',
        'verify_note': 'Prior 2.0% value was not supported by the retrieved BREATHE publication.'
    },
    'Girentuximab': {
        'ada_value': 'ADA incidence not stated in retrieved ARISER phase 3 article',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '50 mg loading; 20 mg weekly',
        'dose_freq': 'Weekly for 24 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved article',
        'pk_efficacy_impact': 'ARISER reports no disease-free or overall survival benefit; ADA incidence not reported in retrieved article',
        'evidence_source': 'JAMA Oncology ARISER randomized clinical trial; PMC full text',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC5824229/; https://pubmed.ncbi.nlm.nih.gov/27787547/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC5824229/',
        'ada_source_pmids': '27787547',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Methods/results reviewed; ARISER article reports safety but no ADA/HACA incidence',
        'verify_note': 'Prior 9.0% value was not supported by the retrieved ARISER full text.'
    },
    'Glembatumumab': {
        'ada_value': 'ADA incidence not stated in retrieved METRIC article; immunogenicity assay described in phase I/II melanoma article',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '1.88 mg/kg in METRIC; phase I/II evaluated multiple schedules',
        'dose_freq': 'Every 21 days in METRIC',
        'route_curated': 'Intravenous',
        'assay_platform': 'Bridging ELISA described for phase I/II melanoma study; METRIC retrieved article did not state ADA incidence',
        'pk_efficacy_impact': 'METRIC reported no PFS advantage; no ADA incidence/impact stated in retrieved text',
        'evidence_source': 'METRIC Nature Breast Cancer article and JCO phase I/II melanoma article',
        'citation_urls': 'https://www.nature.com/articles/s41523-021-00244-6; https://ascopubs.org/doi/10.1200/JCO.2013.54.8115',
        'ada_source_url_primary': 'https://www.nature.com/articles/s41523-021-00244-6',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'METRIC retrieved text: no ADA rate; JCO phase I/II methods: immunogenicity determined by bridging ELISA, sensitivity 50 ng/mL',
        'verify_note': 'Prior 1.0% value was not confirmed in retrieved METRIC or phase I/II article text.'
    },
    'Balstilimab': {
        'ada_value': 'ADA incidence not stated in retrieved phase II cervical cancer article',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '3 mg/kg',
        'dose_freq': 'Every 2 weeks up to 24 months',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved article',
        'pk_efficacy_impact': 'Retrieved article reports ORR and manageable safety; no ADA incidence stated',
        'evidence_source': 'Gynecologic Oncology phase II balstilimab cervical cancer article',
        'citation_urls': 'https://www.sciencedirect.com/science/article/pii/S0090825821013160; https://pubmed.ncbi.nlm.nih.gov/34452745/',
        'ada_source_url_primary': 'https://www.sciencedirect.com/science/article/pii/S0090825821013160',
        'ada_source_pmids': '34452745',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Methods/results reviewed; no immunogenicity/ADA incidence stated in retrieved article',
        'verify_note': 'Prior 10.0% value was not supported by retrieved phase II publication.'
    },
    'Gantenerumab': {
        'ada_value': 'ADA incidence not stated in retrieved gantenerumab development review',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': 'Clinical dose equivalent to 1020 mg every 4 weeks described in review',
        'dose_freq': 'Every 4 weeks in late-stage program',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'Not stated in retrieved review',
        'pk_efficacy_impact': 'Review describes clinical development and exposure but does not state ADA incidence',
        'evidence_source': 'Alzheimer Research & Therapy gantenerumab development review; PMC full text',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9707418/; https://pubmed.ncbi.nlm.nih.gov/36447240/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9707418/',
        'ada_source_pmids': '36447240',
        'ada_source_type_curated': 'peer_reviewed_review',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Development review searched for immunogenicity/ADA terms; no ADA rate found in retrieved text',
        'verify_note': 'Prior 2.0% value was not supported by retrieved review or search results for GRADUATE.'
    },
    'Ianalumab': {
        'ada_value': 'ADA incidence not stated in retrieved 52-week Sjogren phase 2b abstract/full page',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '5, 50, 150, or 300 mg depending on treatment period',
        'dose_freq': 'Every 4 weeks',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'Not stated in retrieved article page',
        'pk_efficacy_impact': 'Retrieved article page reports sustained efficacy and favorable safety; no ADA incidence stated',
        'evidence_source': 'Arthritis & Rheumatology 52-week phase 2b ianalumab Sjogren article page',
        'citation_urls': 'https://acrjournals.onlinelibrary.wiley.com/doi/abs/10.1002/art.43059; https://pubmed.ncbi.nlm.nih.gov/39557617/',
        'ada_source_url_primary': 'https://acrjournals.onlinelibrary.wiley.com/doi/abs/10.1002/art.43059',
        'ada_source_pmids': '39557617',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Retrieved Wiley page/abstract searched for ADA/immunogenicity; no ADA incidence stated',
        'verify_note': 'Prior 1.0% value was not supported by retrieved article page.'
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
