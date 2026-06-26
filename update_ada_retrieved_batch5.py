import pandas as pd


ADA_PATH = "data/immunogenicity_knowledge_base/master/ada_master_328_final_comprehensive.csv"


updates = {
    "Farletuzumab": {
        "ada_value_display": "ADA positive: 4/15 (26.7%)",
        "ada_first_pct": 26.7,
        "ada_value": "26.7%",
        "trial_n_ada_evaluated": "15",
        "nab_pct": "Not reported in retrieved article",
        "route_curated": "IV",
        "dose_mg": "2.5 mg/kg",
        "dose_freq": "weekly; maintenance 2.5 mg/kg weekly or 7.5 mg/kg every 3 weeks",
        "assay_platform": "Validated ADA assay",
        "assay_method": "FAR-specific ADA assay; surrogate positive control sensitivity ~0.5 ng/mL",
        "pk_efficacy_impact": "Four of 15 patients tested ADA-positive; potential immunogenic reactions in two patients; no farletuzumab-related grade 3-4 AEs reported.",
        "evidence_source": "Gynecol Oncol 2016 farletuzumab/carboplatin/PLD phase 1b article",
        "citation_urls": "https://doi.org/10.1016/j.ygyno.2015.11.031",
        "ada_source_url_primary": "https://doi.org/10.1016/j.ygyno.2015.11.031",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Anti-drug antibodies; Safety",
        "ada_evidence_chain_excerpt": "Four of 15 patients (26.7%) tested positive for ADA at least once while on study.",
        "verify_note": "Batch5 reverse retrieval: replaced discontinued_no_public_ada_data / 0% with article-confirmed 4/15 ADA-positive result.",
    },
    "Clivatuzumab": {
        "ada_value_display": "HAHA elevated titer: 1/32 (3.1%)",
        "ada_first_pct": 3.1,
        "ada_value": "3.1%",
        "trial_n_ada_evaluated": "32",
        "nab_pct": "Not reported in retrieved article",
        "route_curated": "IV",
        "dose_mg": "Y-90-hPAM4 6.5-15.0 mCi/m2 weekly x3; MTD 12.0 mCi/m2 weekly x3",
        "dose_freq": "weekly during weeks 2-4 of each 4-week cycle",
        "assay_platform": "ELISA",
        "assay_method": "Anti-hPAM4 antibody response (HAHA) by ELISA at baseline and monthly intervals",
        "pk_efficacy_impact": "One of 32 evaluable patients developed an elevated HAHA titer of uncertain clinical significance.",
        "evidence_source": "Cancer 2012 clivatuzumab tetraxetan phase 1 trial",
        "citation_urls": "https://doi.org/10.1002/cncr.27592",
        "ada_source_url_primary": "https://doi.org/10.1002/cncr.27592",
        "ada_source_type_curated": "peer_reviewed_article",
        "ada_has_text_evidence": True,
        "ada_source_section": "Study assessments; Immunogenicity",
        "ada_evidence_chain_excerpt": "Of the 32 treated patients who had adequate samples for HAHA assessment, only 1 patient developed an elevated titer of uncertain clinical significance.",
        "verify_note": "Batch5 reverse retrieval: replaced legacy 2.0% with article-confirmed 1/32 HAHA result.",
    },
    "Idarucizumab": {
        "ada_value_display": "Treatment-emergent anti-idarucizumab antibodies: 2% of patients; pre-existing cross-reactive antibodies: 4% of patients",
        "ada_first_pct": 2.0,
        "ada_value": "2% treatment-emergent; 4% pre-existing cross-reactive",
        "trial_n_ada_evaluated": "501 patients",
        "nab_pct": "Not separately reported in label",
        "route_curated": "IV",
        "dose_mg": "5 g",
        "dose_freq": "single reversal dose; additional 5 g may be considered in limited circumstances",
        "assay_platform": "ECL",
        "assay_method": "Electro-chemiluminescence assay for antibodies cross-reacting with idarucizumab",
        "pk_efficacy_impact": "Label reports no impact on pharmacokinetics, reversal effect, or hypersensitivity reactions for pre-existing low-titer antibodies.",
        "evidence_source": "DailyMed PRAXBIND prescribing information",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=c7400f8a-dcf4-a6df-6d07-983081b1bf34",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=c7400f8a-dcf4-a6df-6d07-983081b1bf34",
        "ada_source_type_curated": "FDA_DailyMed_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "6.2 Immunogenicity",
        "ada_evidence_chain_excerpt": "Treatment-emergent possibly persisting anti-idarucizumab antibodies with low titers were observed in 2% (8/501) of patients treated with idarucizumab.",
        "verify_note": "Batch5 reverse retrieval: corrected legacy 12.1% summary to label-confirmed 2% treatment-emergent patient ADA and 4% pre-existing cross-reactive antibodies.",
    },
    "Ibritumomab tiuxetan": {
        "ada_value_display": "HAMA/HACA evidence: 11/446 (2.5%); post-treatment HAMA/HACA in 6 patients",
        "ada_first_pct": 2.5,
        "ada_value": "2.5% overall HAMA/HACA evidence; 6 post-treatment cases",
        "trial_n_ada_evaluated": "446",
        "nab_pct": "Not reported in label",
        "route_curated": "IV",
        "dose_mg": "Y-90 Zevalin 0.3-0.4 mCi/kg, max 32 mCi",
        "dose_freq": "single therapeutic regimen with rituximab on day 1 and day 7/8/9",
        "assay_platform": "HAMA/HACA assay",
        "assay_method": "HAMA and HACA response testing across 8 clinical studies",
        "pk_efficacy_impact": "Label does not assign a clinical impact to HAMA/HACA positivity.",
        "evidence_source": "DailyMed ZEVALIN prescribing information",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=25d367dc-da65-44c9-a844-1bf15339c285",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=25d367dc-da65-44c9-a844-1bf15339c285",
        "ada_source_type_curated": "FDA_DailyMed_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "6.3 Immunogenicity",
        "ada_evidence_chain_excerpt": "Overall, 11/446 (2.5%) had evidence of either HAMA formation (N=8) or HACA formation (N=4). Six of these patients developed HAMA/HACA after treatment with Zevalin.",
        "verify_note": "Batch5 reverse retrieval: updated legacy 2.0% to label-confirmed 11/446 (2.5%) HAMA/HACA evidence.",
    },
    "Teplizumab": {
        "ada_value_display": "Anti-teplizumab-mzwv antibodies: approximately 57%; neutralizing antibodies in 46% of ADA-positive patients",
        "ada_first_pct": 57.0,
        "ada_value": "57%",
        "trial_n_ada_evaluated": "Study TN-10 treated patients",
        "nab_pct": "46% of ADA-positive patients",
        "route_curated": "IV",
        "dose_mg": "BSA-based 14-day course: 65 to 1,030 mcg/m2/day",
        "dose_freq": "once daily for 14 consecutive days",
        "assay_platform": "ADA assay",
        "assay_method": "Anti-drug antibody and neutralizing antibody assessment in Study TN-10",
        "pk_efficacy_impact": "Label states there is insufficient information to characterize ADA effects on PK, pharmacodynamics, or effectiveness; rash incidence was higher in ADA-positive patients.",
        "evidence_source": "DailyMed TZIELD prescribing information",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=e8a39a5f-139c-4510-9777-71cbb00138fa",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=e8a39a5f-139c-4510-9777-71cbb00138fa",
        "ada_source_type_curated": "FDA_DailyMed_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "12.6 Immunogenicity",
        "ada_evidence_chain_excerpt": "Approximately 57% of TZIELD-treated patients developed anti-teplizumab-mzwv antibodies, 46% of whom developed neutralizing antibodies.",
        "verify_note": "Batch5 reverse retrieval: corrected legacy ~5% ADA note to label-confirmed approximately 57% ADA.",
    },
    "Ibalizumab": {
        "ada_value_display": "One low-titer anti-ibalizumab positive sample; denominator not stated in label",
        "ada_first_pct": pd.NA,
        "ada_value": "one low-titer positive sample; percentage not stated",
        "trial_n_ada_evaluated": "TMB-301 and TMB-202 subjects; denominator not stated in label section",
        "nab_pct": "Not reported in label",
        "route_curated": "IV",
        "dose_mg": "2,000 mg loading; 800 mg maintenance",
        "dose_freq": "loading dose followed by 800 mg every 2 weeks",
        "assay_platform": "Anti-ibalizumab antibody assay",
        "assay_method": "Anti-ibalizumab antibody testing throughout TMB-301 and TMB-202",
        "pk_efficacy_impact": "No adverse reaction or reduced efficacy was attributed to the positive sample.",
        "evidence_source": "DailyMed TROGARZO prescribing information",
        "citation_urls": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=c548ad82-9d1f-4d16-95b6-4e6106badf43",
        "ada_source_url_primary": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=c548ad82-9d1f-4d16-95b6-4e6106badf43",
        "ada_source_type_curated": "FDA_DailyMed_label",
        "ada_has_text_evidence": True,
        "ada_source_section": "12.6 Immunogenicity",
        "ada_evidence_chain_excerpt": "One sample tested positive with low titer anti-ibalizumab antibodies. No adverse reaction or reduced efficacy was attributed to the positive sample.",
        "verify_note": "Batch5 reverse retrieval: source verified qualitative low-titer positive sample; no new percentage assigned because label does not state denominator in section 12.6.",
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
