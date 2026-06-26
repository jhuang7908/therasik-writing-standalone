import pandas as pd

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

updates = {
    'Gefurulimab': {
        'ada_value': 'ADA incidence not stated in retrieved gefurulimab sources; immunogenicity listed as a study endpoint',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': 'Single subcutaneous dose in device/PK study; dose not stated in retrieved AAN abstract',
        'dose_freq': 'Single dose in phase 1 autoinjector/PFS-SD study',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'Not stated in retrieved sources',
        'pk_efficacy_impact': 'AAN phase 1 abstract lists immunogenicity as a secondary endpoint but reports no results; no ADA impact available',
        'evidence_source': 'AAN 2024 gefurulimab phase 1 PK/safety abstract; clinicaltrials.eu summary linking NCT06677138 and NCT06208488',
        'citation_urls': 'https://index.mirasmart.com/AAN2024/PDFfiles/AAN2024-002532.html; https://clinicaltrials.eu/inn/gefurulimab/',
        'ada_source_url_primary': 'https://index.mirasmart.com/AAN2024/PDFfiles/AAN2024-002532.html',
        'ada_source_type_curated': 'conference_abstract',
        'ada_has_text_evidence': True,
        'ada_source_section': 'AAN abstract: safety, tolerability, immunogenicity, pharmacodynamics, and device performance will be assessed; results N/A.',
        'verify_note': 'Prior MSD/ECL 12.3% value was not supported by retrieved source text.'
    },
    'Gevokizumab': {
        'ada_value': 'Treatment-induced ADA varied by cohort/dose: 0% to 44.44% in Novartis CVPM087A2101 result report',
        'ada_value_display': '16.67% first listed cohort; range 0.0-44.44%',
        'ada_first_pct': 16.67,
        'nab_pct': 'Not stated in retrieved report',
        'dose_mg': '30, 60, or 120 mg',
        'dose_freq': 'Every 4 weeks in oncology trial report; every 4 weeks in Behcet uveitis phase 2 study',
        'route_curated': 'Intravenous; Subcutaneous',
        'assay_platform': 'Anti-gevokizumab-specific ECL immunoassay in Behcet study; ADA analysis set in oncology result report',
        'pk_efficacy_impact': 'Novartis oncology report provides ADA incidence by cohort/dose; no NAb or clinical impact text found in retrieved report',
        'evidence_source': 'Novartis Clinical Trial Results Disclosure CVPM087A2101; Tandfonline Behcet uveitis phase 2 study',
        'citation_urls': 'https://www.novctrd.com/ctrdweb/trialresult/trialresults/pdf?trialResultId=18408; https://www.tandfonline.com/doi/full/10.3109/09273948.2015.1092558; https://pubmed.ncbi.nlm.nih.gov/26829647/',
        'ada_source_url_primary': 'https://www.novctrd.com/ctrdweb/trialresult/trialresults/pdf?trialResultId=18408',
        'ada_source_pmids': '26829647',
        'ada_source_type_curated': 'clinical_trial_result_report',
        'ada_has_text_evidence': True,
        'ada_source_section': 'CVPM087A2101: treatment-induced ADA-positive rates reported by cohort/dose, including 2/12 (16.67%), 3/13 (23.08%), 2/45 (4.44%), 1/8 (12.5%), 4/9 (44.44%), 0/41 (0%), and cohort C/D values 0/22 (0%) and 1/7 (14.29%).',
        'verify_note': 'Replaced generic ELISA/MSD display with cohort-specific clinical trial result report values.'
    },
    'Gontivimab': {
        'ada_value': 'Treatment-emergent ADA positive: 15/45 (33.3%) at 3 mg/kg, 16/44 (36.4%) at 6 mg/kg, 15/46 (32.6%) at 9 mg/kg; placebo 10/39 (25.6%)',
        'ada_value_display': '33.3%',
        'ada_first_pct': 33.3,
        'nab_pct': 'Treatment-emergent NAb positive: 11/45 (24.4%) at 3 mg/kg, 18/44 (40.9%) at 6 mg/kg, 12/46 (26.1%) at 9 mg/kg; placebo 2/39 (5.1%)',
        'dose_mg': '3, 6, or 9 mg/kg',
        'dose_freq': 'Once daily for 3 consecutive days',
        'route_curated': 'Inhalation',
        'assay_platform': 'ADA assay; competitive ligand-binding NAb assay',
        'pk_efficacy_impact': 'Earlier phase I/IIa report states anti-drug antibodies had no effect on PK and no relation with adverse events; RESPIRE result record provides TE ADA and TE NAb counts',
        'evidence_source': 'ClinicalTrials.gov-derived NCT02979431 result page; European Pharmaceutical Review phase I/IIa ALX-0171 top-line report',
        'citation_urls': 'https://cdek.pharmacy.purdue.edu/trial/NCT02979431/; https://europeanpharmaceuticalreview.com/news/40828/alx-0171-infant-rsv-study/; https://cdn.clinicaltrials.gov/large-docs/31/NCT02979431/Prot_000.pdf',
        'ada_source_url_primary': 'https://cdek.pharmacy.purdue.edu/trial/NCT02979431/',
        'ada_source_type_curated': 'clinical_trial_registry_results',
        'ada_has_text_evidence': True,
        'ada_source_section': 'NCT02979431 immunogenicity outcomes: total TE ADA positive counts by ALX-0171 dose; secondary NAb outcome reports post-dose positive NAb counts. Phase I/IIa top-line: ADA had no effect on PK and no relation with AEs.',
        'verify_note': 'Prior 34.0% value was broadly consistent but now sourced and expanded with dose-specific ADA/NAb counts.'
    },
    'Inotuzumab ozogamicin': {
        'ada_value': '7/236 (3%) ADA positive in adult relapsed/refractory ALL; pediatric study 0%',
        'ada_value_display': '3.0%',
        'ada_first_pct': 3.0,
        'nab_pct': '0.0%',
        'dose_mg': '1.8 mg/m2 per cycle in cycle 1; 1.5 or 1.8 mg/m2 per cycle subsequently depending on response',
        'dose_freq': 'Days 1, 8, and 15 of 3- to 4-week cycles',
        'route_curated': 'Intravenous',
        'assay_platform': 'ECL-based ADA immunoassay; cell-based NAb assay',
        'pk_efficacy_impact': 'Positive ADA did not affect clearance; too few ADA-positive patients to assess efficacy/safety impact',
        'evidence_source': 'Pfizer BESPONSA/Inotuzumab ozogamicin labeling',
        'citation_urls': 'https://labeling.pfizer.com/ShowLabeling.aspx?id=12535; https://labeling.pfizer.com/ShowLabeling.aspx?id=14545',
        'ada_source_url_primary': 'https://labeling.pfizer.com/ShowLabeling.aspx?id=12535',
        'ada_source_type_curated': 'regulatory_label',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Immunogenicity: 7/236 (3%) adult patients tested positive for ADA; no patients tested positive for NAb; positive ADA did not affect clearance.',
        'verify_note': 'Prior ELISA 3.0% value reverse-verified against Pfizer label.'
    },
    'Iparomlimab': {
        'ada_value': '12/44 (27.3%) post-baseline ADA positive in QL1604 plus chemotherapy phase II cervical cancer study',
        'ada_value_display': '27.3%',
        'ada_first_pct': 27.3,
        'nab_pct': '0.0%',
        'dose_mg': '200 mg',
        'dose_freq': 'Every 3 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'ADA test; neutralizing antibody assessment',
        'pk_efficacy_impact': 'Phase II cervical cancer study reported no neutralizing antibodies; no ADA impact on PK/efficacy stated',
        'evidence_source': 'Journal of Gynecologic Oncology/PMC QL1604 plus paclitaxel-cisplatin/carboplatin phase II trial; Frontiers phase I QL1604 article',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11543260/; https://ejgo.org/pdf/10.3802/jgo.2024.35.e77; https://pubmed.ncbi.nlm.nih.gov/37936687/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11543260/',
        'ada_source_pmids': '37936687',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Results: 44 patients had ADA tests and 12 (27.3%) tested positive for ADA post-baseline; no patient tested positive for neutralizing antibodies.',
        'verify_note': 'Prior 0.6% value was not supported; updated to explicit peer-reviewed QL1604 ADA result.'
    },
    'Isecarosmab': {
        'ada_value': 'Single-dose study: 4 active M6495-treated participants and 2 placebo participants ADA positive; multiple-dose study: 5 patients overall ADA positive, including 4 treatment-emergent/post-baseline active-dose patients',
        'ada_value_display': '11.1% active SAD; 16.7% treatment-emergent active MAD',
        'ada_first_pct': 11.1,
        'nab_pct': 'Not assessed',
        'dose_mg': '1-300 mg single dose; 75-300 mg multiple dose',
        'dose_freq': 'Single subcutaneous dose; every 2 weeks or weekly in multiple-dose study',
        'route_curated': 'Subcutaneous',
        'assay_platform': 'ADA assays',
        'pk_efficacy_impact': 'ADA did not affect M6495 exposure/PK or ARGS pharmacodynamic modulation; neutralizing antibodies were not assessed',
        'evidence_source': 'ACR Open Rheumatology/PMC M6495 phase 1 studies in healthy subjects and osteoarthritis patients',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11016567/; https://doi.org/10.1002/acr2.11610; https://synapse.patsnap.com/drug/8a19e3bd1926456cba8c1910f56f0fb9',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11016567/',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Single ascending dose and multiple ascending dose ADA results: active and placebo ADA counts, no NAb assessment, no PK/PD effect detected.',
        'verify_note': 'Prior 0.0% value was contradicted by published M6495 phase 1 ADA findings.'
    },
    'Ivonescimab': {
        'ada_value': '8/55 (14.5%) post-baseline ADA positive; 3/55 (5.5%) treatment-emergent ADA positive',
        'ada_value_display': '14.5%',
        'ada_first_pct': 14.5,
        'nab_pct': '5.5% treatment-emergent NAb-positive potential; all 3 treatment-emergent ADA-positive patients developed anti-VEGF neutralizing antibodies and 2 developed anti-PD-1 neutralizing antibodies',
        'dose_mg': '3, 5, 10, 20, or 30 mg/kg Q2W; 10 or 20 mg/kg Q3W',
        'dose_freq': 'Every 2 or 3 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'Electrochemiluminescent immunoassay using Meso Scale Discovery; confirmatory assay and titer evaluation; NAb follow-up',
        'pk_efficacy_impact': 'No correlation between ADA development and dose; impact of neutralizing ADAs on PK to be explored due to small sample size',
        'evidence_source': 'Cancer Medicine/PMC phase I ivonescimab safety, PK, PD, and immunogenicity study',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11925807/; https://pubmed.ncbi.nlm.nih.gov/40114411/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11925807/',
        'ada_source_pmids': '40114411',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Immunogenicity: 8/55 post-baseline ADA-positive; 3/55 treatment-emergent ADA-positive; all 3 treatment-emergent ADA-positive patients had neutralizing potential.',
        'verify_note': 'Corrected prior unsupported MSD 4.5% value to article-confirmed 14.5% post-baseline and 5.5% treatment-emergent ADA.'
    },
    'Lampalizumab': {
        'ada_value': 'ADA/anti-therapeutic antibody incidence not stated in retrieved Chroma/Spectri phase 3 article',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '10 mg intravitreal',
        'dose_freq': 'Every 4 weeks or every 6 weeks',
        'route_curated': 'Intravitreal',
        'assay_platform': 'Anti-therapeutic antibody assessment planned in protocol; assay/results not stated in retrieved article',
        'pk_efficacy_impact': 'Chroma/Spectri showed no reduction in geographic atrophy enlargement; retrieved article did not report ADA incidence or impact',
        'evidence_source': 'JAMA Ophthalmology/PMC Chroma and Spectri phase 3 article; Roche/ClinicalTrials.gov protocol',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC6145777/; https://cdn.clinicaltrials.gov/large-docs/31/NCT02247531/Prot_000.pdf; https://doi.org/10.1001/jamaophthalmol.2018.1544',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC6145777/',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Phase 3 article reports efficacy/safety outcomes; protocol lists evaluation of clinical significance of anti-therapeutic antibodies directed against lampalizumab, but retrieved results do not state incidence.',
        'verify_note': 'Prior 50.0% value was not supported by retrieved JAMA/PMC or protocol text.'
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
