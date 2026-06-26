import pandas as pd


ada_path = "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"
df = pd.read_csv(ada_path)

updates = {
    "Ozanezumab": {
        "ada_value": "In a randomized first-in-human ALS study, anti-ozanezumab antibodies were detected in one subject receiving repeat-dose 15 mg/kg ozanezumab at Week 20 with a weak titer of 2; all previous time points were negative and no other subject had anti-ozanezumab antibodies. The study randomized 57 subjects to active ozanezumab treatment.",
        "ada_value_display": "1/57 active-treated subjects (1.8%) had weak anti-ozanezumab antibodies",
        "ada_first_pct": 1.8,
        "nab_pct": "Not stated",
        "assay_platform": "Immune-electrochemiluminescent assay",
        "pk_efficacy_impact": "No immune-related adverse event was reported around the positive antibody response.",
        "evidence_source": "PLOS One first-in-human ozanezumab ALS study",
        "citation_urls": "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0097803; https://pubmed.ncbi.nlm.nih.gov/24841795/",
        "ada_source_url_primary": "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0097803",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity: one repeat-dose 15 mg/kg subject had anti-ozanezumab antibodies at Week 20 with weak titer 2; no anti-ozanezumab antibodies in any other subject; active treatment n=57.",
        "verify_note": "Replaced unsupported 0.3% value and empty PubMed URL with source-confirmed first-in-human study value calculated as 1/57 active-treated subjects.",
    },
    "Ozoralizumab": {
        "ada_value": "In 52-week OHZORA and NATSUZORA rheumatoid arthritis analyses, the proportion of patients whose ADA titers increased or who became ADA-positive by Week 52 was 30.8% and 29.2% in the OHZORA 30 mg and 80 mg groups, respectively, and 46.8% and 39.1% in the NATSUZORA 30 mg and 80 mg groups, respectively. NAb-positive proportions were 7.0% and 5.2% in OHZORA 30 mg and 80 mg groups; the retrieved text reported higher NAb positivity in NATSUZORA but the line break prevented clean extraction of every NATSUZORA subgroup percentage from the article text.",
        "ada_value_display": "OHZORA: 30.8%/29.2% ADA; NATSUZORA: 46.8%/39.1% ADA",
        "ada_first_pct": 29.2,
        "nab_pct": "OHZORA: 7.0% and 5.2% by dose group; NATSUZORA NAb positivity reported but subgroup extraction incomplete in retrieved text",
        "assay_platform": "Validated electrochemiluminescence immunoassay with acid dissociation; neutralizing antibody assay for ADA-positive plasma",
        "pk_efficacy_impact": "ADA formation tended to lower ozoralizumab concentrations, especially in NATSUZORA 30 mg, but ACR20 response did not show a remarkable difference by ADA formation status in either trial.",
        "evidence_source": "Arthritis Research & Therapy 52-week OHZORA/NATSUZORA ozoralizumab analysis",
        "citation_urls": "https://link.springer.com/article/10.1186/s13075-023-03036-4; https://arthritis-research.biomedcentral.com/counter/pdf/10.1186/s13075-023-03036-4.pdf",
        "ada_source_url_primary": "https://link.springer.com/article/10.1186/s13075-023-03036-4",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Effects of ADA/NAb on plasma concentration and ACR20 response: Week 52 ADA 30.8%/29.2% in OHZORA 30/80 mg and 46.8%/39.1% in NATSUZORA 30/80 mg; ADA-positive status tended to lower concentrations but not markedly ACR20 response.",
        "verify_note": "Corrected unrelated stored PMID and replaced legacy summary with article-confirmed dose-specific ADA rates.",
    },
    "Panitumumab": {
        "ada_value": "In current VECTIBIX labeling, during 23-week monotherapy studies and other clinical trials, anti-panitumumab antibody incidence was 5.2% (74/1417); 18.9% (14/74) of ADA-positive patients had neutralizing antibodies. During VECTIBIX combination-with-chemotherapy studies, anti-panitumumab antibody incidence was 3.2% (47/1470); 14.9% (7/47) of ADA-positive patients had neutralizing antibodies.",
        "ada_value_display": "Monotherapy 5.2% ADA (74/1417); combination chemotherapy 3.2% (47/1470)",
        "ada_first_pct": 5.2,
        "nab_pct": "Monotherapy: 14/74 ADA-positive; combination: 7/47 ADA-positive",
        "assay_platform": "ADA and neutralizing antibody assays (label; method-dependent)",
        "pk_efficacy_impact": "No clinically significant effect on panitumumab pharmacokinetics following monotherapy was identified; effects after combination therapy and on safety/effectiveness are not fully characterized.",
        "evidence_source": "FDA VECTIBIX prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/125147s213lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/125147s213lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: monotherapy 5.2% (74/1417), 14/74 neutralizing; combination chemotherapy 3.2% (47/1470), 7/47 neutralizing.",
        "verify_note": "Replaced older 1.8%/0.2% values with current FDA label values.",
    },
    "Pembrolizumab": {
        "ada_value": "In KEYTRUDA clinical studies using 2 mg/kg every 3 weeks, 200 mg every 3 weeks, or 10 mg/kg every 2 or 3 weeks, 27/1289 (2.1%) evaluable patients tested positive for treatment-emergent anti-pembrolizumab antibodies; 6 patients (0.5%) had neutralizing antibodies.",
        "ada_value_display": "2.1% ADA (27/1289); 0.5% neutralizing",
        "ada_first_pct": 2.1,
        "nab_pct": "0.5% (6 patients) neutralizing antibodies",
        "assay_platform": "ECL ADA assay with subset analysis below drug tolerance level",
        "pk_efficacy_impact": "No clinically significant ADA effects on pharmacokinetics or infusion-reaction risk were identified; effect on effectiveness is unknown due to low ADA occurrence.",
        "evidence_source": "DailyMed/FDA KEYTRUDA prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=9333c79b-d487-4538-a9f0-71b91a02b287",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=9333c79b-d487-4538-a9f0-71b91a02b287",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: 27/1289 (2.1%) treatment-emergent ADA-positive; 6 (0.5%) neutralizing; no clinically significant PK or infusion-reaction effect identified.",
        "verify_note": "Updated from legacy 1.8%/0.4% to current DailyMed label 2.1%/0.5%.",
    },
    "Pemivibart": {
        "ada_value": "Current PEMGARDA EUA fact sheet states that there are no immunogenicity data available for the currently authorized dosing regimen of PEMGARDA 4500 mg IV administered every 3 months.",
        "ada_value_display": "No immunogenicity data for current authorized dosing regimen",
        "ada_first_pct": pd.NA,
        "nab_pct": "Not stated",
        "assay_platform": "Not applicable; no immunogenicity data available for authorized regimen",
        "pk_efficacy_impact": "Not stated for ADA; EUA relies on immunobridging for prophylactic efficacy support.",
        "evidence_source": "DailyMed PEMGARDA EUA fact sheet, Section 12.6 Immunogenicity",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=0bdc20a9-791f-9a06-e063-6394a90a84cc&version=6",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=0bdc20a9-791f-9a06-e063-6394a90a84cc&version=6",
        "ada_source_type_curated": "fda_eua_fact_sheet",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: no immunogenicity data available for the currently authorized PEMGARDA 4500 mg IV every 3 months dosing regimen.",
        "verify_note": "Cleared unsupported 10-15% legacy value because current EUA source explicitly states no immunogenicity data for the authorized regimen.",
    },
    "Penpulimab": {
        "ada_value": "In penpulimab-kcqx labeling, 30% (105/349) of evaluable single-agent patients tested ADA-positive at one or more post-baseline timepoints; 17% (18/105) of ADA-positive patients had neutralizing antibodies. In combination with chemotherapy, 24% (88/371) tested ADA-positive; 44% (39/88) of ADA-positive patients had neutralizing antibodies.",
        "ada_value_display": "Single-agent 30% ADA (105/349); combination chemotherapy 24% (88/371)",
        "ada_first_pct": 30.0,
        "nab_pct": "Single-agent: 18/105 ADA-positive; combination: 39/88 ADA-positive",
        "assay_platform": "ADA and neutralizing antibody assays (label; method-dependent)",
        "pk_efficacy_impact": "Insufficient data to assess whether anti-penpulimab antibodies affect safety or effectiveness.",
        "evidence_source": "FDA penpulimab-kcqx prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761258s000lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761258s000lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: single-agent 30% (105/349), 18/105 neutralizing; combination chemotherapy 24% (88/371), 39/88 neutralizing; insufficient safety/effectiveness impact data.",
        "verify_note": "Corrected unrelated stored PubMed link and replaced generic 10-15% with current FDA label values.",
    },
    "Pertuzumab": {
        "ada_value": "In the original PERJETA randomized trial label, approximately 2.8% (11/386) of PERJETA-treated patients and 6.2% (23/372) of placebo-treated patients tested positive for anti-PERJETA antibodies; none had clearly related anaphylactic/hypersensitivity reactions. Assay interpretation was limited by pertuzumab interference and possible trastuzumab antibody detection.",
        "ada_value_display": "2.8% anti-PERJETA antibodies (11/386) in treated group",
        "ada_first_pct": 2.8,
        "nab_pct": "Not stated",
        "assay_platform": "Anti-PERJETA antibody assay with drug/trastuzumab interference limitations",
        "pk_efficacy_impact": "No anaphylactic/hypersensitivity reactions clearly related to anti-therapeutic antibodies were observed; clinical meaning limited by assay interference.",
        "evidence_source": "FDA PERJETA prescribing information, Section 6.2 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2012/125409lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2012/125409lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.2 Immunogenicity: 2.8% (11/386) PERJETA-treated and 6.2% (23/372) placebo-treated patients anti-PERJETA antibody-positive; no clearly related anaphylactic/hypersensitivity reactions; assay may be affected by pertuzumab and trastuzumab.",
        "verify_note": "Corrected rounded 3% to label-confirmed 2.8%.",
    },
    "Polatuzumab": {
        "ada_value": "In POLIVY studies POLARIX and GO29365, 1.4% (6/427) and 6% (8/134) of patients, respectively, tested positive for antibodies against polatuzumab vedotin-piiq; none were positive for neutralizing antibodies.",
        "ada_value_display": "POLARIX 1.4% (6/427); GO29365 6% (8/134); none neutralizing",
        "ada_first_pct": 1.4,
        "nab_pct": "0% / none neutralizing",
        "assay_platform": "ADA and neutralizing antibody assays (label; method-dependent)",
        "pk_efficacy_impact": "Because of low ADA occurrence, effects on PK, PD, safety, and/or effectiveness are unknown.",
        "evidence_source": "DailyMed/FDA POLIVY prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=20a16ab2-f338-4abb-9dcd-254bd949a2bc&audience=consumer",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=20a16ab2-f338-4abb-9dcd-254bd949a2bc&audience=consumer",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: POLARIX 1.4% (6/427) and GO29365 6% (8/134) anti-polatuzumab antibody-positive; none neutralizing; impact unknown.",
        "verify_note": "Corrected PubMed-derived '<1%' legacy value to label-confirmed study-specific values.",
    },
    "Ramucirumab": {
        "ada_value": "In CYRAMZA clinical trials, 86/2890 (3%) treated patients tested positive for treatment-emergent anti-ramucirumab antibodies by ELISA; neutralizing antibodies were detected in 14 of the 86 ADA-positive patients.",
        "ada_value_display": "3% ADA (86/2890); 14/86 neutralizing",
        "ada_first_pct": 3.0,
        "nab_pct": "14/86 ADA-positive patients had neutralizing antibodies",
        "assay_platform": "ELISA; neutralizing antibody assay",
        "pk_efficacy_impact": "No specific ADA effect stated in retrieved immunogenicity section.",
        "evidence_source": "FDA CYRAMZA prescribing information, Section 6.2 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/125477s051lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/125477s051lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.2 Immunogenicity: 86/2890 (3%) treatment-emergent anti-ramucirumab antibody-positive by ELISA; 14/86 neutralizing.",
        "verify_note": "Normalized source fields from FDA label.",
    },
    "Ranibizumab": {
        "ada_value": "In LUCENTIS labeling, pre-treatment immunoreactivity to LUCENTIS was 0% to 5% across treatment groups. After monthly dosing for 6 to 24 months, antibodies to LUCENTIS were detected in approximately 1% to 9% of patients.",
        "ada_value_display": "Pre-treatment 0-5%; post-dose antibodies 1-9%",
        "ada_first_pct": 1.0,
        "nab_pct": "Not stated",
        "assay_platform": "Immunoassays for antibodies to LUCENTIS",
        "pk_efficacy_impact": "Clinical significance is unclear; some neovascular AMD patients with highest immunoreactivity had iritis or vitritis, while intraocular inflammation was not observed in DME or RVO patients with highest immunoreactivity.",
        "evidence_source": "FDA LUCENTIS prescribing information, Section 6.3 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2014/125156s105lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2014/125156s105lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.3 Immunogenicity: pre-treatment immunoreactivity 0-5%; after monthly dosing for 6-24 months antibodies detected in approximately 1-9%; clinical significance unclear.",
        "verify_note": "Replaced pre-treatment-only numeric emphasis with post-dose antibody range; ada_first_pct stores lower bound of post-dose antibody detection.",
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
