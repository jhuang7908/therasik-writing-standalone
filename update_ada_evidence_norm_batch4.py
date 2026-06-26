import pandas as pd


ada_path = "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"
df = pd.read_csv(ada_path)

updates = {
    "Cemiplimab": {
        "ada_value": "Across tumor types, cemiplimab treatment-emergent ADA incidence was 1.9% for 3 mg/kg every 2 weeks and 2.5% for 350 mg every 3 weeks; no neutralizing antibodies were detected in ADA-positive patients.",
        "ada_value_display": "1.9% (3 mg/kg q2w); 2.5% (350 mg q3w)",
        "ada_first_pct": 1.9,
        "nab_pct": "0% / no neutralizing antibodies detected in ADA-positive patients",
        "assay_platform": "Validated bridging immunoassay",
        "pk_efficacy_impact": "No observed impact of cemiplimab ADAs on pharmacokinetics.",
        "evidence_source": "PubMed abstract: Immunogenicity of Cemiplimab: Low Incidence of Antidrug Antibodies and Cut-Point Suitability Across Tumor Types",
        "citation_urls": "https://pubmed.ncbi.nlm.nih.gov/37656820/",
        "ada_source_url_primary": "https://pubmed.ncbi.nlm.nih.gov/37656820/",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Abstract: overall treatment-emergent ADA incidence rate of 1.9% and 2.5% at IV dose regimens of 3 mg/kg q2w and 350 mg q3w; no neutralizing antibodies detected; no observed PK impact.",
        "verify_note": "Normalized source fields from PubMed abstract.",
    },
    "Certolizumab": {
        "ada_value": "After 3 months in the NOR-DMARD inflammatory joint disease cohort, anti-drug antibodies were detected in 6.1% (19/310) of samples; ADAb-positive patients had significantly lower certolizumab pegol levels than ADAb-negative patients.",
        "ada_value_display": "6.1% ADAb-positive samples at 3 months (19/310)",
        "ada_first_pct": 6.1,
        "nab_pct": "Neutralizing ADAb measured by principal assay; percentage not separately stated in NOR-DMARD abstracted text",
        "assay_platform": "Automated in-house assays; principal neutralizing ADAb assay with confirmatory assays",
        "pk_efficacy_impact": "ADAb positivity was associated with low certolizumab pegol levels and low response proportion at 3 months.",
        "evidence_source": "Arthritis Research & Therapy NOR-DMARD certolizumab pegol study",
        "citation_urls": "https://arthritis-research.biomedcentral.com/articles/10.1186/s13075-019-2009-5; https://pmc.ncbi.nlm.nih.gov/articles/PMC6883678/",
        "ada_source_url_primary": "https://arthritis-research.biomedcentral.com/articles/10.1186/s13075-019-2009-5",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Results/Frequency and clinical significance of ADAb: 19/310 (6.1%) samples ADAb positive after 3 months; ADAb-positive patients had lower CZP levels; 1/11 ADAb-positive patients with response data was a responder.",
        "verify_note": "Normalized to directly retrieved NOR-DMARD 6.1% evidence; label also reports indication-dependent ADA values.",
    },
    "Cetuximab": {
        "ada_value": "Using ELISA, the incidence of anti-cetuximab binding antibodies in 105 patients with at least one post-baseline blood sample was less than 5%.",
        "ada_value_display": "<5% anti-cetuximab binding antibodies",
        "ada_first_pct": 5.0,
        "nab_pct": "Not stated",
        "assay_platform": "ELISA",
        "pk_efficacy_impact": "No specific PK or efficacy impact stated in label immunogenicity section.",
        "evidence_source": "DailyMed/FDA ERBITUX prescribing information, Section 6.2 Immunogenicity",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=8bc6397e-4bd8-4d37-a007-a327e4da34d9",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=8bc6397e-4bd8-4d37-a007-a327e4da34d9",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.2 Immunogenicity: ELISA characterized anti-cetuximab antibodies; incidence in 105 patients with post-baseline samples was <5%.",
        "verify_note": "Label gives a threshold rather than an exact percentage; retained 5.0 as sortable upper-bound numeric with '<5%' display.",
    },
    "Cilgavimab": {
        "ada_value": "In a randomized phase 1 study of AZD7442 in healthy Chinese adults, 3/49 (6.1%) AZD7442-treated participants were treatment-emergent antidrug antibody positive; component-specific cilgavimab-only incidence was not stated in the PubMed abstract.",
        "ada_value_display": "AZD7442 combo: 6.1% TE-ADA (3/49); cilgavimab-only rate not stated",
        "ada_first_pct": 6.1,
        "nab_pct": "Not stated",
        "assay_platform": "Antidrug antibody assessment (method not stated in PubMed abstract)",
        "pk_efficacy_impact": "AZD7442 was well tolerated with predictable pharmacokinetics in the cited phase 1 study.",
        "evidence_source": "PubMed abstract, AZD7442 (tixagevimab/cilgavimab) phase 1 healthy Chinese adult study",
        "citation_urls": "https://pubmed.ncbi.nlm.nih.gov/40799036/",
        "ada_source_url_primary": "https://pubmed.ncbi.nlm.nih.gov/40799036/",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Abstract: Sixty participants randomized; AZD7442 n=49; in AZD7442 recipients, 3 (6.1%) were treatment-emergent antidrug antibody positive.",
        "verify_note": "Replaced unconfirmed component-specific 4.1% value with source-confirmed AZD7442 combination TE-ADA incidence.",
    },
    "Clazakizumab": {
        "ada_value": "Not stated in retrieved PubMed abstract and phase 3 IMAGINE design paper.",
        "ada_value_display": "Not stated",
        "ada_first_pct": pd.NA,
        "nab_pct": "Not stated",
        "assay_platform": "Not stated",
        "pk_efficacy_impact": "Not stated",
        "evidence_source": "Retrieved clazakizumab phase IIb PubMed abstract and phase 3 IMAGINE design paper; numeric ADA incidence not reported in retrieved text",
        "citation_urls": "https://pubmed.ncbi.nlm.nih.gov/26138593/; https://pmc.ncbi.nlm.nih.gov/articles/PMC9772593/",
        "ada_source_url_primary": pd.NA,
        "ada_source_type_curated": pd.NA,
        "ada_has_text_evidence": False,
        "ada_source_section": "No source-confirmed numeric ADA incidence found in retrieved text; IMAGINE design lists immunogenicity as an objective but does not report results.",
        "verify_note": "Cleared prior 1.0% value because the stored PMID was unrelated and no numeric ADA incidence was confirmed.",
    },
    "Clesrovimab": {
        "ada_value": "In Trial 004 and Trial 007 after the approved dose in RSV season 1, 6% (120/2112) and 5% (13/291) of participants were ADA-positive on Day 150, respectively; 12% (124/1033) and 13% (34/261) were ADA-positive through Day 240, respectively.",
        "ada_value_display": "Day 150: 6% (120/2112) and 5% (13/291); through Day 240: 12% and 13%",
        "ada_first_pct": 6.0,
        "nab_pct": "Not stated as anti-drug neutralizing antibodies; RSV serum neutralizing activity not impacted",
        "assay_platform": "Immunogenicity assay (label; method-dependent)",
        "pk_efficacy_impact": "No identified impact of ADA on pharmacokinetics, RSV serum neutralizing activity, or safety during RSV season 1; efficacy impact unknown due to low MALRI and ADA rates.",
        "evidence_source": "FDA/DailyMed ENFLONSIA prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761432s000lbl.pdf; https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=c9004a92-40e8-4cdb-b22d-d07929f8fc3b",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761432s000lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: Trial 004 and Trial 007 ADA-positive rates were 6% and 5% on Day 150, and 12% and 13% through Day 240; no identified ADA impact on PK, RSV serum neutralizing activity, or safety.",
        "verify_note": "Corrected prior 22.6% entry; retrieved label shows 22.6% is AUC geometric CV, not ADA incidence.",
    },
    "Concizumab": {
        "ada_value": "In the explorer4/explorer5 phase 2 trials, three patients in each trial had positive ADA tests, for 6 ADA-positive patients among 53 concizumab-exposed patients; three had neutralizing antibodies in vitro at one time point, with no apparent significant changes in bleeding pattern, PK/PD parameters, adverse events, or coagulation-related laboratory parameters.",
        "ada_value_display": "11.3% ADA (6/53 concizumab-exposed); transient neutralizing activity in 3 patients at one time point",
        "ada_first_pct": 11.3,
        "nab_pct": "3/6 ADA-positive patients had in vitro neutralizing activity at one time point",
        "assay_platform": "Bridging electrochemiluminescence binding ADA assay; modified TFPI functionality chromogenic neutralizing assay",
        "pk_efficacy_impact": "No apparent significant changes in bleeding pattern, PK/PD parameters, adverse events, or coagulation-related labs were observed with ADA development.",
        "evidence_source": "Blood Advances / PMC explorer4 and explorer5 phase 2 concizumab trial results",
        "citation_urls": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6895373/",
        "ada_source_url_primary": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6895373/",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity results: three patients in each trial had positive ADA tests; one noninhibitor and two inhibitor patients had in vitro neutralizing ADAs on one occasion; no apparent significant clinical or PK/PD impact.",
        "verify_note": "Corrected prior 25%/wrong PMID entry to source-confirmed 6/53 phase 2 incidence.",
    },
    "Crizanlizumab": {
        "ada_value": "In a single-arm open-label multiple-dose study, 0/45 sickle cell disease patients treated with ADAKVEO 5 mg/kg tested positive for treatment-induced anti-crizanlizumab antibodies; in a single-dose healthy subject study, 1/61 (1.6%) evaluable subjects tested positive; in a phase 3 study, 0/84 patients had treatment-induced antibodies over 52 weeks.",
        "ada_value_display": "0% in SCD multiple-dose study (0/45); 1.6% healthy single-dose (1/61); 0/84 in phase 3",
        "ada_first_pct": 0.0,
        "nab_pct": "Not stated",
        "assay_platform": "Validated bridging immunoassay for binding anti-crizanlizumab-tmca antibodies",
        "pk_efficacy_impact": "No significant effect on pharmacokinetics or pharmacodynamics has been observed or is expected.",
        "evidence_source": "FDA/DailyMed ADAKVEO prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2019/761128s000lbl.pdf; https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=b2b7f8b4-fe9a-4a86-8129-9e43f99a20c6",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2019/761128s000lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: validated bridging immunoassay; 0/45 SCD patients positive in multiple-dose study; 1/61 healthy subjects positive in single-dose study; 0/84 positive in phase 3 over 52 weeks; no significant PK/PD effect observed or expected.",
        "verify_note": "Normalized source fields from FDA label.",
    },
    "Crovalimab": {
        "ada_value": "In COMMODORE-2, 30.0% (42/140) of treatment-naive subjects and 34.3% (23/67) of switch subjects tested positive for anti-crovalimab antibodies after 24 weeks. Across COMMODORE-1, COMMODORE-2, and COMMODORE-3, treatment-emergent ADA incidence was 31.4% (60/191) in treatment-naive subjects and 23.4% (43/184) in switch subjects.",
        "ada_value_display": "31.4% TE ADA treatment-naive; 23.4% TE ADA switch subjects",
        "ada_first_pct": 31.4,
        "nab_pct": "Neutralizing antibody assay issues identified; results not reviewed in FDA submission",
        "assay_platform": "ADA screening and confirmatory assay; neutralizing assay not accepted for review",
        "pk_efficacy_impact": "ADA-positive medium/high titers increased clearance; approximately 3% of subjects had loss of pharmacological activity coinciding with decreased exposure and variable clinical impact, including loss of hemolysis control.",
        "evidence_source": "FDA BLA 761388 Integrated Review for PIASKY (crovalimab-akkz)",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2024/761388Orig1s000IntegratedR.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2024/761388Orig1s000IntegratedR.pdf",
        "ada_source_type_curated": "fda_review",
        "ada_has_text_evidence": True,
        "ada_source_section": "FDA Integrated Review Immunogenicity: COMMODORE-2 30.0% treatment-naive and 34.3% switch subjects positive after 24 weeks; across COMMODORE studies TE ADA 31.4% treatment-naive and 23.4% switch subjects; approximately 3% had loss of pharmacological activity with decreased exposure.",
        "verify_note": "Corrected prior 10-15% value to FDA review-confirmed COMMODORE pooled ADA incidence.",
    },
    "Daclizumab": {
        "ada_value": "Low titers of anti-idiotype antibodies to daclizumab were detected in adult ZENAPAX-treated patients with an overall incidence of 14%; pediatric patients had 34% anti-daclizumab antibodies; no antibodies affected efficacy, safety, serum daclizumab levels, or other clinically relevant parameters in the label text.",
        "ada_value_display": "14% adults; 34% pediatric renal transplant patients",
        "ada_first_pct": 14.0,
        "nab_pct": "No clinically relevant antibody effect reported in ZENAPAX label text",
        "assay_platform": "ELISA",
        "pk_efficacy_impact": "No antibodies affected efficacy, safety, serum daclizumab levels, or other clinically relevant parameters.",
        "evidence_source": "FDA ZENAPAX prescribing information, Immunogenicity section",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2005/103749s5059lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2005/103749s5059lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity: low titers of anti-idiotype antibodies in adult patients with overall incidence 14%; pediatric incidence 34%; no antibodies affected efficacy, safety, serum levels, or other clinically relevant parameters.",
        "verify_note": "Corrected old broken FDA URL and updated adult incidence from prior <=12% display to label-confirmed 14%.",
    },
}

for col in set().union(*(entry.keys() for entry in updates.values())):
    if col not in df.columns:
        df[col] = pd.NA
    df[col] = df[col].astype("object")

for name, data in updates.items():
    mask = df["antibody_name"].fillna("").astype(str).str.casefold() == name.casefold()
    if mask.any():
        for col, val in data.items():
            df.loc[mask, col] = val
        print(f"Updated {name}")
    else:
        print(f"MISSING {name}")

df.to_csv(ada_path, index=False)
