import pandas as pd


ada_path = "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"
df = pd.read_csv(ada_path)

updates = {
    "Daratumumab": {
        "ada_value": "Across 10 clinical trials of DARZALEX monotherapy or combination therapy, anti-daratumumab antibodies developed in 0.6% (14/2179) of patients and 12 patients tested positive for neutralizing antibodies.",
        "ada_value_display": "0.6% anti-daratumumab antibodies (14/2179)",
        "ada_first_pct": 0.6,
        "nab_pct": "12 patients tested positive for neutralizing antibodies",
        "assay_platform": "Immunogenicity assay (label; method-dependent)",
        "pk_efficacy_impact": "Because of low ADA occurrence, effects on PK, PD, safety, and/or effectiveness are unknown.",
        "evidence_source": "DailyMed/FDA DARZALEX prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=a4d0efe9-5e54-467e-9eb4-56fa7d53b60b; https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761145s029lbl.pdf",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=a4d0efe9-5e54-467e-9eb4-56fa7d53b60b",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: incidence of anti-daratumumab antibody development was 0.6% (14/2179); 12 patients tested positive for neutralizing antibodies; clinical effect unknown due to low occurrence.",
        "verify_note": "Replaced older 0% monotherapy-only display with current label pooled DARZALEX incidence.",
    },
    "Dazukibart": {
        "ada_value": "In two phase 1 healthy adult studies, no Study 1 participants were ADA positive; in Study 2, 20.0% were positive for treatment-induced anti-drug antibodies and neutralizing antibodies.",
        "ada_value_display": "0% in China Study 1; 20.0% treatment-induced ADA/NAb in Japan Study 2",
        "ada_first_pct": 20.0,
        "nab_pct": "20.0% in Study 2 were positive for treatment-induced ADA and neutralizing antibodies",
        "assay_platform": "ADA and NAb assessment (method not stated in PubMed abstract)",
        "pk_efficacy_impact": "PK parameters and immunogenicity rates were consistent with the US study; no new safety signals identified.",
        "evidence_source": "PubMed abstract: Dazukibart phase 1 China and Japan PK/safety/tolerability studies",
        "citation_urls": "https://pubmed.ncbi.nlm.nih.gov/40401504/",
        "ada_source_url_primary": "https://pubmed.ncbi.nlm.nih.gov/40401504/",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Abstract: No participants in Study 1 were ADA positive; 20.0% in Study 2 were positive for treatment-induced antidrug antibodies and neutralizing antibodies.",
        "verify_note": "Normalized source fields from PubMed abstract.",
    },
    "Denosumab": {
        "ada_value": "Using an electrochemiluminescent bridging immunoassay, less than 1% (55/8113) of Prolia-treated patients for up to 5 years tested positive for binding antibodies; none tested positive for neutralizing antibodies.",
        "ada_value_display": "<1% binding antibodies (55/8113); 0% neutralizing",
        "ada_first_pct": 1.0,
        "nab_pct": "0% / none tested positive for neutralizing antibodies",
        "assay_platform": "Electrochemiluminescent bridging immunoassay; chemiluminescent cell-based neutralizing assay",
        "pk_efficacy_impact": "Prolia pharmacokinetics were not affected by binding antibody formation.",
        "evidence_source": "FDA Prolia prescribing information, Section 6.3 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/125320s216lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/125320s216lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.3 Immunogenicity: <1% (55/8113) binding antibody positive; none neutralizing; pharmacokinetics not affected by binding antibody formation.",
        "verify_note": "Label gives a threshold rather than exact percent; retained 1.0 as sortable upper-bound numeric with '<1%' display.",
    },
    "Depemokimab": {
        "ada_value": "In adults and pediatric patients aged 12 years and older with asthma treated with EXDENSUR 100 mg every 6 months in SWIFT-1, SWIFT-2, and an open-label extension, ADA incidence was 10% (66/691); 6% (4/66) of ADA-positive patients developed neutralizing antibodies.",
        "ada_value_display": "10% ADA (66/691); 6% of ADA-positive patients had NAb",
        "ada_first_pct": 10.0,
        "nab_pct": "6% (4/66 ADA-positive patients)",
        "assay_platform": "Immunogenicity assay (label; method-dependent)",
        "pk_efficacy_impact": "No identified clinically significant effect of ADA on PK, PD, safety, or efficacy.",
        "evidence_source": "DailyMed/FDA EXDENSUR prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=30332b20-2ac0-42ad-a775-d3ca7f5fe29f",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=30332b20-2ac0-42ad-a775-d3ca7f5fe29f",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: ADA to depemokimab in SWIFT-1, SWIFT-2, and open-label extension was 10% (66/691); 6% of ADA-positive patients developed neutralizing antibodies; no clinically significant ADA effect identified.",
        "verify_note": "Corrected prior 95% value; retrieved sources indicate 95% was not ADA and label-confirmed ADA is 10%.",
    },
    "Domvanalimab": {
        "ada_value": "Not stated in retrieved phase 2 LIVERTI and EDGE-Gastric articles; the stored 17.2% value is confirmed as objective response rate, not ADA incidence.",
        "ada_value_display": "Not stated",
        "ada_first_pct": pd.NA,
        "nab_pct": "Not stated",
        "assay_platform": "Not stated",
        "pk_efficacy_impact": "Not stated",
        "evidence_source": "Nature Communications LIVERTI and Nature Medicine EDGE-Gastric articles retrieved; no numeric ADA incidence found in extracted text",
        "citation_urls": "https://nature.com/articles/s41467-025-60757-7; http://www.nature.com/articles/s41591-025-04022-w",
        "ada_source_url_primary": pd.NA,
        "ada_source_type_curated": pd.NA,
        "ada_has_text_evidence": False,
        "ada_source_section": "Retrieved articles report ORR/safety outcomes; no ADA incidence reported in extracted text.",
        "verify_note": "Cleared prior 17.2% value because it is the LIVERTI confirmed ORR, not ADA incidence.",
    },
    "Donanemab": {
        "ada_value": "In Study 1, up to 18 months of KISUNLA treatment, 87% (691/792) of patients developed anti-donanemab-azbt antibodies, and 100% of those had neutralizing antibodies. In Study 2, up to 12 months, 87% (176/202) developed anti-donanemab-azbt antibodies, and 100% had neutralizing antibodies.",
        "ada_value_display": "87% ADA in Study 1 (691/792) and Study 2 (176/202); 100% neutralizing among ADA-positive",
        "ada_first_pct": 87.0,
        "nab_pct": "100% of ADA-positive patients",
        "assay_platform": "Immunogenicity assay (label; method-dependent)",
        "pk_efficacy_impact": "ADA increased clearance and high titers showed less amyloid plaque reduction, but no clinically significant effect on effectiveness over 18 months was identified.",
        "evidence_source": "FDA KISUNLA prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761248s004lbl.pdf; https://www.ema.europa.eu/en/documents/product-information/kisunla-epar-product-information_en.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761248s004lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: Study 1 87% (691/792) and Study 2 87% (176/202) developed anti-donanemab antibodies; 100% neutralizing; ADA increased clearance; no clinically significant effectiveness effect over 18 months.",
        "verify_note": "Corrected prior unrelated PMID/>90% entry to FDA label-confirmed 87%.",
    },
    "Dostarlimab": {
        "ada_value": "In the GARNET immunogenicity analysis, treatment-emergent ADA incidence at the recommended therapeutic dose was 2.5%; 7/13 treatment-emergent ADA-positive patients across all parts tested positive for neutralizing antibodies at one or more time points.",
        "ada_value_display": "2.5% treatment-emergent ADA at recommended therapeutic dose",
        "ada_first_pct": 2.5,
        "nab_pct": "7/13 treatment-emergent ADA-positive patients across all parts had NAb at one or more time points",
        "assay_platform": "3-tier bridging ECL ADA assay; competitive ligand-binding NAb assay",
        "pk_efficacy_impact": "No clear safety or efficacy impact was observed; efficacy in NAb-positive patients was comparable or better in analyzed cohorts.",
        "evidence_source": "PMC integrated analysis of dostarlimab immunogenicity",
        "citation_urls": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8321970/",
        "ada_source_url_primary": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8321970/",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Results: RTD treatment-emergent ADA incidence 2.5%; 7/13 treatment-emergent ADA-positive patients across all parts had NAb; no observed efficacy impairment in analyzed NAb-positive cohorts.",
        "verify_note": "Normalized source fields from PMC article.",
    },
    "Dupilumab": {
        "ada_value": "Dupilumab ADA incidence varies by indication and regimen in the FDA label: approximately 6% in adult AD 300 mg Q2W for 52 weeks, 16% in pediatric AD, 5% or 9% in asthma regimens, 5% in CRSwNP, 1% in EoE, 8% in PN, 8% in COPD, and 5% in CSU.",
        "ada_value_display": "Approx. 6% adult AD; 16% pediatric AD; 5-9% asthma; 1-8% other labeled indications",
        "ada_first_pct": 6.0,
        "nab_pct": "Varies by indication/regimen: approx. 0-5% in label sections",
        "assay_platform": "Immunogenicity assay (label; method-dependent)",
        "pk_efficacy_impact": "High-titer antibodies were associated with lower serum dupilumab concentrations; most antibody titers were low.",
        "evidence_source": "FDA DUPIXENT prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761055s051lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761055s051lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: adult AD approx. 6% ADA, 2% persistent, 1% neutralizing; pediatric AD approx. 16% ADA, 3% persistent, 5% neutralizing; asthma and other indications listed with indication-specific rates.",
        "verify_note": "Replaced pooled 7.61% legacy value with label indication-specific values; ada_first_pct uses adult AD label rate.",
    },
    "Durvalumab": {
        "ada_value": "Among 2280 patients receiving IMFINZI 10 mg/kg every 2 weeks or 20 mg/kg every 4 weeks as single agent, 69 (3%) tested positive for treatment-emergent ADA and 12 (0.5%) tested positive for neutralizing antibodies. In CASPIAN combination dosing, 0/201 tested positive for treatment-emergent ADA.",
        "ada_value_display": "3% single-agent TE ADA (69/2280); 0% in CASPIAN combination (0/201)",
        "ada_first_pct": 3.0,
        "nab_pct": "0.5% (12/2280) single-agent neutralizing antibodies",
        "assay_platform": "Immunogenicity assay (label; method-dependent)",
        "pk_efficacy_impact": "ADA development appears to have no clinically relevant effect on pharmacokinetics or safety.",
        "evidence_source": "IMFINZI prescribing information, Section 6.2 Immunogenicity",
        "citation_urls": "https://ce.mayo.edu/sites/default/files/IMFINZI%C2%AE%20%28durvalumab%29%20US%20Prescribing%20Information.pdf",
        "ada_source_url_primary": "https://ce.mayo.edu/sites/default/files/IMFINZI%C2%AE%20%28durvalumab%29%20US%20Prescribing%20Information.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 6.2 Immunogenicity: 69/2280 (3%) single-agent patients TE ADA positive; 12 (0.5%) neutralizing; no clinically relevant PK or safety effect; 0/201 CASPIAN combination patients TE ADA positive.",
        "verify_note": "Corrected prior 0.8% entry to label-confirmed 3% single-agent incidence while preserving 0% combination context.",
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
