import pandas as pd

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

updates = {
    'Namilumab': {
        'ada_value': '0% anti-namilumab antibodies detected in phase 1b rheumatoid arthritis study',
        'ada_value_display': '0.0%',
        'ada_first_pct': 0.0,
        'nab_pct': 'Not applicable; no anti-namilumab antibodies detected',
        'dose_mg': '150 or 300 mg in phase 1b; 20, 80, or 150 mg in phase 2',
        'dose_freq': 'Subcutaneous injections on days 1, 15, and 29 in phase 1b; baseline and weeks 2, 6, and 10 in phase 2',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'Bridging electrochemiluminescence assay for anti-namilumab antibodies',
        'pk_efficacy_impact': 'Anti-namilumab antibodies were not detected; phase 1b PK was linear and typical of subcutaneous IgG1 monoclonal antibody administration',
        'evidence_source': 'Arthritis Research & Therapy phase 1b PRIORA namilumab article; Arthritis Research & Therapy phase 2 NEXUS article',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC5343373/; https://arthritis-research.biomedcentral.com/articles/10.1186/s13075-017-1267-3; https://pmc.ncbi.nlm.nih.gov/articles/PMC6471864/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC5343373/',
        'ada_source_pmids': '28274253; 30999929',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Phase 1b abstract/PK section: no anti-namilumab antibodies were detected; methods: anti-namilumab antibodies quantified using a bridging electrochemiluminescence assay.',
        'verify_note': 'Corrected prior MSD 12.0% value to source-confirmed 0% in the retrieved phase 1b trial.'
    },
    'Odronextamab': {
        'ada_value': '1.5% anti-odronextamab antibodies detected during treatment in Studies 1625 and 1333 (6/400); no neutralizing antibodies observed',
        'ada_value_display': '1.5%',
        'ada_first_pct': 1.5,
        'nab_pct': '0% neutralizing antibodies observed',
        'dose_mg': 'Step-up dosing then 80 mg weekly for FL or 160 mg weekly for DLBCL through cycle 4, followed by maintenance',
        'dose_freq': 'Intravenous infusion with step-up dosing in cycle 1, weekly dosing in cycles 2-4, then every 2 or 4 weeks depending on response',
        'route_curated': 'Intravenous',
        'assay_platform': 'Anti-odronextamab antibody assessment; assay platform not stated in retrieved product information',
        'pk_efficacy_impact': 'No evidence of ADA impact on pharmacokinetics or safety was observed, although data were described as limited',
        'evidence_source': 'EMA Ordspono product information section 5.1 immunogenicity; EMA EPAR overview; PubMed ELM-1 phase 1 trial',
        'citation_urls': 'https://www.ema.europa.eu/en/documents/product-information/ordspono-epar-product-information_en.pdf; https://www.ema.europa.eu/en/medicines/human/EPAR/ordspono; https://pubmed.ncbi.nlm.nih.gov/35366963/',
        'ada_source_url_primary': 'https://www.ema.europa.eu/en/documents/product-information/ordspono-epar-product-information_en.pdf',
        'ada_source_pmids': '35366963',
        'ada_source_type_curated': 'label',
        'ada_has_text_evidence': True,
        'ada_source_section': 'EMA product information section 5.1 Immunogenicity: anti-odronextamab antibodies were detected in 1.5% (6/400) of patients; no neutralizing antibodies were observed; no evidence of ADA impact on PK or safety was observed.',
        'verify_note': 'Prior 1.5% value reverse-verified against EMA product information.'
    },
    'Ozekibart': {
        'ada_value': 'Clinical ADA incidence not stated in retrieved ozekibart/INBRX-109 sources; trial registry lists ADA frequency as a secondary outcome',
        'ada_value_display': 'ADA assessed/planned; numeric not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '3 mg/kg every 3 weeks in chondrosarcoma phase 1 report',
        'dose_freq': 'Every 3 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'Frequency of anti-drug antibodies against INBRX-109 planned/determined in trial registry; assay platform not stated',
        'pk_efficacy_impact': 'Retrieved sources report favorable safety and antitumor activity; they do not report treatment-emergent ADA incidence',
        'evidence_source': 'ClinicalTrials.gov NCT03715933 INBRX-109 phase 1 trial record; PubMed phase 1 chondrosarcoma report; Inhibrx ozekibart mechanism page',
        'citation_urls': 'https://clinicaltrials.gov/study/NCT03715933; https://pubmed.ncbi.nlm.nih.gov/37265425/; https://inhibrx.com/ozekibart-inbrx-109/',
        'ada_source_url_primary': 'https://clinicaltrials.gov/study/NCT03715933',
        'ada_source_pmids': '37265425',
        'ada_source_type_curated': 'clinical_trial_registry',
        'ada_has_text_evidence': True,
        'ada_source_section': 'ClinicalTrials.gov secondary outcome: frequency of anti-drug antibodies against INBRX-109 will be determined; retrieved phase 1 article describes pre-existing anti-sdAb antibody assessment/design but no clinical ADA incidence result.',
        'verify_note': 'Prior 0% value was not supported as treatment-emergent clinical ADA incidence in retrieved ozekibart sources.'
    },
    'Pasotuxizumab': {
        'ada_value': '100% treatment-emergent ADA in subcutaneous AMG 212 arm among subjects completing at least 1 cycle (30/30); 0% ADA in continuous intravenous arm',
        'ada_value_display': '100.0% SC; 0.0% CIV',
        'ada_first_pct': 100.0,
        'nab_pct': 'Neutralizing ADAs reported in SC arm',
        'dose_mg': 'Daily SC dose escalation from 0.5 micrograms/day; CIV starting dose 5 micrograms/day',
        'dose_freq': 'Daily subcutaneous dosing or continuous intravenous infusion in 21-day cycles',
        'route_curated': 'Subcutaneous; Continuous intravenous infusion',
        'assay_platform': 'Validated electrochemiluminescence-based antibody assay for binding ADA; neutralizing ADA characterization reported',
        'pk_efficacy_impact': 'Neutralizing ADAs caused profound exposure loss and were associated with reversal of initial PSA responses, limiting response durability',
        'evidence_source': 'Frontiers in Immunology/PMC pasotuxizumab immunogenicity root-cause analysis; PubMed abstract',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10628759/; https://pubmed.ncbi.nlm.nih.gov/37942314/; https://www.frontiersin.org/journals/immunology/articles/10.3389/fimmu.2023.1261070/full',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10628759/',
        'ada_source_pmids': '37942314',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Abstract/results and Figure 1 caption: TE-ADA developed in all subjects treated with at least 1 cycle in the SC arm; 30/31 enrolled completed at least 1 cycle and all 30 developed binding ADA; no subjects developed ADA in the CIV arm.',
        'verify_note': 'Corrected prior MSD 25.0% value to route-specific 100% SC and 0% CIV evidence.'
    },
    'Porustobart': {
        'ada_value': 'ADA incidence not stated in retrieved porustobart/HBM4003 clinical result sources; trial registries list immunogenicity/ADA/NAb as outcomes',
        'ada_value_display': 'ADA assessed/planned; numeric not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'NAb incidence planned for ADA-positive patients; numeric not stated',
        'dose_mg': '0.3 mg/kg with toripalimab 240 mg every 3 weeks in melanoma phase 1; 0.45 mg/kg with toripalimab 240 mg every 21 days in HCC phase 1',
        'dose_freq': 'Every 21 days',
        'route_curated': 'Intravenous',
        'assay_platform': 'ADA-positive and neutralizing antibody incidence planned in trial registries; assay platform not stated',
        'pk_efficacy_impact': 'Retrieved publications report PK/immunogenicity as evaluated or planned but do not state ADA incidence or impact',
        'evidence_source': 'PubMed melanoma and HCC porustobart/HBM4003 phase 1 studies; ClinicalTrials.gov NCT04727164 and NCT05149027; CISMeF/NCI drug page',
        'citation_urls': 'https://pubmed.ncbi.nlm.nih.gov/39366752/; https://pubmed.ncbi.nlm.nih.gov/40378055/; https://clinicaltrials.gov/study/NCT04727164; https://clinicaltrials.gov/study/NCT05149027; https://www.cismef.org/page/detail/en/NCI_CO_C173540',
        'ada_source_url_primary': 'https://clinicaltrials.gov/study/NCT04727164',
        'ada_source_pmids': '39366752; 40378055',
        'ada_source_type_curated': 'clinical_trial_registry',
        'ada_has_text_evidence': True,
        'ada_source_section': 'ClinicalTrials.gov outcomes: immunogenicity of HBM4003 and toripalimab including incidence of ADA-positive and NAb-positive patients; retrieved abstracts do not state numeric ADA incidence.',
        'verify_note': 'Prior 5.0% value was not supported by retrieved porustobart source text.'
    },
    'Produvofusp': {
        'ada_value': 'ADA incidence not stated in retrieved produvofusp public drug/product sources',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': 'Not stated in retrieved public drug/product sources',
        'dose_freq': 'Not stated in retrieved public drug/product sources',
        'route_curated': 'Not stated in retrieved public drug/product sources',
        'assay_platform': 'Not stated in retrieved public drug/product sources',
        'pk_efficacy_impact': 'Retrieved sources describe produvofusp as an investigational human fusion protein targeting complement factors; no clinical ADA incidence or impact reported',
        'evidence_source': 'NCATS/Inxight Drugs produvofusp page; TargetMol product page; Synapse search result',
        'citation_urls': 'https://drugs.ncats.io/substance/R2Z6HC43VT; https://www.targetmol.com/compound/produvofusp; https://synapse.patsnap.com/drug/95ace4d1da0d49349e6c34f2f7243323',
        'ada_source_url_primary': 'https://drugs.ncats.io/substance/R2Z6HC43VT',
        'ada_source_type_curated': 'drug_database',
        'ada_has_text_evidence': True,
        'ada_source_section': 'NCATS page identifies produvofusp as an investigational human fusion protein; TargetMol describes complement factor targeting/research use; neither source reports ADA incidence.',
        'verify_note': 'Prior 0% value was not supported by retrieved produvofusp source text.'
    },
    'Quilizumab': {
        'ada_value': '1.6% treatment-emergent anti-therapeutic antibody incidence across quilizumab dose groups (7/427)',
        'ada_value_display': '1.6%',
        'ada_first_pct': 1.6,
        'nab_pct': 'Not stated',
        'dose_mg': '150 mg quarterly, 450 mg quarterly, or 300 mg monthly',
        'dose_freq': 'Subcutaneous dosing for 36 weeks with 48-week safety follow-up',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'Validated bridging ELISA for serum anti-therapeutic antibodies',
        'pk_efficacy_impact': 'No apparent impact of positive ATA results on pharmacokinetic profiles or safety',
        'evidence_source': 'Respiratory Research/PMC phase 2 allergic asthma quilizumab trial; IUPHAR/BPS clinical trial page; ClinicalTrials.gov CSU quilizumab trial',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC4797126/; https://respiratory-research.biomedcentral.com/articles/10.1186/s12931-016-0347-2; https://www.guidetopharmacology.org/GRAC/LigandDisplayForward?ligandId=8998&tab=clinical; https://clinicaltrials.gov/study/NCT01987947',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC4797126/',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Safety/pharmacokinetics section: treatment-emergent ATA rate was 1.4% in 150 mg Q and 300 mg M groups, 2.1% in 450 mg Q group, and 1.6% overall (7/427 quilizumab-dosed patients); no apparent PK/safety impact.',
        'verify_note': 'Corrected prior ECL 18.0% value to source-confirmed 1.6% ATA incidence.'
    },
    'Rimteravimab': {
        'ada_value': 'ADA incidence not stated in retrieved rimteravimab/XVR011 public trial and drug sources',
        'ada_value_display': 'ADA assessed/planned; numeric not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': 'Not stated in retrieved public result summary',
        'dose_freq': 'Single ascending dose phase 1 followed by planned phase 2 in hospitalized COVID-19 trial',
        'route_curated': 'Intravenous',
        'assay_platform': 'Immunogenicity of XVR011 was an exploratory/secondary assessment; assay platform not stated in retrieved public result summary',
        'pk_efficacy_impact': 'EudraCT result page describes trial design and results publication but does not state ADA incidence; drug pages identify rimteravimab/XVR011 without ADA data',
        'evidence_source': 'EU Clinical Trials Register EudraCT 2020-005299-36 XVR011 result page; NCATS/Inxight Drugs rimteravimab page; CISMeF/NCI drug page; Research with human participants search result',
        'citation_urls': 'https://www.clinicaltrialsregister.eu/ctr-search/trial/2020-005299-36/results; https://drugs.ncats.io/substance/Z4LZB5VCU4; https://www.cismef.org/page/detail/en/NCI_CO_C183318; https://onderzoekmetmensen.nl/en/trial/49939',
        'ada_source_url_primary': 'https://www.clinicaltrialsregister.eu/ctr-search/trial/2020-005299-36/results',
        'ada_source_type_curated': 'clinical_trial_registry',
        'ada_has_text_evidence': True,
        'ada_source_section': 'EudraCT result page identifies the XVR011 first-in-human single ascending dose plus phase 2 COVID-19 trial; retrieved public pages do not state ADA incidence. Search result for healthy volunteer phase 1 identifies immunogenicity as assessed after IV single ascending doses.',
        'verify_note': 'Prior MSD/ECL 2.1% value was not supported by retrieved rimteravimab/XVR011 source text.'
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
