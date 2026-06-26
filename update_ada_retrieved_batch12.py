import pandas as pd

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

updates = {
    'Cadonilimab': {
        'ada_value': 'ADA incidence not stated in retrieved cadonilimab clinical/safety sources',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '10 mg/kg',
        'dose_freq': 'Every 3 weeks in COMPASSION-16; 6 mg/kg every 2 weeks also reported in real-world study',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved sources',
        'pk_efficacy_impact': 'COMPASSION-16 reports improved PFS/OS and manageable safety; retrieved sources do not report ADA incidence or impact',
        'evidence_source': 'Lancet COMPASSION-16 PubMed record; Cancer Medicine systematic safety review; Frontiers real-world cervical cancer study',
        'citation_urls': 'https://pubmed.ncbi.nlm.nih.gov/39426385/; https://www.ovid.com/journals/camed/pdf/10.1002/cam4.71210~the-safety-of-cadonilimab-a-systematic-review-and-singlearm; https://www.frontiersin.org/articles/10.3389/fimmu.2025.1611696',
        'ada_source_url_primary': 'https://pubmed.ncbi.nlm.nih.gov/39426385/',
        'ada_source_pmids': '39426385',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'COMPASSION-16 abstract and retrieved safety/real-world full texts reviewed; efficacy and AE data reported, but no anti-drug antibody incidence stated.',
        'verify_note': 'Prior MSD 3.8% value was not supported by retrieved clinical, safety review, or sponsor/source search text.'
    },
    'Demcizumab': {
        'ada_value': '6/55 confirmed ADA positive (11%)',
        'ada_value_display': '11.0%',
        'ada_first_pct': 11.0,
        'nab_pct': 'Not reported',
        'dose_mg': '0.5, 1, 2.5, 5, or 10 mg/kg',
        'dose_freq': 'Weekly or every other week depending on cohort',
        'route_curated': 'Intravenous',
        'assay_platform': 'Anti-demcizumab antibody assay; confirmatory immunodepletion assay',
        'pk_efficacy_impact': 'ADA formation was generally late emerging and did not appear to impact drug exposure, safety, or biologic activity',
        'evidence_source': 'Clinical Cancer Research phase I demcizumab solid tumor article',
        'citation_urls': 'https://aacrjournals.org/clincancerres/article/20/24/6295/118145/A-Phase-I-Dose-Escalation-and-Expansion-Study-of; https://doi.org/10.1158/1078-0432.CCR-14-1373',
        'ada_source_url_primary': 'https://aacrjournals.org/clincancerres/article/20/24/6295/118145/A-Phase-I-Dose-Escalation-and-Expansion-Study-of',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Immunogenicity: six of 55 (11%) patients were confirmed positive for ADAs; formation generally late; no apparent impact on exposure, safety, or biologic activity.',
        'verify_note': 'Corrected prior unsupported MSD 40.0% value to article-confirmed 11%.'
    },
    'Depatuxizumab': {
        'ada_value': 'ADA incidence not stated in retrieved INTELLANCE-1 phase 3 source',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': 'Not stated in retrieved PubMed abstract',
        'dose_freq': 'With radiotherapy and temozolomide in phase 3 trial',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved PubMed abstract',
        'pk_efficacy_impact': 'INTELLANCE-1 interim analysis showed no OS benefit; no new important safety risks; ADA incidence not reported in retrieved abstract',
        'evidence_source': 'PubMed INTELLANCE-1 phase III depatuxizumab mafodotin glioblastoma trial; Synapse drug page',
        'citation_urls': 'https://pubmed.ncbi.nlm.nih.gov/35849035/; https://synapse.patsnap.com/drug/f424d333eeb9407d97755d12e1e2fc5b',
        'ada_source_url_primary': 'https://pubmed.ncbi.nlm.nih.gov/35849035/',
        'ada_source_pmids': '35849035',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'PubMed abstract reports OS/PFS and corneal epitheliopathy safety outcomes; no immunogenicity/ADA incidence stated.',
        'verify_note': 'Prior 1.0% value was not supported by retrieved INTELLANCE-1 source.'
    },
    'Efungumab': {
        'ada_value': '11% HADA in invasive candidiasis patients; 55% in healthy volunteers',
        'ada_value_display': '11.0%',
        'ada_first_pct': 11.0,
        'nab_pct': 'Not reported',
        'dose_mg': '1 mg/kg',
        'dose_freq': 'Twice daily for 5 days',
        'route_curated': 'Intravenous',
        'assay_platform': 'Human anti-drug antibody (HADA) assessment',
        'pk_efficacy_impact': 'EMA report states no link between HADA response and adverse events; refusal was driven by quality/safety concerns including immunogenicity risk from host-cell proteins and aggregates',
        'evidence_source': 'EMA Mycograb EPAR refusal public assessment report',
        'citation_urls': 'https://www.ema.europa.eu/en/documents/assessment-report/mycograb-epar-refusal-public-assessment-report_en.pdf',
        'ada_source_url_primary': 'https://www.ema.europa.eu/en/documents/assessment-report/mycograb-epar-refusal-public-assessment-report_en.pdf',
        'ada_source_type_curated': 'regulatory_review',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Safety data: HADA levels in healthy volunteers were similar to invasive candidiasis patients but occurred more frequently (55% versus 11%); no link between HADA response and adverse events.',
        'verify_note': 'Corrected prior unsupported 5.0% value to EMA-confirmed patient HADA frequency of 11%.'
    },
    'Eldelumab': {
        'ada_value': '0% anti-eldelumab antibodies; no immunogenicity observed',
        'ada_value_display': '0.0%',
        'ada_first_pct': 0.0,
        'nab_pct': 'Not reported',
        'dose_mg': '15 or 25 mg/kg',
        'dose_freq': 'Days 1 and 8, then every other week during induction',
        'route_curated': 'Intravenous',
        'assay_platform': 'Validated electrochemiluminescent bridging immunoassay (Meso Scale Discovery)',
        'pk_efficacy_impact': 'No instances of immunogenicity observed; none of the patients with acute infusion reactions had anti-eldelumab antibodies',
        'evidence_source': 'Journal of Crohn’s and Colitis phase 2b eldelumab UC article; PMC full text',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC4946756/; https://academic.oup.com/ecco-jcc/article/10/4/418/2571191',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC4946756/',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Results/immunogenicity: eldelumab treatment was well tolerated and no immunogenicity was observed; no instances by anti-eldelumab antibody assay.',
        'verify_note': 'Corrected prior unsupported MSD 14.0% value to article-confirmed no immunogenicity.'
    },
    'Enristomig': {
        'ada_value': 'ADA incidence not stated in retrieved INBRX-105/enristomig phase 1 sources',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '0.001-3 mg/kg monotherapy; 0.03-1.0 mg/kg with pembrolizumab',
        'dose_freq': 'Every 2, 3, or 4 weeks depending on study part',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved PubMed abstract',
        'pk_efficacy_impact': 'Clinical development ended because of hepatotoxicity and limited efficacy; no ADA incidence reported in retrieved sources',
        'evidence_source': 'PubMed phase 1 INBRX-105 solid tumor study; CISMeF/NCI enristomig entry',
        'citation_urls': 'https://pubmed.ncbi.nlm.nih.gov/41724817/; https://pubmed.ncbi.nlm.nih.gov/41592317/; https://www.cismef.org/page/detail/en/NCI_CO_C159978',
        'ada_source_url_primary': 'https://pubmed.ncbi.nlm.nih.gov/41724817/',
        'ada_source_pmids': '41724817; 41592317',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'PubMed abstract reports phase 1 safety, dosing, response, and hepatotoxicity; no immunogenicity or ADA incidence stated.',
        'verify_note': 'Prior MSD/ECL 4.5% value was not supported by retrieved enristomig/INBRX-105 source text.'
    },
    'Erfonrilimab': {
        'ada_value': 'ADA incidence not stated in retrieved KN046/erfonrilimab clinical sources',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '1, 3, or 5 mg/kg; 300 mg fixed dose',
        'dose_freq': 'Every 2 or 3 weeks depending on cohort',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved phase 1 publication',
        'pk_efficacy_impact': 'KN046 phase I publication lists immunogenicity as an endpoint but retrieved text did not report ADA incidence; phase 2 NSCLC article likewise did not report ADA incidence',
        'evidence_source': 'JITC/PMC phase I KN046 advanced solid tumor article; Nature Communications phase II KN046 plus chemotherapy NSCLC article; Alphamab KN046 page',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10254625/; https://pubmed.ncbi.nlm.nih.gov/37263673/; https://pmc.ncbi.nlm.nih.gov/articles/PMC10983105/; https://www.alphamabonc.com/en/pipeline/kn046.html',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10254625/',
        'ada_source_pmids': '37263673',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Phase I methods/results reviewed: immunogenicity included as an endpoint, but anti-drug antibody incidence not reported in retrieved publication.',
        'verify_note': 'Prior 66.7% value was not supported by retrieved KN046/erfonrilimab clinical sources.'
    },
    'Felzartamab': {
        'ada_value': '0% anti-MOR202 antibodies detected',
        'ada_value_display': '0.0%',
        'ada_first_pct': 0.0,
        'nab_pct': 'Not reported',
        'dose_mg': '0.01 to 16 mg/kg',
        'dose_freq': 'Weekly or twice-weekly/combination regimens in phase 1-2a multiple myeloma trial',
        'route_curated': 'Intravenous',
        'assay_platform': 'Anti-MOR202 antibody assessment',
        'pk_efficacy_impact': 'No anti-MOR202 antibodies were detected; MOR202 IV infusions were safely administered within 30 minutes',
        'evidence_source': 'Lancet Haematology/PubMed first-in-human MOR202 phase 1-2a multiple myeloma trial',
        'citation_urls': 'https://pubmed.ncbi.nlm.nih.gov/32171061/; https://www.thelancet.com/journals/lanhae/article/PIIS2352-3026(19)30249-2/abstract',
        'ada_source_url_primary': 'https://pubmed.ncbi.nlm.nih.gov/32171061/',
        'ada_source_pmids': '32171061',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Findings: no anti-MOR202 antibodies were detected in patients.',
        'verify_note': 'Prior 0.0% value was reverse-verified against PubMed/Lancet abstract text.'
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
