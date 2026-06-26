import pandas as pd

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

updates = {
    'Ganitumab': {
        'ada_value': '0% treatment-emergent anti-ganitumab binding antibodies in phase 1 Japanese study',
        'ada_value_display': '0.0%',
        'ada_first_pct': 0.0,
        'nab_pct': '0.0%',
        'dose_mg': '6, 12, or 20 mg/kg',
        'dose_freq': 'Every 2 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'MSD electrochemiluminescence binding antibody assay; cell-based neutralizing assay',
        'pk_efficacy_impact': 'No patient developed anti-ganitumab binding antibodies; no neutralizing antibodies detected among baseline-positive binding antibody samples',
        'evidence_source': 'Cancer Chemotherapy and Pharmacology phase 1 ganitumab Japanese solid tumor study; PMC full text',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC3428530/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC3428530/',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Safety/anti-ganitumab antibodies: no patient developed anti-ganitumab binding antibodies; no neutralizing antibodies detected',
        'verify_note': 'GAMMA phase 3 paper states anti-ganitumab antibody samples were collected but does not provide a 1.0% ADA result in retrieved text.'
    },
    'Amubarvimab': {
        'ada_value': 'ADA incidence not stated in retrieved ACTIV-2 amubarvimab/romlusevimab article',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '1000 mg amubarvimab plus 1000 mg romlusevimab',
        'dose_freq': 'Single sequential IV infusion regimen',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved article',
        'pk_efficacy_impact': 'ACTIV-2 article reports clinical benefit and no severe infusion reactions or drug-related serious adverse events, but no ADA incidence',
        'evidence_source': 'Annals of Internal Medicine ACTIV-2 amubarvimab/romlusevimab trial; PMC full text',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10150320/; https://pubmed.ncbi.nlm.nih.gov/37068272/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10150320/',
        'ada_source_pmids': '37068272',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Methods/results reviewed for treatment, safety, and clinical outcomes; no immunogenicity/ADA incidence stated in retrieved article',
        'verify_note': 'Prior 1.0% ADA display value was not supported by the retrieved ACTIV-2 publication.'
    },
    'Birtamimab': {
        'ada_value': 'ADA incidence not stated in retrieved VITAL phase 3 article',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '24 mg/kg up to 2500 mg',
        'dose_freq': 'Every 28 days',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved article',
        'pk_efficacy_impact': 'VITAL article reports safety/efficacy outcomes but no ADA incidence in retrieved main text',
        'evidence_source': 'Blood 2023 VITAL phase 3 birtamimab trial; PMC full text',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10644097/; https://pubmed.ncbi.nlm.nih.gov/37366170/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10644097/',
        'ada_source_pmids': '37366170',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'VITAL methods/safety text reviewed; anti-drug antibody incidence not reported in retrieved article',
        'verify_note': 'Prior 0.0% value was not confirmed in the retrieved VITAL full text.'
    },
    'Enoblituzumab': {
        'ada_value': 'ADA incidence not stated in retrieved enoblituzumab+pembrolizumab phase I/II article',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '3-15 mg/kg enoblituzumab plus pembrolizumab 2 mg/kg',
        'dose_freq': 'Weekly enoblituzumab during dose escalation/expansion; pembrolizumab every 3 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'Immunogenicity assessed; assay details/rate not stated in retrieved article',
        'pk_efficacy_impact': 'Article reports acceptable safety and antitumor activity; no ADA incidence or impact stated in retrieved text',
        'evidence_source': 'Journal for ImmunoTherapy of Cancer 2022 enoblituzumab+pembrolizumab phase I/II article; PMC full text',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9006844/; https://doi.org/10.1136/jitc-2021-004424',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9006844/',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Study design states immunogenicity was assessed; retrieved results text does not provide an ADA percentage',
        'verify_note': 'Prior 2.0% value was not confirmed in the retrieved phase I/II article.'
    },
    'Envafolimab': {
        'ada_value': 'ADA incidence not stated in retrieved model-informed development article',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '2.5 mg/kg QW, 150 mg QW, or 300 mg Q2W regimens evaluated/simulated',
        'dose_freq': 'Weekly or every 2 weeks depending on regimen',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'ADA sampling included across source studies; rate not stated in retrieved article',
        'pk_efficacy_impact': 'PopPK/exposure-response article reports no dose adjustment needed; no ADA incidence or ADA impact stated in main text',
        'evidence_source': 'The Oncologist 2024 envafolimab model-informed drug development article; PMC full text',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11379657/; https://pubmed.ncbi.nlm.nih.gov/38982653/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11379657/',
        'ada_source_pmids': '38982653',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Methods: ADA sampling summarized for included studies; no ADA incidence reported in retrieved main text',
        'verify_note': 'Prior 5.0% value was not supported by the retrieved model-informed development article.'
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
