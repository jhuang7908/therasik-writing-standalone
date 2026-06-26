import pandas as pd


ada_path = "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"
df = pd.read_csv(ada_path)

updates = {
    "Lebrikizumab": {
        "ada_value": "In EBGLYSS atopic dermatitis studies, antibodies to lebrikizumab-lbkz developed in 4/145 (2.8%) subjects treated with EBGLYSS 250 mg every 2 weeks up to Week 16; none of the antibodies were neutralizing and titers were low. Similar results were observed in pediatric subjects up to 12 months.",
        "ada_value_display": "2.8% ADA (4/145); none neutralizing",
        "ada_first_pct": 2.8,
        "nab_pct": "0% / none neutralizing",
        "assay_platform": "ADA and neutralizing antibody assays (label; method-dependent)",
        "pk_efficacy_impact": "ADA presence was not associated with changes to pharmacokinetics, efficacy, or safety; clinical relevance is unknown due to low ADA occurrence.",
        "evidence_source": "FDA EBGLYSS prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761306s003lbl.pdf; https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=7a774ea2-acde-4aaa-9a8f-ccba5a5b1d5f",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761306s003lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: 4/145 (2.8%) subjects developed antibodies to lebrikizumab-lbkz; none were neutralizing; no PK, efficacy, or safety association identified.",
        "verify_note": "Corrected unrelated stored PubMed link and replaced legacy 5.2% with current FDA label-confirmed 2.8%.",
    },
    "Lecanemab": {
        "ada_value": "During the 18-month treatment period in LEQEMBI Study 1, 63/154 (40.9%) patients treated with 10 mg/kg every 2 weeks developed anti-lecanemab-irmb antibodies; neutralizing anti-lecanemab-irmb antibodies were detected in 16/63 (25.4%) ADA-positive patients.",
        "ada_value_display": "40.9% ADA (63/154); 25.4% of ADA-positive neutralizing",
        "ada_first_pct": 40.9,
        "nab_pct": "16/63 (25.4%) ADA-positive patients had neutralizing antibodies",
        "assay_platform": "ADA and neutralizing antibody assays subject to serum lecanemab interference",
        "pk_efficacy_impact": "Label states there is insufficient information to characterize ADA effects on PK, PD, safety, or effectiveness.",
        "evidence_source": "FDA LEQEMBI prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761269s005lbl.pdf; https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=9d1ff786-e577-410a-a273-c4d7d0e4e975",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761269s005lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: Study 1 63/154 (40.9%) developed anti-lecanemab antibodies; 16/63 (25.4%) neutralizing; assays subject to drug interference; insufficient information on ADA effect.",
        "verify_note": "Corrected unrelated stored PubMed link and replaced legacy 3.4% with current label-confirmed 40.9%.",
    },
    "Lemalesomab": {
        "ada_value": "Not confirmed in retrieved sources. Searches confirmed lemalesomab is a mouse monoclonal antibody used for diagnostic imaging, but no retrievable clinical source confirmed a precise 40% human anti-mouse antibody/ADA incidence.",
        "ada_value_display": "Not stated",
        "ada_first_pct": pd.NA,
        "nab_pct": "Not stated",
        "assay_platform": "Not stated",
        "pk_efficacy_impact": "Not stated",
        "evidence_source": "Retrieved NCATS/vendor summaries did not report a numeric clinical ADA/HAMA incidence",
        "citation_urls": "https://drugs.ncats.io/substance/018649S21N",
        "ada_source_url_primary": pd.NA,
        "ada_source_type_curated": pd.NA,
        "ada_has_text_evidence": False,
        "ada_source_section": "Retrieved sources identify lemalesomab as a mouse monoclonal antibody but do not provide a precise clinical ADA/HAMA percentage.",
        "verify_note": "Cleared prior 40.0% value because no precise retrievable source confirmed it.",
    },
    "Leronlimab": {
        "ada_value": "In a randomized, double-blind phase 2a PRO 140 study, antibodies to PRO 140 were detected in two subjects in each PRO 140 dose group (4/20 active-treated subjects). Antibodies were low-titer (1:32 or less), non-neutralizing in vitro, and had no apparent effect on pharmacokinetics or viral load reductions.",
        "ada_value_display": "20% anti-PRO 140 antibodies in phase 2a IV study (4/20 active-treated); non-neutralizing",
        "ada_first_pct": 20.0,
        "nab_pct": "0% neutralizing in vitro",
        "assay_platform": "ELISA for anti-PRO 140 antibodies; in vitro neutralizing activity test",
        "pk_efficacy_impact": "Low-titer antibodies did not have any apparent effect on PK or viral-load reductions.",
        "evidence_source": "PMC phase 2a study of PRO 140 administered intravenously to HIV-infected adults",
        "citation_urls": "https://pmc.ncbi.nlm.nih.gov/articles/PMC2944554/; https://journals.asm.org/doi/10.1128/aac.00086-10",
        "ada_source_url_primary": "https://pmc.ncbi.nlm.nih.gov/articles/PMC2944554/",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Results: antibodies to PRO 140 detected in two subjects in each PRO 140 dose group; low-titer, non-neutralizing, and no apparent PK or viral-load effect.",
        "verify_note": "Corrected unrelated stored PubMed link; calculated 4/20 active-treated phase 2a subjects as 20.0%.",
    },
    "Levilimab": {
        "ada_value": "During clinical studies of Ilsira/levilimab, including long-term one-year rheumatoid arthritis treatment, no production of binding antibodies to levilimab was detected.",
        "ada_value_display": "0% binding antibodies detected in clinical studies",
        "ada_first_pct": 0.0,
        "nab_pct": "Not applicable/no binding antibodies detected",
        "assay_platform": "Binding antibody assessment; platform not specified in retrieved label-like source",
        "pk_efficacy_impact": "No binding antibodies detected; ADA impact not assessable.",
        "evidence_source": "Ilsira/levilimab product information mirrored by Medixlife; PMC CORONA article as contextual source",
        "citation_urls": "https://www.medixlife.com/ilsira-instructions/; https://pmc.ncbi.nlm.nih.gov/articles/PMC8479713/",
        "ada_source_url_primary": "https://www.medixlife.com/ilsira-instructions/",
        "ada_source_type_curated": "drug_label_or_monograph",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity: during clinical studies of Ilsira, including one-year rheumatoid arthritis treatment, no production of binding antibodies to levilimab was detected.",
        "verify_note": "Corrected unrelated stored PubMed link and replaced '<2%' with source-confirmed 0% binding antibodies detected.",
    },
    "Lumiliximab": {
        "ada_value": "In a phase 1/2 lumiliximab plus FCR study, 13/31 treated patients had serum anti-lumiliximab and anti-rituximab evaluations at baseline and at least one post-dose time point; all measured anti-lumiliximab antibody values were undetectable.",
        "ada_value_display": "0% detectable anti-lumiliximab antibodies among evaluated patients (0/13)",
        "ada_first_pct": 0.0,
        "nab_pct": "Not applicable/no anti-lumiliximab antibodies detected",
        "assay_platform": "Validated anti-lumiliximab ELISA",
        "pk_efficacy_impact": "No anti-lumiliximab antibodies detected among evaluated patients; ADA impact not assessable.",
        "evidence_source": "PMC phase 1/2 lumiliximab plus FCR study",
        "citation_urls": "https://pmc.ncbi.nlm.nih.gov/articles/PMC2810983/; https://pubmed.ncbi.nlm.nih.gov/19843887/",
        "ada_source_url_primary": "https://pmc.ncbi.nlm.nih.gov/articles/PMC2810983/",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Anti-lumiliximab antibodies: 13/31 patients had baseline and post-dose evaluations; all measured values were undetectable.",
        "verify_note": "Replaced generic AACR URL with retrievable PMC clinical study source; retained 0% among evaluated patients.",
    },
    "Mepolizumab": {
        "ada_value": "In adult and adolescent patients with severe asthma receiving NUCALA 100 mg, 15/260 (6%) had detectable anti-mepolizumab antibodies; neutralizing antibodies were detected in one patient. Other label indications reported 3% in CRSwNP, 4% in COPD, <2% in EGPA, and 2% in HES.",
        "ada_value_display": "6% severe asthma ADA (15/260); 1 neutralizing patient",
        "ada_first_pct": 6.0,
        "nab_pct": "1 severe asthma patient had neutralizing antibodies; none detected in CRSwNP/COPD/EGPA/HES patients described",
        "assay_platform": "ADA and neutralizing antibody assays (label; method-dependent)",
        "pk_efficacy_impact": "Anti-mepolizumab antibodies slightly increased clearance by approximately 20%; clinical relevance is not known.",
        "evidence_source": "FDA NUCALA prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/125526s007lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/125526s007lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: severe asthma 15/260 (6%) anti-mepolizumab antibodies; one neutralizing; antibodies slightly increased clearance by about 20%; other indication rates 3%, 4%, <2%, and 2%.",
        "verify_note": "Replaced prior 2.91% CI-derived value with current label-confirmed 6% severe asthma rate.",
    },
    "Mirikizumab": {
        "ada_value": "During the 52-week UC-1 and UC-2 treatment period, 23% (88/378) of OMVOH-treated subjects at the recommended dosage and evaluable for assessment developed anti-mirikizumab-mrkz antibodies. Of these, 33/88 (38%) developed titers >=1:160; 10 of those 33 had reduced serum trough concentrations and 5 of those 10 did not achieve clinical response at Week 52.",
        "ada_value_display": "23% ADA (88/378) in UC-1/UC-2 at recommended dosage",
        "ada_first_pct": 23.0,
        "nab_pct": "Not stated",
        "assay_platform": "ADA assay (label; method-dependent)",
        "pk_efficacy_impact": "High-titer ADA was associated with reduced trough concentrations in 10 subjects and lack of Week 52 clinical response in 5 of those 10; no identified clinically significant safety effect over 52 weeks.",
        "evidence_source": "FDA OMVOH prescribing information, Section 12.6 Immunogenicity",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/761279s000lbl.pdf; https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=472cbe04-263e-433d-9a0f-58c1b50b715a",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/761279s000lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Section 12.6 Immunogenicity: 23% (88/378) ADA; 33/88 high titer >=1:160; 10 had reduced trough concentrations and 5 did not achieve Week 52 clinical response; no clinically significant safety effect identified.",
        "verify_note": "Corrected stored PubMed-derived 5.6% to current FDA label-confirmed 23%.",
    },
    "Mogamulizumab": {
        "ada_value": "Among 313 patients treated with POTELIGEO and tested for antibodies, 44 (14.1%) tested positive for anti-mogamulizumab-kpkc antibodies. There was no identified clinically significant effect on pharmacokinetics, safety, or effectiveness, and there were no positive neutralizing antibody responses.",
        "ada_value_display": "14.1% anti-mogamulizumab antibodies (44/313); 0% neutralizing",
        "ada_first_pct": 14.1,
        "nab_pct": "0% / no positive neutralizing antibody responses",
        "assay_platform": "ADA and neutralizing antibody assays (label; method-dependent)",
        "pk_efficacy_impact": "No identified clinically significant effect of ADA on PK, safety, or effectiveness.",
        "evidence_source": "FDA POTELIGEO prescribing information, Immunogenicity section",
        "citation_urls": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761051s018lbl.pdf",
        "ada_source_url_primary": "https://www.accessdata.fda.gov/drugsatfda_docs/label/2025/761051s018lbl.pdf",
        "ada_source_type_curated": "fda_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity: among 313 tested POTELIGEO-treated patients, 44 (14.1%) were ADA-positive; no clinically significant PK/safety/effectiveness effect; no positive neutralizing antibody responses.",
        "verify_note": "Replaced prior 3.9% (10/258) value with current label-confirmed 14.1% (44/313).",
    },
    "Muromonab-CD3": {
        "ada_value": "Retrieved label/review sources state that neutralizing antibodies to ORTHOCLONE OKT3 can develop and that before concomitant cyclosporine use the majority of patients developed anti-muromonab-CD3 antibodies, but no precise 50% numeric incidence was confirmed in retrievable text.",
        "ada_value_display": "Anti-muromonab antibodies reported; precise numeric incidence not stated",
        "ada_first_pct": pd.NA,
        "nab_pct": "Neutralizing antibodies can develop; exact incidence not stated",
        "assay_platform": "Not stated",
        "pk_efficacy_impact": "Neutralizing antibodies may block OKT3 binding and limit repeated courses of therapy.",
        "evidence_source": "Orthoclone OKT3 label and Drugs review text",
        "citation_urls": "https://www.drugs.com/pro/orthoclone-okt3.html; https://link.springer.com/article/10.2165/00003495-198937060-00004",
        "ada_source_url_primary": "https://www.drugs.com/pro/orthoclone-okt3.html",
        "ada_source_type_curated": "drug_label_or_monograph",
        "ada_has_text_evidence": True,
        "ada_source_section": "Label/review: reappearance of CD3-positive cells attributed to neutralizing antibodies; before concomitant cyclosporine, the majority of patients developed anti-muromonab-CD3 antibodies. No precise 50% incidence was stated.",
        "verify_note": "Cleared prior 50.0% value because retrieved sources supported qualitative high immunogenicity but not a precise percentage.",
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
