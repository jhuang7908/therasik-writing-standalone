import pandas as pd


ada_path = "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"
df = pd.read_csv(ada_path)

updates = {
    "Bimagrumab": {
        "ada_value": "No anti-drug antibodies were detected in study participants from either cohort in the phase I healthy older/obese adult bimagrumab study.",
        "ada_value_display": "0% (no ADA detected; n=24)",
        "ada_first_pct": 0.0,
        "nab_pct": "Not applicable/no ADA detected",
        "assay_platform": "Anti-drug antibody assay (platform not stated in extracted text)",
        "pk_efficacy_impact": "No ADA detected; impact not assessable",
        "evidence_source": "Journal of Cachexia, Sarcopenia and Muscle / PMC bimagrumab phase I safety and PK study; PubMed PMID 33264516",
        "citation_urls": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7749589/; https://pubmed.ncbi.nlm.nih.gov/33264516/",
        "ada_source_url_primary": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7749589/",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity: No anti-drug antibodies were detected in study participants from either cohort.",
        "verify_note": "Corrected prior unrelated PMID/4.0% entry; retrieved article supports 0% ADA in the reported phase I cohorts.",
    },
    "Bimekizumab": {
        "ada_value": "Across pivotal trials, 116/257 (45%) plaque psoriasis subjects treated with the recommended BIMZELX dosage developed anti-bimekizumab-bkzx antibodies; approximately 16% of ADA-positive subjects had neutralizing antibodies.",
        "ada_value_display": "45% ADA (116/257 plaque psoriasis); ~16% neutralizing among ADA-positive",
        "ada_first_pct": 45.0,
        "nab_pct": "~16% of ADA-positive subjects in plaque psoriasis trials",
        "assay_platform": "Immunogenicity assay (label; method-dependent)",
        "pk_efficacy_impact": "No identified clinically significant effect of anti-bimekizumab-bkzx antibodies, including neutralizing ADA, on safety or effectiveness across pivotal trials.",
        "evidence_source": "FDA/UCB BIMZELX prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://www.ucb-usa.com/bimzelx-prescribing-information.pdf; https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/761151s009lbl.pdf",
        "ada_source_url_primary": "https://www.ucb-usa.com/bimzelx-prescribing-information.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: 116/257 (45%) BIMZELX-treated plaque psoriasis subjects developed ADA; approximately 16% of ADA-positive subjects had neutralizing antibodies; no identified clinically significant effect on safety or effectiveness.",
        "verify_note": "Replaced earlier phase IIa/review-derived 34% context with current prescribing-information plaque psoriasis ADA incidence.",
    },
    "Brentuximab vedotin": {
        "ada_value": "Among adult relapsed/refractory cHL and systemic ALCL patients in Studies 1 and 2, treatment-emergent anti-brentuximab vedotin antibodies developed in 37% (58/156); approximately 7% were persistently positive and 30% transiently positive; neutralizing antibodies occurred in 62% (36/58) of ADA-positive patients.",
        "ada_value_display": "37% ADA (58/156); 7% persistent, 30% transient",
        "ada_first_pct": 37.0,
        "nab_pct": "62% (36/58 ADA-positive patients)",
        "assay_platform": "ECL bridging immunoassay",
        "pk_efficacy_impact": "Higher incidence of infusion-related reactions in persistently ADA-positive patients; effect on efficacy not stated for the cited adult Studies 1 and 2.",
        "evidence_source": "DailyMed/FDA ADCETRIS prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=3904f8dd-1aef-3490-e48f-bd55f32ed67f",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=3904f8dd-1aef-3490-e48f-bd55f32ed67f",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: treatment-emergent ADA developed in 37% (58/156); 7% persistently positive; 30% transiently positive; neutralizing antibodies in 62% (36/58).",
        "verify_note": "Normalized source fields from DailyMed label text.",
    },
    "Brodalumab": {
        "ada_value": "Approximately 3% of subjects treated with SILIQ developed antibodies to brodalumab through the 52-week treatment period; none of those subjects had antibodies classified as neutralizing, although the neutralizing antibody assay had limitations in the presence of brodalumab.",
        "ada_value_display": "~3% ADA through 52 weeks; no neutralizing antibodies classified",
        "ada_first_pct": 3.0,
        "nab_pct": "0% classified as neutralizing among ADA-positive subjects; assay limitations noted",
        "assay_platform": "Immunogenicity assay (label; method-dependent)",
        "pk_efficacy_impact": "No specific PK or efficacy impact stated in label immunogenicity section.",
        "evidence_source": "DailyMed/FDA SILIQ prescribing information, Section 6.2 Immunogenicity",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=1a550c33-456a-4833-814e-8591aea7c688",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=1a550c33-456a-4833-814e-8591aea7c688",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.2 Immunogenicity: Approximately 3% of SILIQ-treated subjects developed antibodies to brodalumab through 52 weeks; none were classified as neutralizing; neutralizing assay limitations were noted.",
        "verify_note": "Normalized to label-confirmed approximately 3% value rather than mixed review values.",
    },
    "Brolucizumab": {
        "ada_value": "Anti-brolucizumab antibodies were detected in 36% to 52% of treatment-naive patients before treatment and in at least one serum sample in 53% to 67% of BEOVU-treated patients after initiation of dosing; intraocular inflammation occurred in 6% of patients with anti-brolucizumab antibodies.",
        "ada_value_display": "53-67% post-dose ADA; 36-52% pre-treatment ADA",
        "ada_first_pct": 53.0,
        "nab_pct": "Not specified",
        "assay_platform": "Immunoassay",
        "pk_efficacy_impact": "Intraocular inflammation observed in 6% of patients with anti-brolucizumab antibodies; significance for clinical effectiveness and safety not known.",
        "evidence_source": "FDA BEOVU prescribing information, Section 6.2 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2019/761125s000lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2019/761125s000lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.2 Immunogenicity: pre-treatment anti-brolucizumab antibodies in 36% to 52%; after dosing, antibodies in at least one serum sample in 53% to 67%; intraocular inflammation in 6% of antibody-positive patients.",
        "verify_note": "Changed ada_first_pct from pre-treatment maximum 52% to post-dose lower bound 53% while preserving pre-existing ADA context.",
    },
    "Budigalimab": {
        "ada_value": "Treatment-emergent ADAs were observed in approximately 52% of participants in active budigalimab treatment arms in a phase 1b HIV-1 study: 4/10, 5/10, and 7/11 participants in the 2 mg stage I, 10 mg stage I, and 10 mg stage II groups, respectively; baseline incidence was 0% for all groups.",
        "ada_value_display": "~52% TE ADA across active arms (4/10, 5/10, 7/11)",
        "ada_first_pct": 52.0,
        "nab_pct": "Not stated",
        "assay_platform": "ADA titer assessment (platform not stated in extracted text)",
        "pk_efficacy_impact": "ADA-positive and ADA-negative exposure ranges largely overlapped, suggesting no apparent impact of ADA status on budigalimab pharmacokinetics.",
        "evidence_source": "Nature Medicine phase 1b budigalimab HIV-1 study",
        "citation_urls": "https://www.nature.com/articles/s41591-025-03993-0",
        "ada_source_url_primary": "https://www.nature.com/articles/s41591-025-03993-0",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Pharmacokinetics/pharmacodynamics results: treatment-emergent ADAs in ~52% of active arms; 4/10, 5/10, and 7/11 by cohort; baseline incidence 0%; no apparent impact on PK.",
        "verify_note": "Corrected prior unrelated PMID/1.8% entry; no 1.8% ADA source was found in retrieved budigalimab papers.",
    },
    "Burosumab": {
        "ada_value": "In XLH clinical studies, 0/13 (0%) patients aged 1 to 4 years, 10/52 (19%) patients aged 5 to 12 years, and 20/131 (15%) adult patients tested positive for anti-drug antibodies; 30% of ADA-positive children aged 5 to 12 years tested positive for neutralizing antibodies and none of the ADA-positive adults did.",
        "ada_value_display": "Adults: 15% (20/131); children 5-12 years: 19% (10/52); children 1-4 years: 0% (0/13)",
        "ada_first_pct": 15.0,
        "nab_pct": "30% of ADA-positive children aged 5-12; 0% of ADA-positive adults",
        "assay_platform": "Immunogenicity assay (label; method-dependent)",
        "pk_efficacy_impact": "ADA was not associated with clinically relevant changes in pharmacokinetics, pharmacodynamics, or safety.",
        "evidence_source": "FDA CRYSVITA prescribing information, Section 6.2 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2020/761068s005lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2020/761068s005lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.2 Immunogenicity: 0/13 age 1-4, 10/52 (19%) age 5-12, and 20/131 (15%) adults ADA-positive; 30% of ADA-positive children neutralizing; ADA not associated with clinically relevant PK, PD, or safety changes.",
        "verify_note": "Normalized source fields from FDA label text.",
    },
    "Camrelizumab": {
        "ada_value": "ADA incidence for camrelizumab was evaluated in 49 patients in a phase I advanced solid tumor study; 20.4% of patients had at least one ADA-positive sample.",
        "ada_value_display": "20.4% (at least one ADA-positive sample; n=49 evaluated)",
        "ada_first_pct": 20.4,
        "nab_pct": "Not stated",
        "assay_platform": "Immunogenicity/ADA assay in phase I PK/PD study",
        "pk_efficacy_impact": "No significant impact of ADA on PFS, OS, or adverse events was observed in the phase I study; a later separate study reported high ADA levels associated with shorter OS/PFS.",
        "evidence_source": "Signal Transduction and Targeted Therapy phase I camrelizumab study; PMC later survival association study retained as supplemental context",
        "citation_urls": "https://www.nature.com/articles/s41392-022-01213-6; https://pmc.ncbi.nlm.nih.gov/articles/PMC12167428/",
        "ada_source_url_primary": "https://www.nature.com/articles/s41392-022-01213-6",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Phase I study text: ADA incidences were evaluated in 49 patients; 20.4% had at least one ADA-positive sample; ADA was not significantly associated with PFS, OS, or AEs in that cohort.",
        "verify_note": "Primary source changed from later high-ADA survival article to the phase I study that explicitly reports the 20.4% incidence.",
    },
    "Canakinumab": {
        "ada_value": "Antibodies against ILARIS were observed in approximately 1.5% of CAPS patients and 3.1% of SJIA patients; no neutralizing antibodies were detected.",
        "ada_value_display": "1.5% CAPS; 3.1% SJIA",
        "ada_first_pct": 1.5,
        "nab_pct": "0% / no neutralizing antibodies detected",
        "assay_platform": "Biosensor binding assay for CAPS; bridging immunoassay for most SJIA studies",
        "pk_efficacy_impact": "No apparent correlation of antibody development with clinical response or adverse events was observed.",
        "evidence_source": "DailyMed/FDA ILARIS prescribing information, Section 6.3 Immunogenicity",
        "citation_urls": "https://fda.report/DailyMed/7d271f3b-e4f9-4d80-8dcf-28d49123f80e",
        "ada_source_url_primary": "https://fda.report/DailyMed/7d271f3b-e4f9-4d80-8dcf-28d49123f80e",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.3 Immunogenicity: antibodies against ILARIS in approximately 1.5% CAPS and 3.1% SJIA; no neutralizing antibodies; no apparent correlation with clinical response or adverse events.",
        "verify_note": "Normalized source fields from label text.",
    },
    "Caplacizumab": {
        "ada_value": "Pre-existing antibodies binding to caplacizumab-yhdp varied between 4% and 63%; treatment-emergent ADA against caplacizumab-yhdp were detected in 3% of CABLIVI-treated patients in HERCULES and were characterized as having neutralizing potential.",
        "ada_value_display": "3% treatment-emergent ADA; pre-existing antibodies 4-63%",
        "ada_first_pct": 3.0,
        "nab_pct": "Treatment-emergent ADA had neutralizing potential",
        "assay_platform": "Immunogenicity assay (label; method-dependent)",
        "pk_efficacy_impact": "No clinically apparent impact of pre-existing antibodies on efficacy or safety was found.",
        "evidence_source": "Sanofi/FDA CABLIVI prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://products.sanofi.us/cablivi/cablivi.pdf",
        "ada_source_url_primary": "https://products.sanofi.us/cablivi/cablivi.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: pre-existing caplacizumab-binding antibodies varied between 4% and 63%; treatment-emergent ADA detected in 3% in HERCULES; TE ADA had neutralizing potential.",
        "verify_note": "Corrected ada_first_pct from 9%/MSD legacy entry to label-confirmed 3% treatment-emergent ADA.",
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
