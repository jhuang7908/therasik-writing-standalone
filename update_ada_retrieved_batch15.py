import pandas as pd

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

updates = {
    'Naptumomab': {
        'ada_value': 'Approximately 50% of patients had stable or only moderately increased anti-SAg (anti-SEA/E-120) levels after one cycle; human anti-mouse antibody levels were very low',
        'ada_value_display': '~50% anti-SAg stable/moderate increase; HAMA very low',
        'ada_first_pct': 50.0,
        'nab_pct': 'Not stated',
        'dose_mg': '0.5 to 27.4 micrograms/kg in MONO study; 10.3 to 22 micrograms/kg in COMBO study',
        'dose_freq': 'Daily IV bolus for 4-5 days per cycle depending on study',
        'route_curated': 'Intravenous',
        'assay_platform': 'Anti-SAg titer assessment; human anti-mouse antibody assessment',
        'pk_efficacy_impact': 'Anti-SAg levels were stable or only moderately increased in approximately 50% after one cycle; no significant first-cycle PK effect of anti-SAg antibody levels was reported',
        'evidence_source': 'JCO/PMC phase I naptumomab estafenatox studies; Current Oncology Reports/PMC review',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC2734423/; https://pmc.ncbi.nlm.nih.gov/articles/PMC3918406/; https://doi.org/10.1200/JCO.2008.20.2515',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC3918406/',
        'ada_source_pmids': '24445502; 19636016',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Review of phase I studies: anti-SAg (anti-SEA/E-120) levels were stable or only moderately increased in approximately 50% of patients after one cycle, and human anti-mouse antibody levels were very low.',
        'verify_note': 'The ~50% value refers to anti-superantigen response behavior, not a standard therapeutic-mAb ADA percentage.'
    },
    'Narsoplimab': {
        'ada_value': '11% ADA positivity in HSCT-TMA population in population PK/PD analysis',
        'ada_value_display': '11.0%',
        'ada_first_pct': 11.0,
        'nab_pct': 'Not stated',
        'dose_mg': '2 or 4 mg/kg in analyzed regimens; weight-based dosing recommended',
        'dose_freq': 'Weekly IV dosing in analyzed clinical datasets',
        'route_curated': 'Intravenous',
        'assay_platform': 'Population PK/PD model covariate analysis including ADA status',
        'pk_efficacy_impact': 'ADA positivity was associated with higher maximum elimination velocity but only slightly lower overall exposure',
        'evidence_source': 'OncLive report of EBMT population PK/PD analysis of narsoplimab; PubMed HSCT-TMA narsoplimab study for clinical context',
        'citation_urls': 'https://www.onclive.com/view/weight-based-dosing-with-narsoplimab-is-recommended-in-hsct-tma; https://pubmed.ncbi.nlm.nih.gov/35439028/',
        'ada_source_url_primary': 'https://www.onclive.com/view/weight-based-dosing-with-narsoplimab-is-recommended-in-hsct-tma',
        'ada_source_pmids': '35439028',
        'ada_source_type_curated': 'conference_report',
        'ada_has_text_evidence': True,
        'ada_source_section': 'OncLive/EBMT report: ADA were observed in 11% of patients with HSCT-TMA; ADA-positive patients had higher maximum elimination velocity but only slightly lower overall exposure.',
        'verify_note': 'Corrected prior 0% value to source-confirmed 11%.'
    },
    'Onartuzumab': {
        'ada_value': 'Antitherapeutic antibodies assessed; incidence percentage not stated in retrieved phase I article',
        'ada_value_display': 'ATA assessed; numeric not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '1, 4, 10, 15, 20, or 30 mg/kg',
        'dose_freq': 'Every 3 weeks IV',
        'route_curated': 'Intravenous',
        'assay_platform': 'Validated bridging electrochemiluminescence assay for antitherapeutic antibodies',
        'pk_efficacy_impact': 'Antitherapeutic antibodies did not seem to affect safety or pharmacokinetics of onartuzumab in retrieved phase I report',
        'evidence_source': 'Clinical Cancer Research phase I onartuzumab study; PLOS One clinical program safety review',
        'citation_urls': 'https://aacrjournals.org/clincancerres/article/20/6/1666/210950/Phase-I-Dose-Escalation-Study-of-Onartuzumab-as-a; https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0139679',
        'ada_source_url_primary': 'https://aacrjournals.org/clincancerres/article/20/6/1666/210950/Phase-I-Dose-Escalation-Study-of-Onartuzumab-as-a',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Abstract and methods: serum samples were collected for antitherapeutic antibodies; ATA did not seem to affect safety or PK; no incidence percentage stated in retrieved text.',
        'verify_note': 'Prior 14% value was not supported by retrieved onartuzumab sources.'
    },
    'Oportuzumab': {
        'ada_value': 'All analyzable patients developed anti-ETA antibodies to VB4-845 by end of intratumoral phase I study; anti-scFv antibodies developed in 15/17 by day 28',
        'ada_value_display': '100.0% anti-ETA; 88.2% anti-scFv',
        'ada_first_pct': 100.0,
        'nab_pct': '7 patients had neutralizing antibody effect',
        'dose_mg': '100 to 930 micrograms weekly intratumoral VB4-845',
        'dose_freq': 'Weekly for 4 weeks',
        'route_curated': 'Intratumoral',
        'assay_platform': 'ELISA anti-ETA and anti-scFv antibody titers; cytotoxicity assay for neutralizing effect',
        'pk_efficacy_impact': 'All analyzable patients eventually developed an immune response, but neutralizing antibody effect was demonstrated in seven patients',
        'evidence_source': 'PMC/Dove Medical Press phase I VB4-845 intratumoral head and neck cancer study',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC2761172/; https://pubmed.ncbi.nlm.nih.gov/19920898/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC2761172/',
        'ada_source_pmids': '19920898',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Immunogenicity section: by end of study all patients analyzed had detectable anti-ETA titers; 15/17 had detectable anti-scFv titers by day 28; neutralizing effect demonstrated in seven patients.',
        'verify_note': '100% value confirmed for anti-ETA response in intratumoral VB4-845 study.'
    },
    'Oportuzumab monatox': {
        'ada_value': 'Intravesical VB4-845 study: HAPA 47/61 (77.0%) and HAHA 10/61 (16.4%) at final visit; intratumoral study reported anti-scFv 15/17 (88.2%) by day 28',
        'ada_value_display': '77.0% HAPA; 16.4% HAHA; 88.2% anti-scFv in separate IT study',
        'ada_first_pct': 77.0,
        'nab_pct': 'Not stated for intravesical study; 7 patients had neutralizing antibody effect in separate intratumoral study',
        'dose_mg': '0.1 to 30.16 mg intravesical; phase II 30 mg',
        'dose_freq': 'Weekly intravesical instillation for 6 weeks; phase II induction 6 or 12 weekly instillations plus maintenance',
        'route_curated': 'Intravesical',
        'assay_platform': 'ELISA HAPA and HAHA titers to ETA and scFv portions',
        'pk_efficacy_impact': 'Intravesical study reported no apparent relationship between antibody titer and treatment response; systemic absorption was minimal',
        'evidence_source': 'PMC/Dove Medical Press phase I intravesical VB4-845 study; Journal of Urology phase II oportuzumab monatox abstract; PMC phase I intratumoral VB4-845 study',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC2998804/; https://pubmed.ncbi.nlm.nih.gov/21151619/; https://www.auajournals.org/doi/10.1016/j.juro.2012.07.020; https://pmc.ncbi.nlm.nih.gov/articles/PMC2761172/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC2998804/',
        'ada_source_pmids': '21151619; 19920898',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Intravesical study Table 5: final visit HAPA 47/61 and HAHA 10/61. Text: majority developed antibodies to exotoxin portion; no apparent relationship between antibody titer and response.',
        'verify_note': 'Replaced unqualified ELISA 88% with route-specific values; 88.2% anti-scFv came from a separate intratumoral VB4-845 study.'
    },
    'Otilimab': {
        'ada_value': 'Immunogenicity monitored in retrieved otilimab phase 2b/phase 3 sources; ADA incidence percentage not stated in retrieved text',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '22.5, 45, 90, 135, 150, or 180 mg depending on trial',
        'dose_freq': 'Subcutaneous weekly or weekly then every other week depending on trial',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'Not stated in retrieved article text; immunogenicity monitored',
        'pk_efficacy_impact': 'Retrieved BAROQUE and contRAst reports describe efficacy/safety but do not state ADA incidence percentage',
        'evidence_source': 'Lancet Rheumatology/PubMed phase 2b BAROQUE study; Annals of the Rheumatic Diseases contRAst phase 3 studies',
        'citation_urls': 'https://pubmed.ncbi.nlm.nih.gov/38279364/; https://ard.bmj.com/content/82/12/1516; https://pubmed.ncbi.nlm.nih.gov/37696589/',
        'ada_source_url_primary': 'https://pubmed.ncbi.nlm.nih.gov/38279364/',
        'ada_source_pmids': '38279364; 37699654; 37696589',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Phase 2b article lists immunogenicity monitoring among safety parameters; phase 3 abstracts/full text reviewed did not state ADA incidence.',
        'verify_note': 'Prior 2% value was not supported by retrieved otilimab source text.'
    },
    'Parsatuzumab': {
        'ada_value': 'Antitherapeutic antibodies assessed by bridging ELISA; incidence percentage not stated in retrieved phase II trial text',
        'ada_value_display': 'ATA assessed; numeric not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '400 mg flat dose',
        'dose_freq': 'Every 2 weeks with mFOLFOX6 and bevacizumab',
        'route_curated': 'Intravenous',
        'assay_platform': 'Bridging ELISA for antitherapeutic antibodies, confirmed by competition inhibition',
        'pk_efficacy_impact': 'Trial reported no efficacy benefit and similar adverse event profiles; retrieved text does not provide ATA incidence',
        'evidence_source': 'The Oncologist phase II parsatuzumab metastatic colorectal cancer trial',
        'citation_urls': 'https://repositoriosaludmadrid.es/bitstreams/d553675b-e782-40ee-8540-2bdb22b3859b/download; https://escholarship.org/uc/item/6597s3st; https://www.cismef.org/page/detail/en/NCI_CO_C90567',
        'ada_source_url_primary': 'https://repositoriosaludmadrid.es/bitstreams/d553675b-e782-40ee-8540-2bdb22b3859b/download',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Assessments section: immunogenicity assessed using bridging ELISA to detect antitherapeutic antibodies against parsatuzumab; no numeric incidence result stated in retrieved text.',
        'verify_note': 'Prior 2% value was not supported by retrieved parsatuzumab source text.'
    },
    'Patritumab': {
        'ada_value': '0% anti-patritumab antibody formation in Japanese phase 1 dose-finding study (all tested patients negative)',
        'ada_value_display': '0.0%',
        'ada_first_pct': 0.0,
        'nab_pct': 'Not stated',
        'dose_mg': '9 or 18 mg/kg',
        'dose_freq': 'Every 3 weeks IV',
        'route_curated': 'Intravenous',
        'assay_platform': 'Electrochemiluminescence immunoassay for anti-patritumab antibody',
        'pk_efficacy_impact': 'All patients tested negative for anti-patritumab antibodies; PK profile was similar to preceding US phase 1 study',
        'evidence_source': 'PMC/Springer phase 1 dose-finding patritumab study in Japanese patients with advanced solid tumors',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC3931937/; https://doi.org/10.1007/s00280-014-2375-2',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC3931937/',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Abstract/results: all patients tested had negative for anti-patritumab antibody formation; methods: anti-patritumab antibody measured by electrochemiluminescence immunoassay.',
        'verify_note': 'Corrected prior 1.5% value to 0% in retrieved phase 1 source.'
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
