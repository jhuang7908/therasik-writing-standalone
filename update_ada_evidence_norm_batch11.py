import pandas as pd


ada_path = "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"
df = pd.read_csv(ada_path)

updates = {
    "Ravulizumab": {
        "ada_value": "In adult PNH, pediatric PNH, aHUS, gMG, and NMOSD studies totaling 721 ravulizumab-treated patients, 2 (0.3%) cases of treatment-emergent anti-drug antibodies were reported. These antibodies were transient, low-titer, and did not correlate with clinical response or adverse events.",
        "ada_value_display": "0.3% treatment-emergent ADA (2/721); transient low-titer",
        "ada_first_pct": 0.3,
        "nab_pct": "Not stated",
        "assay_platform": "ADA assay (EMA product information; method-dependent)",
        "pk_efficacy_impact": "Transient low-titer ADA did not correlate with clinical response or adverse events.",
        "evidence_source": "EMA ULTOMIRIS product information, Immunogenicity section",
        "citation_urls": "https://www.ema.europa.eu/en/documents/product-information/ultomiris-epar-product-information_en.pdf",
        "ada_source_url_primary": "https://www.ema.europa.eu/en/documents/product-information/ultomiris-epar-product-information_en.pdf",
        "ada_source_type_curated": "ema_product_information",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity: 2 (0.3%) cases of treatment-emergent ADA across adult PNH, pediatric PNH, aHUS, gMG, and NMOSD studies; transient, low-titer, and no correlation with response or adverse events.",
        "verify_note": "Corrected legacy 0.5% to EMA-confirmed 0.3%.",
    },
    "Recaticimab": {
        "ada_value": "In a randomized phase 1b/2 recaticimab hypercholesterolemia study, 26.4% (24/91) of recaticimab-treated patients had detectable ADAs; neutralizing antibodies developed in 1.1% (1/91). Serum exposure was similar between patients who developed ADAs and those who did not.",
        "ada_value_display": "26.4% ADA (24/91); 1.1% neutralizing (1/91)",
        "ada_first_pct": 26.4,
        "nab_pct": "1.1% (1/91) neutralizing antibodies",
        "assay_platform": "Binding ADA assay after first and last administration; neutralizing testing for binding ADA-positive samples",
        "pk_efficacy_impact": "Serum exposure was similar between ADA-positive and ADA-negative patients in the retrieved study.",
        "evidence_source": "PMC phase 1b/2 recaticimab hypercholesterolemia study",
        "citation_urls": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8763618/",
        "ada_source_url_primary": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8763618/",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity: 26.4% (24/91) detectable ADAs; neutralizing antibodies in 1.1% (1/91); similar serum exposure with and without ADAs.",
        "verify_note": "Corrected unrelated stored PMID and replaced '<1%' with source-confirmed ADA/NAb rates.",
    },
    "Regdanvimab": {
        "ada_value": "A peer-reviewed first-approval review states that in the phase I trial NCT04593641, anti-drug antibodies were not detected in any patient. No retrievable source confirmed the prior 10% ADA value.",
        "ada_value_display": "0% ADA detected in phase I trial; prior 10% not confirmed",
        "ada_first_pct": 0.0,
        "nab_pct": "Not applicable/no ADA detected",
        "assay_platform": "ADA assessment in phase I trial; platform not stated in retrieved review text",
        "pk_efficacy_impact": "No ADA-positive population was identified in the phase I trial.",
        "evidence_source": "PMC peer-reviewed Regdanvimab First Approval review",
        "citation_urls": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8558754/",
        "ada_source_url_primary": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8558754/",
        "ada_source_type_curated": "peer_reviewed_review",
        "ada_has_text_evidence": True,
        "ada_source_section": "Safety section: in phase I trial NCT04593641, ADAs were not detected in any patient.",
        "verify_note": "Corrected unrelated stored PMID and replaced unsupported 10% with source-confirmed phase I no-ADA-detected statement.",
    },
    "Reslizumab": {
        "ada_value": "In CINQAIR placebo-controlled studies, treatment-emergent anti-reslizumab antibodies developed in 53/983 (5.4%) patients receiving 3 mg/kg. In the long-term open-label study, treatment-emergent anti-reslizumab antibodies were detected in 49/1014 (4.8%). Neutralizing antibodies were not evaluated.",
        "ada_value_display": "5.4% ADA (53/983) in placebo-controlled studies; 4.8% long-term",
        "ada_first_pct": 5.4,
        "nab_pct": "Neutralizing antibodies were not evaluated",
        "assay_platform": "Anti-reslizumab antibody assay (label; method-dependent)",
        "pk_efficacy_impact": "No detectable impact on clinical pharmacokinetics, pharmacodynamics, efficacy, or safety was observed.",
        "evidence_source": "FDA CINQAIR prescribing information, Section 6.2 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2019/0761033s010lbl.pdf; https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=053b9158-2a5b-48b9-bf47-5fa78a35ec33",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2019/0761033s010lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.2 Immunogenicity: placebo-controlled studies 53/983 (5.4%) treatment-emergent ADA; long-term study 49/1014 (4.8%); neutralizing antibodies not evaluated; no detectable PK/PD/efficacy/safety impact.",
        "verify_note": "Replaced meta-analysis-derived 4.39% with FDA label-confirmed 5.4%.",
    },
    "Risankizumab": {
        "ada_value": "In SKYRIZI plaque psoriasis studies, by Week 52 approximately 24% (263/1079) of subjects at the recommended dose developed antibodies to risankizumab-rzaa; approximately 57% of ADA-positive subjects, corresponding to 14% of all treated subjects, had neutralizing antibodies. In psoriatic arthritis, by Week 28 approximately 12.1% (79/652) developed antibodies and none were neutralizing.",
        "ada_value_display": "Plaque psoriasis: 24% ADA (263/1079), 14% all-treated neutralizing; PsA: 12.1% ADA",
        "ada_first_pct": 24.0,
        "nab_pct": "Plaque psoriasis: approximately 57% of ADA-positive subjects, 14% of all treated subjects; PsA: none neutralizing",
        "assay_platform": "ADA and neutralizing antibody assays (label; method-dependent)",
        "pk_efficacy_impact": "Higher titers in approximately 1% were associated with lower drug concentrations and reduced clinical response; PsA antibodies were not associated with clinical response changes.",
        "evidence_source": "FDA SKYRIZI prescribing information, Section 6.2 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/761105s027,761262s008lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/761105s027,761262s008lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.2 Immunogenicity: plaque psoriasis Week 52 24% (263/1079) ADA and 14% all-treated neutralizing; PsA Week 28 12.1% (79/652), none neutralizing; high titers in about 1% associated with lower concentrations and reduced response.",
        "verify_note": "Normalized source fields from FDA label.",
    },
    "Rituximab": {
        "ada_value": "In RITUXAN labeling, anti-human anti-chimeric antibody (HACA) was detected in 4/356 (1.1%) patients with low-grade or follicular NHL. In rheumatoid arthritis, 273/2578 (11%) patients tested HACA-positive at any time after receiving Rituxan. In GPA/MPA, 23/99 (23%) tested HACA-positive by 18 months.",
        "ada_value_display": "RA: 11% HACA (273/2578); NHL 1.1%; GPA/MPA 23%",
        "ada_first_pct": 11.0,
        "nab_pct": "Not stated",
        "assay_platform": "ELISA for HACA / anti-rituximab antibodies",
        "pk_efficacy_impact": "HACA positivity in RA was not associated with increased infusion reactions or other adverse events; clinical relevance in GPA/MPA was unclear.",
        "evidence_source": "FDA RITUXAN prescribing information, Immunogenicity section",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2012/103705s5367s5388lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2012/103705s5367s5388lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.4 Immunogenicity: NHL 4/356 (1.1%); RA 273/2578 (11%) HACA-positive; GPA/MPA 23/99 (23%); RA HACA not associated with increased infusion reactions or other adverse events.",
        "verify_note": "Normalized source fields; retained RA 11% HACA value with FDA label source.",
    },
    "Romosozumab": {
        "ada_value": "NCBI Bookshelf/StatPearls summarizes that one study found 17.6% of romosozumab-treated patients developed binding antibodies and 2.9% developed neutralizing antibodies by Month 9. Binding or neutralizing antibodies did not significantly affect efficacy, safety, or drug exposure.",
        "ada_value_display": "17.6% binding antibodies; 2.9% neutralizing by Month 9",
        "ada_first_pct": 17.6,
        "nab_pct": "2.9% neutralizing antibodies by Month 9",
        "assay_platform": "Binding and neutralizing antibody assessment; platform not specified in retrieved review",
        "pk_efficacy_impact": "Neither binding nor neutralizing antibodies significantly affected efficacy, safety, or drug exposure in the summarized study.",
        "evidence_source": "NCBI Bookshelf StatPearls romosozumab review",
        "citation_urls": "https://www.ncbi.nlm.nih.gov/books/NBK585139/",
        "ada_source_url_primary": "https://www.ncbi.nlm.nih.gov/books/NBK585139/",
        "ada_source_type_curated": "clinical_review",
        "ada_has_text_evidence": True,
        "ada_source_section": "Pharmacokinetics section: 17.6% binding antibodies and 2.9% neutralizing by Month 9; no significant effect on efficacy, safety, or drug exposure.",
        "verify_note": "Normalized source fields from retrievable NCBI Bookshelf source.",
    },
    "Sacituzumab": {
        "ada_value": "During the median 4-month treatment period across TRODELVY clinical studies, 9/785 (1.1%) patients developed antibodies to sacituzumab govitecan; 6 patients (0.8% of all treated patients) had neutralizing antibodies.",
        "ada_value_display": "1.1% ADA (9/785); 0.8% neutralizing",
        "ada_first_pct": 1.1,
        "nab_pct": "0.8% of all treated patients had neutralizing antibodies",
        "assay_platform": "ADA and neutralizing antibody assays (label; method-dependent)",
        "pk_efficacy_impact": "Because of low ADA occurrence, effects on PK, PD, safety, and/or effectiveness are unknown.",
        "evidence_source": "FDA TRODELVY prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761115s059lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761115s059lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: 9/785 (1.1%) developed antibodies to sacituzumab govitecan; 6 patients (0.8%) neutralizing; impact unknown due to low occurrence.",
        "verify_note": "Corrected PubMed-only source to current FDA label.",
    },
    "Sarilumab": {
        "ada_value": "In the KEVZARA RA pre-rescue population, 4.0% of patients treated with 200 mg plus DMARD, 5.7% with 150 mg plus DMARD, and 1.9% with placebo plus DMARD had an ADA response. Neutralizing antibodies were detected in 1.0%, 1.6%, and 0.2%, respectively. In RA monotherapy, 9.2% had ADA and 6.9% had neutralizing antibodies.",
        "ada_value_display": "RA DMARD: 4.0% ADA at 200 mg, 5.7% at 150 mg; monotherapy 9.2%",
        "ada_first_pct": 4.0,
        "nab_pct": "RA DMARD: 1.0% at 200 mg, 1.6% at 150 mg; monotherapy 6.9%",
        "assay_platform": "ADA and neutralizing antibody assays (label; method-dependent)",
        "pk_efficacy_impact": "No correlation was observed between ADA development and loss of efficacy or adverse reactions in RA patients.",
        "evidence_source": "KEVZARA prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://products.sanofi.us/kevzara/kevzara.pdf",
        "ada_source_url_primary": "https://products.sanofi.us/kevzara/kevzara.pdf",
        "ada_source_type_curated": "drug_label_or_monograph",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: RA pre-rescue 4.0% ADA at 200 mg plus DMARD, 5.7% at 150 mg plus DMARD, neutralizing 1.0% and 1.6%; monotherapy 9.2% ADA and 6.9% neutralizing; no RA efficacy/safety correlation.",
        "verify_note": "Normalized source fields from manufacturer label.",
    },
    "Satralizumab": {
        "ada_value": "In ENSPRYNG phase III study BN40898 with immunosuppressive therapy and BN40900 monotherapy, ADAs were observed in 41% and 71% of satralizumab-treated patients during the double-blind period, respectively. Neutralizing ability was unknown.",
        "ada_value_display": "41% ADA with IST; 71% ADA in monotherapy",
        "ada_first_pct": 41.0,
        "nab_pct": "Neutralizing ability unknown",
        "assay_platform": "ADA assay (EMA product information; method-dependent)",
        "pk_efficacy_impact": "Exposure was lower in ADA-positive patients, but there was no impact on safety and no clear impact on efficacy or target-engagement pharmacodynamic markers.",
        "evidence_source": "EMA ENSPRYNG product information, Immunogenicity section",
        "citation_urls": "https://www.ema.europa.eu/en/documents/product-information/enspryng-epar-product-information_en.pdf",
        "ada_source_url_primary": "https://www.ema.europa.eu/en/documents/product-information/enspryng-epar-product-information_en.pdf",
        "ada_source_type_curated": "ema_product_information",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity: BN40898 with IST 41% ADA; BN40900 monotherapy 71% ADA; neutralizing ability unknown; lower exposure in ADA-positive patients but no safety impact and no clear efficacy/PD impact.",
        "verify_note": "Normalized source fields from EMA product information.",
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
