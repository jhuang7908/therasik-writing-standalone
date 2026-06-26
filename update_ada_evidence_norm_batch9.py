import pandas as pd


ada_path = "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"
df = pd.read_csv(ada_path)

updates = {
    "Natalizumab": {
        "ada_value": "In TYSABRI MS Study MS1, approximately 9% of patients developed detectable anti-natalizumab antibodies at least once during treatment, and approximately 6% had positive antibodies on more than one occasion. Anti-natalizumab antibodies were neutralizing in vitro. In Crohn's disease studies, approximately 10% were antibody-positive at least once and 5% had positive antibodies on more than one occasion.",
        "ada_value_display": "MS: 9% detectable at least once; 6% persistent; CD: 10% at least once, 5% persistent",
        "ada_first_pct": 6.0,
        "nab_pct": "Anti-natalizumab antibodies were neutralizing in vitro",
        "assay_platform": "Sequential serum antibody tests; assay unable to detect low-to-moderate antibody levels",
        "pk_efficacy_impact": "Persistent antibodies reduced serum natalizumab levels, reduced efficacy, and increased infusion-related reactions.",
        "evidence_source": "FDA TYSABRI prescribing information, Section 6.2 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/125104s984lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/125104s984lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.2 Immunogenicity: MS Study MS1 approximately 9% antibody-positive at least once and 6% on more than one occasion; anti-natalizumab antibodies neutralizing in vitro; persistent antibodies reduced efficacy and increased infusion reactions.",
        "verify_note": "Normalized source fields from current FDA label; ada_first_pct retains persistent MS antibody rate.",
    },
    "Necitumumab": {
        "ada_value": "In PORTRAZZA clinical trials, treatment-emergent anti-necitumumab antibodies were detected in 4.1% (33/814) of patients by ELISA; neutralizing antibodies were detected in 1.4% (11/814) of patients post exposure.",
        "ada_value_display": "4.1% ADA (33/814); 1.4% neutralizing (11/814)",
        "ada_first_pct": 4.1,
        "nab_pct": "1.4% (11/814) neutralizing antibodies",
        "assay_platform": "ELISA for treatment-emergent ADA; neutralizing antibody assay",
        "pk_efficacy_impact": "No clear clinical effect stated in retrieved immunogenicity section.",
        "evidence_source": "FDA PORTRAZZA prescribing information, Section 6.2 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2015/125547s000lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2015/125547s000lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.2 Immunogenicity: treatment-emergent ADA detected in 4.1% (33/814) by ELISA; neutralizing antibodies in 1.4% (11/814).",
        "verify_note": "Normalized source fields from FDA label.",
    },
    "Nemolizumab": {
        "ada_value": "In NEMLUVIO phase 3 prurigo nodularis trials up to 24 weeks, treatment-emergent ADA incidence was 7% and neutralizing antibodies were seen in 3% of subjects. In atopic dermatitis phase 3 trials up to 16 weeks, treatment-emergent ADA incidence was 6.1% (67/1092); continuing-treatment ADA incidence through Week 48 was 13.9% for 30 mg every 4 weeks and 10.6% for 30 mg every 8 weeks; neutralizing antibody incidence was 4.5% among ADA-positive subjects.",
        "ada_value_display": "PN: 7% ADA, 3% neutralizing; AD: 6.1% ADA (67/1092)",
        "ada_first_pct": 7.0,
        "nab_pct": "PN: 3% neutralizing; AD: 4.5% among ADA-positive subjects through 48 weeks",
        "assay_platform": "ADA and neutralizing antibody assays (label; method-dependent)",
        "pk_efficacy_impact": "PN: no clinically significant ADA effect on PK, safety, or efficacy over 24 weeks. AD: ADA associated with 20-70% lower nemolizumab concentrations beyond Week 16 but no clinically significant safety or efficacy effect over 48 weeks.",
        "evidence_source": "FDA NEMLUVIO prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761391s001s002lbl.pdf; https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=e9229ef1-ac60-4c24-afb6-009d3c781687",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761391s001s002lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: PN 7% ADA and 3% neutralizing up to 24 weeks; AD 6.1% (67/1092) up to 16 weeks; continuing-treatment ADA 13.9% q4w and 10.6% q8w through Week 48; AD ADA associated with 20-70% lower concentrations.",
        "verify_note": "Corrected stored PubMed link and replaced 5.6% with FDA label-confirmed PN/AD indication-specific values.",
    },
    "Nimotuzumab": {
        "ada_value": "In BIOMAB prescribing information, HAHA/anti-idiotypic response against nimotuzumab was evaluated in clinical studies at single and multiple doses to a maximum of 2400 mg with one-year follow-up; out of 34 evaluated patients, one patient showed a response. A high-grade glioma randomized trial also reported no anti-idiotypic response detected.",
        "ada_value_display": "2.9% HAHA/anti-idiotypic response (1/34 evaluated); no anti-idiotypic response in HGG trial",
        "ada_first_pct": 2.9,
        "nab_pct": "Not stated",
        "assay_platform": "HAHA/anti-idiotypic response assessment",
        "pk_efficacy_impact": "Prescribing information states the incidence of antibody development is not conclusive; low anti-idiotypic response indicates low immunogenicity.",
        "evidence_source": "BIOMAB nimotuzumab prescribing information; BMC Cancer/PMC high-grade glioma trial",
        "citation_urls": "https://biocon.com/docs/prescribing_information/oncology/biomab_pi.pdf; https://pmc.ncbi.nlm.nih.gov/articles/PMC3691625/",
        "ada_source_url_primary": "https://biocon.com/docs/prescribing_information/oncology/biomab_pi.pdf",
        "ada_source_type_curated": "drug_label_or_monograph",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity: HAHA anti-idiotypic response evaluated up to 2400 mg with one-year follow-up; 1/34 evaluated patients showed a response. The label notes antibody-development incidence is not conclusive.",
        "verify_note": "Corrected unrelated stored PubMed link and replaced unsupported 10-15% with source-confirmed 1/34 response.",
    },
    "Nirsevimab": {
        "ada_value": "In BEYFORTUS Trial 03, 3.3% (16/492) subjects receiving recommended-dose nirsevimab-alip were ADA-positive on Day 361; none had neutralizing antibodies. In Trial 04, 7% (55/830) were ADA-positive on Day 361, of whom 22% (12/55) had neutralizing antibodies. In Trial 05 first RSV season, 6% (32/534) were ADA-positive and 6% (2/32) had neutralizing antibodies.",
        "ada_value_display": "Trial 03: 3.3%; Trial 04: 7%; Trial 05: 6%",
        "ada_first_pct": 3.3,
        "nab_pct": "Trial 03: 0%; Trial 04: 12/55 ADA-positive; Trial 05: 2/32 ADA-positive",
        "assay_platform": "ADA and neutralizing antibody assays (label; method-dependent)",
        "pk_efficacy_impact": "ADA-positive subjects had 50-60% lower nirsevimab concentrations at Day 361; effect on effectiveness is unknown due to low ADA and MA RSV LRTI occurrence.",
        "evidence_source": "FDA BEYFORTUS prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/761328s000lbl.pdf; https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=2f08fa60-f674-432d-801b-1f9514bd9b39",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/761328s000lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: Trial 03 3.3% (16/492), no neutralizing; Trial 04 7% (55/830), 12/55 neutralizing; Trial 05 6% (32/534), 2/32 neutralizing; ADA-positive subjects had 50-60% lower Day 361 concentrations.",
        "verify_note": "Corrected unrelated stored PubMed link; retained Trial 03 first numeric value and added label-confirmed Trial 04/05 context.",
    },
    "Nivolumab": {
        "ada_value": "Current OPDIVO labeling reports treatment-regimen-specific anti-nivolumab ADA incidence: OPDIVO single agent 11% (229/2085) with NAb in 7% of ADA-positive patients; OPDIVO plus ipilimumab followed by OPDIVO single agent had 38% in melanoma, 56% in HCC, and 26% in RCC/CRC; OPDIVO plus ipilimumab without single-agent follow-up had 26% in malignant pleural mesothelioma and 37% in NSCLC; OPDIVO plus ipilimumab plus 2 cycles platinum-doublet chemotherapy had 34% in NSCLC.",
        "ada_value_display": "Single-agent 11%; combination regimens 26-56% depending on indication",
        "ada_first_pct": 11.0,
        "nab_pct": "Single-agent: 7% of ADA-positive; combination values range 2.9-41% of ADA-positive depending on regimen/indication",
        "assay_platform": "ADA and neutralizing antibody assays (label; method-dependent)",
        "pk_efficacy_impact": "Treatment-emergent ADA increased nivolumab clearance up to 20%, not considered clinically significant; no clinically significant infusion-reaction effect identified; effectiveness effects not fully characterized.",
        "evidence_source": "DailyMed/FDA OPDIVO prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=f570b9c4-6846-4de2-abfa-4d0a4ae4e394",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=f570b9c4-6846-4de2-abfa-4d0a4ae4e394",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity Table 56: single-agent 11% (229/2085), NAb 7% of ADA-positive; combination regimens 26-56%; ADA increased clearance up to 20% but not clinically significant.",
        "verify_note": "Replaced legacy 37.8% combination-only value with current label treatment-regimen-specific values; ada_first_pct uses single-agent incidence.",
    },
    "Obinutuzumab": {
        "ada_value": "In GAZYVA CLL studies, approximately 13% (9/70) of treated patients tested positive for anti-GAZYVA antibodies at one or more time points during the 12-month follow-up period. Neutralizing activity was not assessed.",
        "ada_value_display": "Approximately 13% anti-GAZYVA antibodies (9/70)",
        "ada_first_pct": 13.0,
        "nab_pct": "Neutralizing activity not assessed",
        "assay_platform": "Serum anti-GAZYVA antibody testing",
        "pk_efficacy_impact": "Clinical significance of anti-GAZYVA antibodies is not known.",
        "evidence_source": "FDA GAZYVA prescribing information, Section 6.2 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2014/125486_s008lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2014/125486_s008lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.2 Immunogenicity: approximately 13% (9/70) anti-GAZYVA antibody-positive during 12-month follow-up; neutralizing activity not assessed; clinical significance unknown.",
        "verify_note": "Normalized source fields from FDA label.",
    },
    "Ofatumumab": {
        "ada_value": "In ARZERRA CLL studies, serum samples from more than 550 patients were tested during and after treatment; formation of anti-ofatumumab antibodies was observed in less than 1% of patients with CLL after treatment.",
        "ada_value_display": "<1% anti-ofatumumab antibodies in CLL studies",
        "ada_first_pct": 1.0,
        "nab_pct": "Not stated",
        "assay_platform": "Serum anti-ARZERRA antibody testing",
        "pk_efficacy_impact": "No specific ADA effect stated in retrieved immunogenicity section.",
        "evidence_source": "FDA ARZERRA prescribing information, Section 6.2 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2016/125326s062lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2016/125326s062lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.2 Immunogenicity: more than 550 CLL patients tested; anti-ofatumumab antibody formation observed in less than 1% after treatment.",
        "verify_note": "Replaced precise 0.22% legacy value with label-confirmed '<1%' upper-bound numeric value.",
    },
    "Olaratumab": {
        "ada_value": "In LARTRUVO clinical trials, 13/370 (3.5%) evaluable treated patients tested positive for treatment-emergent anti-olaratumab antibodies by ELISA; neutralizing antibodies were detected in all patients who tested positive.",
        "ada_value_display": "3.5% ADA (13/370); all ADA-positive neutralizing",
        "ada_first_pct": 3.5,
        "nab_pct": "All treatment-emergent ADA-positive patients had neutralizing antibodies",
        "assay_platform": "ELISA; neutralizing antibody assay",
        "pk_efficacy_impact": "Effects on efficacy, safety, and exposure could not be assessed due to limited number of ADA-positive patients.",
        "evidence_source": "FDA LARTRUVO prescribing information, Section 6.2 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2016/761038lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2016/761038lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.2 Immunogenicity: 13/370 (3.5%) treatment-emergent ADA-positive by ELISA; all ADA-positive patients had neutralizing antibodies; effects not assessable.",
        "verify_note": "Normalized source fields from FDA label.",
    },
    "Omalizumab": {
        "ada_value": "In XOLAIR asthma studies in patients 12 years and older, antibodies to XOLAIR were detected in approximately 1/1723 (<0.1%) treated patients. In three pediatric asthma studies, antibodies were detected in 1/581 patients aged 6 to <12 years. No detectable antibodies were observed in CIU trials, though antibody determination was limited by drug levels and missing samples.",
        "ada_value_display": "<0.1% anti-omalizumab antibodies in adult/adolescent asthma (1/1723); 1/581 pediatric",
        "ada_first_pct": 0.06,
        "nab_pct": "Not stated",
        "assay_platform": "ELISA for anti-XOLAIR antibodies",
        "pk_efficacy_impact": "No specific ADA effect stated in retrieved immunogenicity section.",
        "evidence_source": "FDA XOLAIR prescribing information, Section 6.2 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2021/103976s5238lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2021/103976s5238lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.2 Immunogenicity: adult/adolescent asthma approximately 1/1723 (<0.1%) anti-XOLAIR antibody-positive; pediatric asthma 1/581; no detectable antibodies in CIU trials with sampling limitations.",
        "verify_note": "Corrected prior 0.00% display to label-confirmed 1/1723 (<0.1%); ada_first_pct stores calculated 0.06%.",
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
