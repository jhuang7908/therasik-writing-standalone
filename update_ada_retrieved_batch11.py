import pandas as pd

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

updates = {
    'Abelacimab': {
        'ada_value': 'ADA incidence not stated in retrieved phase 2/phase 3 sources; ADA assay validation publication identified',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '30, 75, or 150 mg single IV dose in knee arthroplasty phase 2; monthly SC/IV evaluated in later trials',
        'dose_freq': 'Single IV dose in ANT-005 TKA; monthly in later programs',
        'route_curated': 'Intravenous; Subcutaneous',
        'assay_platform': 'Specific ADA assay for abelacimab reported; designed to avoid Factor XI interference',
        'pk_efficacy_impact': 'NEJM phase 2 trial reports efficacy/safety outcomes and hypersensitivity monitoring but no ADA incidence; EU registry lists immunogenicity as a phase 3 safety endpoint',
        'evidence_source': 'NEJM ANT-005 TKA phase 2 trial; EU Clinical Trials Register ASTER protocol; ADA assay validation article page',
        'citation_urls': 'https://www.nejm.org/doi/full/10.1056/NEJMoa2105872; https://www.clinicaltrialsregister.eu/ctr-search/trial/2021-003076-14/LV; https://discovery.researcher.life/article/development-and-validation-of-a-specific-and-sensitive-anti-drug-antibody-assay-for-abelacimab-that-avoids-false-positive-results-due-to-factor-xi-interference/473b9f1b9a8535e18f998c123a235912',
        'ada_source_url_primary': 'https://www.nejm.org/doi/full/10.1056/NEJMoa2105872',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'NEJM methods: monitoring included hypersensitivity and infusion-related reactions; no ADA incidence reported. EU registry: immunogenicity listed as safety/tolerability endpoint.',
        'verify_note': 'Prior 0.0% display was not supported by retrieved phase 2 publication; numeric field set to missing.'
    },
    'Abrezekimab': {
        'ada_value': 'ADA incidence not stated in retrieved IUPHAR/Thera-SAbDab/NCATS pages',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': 'Not stated in retrieved public pages',
        'dose_freq': 'Not stated in retrieved public pages',
        'route_curated': 'Inhalation dry-powder formulation reported by IUPHAR',
        'assay_platform': 'Not stated in retrieved public pages',
        'pk_efficacy_impact': 'IUPHAR states phase 1 completed and positive ATS abstract reported, but no ADA incidence or immunogenicity result was available on retrieved pages',
        'evidence_source': 'IUPHAR/BPS Guide to Pharmacology; Thera-SAbDab; NCATS Inxight Drugs',
        'citation_urls': 'https://www.guidetopharmacology.org/GRAC/LigandDisplayForward?ligandId=9806&tab=clinical; https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/therasabdab/therasummary/?INN=abrezekimab; https://drugs.ncats.io/drug/7V0TA49ZVC',
        'ada_source_url_primary': 'https://www.guidetopharmacology.org/GRAC/LigandDisplayForward?ligandId=9806&tab=clinical',
        'ada_source_type_curated': 'drug_database',
        'ada_has_text_evidence': True,
        'ada_source_section': 'IUPHAR clinical summary: phase 1 completed; results reported as ATS abstract, not formally peer-reviewed; retrieved pages do not state ADA incidence.',
        'verify_note': 'Prior Low (<4%) value was not supported by retrieved source text.'
    },
    'Actoxumab': {
        'ada_value': 'ADA incidence not stated for actoxumab in retrieved MODIFY/FDA sources',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '10 mg/kg',
        'dose_freq': 'Single IV infusion',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated for actoxumab in retrieved sources',
        'pk_efficacy_impact': 'MODIFY I actoxumab-alone enrollment stopped after interim analysis due to safety concerns and lower efficacy versus combination; no actoxumab ADA incidence reported',
        'evidence_source': 'FDA briefing document for bezlotoxumab BLA; NEJM MODIFY I/II phase 3 article',
        'citation_urls': 'https://www.fda.gov/media/98708/download; https://www.nejm.org/doi/full/10.1056/NEJMoa1602615',
        'ada_source_url_primary': 'https://www.fda.gov/media/98708/download',
        'ada_source_type_curated': 'regulatory_review',
        'ada_has_text_evidence': True,
        'ada_source_section': 'FDA briefing/NEJM MODIFY text describes actoxumab arms and discontinuation; immunogenicity text retrieved refers to no treatment-emergent ADA against bezlotoxumab, not actoxumab.',
        'verify_note': 'Prior 0.0% value was not supported for actoxumab specifically; numeric field set to missing.'
    },
    'Adecatumumab': {
        'ada_value': '0% HAHA/immune responses detected',
        'ada_value_display': '0.0%',
        'ada_first_pct': 0.0,
        'nab_pct': 'Not reported',
        'dose_mg': '10 to 262 mg/m2 in phase 1; 2 or 6 mg/kg q2w in phase 2 breast cancer study',
        'dose_freq': 'Two infusions 14 days apart in phase 1; every 2 weeks in phase 2',
        'route_curated': 'Intravenous',
        'assay_platform': 'HAHA / human antibodies against adecatumumab assessment',
        'pk_efficacy_impact': 'Phase 1 reported immune responses were not detected; phase 2 reported HAHA not detected in a single patient',
        'evidence_source': 'PubMed phase 1 adecatumumab prostate cancer abstract; Annals of Oncology phase 2 metastatic breast cancer article',
        'citation_urls': 'https://pubmed.ncbi.nlm.nih.gov/16930989/; https://www.annalsofoncology.org/article/S0923-7534(19)38761-7/fulltext',
        'ada_source_url_primary': 'https://www.annalsofoncology.org/article/S0923-7534(19)38761-7/fulltext',
        'ada_source_pmids': '16930989',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Phase 1: immune responses to the antibody were not detected. Phase 2: human antibodies against adecatumumab were not detected in a single patient.',
        'verify_note': 'Explicit qualitative zero immunogenicity evidence supports 0.0% display; no NAb rate reported.'
    },
    'Afimkibart': {
        'ada_value': '82% ADA; 10% NAb in phase 2a PF-06480605 TUSCANY study',
        'ada_value_display': '82.0%',
        'ada_first_pct': 82.0,
        'nab_pct': '10.0%',
        'dose_mg': '500 mg PF-06480605',
        'dose_freq': 'Every 2 weeks for 7 IV doses',
        'route_curated': 'Intravenous',
        'assay_platform': 'ADA assay with acid pre-treatment; drug-tolerant cell-based NAb assay',
        'pk_efficacy_impact': 'Phase 2a article reports sustained target engagement and acceptable safety profile; phase 1 abstract states ADA/NAb did not impact safety, PK, or pharmacodynamics at higher doses',
        'evidence_source': 'Clinical Gastroenterology and Hepatology phase 2a TUSCANY article; EU Clinical Trials Register results; PubMed phase 1 PF-06480605 abstract',
        'citation_urls': 'https://www.cghjournal.org/article/S1542-3565(21)00614-5/fulltext; https://www.clinicaltrialsregister.eu/ctr-search/trial/2016-001158-16/results; https://pubmed.ncbi.nlm.nih.gov/31758576/',
        'ada_source_url_primary': 'https://www.cghjournal.org/article/S1542-3565(21)00614-5/fulltext',
        'ada_source_pmids': '31758576',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Results: forty-one participants (82%) tested positive for anti-drug antibodies and 5 (10%) for neutralizing antibodies; EudraCT endpoint values confirm ADA 82.0 and NAb 10.0.',
        'verify_note': 'Prior 82%/10% values were reverse-verified against article and trial registry text.'
    },
    'Bavituximab': {
        'ada_value': 'ADA incidence not stated in retrieved SUNRISE phase 3 or HCC phase 2 articles',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '3 mg/kg',
        'dose_freq': 'Weekly IV in SUNRISE; schedule not stated in HCC abstract page',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated for ADA in retrieved articles',
        'pk_efficacy_impact': 'SUNRISE showed no OS/PFS superiority with docetaxel; retrieved articles did not report ADA incidence or ADA impact',
        'evidence_source': 'Annals of Oncology SUNRISE phase 3 article; Nature Communications bavituximab plus pembrolizumab HCC phase 2 article',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC6887726/; https://www.nature.com/articles/s41467-024-46542-y',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC6887726/',
        'ada_source_pmids': '31429027',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'SUNRISE and HCC phase 2 retrieved full texts reviewed; no anti-drug antibody incidence reported.',
        'verify_note': 'Prior ELISA 2.5% value was not supported by retrieved full-text sources.'
    },
    'Bermekimab': {
        'ada_value': 'ADA incidence not stated in retrieved phase 2 HS article; protocol includes ADA sample collection',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '400 mg SC weekly in open-label HS article; protocol evaluated 800 mg loading then 400 mg SC weekly or every other week',
        'dose_freq': 'Weekly, or every other week in protocol arm',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'Protocol lists PK/ADA/PD/biomarker collection; assay and results not stated in retrieved article',
        'pk_efficacy_impact': 'Published phase 2 article reports HS clinical response and injection-site reactions but no ADA incidence or ADA impact',
        'evidence_source': 'PubMed phase II HS article; ClinicalTrials.gov protocol PDF NCT04019041',
        'citation_urls': 'https://pubmed.ncbi.nlm.nih.gov/32004568/; https://cdn.clinicaltrials.gov/large-docs/41/NCT04019041/Prot_000.pdf',
        'ada_source_url_primary': 'https://pubmed.ncbi.nlm.nih.gov/32004568/',
        'ada_source_pmids': '32004568',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'PubMed abstract: safety/efficacy and injection site reactions reported; protocol section 6.1 lists PK/ADA/PD sample collection; no ADA result found.',
        'verify_note': 'Prior 0.0% value was not supported by retrieved article/protocol text.'
    },
    'Brontictuzumab': {
        'ada_value': 'ADA incidence not stated in retrieved phase 1 abstract',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '1.5 mg/kg MTD',
        'dose_freq': 'Every 3 weeks during expansion',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved PubMed abstract',
        'pk_efficacy_impact': 'Phase 1 abstract lists immunogenicity as a study objective and reports nonlinear PK; no ADA incidence stated',
        'evidence_source': 'PubMed phase I brontictuzumab solid tumor study abstract',
        'citation_urls': 'https://pubmed.ncbi.nlm.nih.gov/29726923/',
        'ada_source_url_primary': 'https://pubmed.ncbi.nlm.nih.gov/29726923/',
        'ada_source_pmids': '29726923',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Abstract purpose included safety, PK, immunogenicity and efficacy; results reported PK and efficacy signal but no ADA incidence.',
        'verify_note': 'Prior MSD 28.0% value was not supported by retrieved abstract/search results.'
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
