import pandas as pd

ada_path = 'data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv'
df = pd.read_csv(ada_path)

updates = {
    'Lenzilumab': {
        'ada_value': 'ADA incidence not stated in retrieved lenzilumab clinical sources',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '600 mg',
        'dose_freq': 'Three IV doses 8 hours apart in LIVE-AIR',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved sources',
        'pk_efficacy_impact': 'LIVE-AIR reported improved survival without invasive mechanical ventilation and placebo-like safety; retrieved sources do not report ADA incidence',
        'evidence_source': 'Lancet Respiratory Medicine LIVE-AIR phase 3 article; Drugs Design Development and Therapy healthy Korean PK/safety article',
        'citation_urls': 'https://www.thelancet.com/journals/lanres/article/PIIS2213-2600(21)00494-X/fulltext; https://www.dovepress.com/pharmacokinetics-safety-and-tolerability-of-intravenous-lenzilumab-an--peer-reviewed-fulltext-article-DDDT; https://pmc.ncbi.nlm.nih.gov/articles/PMC8109186/',
        'ada_source_url_primary': 'https://www.thelancet.com/journals/lanres/article/PIIS2213-2600(21)00494-X/fulltext',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'LIVE-AIR and healthy-volunteer PK/safety sources reviewed; dosing, PK, and safety reported, but no anti-drug antibody incidence stated.',
        'verify_note': 'Prior 3.8% value was not supported by retrieved lenzilumab sources.'
    },
    'Lerdelimumab': {
        'ada_value': 'Immunogenicity described qualitatively as very low; no precise ADA percentage stated in retrieved phase III abstract page',
        'ada_value_display': 'Very low; numeric not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '100 micrograms per subconjunctival injection',
        'dose_freq': 'Four injections around first-time trabeculectomy',
        'route_curated': 'Subconjunctival',
        'assay_platform': 'Not stated in retrieved abstract page',
        'pk_efficacy_impact': 'CAT-152 did not improve trabeculectomy success versus placebo; safety profile was similar to placebo',
        'evidence_source': 'Ophthalmology phase III CAT-152/lerdelimumab trabeculectomy study abstract page',
        'citation_urls': 'https://www.aaojournal.org/article/S0161-6420(07)00331-4/abstract; https://doi.org/10.1016/j.ophtha.2007.03.050',
        'ada_source_url_primary': 'https://www.aaojournal.org/article/S0161-6420(07)00331-4/abstract',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Abstract: administration of CAT-152 was not associated with increased adverse events; immunogenicity of CAT-152 was very low.',
        'verify_note': 'Prior 1.0% value was not supported as a precise numeric ADA incidence in retrieved source text.'
    },
    'Letolizumab': {
        'ada_value': 'ADA incidence not stated in retrieved letolizumab public drug/source pages',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': 'Not stated in retrieved public pages',
        'dose_freq': 'Not stated in retrieved public pages',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved public pages',
        'pk_efficacy_impact': 'Retrieved drug pages describe CD40L-targeting Fc-fusion mechanism and clinical development but do not report ADA incidence or impact',
        'evidence_source': 'CISMeF/NCI letolizumab drug page; Orphanet search result page',
        'citation_urls': 'https://www.cismef.org/page/detail/en/NCI_CO_C120140; https://www.orpha.net/en/drug/substance/512278',
        'ada_source_url_primary': 'https://www.cismef.org/page/detail/en/NCI_CO_C120140',
        'ada_source_type_curated': 'drug_database',
        'ada_has_text_evidence': True,
        'ada_source_section': 'CISMeF/NCI page describes letolizumab/BMS-986004 mechanism and target; no immunogenicity or ADA incidence stated.',
        'verify_note': 'Prior MSD/ECL 6.1% value was not supported by retrieved public source text.'
    },
    'Lirentelimab': {
        'ada_value': 'ADA incidence not stated in retrieved ENIGMA article or later protocol; protocol lists anti-lirentelimab antibody assessment',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '0.3, 1, or 3 mg/kg depending on low/high-dose schedule',
        'dose_freq': 'Monthly IV infusions in ENIGMA phase 2',
        'route_curated': 'Intravenous; Subcutaneous',
        'assay_platform': 'Anti-lirentelimab antibody assessment listed in protocol; assay results not stated in retrieved sources',
        'pk_efficacy_impact': 'ENIGMA showed eosinophil/symptom reduction but more infusion reactions; no ADA incidence or impact reported in retrieved article',
        'evidence_source': 'NEJM ENIGMA phase 2 lirentelimab article; Allakos NCT05528861 protocol',
        'citation_urls': 'https://www.nejm.org/doi/10.1056/NEJMoa2012047; https://pubmed.ncbi.nlm.nih.gov/33085861/; https://cdn.clinicaltrials.gov/large-docs/61/NCT05528861/Prot_000.pdf',
        'ada_source_url_primary': 'https://www.nejm.org/doi/10.1056/NEJMoa2012047',
        'ada_source_pmids': '33085861',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'NEJM ENIGMA article reviewed for safety/infusion reactions; no ADA incidence stated. Later protocol includes anti-lirentelimab antibody and anti-drug antibody analysis sections.',
        'verify_note': 'Prior 2.0% value was not supported by retrieved ENIGMA/protocol text.'
    },
    'Maftivimab': {
        'ada_value': '0% anti-REGN3479 (maftivimab) antibodies detected in phase 1 healthy adults',
        'ada_value_display': '0.0%',
        'ada_first_pct': 0.0,
        'nab_pct': 'Not reported',
        'dose_mg': '50 mg/kg component dose in approved INMAZEB regimen',
        'dose_freq': 'Single IV infusion',
        'route_curated': 'Intravenous',
        'assay_platform': 'Anti-REGN3470/3471/3479 antibody assessment',
        'pk_efficacy_impact': 'REGN3470-3471-3479 was well tolerated, displayed linear PK, and did not lead to detectable immunogenicity',
        'evidence_source': 'Lancet Infectious Diseases/PubMed first-in-human REGN-EB3 phase 1 study; FDA INMAZEB label',
        'citation_urls': 'https://pubmed.ncbi.nlm.nih.gov/29929783/; https://www.accessdata.fda.gov/drugsatfda_docs/label/2020/761169s000lbl.pdf',
        'ada_source_url_primary': 'https://pubmed.ncbi.nlm.nih.gov/29929783/',
        'ada_source_pmids': '29929783',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Findings/label immunogenicity: no participants tested positive for anti-REGN3470, anti-REGN3471, or anti-REGN3479 antibodies; immunogenic responses not detected through 168 days post-dose.',
        'verify_note': 'Corrected prior discontinued/no-public-data note to phase 1 and FDA label-confirmed 0% anti-maftivimab antibody detection.'
    },
    'Milatuzumab': {
        'ada_value': '1/25 borderline positive human anti-milatuzumab antibody titers in relapsed/refractory multiple myeloma phase I trial',
        'ada_value_display': '4.0% borderline positive',
        'ada_first_pct': 4.0,
        'nab_pct': 'Not reported',
        'dose_mg': '1.5, 4, 8, or 16 mg/kg',
        'dose_freq': 'Twice weekly for 4 weeks in multiple myeloma trial; varied schedule in lymphoma trial',
        'route_curated': 'Intravenous',
        'assay_platform': 'Human anti-milatuzumab antibody titer assessment',
        'pk_efficacy_impact': 'Milatuzumab was rapidly cleared with little accumulation and low trough levels; borderline ADA clinical significance uncertain',
        'evidence_source': 'PubMed phase I milatuzumab multiple myeloma trial; PubMed phase I B-cell lymphoma trial',
        'citation_urls': 'https://pubmed.ncbi.nlm.nih.gov/24112026/; https://pubmed.ncbi.nlm.nih.gov/25754579/',
        'ada_source_url_primary': 'https://pubmed.ncbi.nlm.nih.gov/24112026/',
        'ada_source_pmids': '24112026; 25754579',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'Multiple myeloma phase I abstract: only one patient developed borderline positive human anti-milatuzumab antibody titers of uncertain clinical significance.',
        'verify_note': 'Refined prior ELISA 5.0% value to 1/25 borderline-positive trial evidence.'
    },
    'Monalizumab': {
        'ada_value': 'ADA incidence not stated in retrieved monalizumab plus durvalumab phase 1/2 source',
        'ada_value_display': 'Not stated',
        'ada_first_pct': pd.NA,
        'nab_pct': 'Not stated',
        'dose_mg': '750 mg monalizumab with durvalumab 1500 mg in expansion cohorts',
        'dose_freq': 'Monalizumab every 2 or 4 weeks; durvalumab every 4 weeks',
        'route_curated': 'Intravenous',
        'assay_platform': 'Not stated in retrieved PubMed abstract',
        'pk_efficacy_impact': 'Monalizumab plus durvalumab was well tolerated with modest efficacy and immune activation; no ADA incidence reported in retrieved abstract/search results',
        'evidence_source': 'PubMed phase 1/2 monalizumab plus durvalumab advanced solid tumor study; clinical trial pages',
        'citation_urls': 'https://pubmed.ncbi.nlm.nih.gov/38309722/; https://www.dana-farber.org/clinical-trials/17-543; https://clinicaltrials.eu/inn/monalizumab/',
        'ada_source_url_primary': 'https://pubmed.ncbi.nlm.nih.gov/38309722/',
        'ada_source_pmids': '38309722',
        'ada_source_type_curated': 'peer_reviewed_article',
        'ada_has_text_evidence': True,
        'ada_source_section': 'PubMed abstract reports safety, efficacy, and exploratory immune activation analyses; no immunogenicity/ADA incidence stated.',
        'verify_note': 'Prior 0.4% value was not supported by retrieved monalizumab source text.'
    },
    'Motavizumab': {
        'ada_value': '1.8% ADA in phase 3 high-risk pediatric RSV prophylaxis trial; phase 2 sequential study ADA <=5.1% in any group',
        'ada_value_display': '1.8%',
        'ada_first_pct': 1.8,
        'nab_pct': 'Not reported',
        'dose_mg': '15 mg/kg prophylaxis; 30 or 100 mg/kg treatment study',
        'dose_freq': 'Monthly intramuscular prophylaxis for 5 doses in pediatric prophylaxis studies',
        'route_curated': 'Intramuscular; Intravenous',
        'assay_platform': 'ELISA ADA assays in phase 2 sequential study; MSD immunogenicity application reference for phase 3 trial',
        'pk_efficacy_impact': 'Phase 2 sequential study reported comparable serum trough concentrations and infrequent ADA; phase 3 reference reports patients with ADA had RSV and cutaneous events',
        'evidence_source': 'Meso Scale Discovery reference page for Pediatrics motavizumab phase 3 trial; BMC Pediatrics phase 2 sequential motavizumab/palivizumab study',
        'citation_urls': 'https://www.mesoscale.com/en/references/2010/motavizumab_for; https://bmcpediatr.biomedcentral.com/articles/10.1186/1471-2431-10-38; https://pmc.ncbi.nlm.nih.gov/articles/PMC2759493/',
        'ada_source_url_primary': 'https://www.mesoscale.com/en/references/2010/motavizumab_for',
        'ada_source_type_curated': 'peer_reviewed_article_reference',
        'ada_has_text_evidence': True,
        'ada_source_section': 'MSD reference abstract: antidrug antibodies detected in 1.8% of motavizumab recipients; phase 2 BMC study: ADA detection was infrequent, 5.1% or less of any group.',
        'verify_note': 'Prior 1.8% value reverse-verified against MSD/Pediatrics reference and BMC supporting study.'
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
