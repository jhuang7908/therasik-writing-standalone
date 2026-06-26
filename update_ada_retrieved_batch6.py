import pandas as pd


ADA_PATH = "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"


updates = {
    "Abrilumab": {
        "ada_value_display": "Anti-abrilumab binding antibodies: 2/234 treated patients (0.9%); no neutralizing antibodies detected",
        "ada_first_pct": 0.9,
        "ada_value": "0.9%",
        "trial_n_ada_evaluated": "234 abrilumab-treated patients with post-baseline ADA evaluation",
        "nab_pct": "0%",
        "route_curated": "SC",
        "dose_mg": "7, 21, 70, or 210 mg",
        "dose_freq": "7/21/70 mg on day 1, weeks 2 and 4, then every 4 weeks; 210 mg on day 1 only in induction",
        "assay_platform": "ECL",
        "assay_method": "Validated electrochemiluminescent anti-abrilumab binding antibody assays; cell-based neutralizing antibody assay for binding-positive samples",
        "pk_efficacy_impact": "Two abrilumab-treated patients were binding-antibody positive; no neutralizing antibodies detected.",
        "evidence_source": "Gastroenterology 2019 abrilumab phase 2b ulcerative colitis trial",
        "citation_urls": "https://doi.org/10.1053/j.gastro.2018.11.035",
        "ada_source_url_primary": "https://doi.org/10.1053/j.gastro.2018.11.035",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Immunogenicity",
        "ada_evidence_chain_excerpt": "Post-baseline anti-abrilumab antibody evaluation from 348 patients indicated 1 patient in the 70-mg group and 1 in the 210-mg group were positive for anti-abrilumab-binding antibodies. No neutralizing antibodies were detected.",
        "verify_note": "Batch6 reverse retrieval: replaced unsourced ~1-3% summary with article-confirmed 2/234 treated ADA-positive result.",
    },
    "Arcitumomab": {
        "ada_value_display": "HAMA to antibody fragment: <1% of evaluated patients",
        "ada_first_pct": pd.NA,
        "ada_value": "<1%",
        "trial_n_ada_evaluated": "over 400",
        "nab_pct": "Not applicable / not reported",
        "route_curated": "IV",
        "dose_mg": "1 mg arcitumomab labeled with 20-30 mCi Tc-99m",
        "dose_freq": "single diagnostic imaging dose",
        "assay_platform": "ELISA",
        "assay_method": "Immunomedics ELISA HAMA assessment for mouse monoclonal antibody fragments",
        "pk_efficacy_impact": "Package insert warns HAMA may interfere with murine antibody-based immunoassays and alter clearance/biodistribution; fewer than 1% showed HAMA elevation after CEA-Scan.",
        "evidence_source": "CEA-Scan arcitumomab package insert",
        "citation_urls": "https://pharmacyce.unm.edu/nuclear_program/neolibrary/libraryfiles/package_inserts/cea-scan.pdf",
        "ada_source_url_primary": "https://pharmacyce.unm.edu/nuclear_program/neolibrary/libraryfiles/package_inserts/cea-scan.pdf",
        "ada_source_type_curated": "product_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "Clinical pharmacology; Heterologous Protein Administration; Adverse Reactions",
        "ada_evidence_chain_excerpt": "Over 400 patients who have received CEA-Scan have been evaluated for HAMA by ELISA methodology. Fewer than 1% of the patients showed an elevation of HAMA levels to fragment after being injected with CEA-Scan.",
        "verify_note": "Batch6 reverse retrieval: replaced unsourced IDC 10% with package-insert-confirmed <1% HAMA-to-fragment rate.",
    },
    "Batoclimab": {
        "ada_value_display": "Newly emerged anti-batoclimab antibodies: 6.0%",
        "ada_first_pct": 6.0,
        "ada_value": "6.0%",
        "trial_n_ada_evaluated": "67 batoclimab-treated patients in phase 3 trial",
        "nab_pct": "Not reported in retrieved article",
        "route_curated": "SC",
        "dose_mg": "680 mg",
        "dose_freq": "weekly x6 per treatment cycle",
        "assay_platform": "MSD ECL",
        "assay_method": "Meso Scale Discovery electrochemiluminescence antibatoclimab antibody assay; neutralizing antibodies tested only in ADA-positive patients",
        "pk_efficacy_impact": "Clinical relevance requires further investigation; phase 3 article reports lower newly emerged ADA rate than efgartigimod comparison.",
        "evidence_source": "JAMA Neurology 2024 batoclimab generalized myasthenia gravis phase 3 trial",
        "citation_urls": "https://doi.org/10.1001/jamaneurol.2024.0044; https://pmc.ncbi.nlm.nih.gov/articles/PMC10913013/",
        "ada_source_url_primary": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10913013/",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Pharmacokinetics, Pharmacodynamics, and Immunogenicity; Discussion",
        "ada_evidence_chain_excerpt": "The rate of newly emerged antibatoclimab antibodies after batoclimab treatment (6.0%) in this trial was lower than that reported for antidrug antibody with efgartigimod (20%).",
        "verify_note": "Batch6 reverse retrieval: replaced unsourced 0% with article-confirmed 6.0% newly emerged anti-batoclimab antibody rate.",
    },
    "Mavrilimumab": {
        "ada_value_display": "Detectable ADA: 20/158 treated patients (12.7%); high-titer ADA: 10/158 treated patients (6.3%)",
        "ada_first_pct": 12.7,
        "ada_value": "12.7% detectable ADA; 6.3% high-titer ADA",
        "trial_n_ada_evaluated": "158 mavrilimumab-treated patients",
        "nab_pct": "Not reported in retrieved article",
        "route_curated": "SC",
        "dose_mg": "10, 30, 50, or 100 mg",
        "dose_freq": "every other week for 12 weeks",
        "assay_platform": "ECL",
        "assay_method": "Two-step electrochemiluminescence screening immunoassay and confirmatory inhibition assay",
        "pk_efficacy_impact": "ADA titers were generally low and transient; high-titer ADA was associated with reduced PK exposure but no observed correlation with tolerability or tachyphylaxis.",
        "evidence_source": "Ann Rheum Dis 2013 mavrilimumab EARTH rheumatoid arthritis phase 2 trial",
        "citation_urls": "https://doi.org/10.1136/annrheumdis-2012-202450; https://pmc.ncbi.nlm.nih.gov/articles/PMC3756523/",
        "ada_source_url_primary": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3756523/",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Pharmacokinetics and Immunogenicity",
        "ada_evidence_chain_excerpt": "During the study, 23 subjects developed detectable ADA (3 placebo and 20 treated). High-titre ADAs were reported in 10 mavrilimumab (6.3%) subjects.",
        "verify_note": "Batch6 reverse retrieval: replaced unsourced IDC 18% with article-confirmed 20/158 detectable ADA and 10/158 high-titer ADA.",
    },
}


def main() -> None:
    df = pd.read_csv(ADA_PATH)

    for col in set().union(*(entry.keys() for entry in updates.values())):
        if col not in df.columns:
            df[col] = pd.NA
        df[col] = df[col].astype("object")

    for antibody_name, data in updates.items():
        mask = df["antibody_name"].astype(str).str.casefold() == antibody_name.casefold()
        if not mask.any():
            print(f"MISSING {antibody_name}")
            continue
        for col, val in data.items():
            df.loc[mask, col] = val
        print(f"Updated {antibody_name}")

    df.to_csv(ADA_PATH, index=False)


if __name__ == "__main__":
    main()
