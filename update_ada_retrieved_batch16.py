import pandas as pd

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

updates = {
    'Pexelizumab': {
        'ada_value': 'ADA incidence not stated in retrieved pexelizumab clinical/meta-analysis sources',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '2 mg/kg bolus plus 0.05 mg/kg/hour infusion for 20-24 hours in ischemic heart disease trials',
        'dose_freq': 'Single peri-procedural IV bolus plus infusion in CABG/STEMI studies',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved sources',
        'pk_efficacy_impact': 'Meta-analysis of 15,196 patients focused on mortality and cardiovascular outcomes; retrieved sources do not report ADA incidence',
        'evidence_source': 'Journal of Thoracic and Cardiovascular Surgery pexelizumab meta-analysis; Annals of Thoracic Surgery cardiac surgery analysis; Creative Biolabs drug overview',
        'citation_urls': 'https://www.jtcvs.org/article/S0022-5223(08)00714-9/fulltext; https://www.annalsthoracicsurgery.org/article/S0003-4975(03)01932-5/fulltext; https://www.creativebiolabs.net/Anti-Human-C5-Therapeutic-Antibody-Pexelizumab-335.htm',
        'ada_source_url_primary': 'https://www.jtcvs.org/article/S0022-5223(08)00714-9/fulltext',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Pexelizumab meta-analysis describes humanized anti-C5 scFv and randomized clinical outcomes but does not report immunogenicity or ADA incidence.',
        'verify_note': 'Prior 0.1% value was not supported by retrieved pexelizumab source text.'
    },
    'Ranibizumab PDS': {
        'ada_value': 'After SUSVIMO implant insertion and treatment, anti-ranibizumab antibodies were detected in 12% AMD, 13% DME, and 17% DR patients; pre-treatment positivity was 2.1-3.6%',
        'ada_value_display': '12-17% post-treatment anti-ranibizumab antibodies',
        'ada_first_pct': 12.0,
        'nab_pct': 'Not stated',
        'dose_mg': '2 mg via SUSVIMO implant; supplemental 0.5 mg intravitreal ranibizumab if needed',
        'dose_freq': 'Continuous delivery via ocular implant with refill every 24 weeks for AMD/DME or every 36 weeks for DR',
        'route_curated': 'Intravitreal via ocular implant',
        'assay_platform': 'Anti-ranibizumab antibody assay; label does not specify platform in retrieved text',
        'pk_efficacy_impact': 'No clinically meaningful differences in pharmacokinetics, efficacy, or safety were observed in patients testing positive for anti-ranibizumab antibodies',
        'evidence_source': 'Genentech SUSVIMO prescribing information; Drugs.com label mirror',
        'citation_urls': 'https://www.gene.com/download/pdf/susvimo_prescribing.pdf; https://www.drugs.com/pro/susvimo.html',
        'ada_source_url_primary': 'https://www.gene.com/download/pdf/susvimo_prescribing.pdf',
        'ada_source_type_curated': 'label',
        'ada_has_text_evidence': True,
        'ada_source_section': 'SUSVIMO label section 12.6: anti-ranibizumab antibodies detected in 12% AMD (29/247), 13% DME (41/320), and 17% DR (17/99) after implant insertion/treatment; no clinically meaningful PK/efficacy/safety differences observed.',
        'verify_note': 'Corrected prior ECL 4.5% value to current SUSVIMO label-confirmed post-treatment values.'
    },
    'Rovelizumab': {
        'ada_value': 'ADA incidence not stated in retrieved rovelizumab/LeukArrest sources',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': 'Not stated in retrieved sources',
        'dose_freq': 'Not stated in retrieved sources',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved sources',
        'pk_efficacy_impact': 'Retrieved sources identify rovelizumab as humanized anti-CD18/ITGB2 antibody and describe discontinued clinical development; no ADA incidence reported',
        'evidence_source': 'IUPHAR/BPS Guide to Pharmacology rovelizumab page; Creative Biolabs rovelizumab overview; FESTIVAL study search result',
        'citation_urls': 'https://www.guidetopharmacology.org/GRAC/LigandDisplayForward?ligandId=9598; https://www.creativebiolabs.net/rovelizumab-overview.htm',
        'ada_source_url_primary': 'https://www.guidetopharmacology.org/GRAC/LigandDisplayForward?ligandId=9598',
        'ada_source_type_curated': 'drug_database',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Drug pages confirm rovelizumab/Hu23F2G/LeukArrest identity and target but do not report immunogenicity or anti-drug antibody incidence.',
        'verify_note': 'Prior 1% value was not supported by retrieved rovelizumab source text.'
    },
    'Rulonilimab': {
        'ada_value': 'ADA incidence not stated in retrieved rulonilimab public drug/trial sources',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': 'Not stated in retrieved public drug pages',
        'dose_freq': 'Not stated in retrieved public drug pages',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved public drug pages',
        'pk_efficacy_impact': 'Retrieved sources describe humanized anti-PD-1 IgG1 clinical development; no ADA incidence or impact reported',
        'evidence_source': 'NCATS/Inxight Drugs rulonilimab page; Antibody Society and trial registry search results',
        'citation_urls': 'https://drugs.ncats.io/substance/KQA6N2NT4Z; https://db.antibodysociety.org/db0/621/',
        'ada_source_url_primary': 'https://drugs.ncats.io/substance/KQA6N2NT4Z',
        'ada_source_type_curated': 'drug_database',
        'ada_has_text_evidence': True,
        'ada_source_section': 'NCATS page identifies rulonilimab as a humanized mouse IgG1 monoclonal antibody targeting PD-1; no immunogenicity or ADA incidence stated.',
        'verify_note': 'Prior 1% value was not supported by retrieved rulonilimab source text.'
    },
    'Sabatolimab': {
        'ada_value': 'ADA prevalence/incidence was a planned or reported endpoint in retrieved sabatolimab SAP/clinical-result sources; numeric ADA incidence not stated in retrieved text',
        'ada_value_display': 'ADA assessed; numeric not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '20-1200 mg in solid tumor phase I/Ib; 400 or 800 mg Q4W in MDS safety run-in',
        'dose_freq': 'Every 2 or 4 weeks depending on study',
        'route_curated': 'Intravenous',
        'assay_platform': 'ADA prevalence at baseline and on-treatment incidence planned; assay platform not stated in retrieved text',
        'pk_efficacy_impact': 'Retrieved public sources support sabatolimab clinical safety/PK/immunogenicity assessment but do not provide numeric ADA incidence',
        'evidence_source': 'ClinicalTrials.gov SAP for CMBG453B12203; Novartis trial results PDF; PubMed phase I/Ib and phase Ib sabatolimab publications',
        'citation_urls': 'https://cdn.clinicaltrials.gov/large-docs/48/NCT04812548/SAP_001.pdf; https://www.novctrd.com/ctrdweb/trialresult/trialresults/pdf?trialResultId=18146; https://pubmed.ncbi.nlm.nih.gov/33883177/; https://pubmed.ncbi.nlm.nih.gov/37994196/',
        'ada_source_url_primary': 'https://cdn.clinicaltrials.gov/large-docs/48/NCT04812548/SAP_001.pdf',
        'ada_source_pmids': '33883177; 37994196',
        'ada_source_type_curated': 'clinical_trial_document',
        'ada_has_text_evidence': True,
        'ada_source_section': 'SAP endpoint: anti-drug antibody prevalence at baseline and ADA incidence on-treatment by dose level; retrieved clinical result/publication text does not state numeric ADA incidence.',
        'verify_note': 'Prior 1% value was not supported by retrieved sabatolimab source text.'
    },
    'Simridarlimab': {
        'ada_value': 'ADA incidence not stated in retrieved simridarlimab/IBI322 public sources',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '45 mg/kg in phase I cHL abstract',
        'dose_freq': 'Every 2 weeks IV in cHL phase I abstract',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved sources',
        'pk_efficacy_impact': 'Retrieved IBI322 phase I cHL abstract reports efficacy and safety but no ADA incidence; preclinical article describes tumor-selective CD47/PD-L1 blockade',
        'evidence_source': 'PMC/Hemasphere phase I IBI322 cHL abstract; CISMeF/NCI simridarlimab drug page; Cancer Immunology Immunotherapy preclinical IBI322 article',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10428475/; https://www.cismef.org/page/detail/en/NCI_CO_C176744; https://link.springer.com/article/10.1007/s00262-020-02679-5',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10428475/',
        'ada_source_type_curated': 'conference_abstract',
        'ada_has_text_evidence': True,
        'ada_source_section': 'IBI322 phase I cHL abstract reports dosing, response, and TRAEs; no immunogenicity or ADA incidence stated.',
        'verify_note': 'Prior MSD/ECL 5% value was not supported by retrieved simridarlimab source text.'
    },
    'Socazolimab': {
        'ada_value': '25% ADA positivity in ES-SCLC phase 1b combination study (5/20 patients); cervical cancer study reported 10.6% (11/104 assessable patients)',
        'ada_value_display': '25.0% in ES-SCLC; 10.6% in cervical cancer',
        'ada_first_pct': 25.0,
        'nab_pct': 'Not stated',
        'dose_mg': '5 mg/kg',
        'dose_freq': 'Every 3 weeks in ES-SCLC combination study; every 2 weeks in cervical cancer study',
        'route_curated': 'Intravenous',
        'assay_platform': 'Electrochemiluminescence method for ADA positivity in ES-SCLC study',
        'pk_efficacy_impact': 'In ES-SCLC study, five of 20 patients had ADA positives within testing cycles; one patient remained positive throughout the test. Clinical impact on PK/efficacy not stated.',
        'evidence_source': 'PMC/JTO Clinical and Research Reports ES-SCLC phase 1b socazolimab study; PubMed cervical cancer phase I study',
        'citation_urls': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10067846/; https://pubmed.ncbi.nlm.nih.gov/37020926/; https://pubmed.ncbi.nlm.nih.gov/36136294/',
        'ada_source_url_primary': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10067846/',
        'ada_source_pmids': '37020926; 36136294',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Methods/results: ADA positive rate judged by electrochemiluminescence; five of 20 patients had 10 positives within testing cycles. Discussion: ADAs detected in 11 of 104 assessable cervical cancer patients (10.6%).',
        'verify_note': 'Prior 25% value reverse-verified in ES-SCLC phase 1b source.'
    },
    'Suvizumab': {
        'ada_value': 'ADA incidence not stated in retrieved suvizumab/KD-247 public trial and drug sources',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '4, 8, or 16 mg/kg KD-247',
        'dose_freq': 'IV infusions on Days 1, 8, and 15 in phase 1 trial',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved public trial record',
        'pk_efficacy_impact': 'ClinicalTrials.gov record states safety/tolerability, PK, HIV-1 RNA load, and CD4 count objectives; no ADA incidence reported',
        'evidence_source': 'ClinicalTrials.gov NCT00917813 KD-247 phase 1 trial; Synapse/search drug pages; ScienceDirect phase I hNM01 article result',
        'citation_urls': 'https://clinicaltrials.gov/study/NCT00917813; https://synapse.patsnap.com/drug/593a434eadeb4494ab84971513d20ca4; https://www.sciencedirect.com/science/article/abs/pii/S1386653204002240',
        'ada_source_url_primary': 'https://clinicaltrials.gov/study/NCT00917813',
        'ada_source_type_curated': 'clinical_trial_registry',
        'ada_has_text_evidence': True,
        'ada_source_section': 'ClinicalTrials.gov NCT00917813 describes KD-247 dosing and safety/PK objectives; no immunogenicity or ADA incidence stated.',
        'verify_note': 'Prior MSD 3% value was not supported by retrieved suvizumab/KD-247 source text.'
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
