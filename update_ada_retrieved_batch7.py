import pandas as pd

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

updates = {
    'Nipocalimab': {
        'ada_value': '40.7% ADA; 14.8% NAb',
        'ada_value_display': '40.7%',
        'ada_first_pct': 40.7,
        'nab_pct': '14.8%',
        'dose_mg': '5 mg/kg, 30 mg/kg, or 60 mg/kg',
        'dose_freq': 'Every 2 weeks or every 4 weeks in phase 2 gMG dose-ranging study',
        'route_curated': 'Intravenous',
        'assay_platform': 'Validated immunoassay; NAb assessed in evaluable ADA population',
        'pk_efficacy_impact': 'ADA/NAb did not affect PK, IgG lowering, efficacy, or safety in the retrieved phase 2 gMG report',
        'evidence_source': 'Neurology 2024 Vivacity-MG phase 2 report; PMID/PMC full text',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10962909/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10962909/',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Results/Immunogenicity: 54 nipocalimab-treated patients evaluable; 40.7% ADA; 14.8% NAb; no PK/PD/efficacy/safety impact reported',
        'verify_note': 'Original text states 22/54 ADA-positive through day 113 and 8/54 NAb-positive; ADA titers generally low and transient.'
    },
    'Tiragolumab': {
        'ada_value': '1.9% treatment-emergent ADA',
        'ada_value_display': '1.9%',
        'ada_first_pct': 1.9,
        'nab_pct': 'Not reported in retrieved PK/immunogenicity article',
        'dose_mg': '2-1200 mg Q3W; 840 mg Q4W cohorts; recommended phase 2 dose 600 mg Q3W',
        'dose_freq': 'Every 3 weeks or every 4 weeks in GO30103',
        'route_curated': 'Intravenous',
        'assay_platform': 'Validated immunoassay; relative ADA sensitivity 2.90 ng/mL',
        'pk_efficacy_impact': 'No apparent immunogenicity liability; no meaningful drug-drug interaction reported',
        'evidence_source': 'Journal of Clinical Pharmacology 2024 tiragolumab GO30103 PK/immunogenicity report',
        'citation_urls': 'https://repositori.upf.edu/bitstreams/b79cac40-64bc-4916-8d35-b006735bf135/download; https://doi.org/10.1002/jcph.2397',
        'ada_source_url_primary': 'https://repositori.upf.edu/bitstreams/b79cac40-64bc-4916-8d35-b006735bf135/download',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Immunogenicity: 4/207 phase 1b evaluable patients (1.9%) positive for treatment-emergent ADAs against tiragolumab',
        'verify_note': 'Original text reports all four ADA-positive patients were transiently positive at one time point only.'
    },
    'Suptavumab': {
        'ada_value': '3% in 1-dose group; <1% in 2-dose group',
        'ada_value_display': '3.0%',
        'ada_first_pct': 3.0,
        'nab_pct': 'Not reported separately in retrieved article',
        'dose_mg': '30 mg/kg',
        'dose_freq': 'One or two intramuscular doses 8 weeks apart',
        'route_curated': 'Intramuscular',
        'assay_platform': 'Validated electrochemiluminescence bridging immunoassay',
        'pk_efficacy_impact': 'Lack of efficacy was not due to anti-suptavumab antibody responses; incidence and titers were low across treatment groups',
        'evidence_source': 'Clinical Infectious Diseases 2021/PMC NURSERY phase 3 suptavumab trial',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC8653633/; https://pubmed.ncbi.nlm.nih.gov/32897368/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC8653633/',
        'ada_source_pmids': '32897368',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Immunogenicity: 3% and <1% of infants in the 1- and 2-dose groups produced low-titer anti-suptavumab antibody response; placebo 4%',
        'verify_note': 'Original text reports low immunogenicity and no efficacy failure attributable to anti-suptavumab responses.'
    },
    'Ublituximab': {
        'ada_value': '81% ADA at one or more timepoints; 18.5% ADA at Week 96',
        'ada_value_display': '81.0%',
        'ada_first_pct': 81.0,
        'nab_pct': '6.4%',
        'dose_mg': '150 mg first infusion; 450 mg second and subsequent infusions',
        'dose_freq': 'Second infusion at 2 weeks; subsequent infusions every 24 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'Anti-drug antibody assay in RMS clinical efficacy and safety trials',
        'pk_efficacy_impact': 'Presence of ADA or neutralising antibodies had no observable impact on safety or efficacy',
        'evidence_source': 'European Commission/EMA BRIUMVI product information',
        'citation_urls': 'https://ec.europa.eu/health/documents/community-register/2023/20230531159144/anx_159144_en.pdf',
        'ada_source_url_primary': 'https://ec.europa.eu/health/documents/community-register/2023/20230531159144/anx_159144_en.pdf',
        'ada_source_type_curated': 'regulatory_label',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Immunogenicity: 81% ADA at one or more timepoints over 96 weeks; 18.5% positive at Week 96; 6.4% neutralising activity',
        'verify_note': 'EU product information gives higher cumulative ADA incidence than the unsourced existing 18% value; 18.5% refers to Week 96 only.'
    },
    'Zanidatamab': {
        'ada_value': 'Insufficient information to characterize ADA response',
        'ada_value_display': 'Not quantifiable',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not quantifiable',
        'dose_mg': '20 mg/kg',
        'dose_freq': 'Every 2 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not characterized in FDA label',
        'pk_efficacy_impact': 'FDA label states insufficient information to characterize ADA effects on PK, pharmacodynamics, safety, or effectiveness',
        'evidence_source': 'FDA Label / ZIIHERA',
        'citation_urls': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/761416s000lbl.pdf',
        'ada_source_url_primary': 'https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/761416s000lbl.pdf',
        'ada_source_type_curated': 'regulatory_label',
        'ada_has_text_evidence': True,
        'ada_source_section': '12.6 Immunogenicity: insufficient information to characterize anti-drug antibody response',
        'verify_note': 'Official label does not support the prior unsourced 1.5% ADA value; numeric field intentionally set to missing.'
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
