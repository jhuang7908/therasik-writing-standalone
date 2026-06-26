import pandas as pd


ada_path = "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"
df = pd.read_csv(ada_path)

updates = {
    "Atezolizumab": {
        "ada_value": "During the first year of TECENTRIQ treatment across 8 clinical studies, 13% to 36% of patients developed anti-atezolizumab antibodies; 4.3% to 27.5% of NAb-evaluable patients had neutralizing antibodies.",
        "ada_value_display": "13-36% ADA across 8 studies; 4.3-27.5% NAb-evaluable NAb",
        "ada_first_pct": 13.0,
        "nab_pct": "4.3-27.5% of NAb-evaluable patients",
        "assay_platform": "ADA and NAb assays described in label; specific platform not stated in retrieved label text",
        "pk_efficacy_impact": "Median atezolizumab clearance was 19% higher in ADA-positive patients; ADA was not predicted to have clinically significant PK effect, with study-specific exploratory efficacy findings.",
        "evidence_source": "FDA TECENTRIQ prescribing information",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/761034s053lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/761034s053lbl.pdf",
        "ada_source_type_curated": "regulatory_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity section: across 8 clinical studies during the first year, 13% to 36% developed ADA; median clearance was 19% higher in ADA-positive patients; 4.3% to 27.5% of NAb-evaluable patients had neutralizing antibodies.",
        "verify_note": "Replaced prior average 30% display with label-confirmed ADA and NAb ranges.",
    },
    "Atoltivimab": {
        "ada_value": "Anti-atoltivimab, anti-maftivimab, and anti-odesivimab antibodies were evaluated in 24 healthy adults after a single dose; immunogenic responses were not detected at baseline or through 168 days post-dose.",
        "ada_value_display": "0% in 24 healthy adults through 168 days",
        "ada_first_pct": 0.0,
        "nab_pct": "Not applicable; immunogenic responses not detected",
        "assay_platform": "ADA assessment described in label; specific platform not stated in retrieved label text",
        "pk_efficacy_impact": "No immunogenic responses detected in the healthy-adult study; clinical infected-patient impact not stated.",
        "evidence_source": "FDA/DailyMed INMAZEB prescribing information",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2020/761169s000lbl.pdf; https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=0536b6fe-6fe5-4fd6-8cc6-1b481945c1fa",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2020/761169s000lbl.pdf",
        "ada_source_type_curated": "regulatory_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity section: development of anti-atoltivimab, anti-maftivimab, and anti-odesivimab antibodies was evaluated in 24 healthy adults; immunogenic responses were not detected at baseline or through 168 days post-dose.",
        "verify_note": "Corrected prior unsupported 80% value to source-confirmed 0% in the retrieved label.",
    },
    "Avelumab": {
        "ada_value": "BAVENCIO ADA incidence varied by trial: 8.9% (7/79) in JAVELIN Merkel 200 Part A, 8.2% (9/110) Part B, 19% (62/326) in JAVELIN Bladder 100, 18% (41/226) in JAVELIN Solid Tumor UC cohort, and 16% (65/411) in JAVELIN Renal 101.",
        "ada_value_display": "8.2-19% ADA across JAVELIN trials",
        "ada_first_pct": 8.9,
        "nab_pct": "NAb among ADA-positive: 71%, 89%, 97%, not tested, and 78% by listed trial",
        "assay_platform": "ADA and neutralizing antibody testing described in label; specific platform not stated in retrieved text",
        "pk_efficacy_impact": "In advanced UC or RCC, clearance was approximately 15% higher in ADA-positive patients, not considered clinically meaningful; efficacy/safety effect could not be determined.",
        "evidence_source": "DailyMed/FDA BAVENCIO prescribing information",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=5cd725a1-2fa4-408a-a651-57a7b84b2118",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=5cd725a1-2fa4-408a-a651-57a7b84b2118",
        "ada_source_type_curated": "regulatory_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity Table 9: ADA incidence 8.9%, 8.2%, 19%, 18%, and 16% across listed JAVELIN trials; clearance about 15% higher in ADA-positive UC/RCC patients.",
        "verify_note": "Corrected prior 4.1% value to current label-confirmed trial-specific range.",
    },
    "Axatilimab": {
        "ada_value": "In 276 cGVHD patients receiving NIKTIMVO, axatilimab-csfr treatment-emergent ADA incidence was 33.7% (93/276) after median exposure of 7.8 months; NAb were detected in 47 of 93 ADA-positive patients.",
        "ada_value_display": "33.7% (93/276); NAb 47/93 ADA-positive",
        "ada_first_pct": 33.7,
        "nab_pct": "47/93 ADA-positive patients had NAb",
        "assay_platform": "ADA and NAb assays described in label; specific platform not stated in retrieved text",
        "pk_efficacy_impact": "No clinically meaningful effect on PK, PD, or effectiveness; NAb presence correlated with hypersensitivity reactions.",
        "evidence_source": "DailyMed/FDA NIKTIMVO prescribing information",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=bb6dba23-e7a6-4765-a1e6-b9e277ce0381; https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/761411s000lbl.pdf",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=bb6dba23-e7a6-4765-a1e6-b9e277ce0381",
        "ada_source_type_curated": "regulatory_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity section: treatment-emergent ADA incidence was 33.7% (93/276); NAb detected in 47/93 ADA-positive cGVHD patients; NAb correlated with hypersensitivity reactions.",
        "verify_note": "Corrected prior 16.3% value, which matched volume-of-distribution CV rather than ADA incidence.",
    },
    "Bamlanivimab": {
        "ada_value": "Clinical ADA incidence was not stated in retrieved FDA/DailyMed bamlanivimab and bamlanivimab-etesevimab EUA fact sheets or public trial review sources.",
        "ada_value_display": "Not stated",
        "ada_first_pct": pd.NA,
        "nab_pct": "Not stated",
        "assay_platform": "Not stated",
        "pk_efficacy_impact": "No ADA impact stated in retrieved public documents.",
        "evidence_source": "DailyMed/FDA bamlanivimab-etesevimab EUA fact sheet; FDA bamlanivimab fact sheet; BLAZE-1 public article",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=aacdd8a7-18b7-43c6-b866-14aa491a0c15; https://www.fda.gov/media/143603/download; https://link.springer.com/article/10.1007/s40121-024-01031-z",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=aacdd8a7-18b7-43c6-b866-14aa491a0c15",
        "ada_source_type_curated": "regulatory_document",
        "ada_has_text_evidence": True,
        "ada_source_section": "Retrieved bamlanivimab/bamlanivimab-etesevimab EUA and public trial sources do not report anti-drug antibody or immunogenicity incidence.",
        "verify_note": "Prior 2.1% value was a COVID-19 hospitalization/death endpoint, not ADA; numeric ADA field cleared.",
    },
    "Belantamab": {
        "ada_value": "Clinical ADA incidence for unconjugated belantamab was not stated in retrieved public sources; available clinical sources refer primarily to belantamab mafodotin.",
        "ada_value_display": "Not stated separately from belantamab mafodotin",
        "ada_first_pct": pd.NA,
        "nab_pct": "Not stated",
        "assay_platform": "Not stated",
        "pk_efficacy_impact": "No separate unconjugated belantamab ADA impact found in retrieved public text.",
        "evidence_source": "Belantamab mafodotin DREAMM review and public trial sources",
        "citation_urls": "https://nature.com/articles/s41408-025-01212-0; https://www.sciencedirect.com/science/article/abs/pii/S1470204519307880",
        "ada_source_url_primary": "https://nature.com/articles/s41408-025-01212-0",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Retrieved sources describe belantamab mafodotin clinical studies; no separate clinical ADA incidence for unconjugated belantamab was stated.",
        "verify_note": "Prior 17% value was not supported by retrieved belantamab-specific source text.",
    },
    "Belantamab mafodotin": {
        "ada_value": "In BLENREP combination therapy studies, 3% (15/515) of patients tested positive for treatment-emergent belantamab mafodotin-blmf ADA; 2 of 15 ADA-positive patients had neutralizing antibodies.",
        "ada_value_display": "3% (15/515); NAb 2/15 ADA-positive",
        "ada_first_pct": 3.0,
        "nab_pct": "2/15 ADA-positive patients had NAb",
        "assay_platform": "ADA and NAb assays described in label; specific platform not stated in retrieved text",
        "pk_efficacy_impact": "Label does not state a defined ADA effect on PK, efficacy, or safety.",
        "evidence_source": "FDA BLENREP prescribing information",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761440s000lbl.pdf; https://gskpro.com/content/dam/global/hcpportal/en_US/Prescribing_Information/Blenrep/pdf/BLENREP-PI-MG.PDF",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761440s000lbl.pdf",
        "ada_source_type_curated": "regulatory_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity section: 3% (15/515) tested positive for treatment-emergent belantamab mafodotin-blmf ADA; 2 ADA-positive patients had neutralizing antibodies.",
        "verify_note": "Source-confirmed 3% label value retained and normalized.",
    },
    "Belimumab": {
        "ada_value": "In IV adult SLE Trials 2 and 3, anti-belimumab antibodies were detected in 4/563 (0.7%) subjects receiving 10 mg/kg and 27/559 (4.8%) receiving 1 mg/kg; the 10 mg/kg frequency may be underestimated due to lower assay sensitivity at high drug concentrations.",
        "ada_value_display": "0.7% at 10 mg/kg (4/563); 4.8% at 1 mg/kg (27/559)",
        "ada_first_pct": 0.7,
        "nab_pct": "Neutralizing antibodies detected in 3 subjects receiving 1 mg/kg",
        "assay_platform": "Anti-belimumab antibody testing described in label; assay sensitivity caveat noted",
        "pk_efficacy_impact": "Clinical relevance of anti-belimumab antibodies is not known; three antibody-positive subjects had mild infusion reactions.",
        "evidence_source": "DailyMed/FDA BENLYSTA prescribing information",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=2fa3c528-1777-4628-8a55-a69dae2381a3",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=2fa3c528-1777-4628-8a55-a69dae2381a3",
        "ada_source_type_curated": "regulatory_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity section: anti-belimumab antibodies detected in 0.7% at 10 mg/kg and 4.8% at 1 mg/kg; neutralizing antibodies in 3 subjects at 1 mg/kg.",
        "verify_note": "Normalized field and set primary numeric to recommended 10 mg/kg label incidence while retaining 1 mg/kg value in display.",
    },
    "Benralizumab": {
        "ada_value": "In adult and adolescent asthma patients treated with FASENRA at the recommended regimen during the 48- to 56-week treatment period, ADA incidence was 13%; 12% developed neutralizing antibodies.",
        "ada_value_display": "13% ADA in asthma; 12% NAb",
        "ada_first_pct": 13.0,
        "nab_pct": "12% in adult/adolescent asthma; 1/6 ADA-positive EGPA patients had neutralizing activity",
        "assay_platform": "ADA and neutralizing antibody testing described in label; specific platform not stated in retrieved text",
        "pk_efficacy_impact": "ADA was associated with increased clearance and increased eosinophil levels in high-titer asthma patients; no evidence of association with efficacy or safety in asthma or EGPA trials.",
        "evidence_source": "DailyMed/FDA FASENRA prescribing information",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=da6aca1a-19ed-44a4-abb7-696c7d58b784",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=da6aca1a-19ed-44a4-abb7-696c7d58b784",
        "ada_source_type_curated": "regulatory_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity section: ADA incidence 13% in adult/adolescent asthma at recommended regimen; 12% developed neutralizing antibodies; EGPA ADA incidence 9% (6/67).",
        "verify_note": "Source-confirmed 13% value retained and normalized.",
    },
    "Bevacizumab": {
        "ada_value": "In clinical studies for adjuvant treatment of a solid tumor, 0.6% (14/2233) of patients tested positive for treatment-emergent anti-bevacizumab antibodies by ECL-based assay; 3/14 tested positive for neutralizing antibodies.",
        "ada_value_display": "0.6% (14/2233); NAb 3/14 ADA-positive",
        "ada_first_pct": 0.6,
        "nab_pct": "3/14 ADA-positive patients had neutralizing antibodies",
        "assay_platform": "Electrochemiluminescent (ECL)-based assay",
        "pk_efficacy_impact": "Clinical significance of anti-bevacizumab antibodies is not known.",
        "evidence_source": "FDA bevacizumab-awwb prescribing information",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/761028s011lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/761028s011lbl.pdf",
        "ada_source_type_curated": "regulatory_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity section: 0.6% (14/2233) treatment-emergent anti-bevacizumab antibodies by ECL-based assay; 3 of 14 tested positive for neutralizing antibodies.",
        "verify_note": "Source-confirmed 0.6% value retained and normalized.",
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
