"""One-off: realign 15 confirmed_p70 rows to primary labels (DailyMed SPL / PMC).

Run from repo root:
  python scripts/_patch_ada_p70_evidence_15.py
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv"

# DailyMed drugInfo base
DM = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid="

PATCHES: dict[str, dict] = {
    "Lanadelumab": {
        "ada_first_pct": "12.0",
        "ada_value_display": "12% (Trial 1: 10 of lanadelumab-flyo-treated patients; 26-week period; US PI §12.6)",
        "citation_urls": DM + "15f99d8c-efe7-4f7d-aa20-0d0f1e30c6e8",
        "ada_source_url_primary": DM + "15f99d8c-efe7-4f7d-aa20-0d0f1e30c6e8",
        "ada_source_pmids": "",
        "evidence_source": "US prescribing information (TAKHZYRO; DailyMed SPL §12.6)",
        "ada_evidence_chain_excerpt": (
            "## Lanadelumab ADA evidence (US PI, DailyMed SPL)\n\n"
            "### Data Summary\n"
            "Section 12.6 (Immunogenicity) states that in Trial 1 (adults and pediatrics ≥12 y), "
            "**10 (12%)** lanadelumab-flyo-treated patients had at least one ADA-positive sample during the 26-week period "
            "(vs **2 (5%)** placebo-treated patients); titers were low and several responses were transient.\n\n"
            "### Source\n"
            "NIH DailyMed SPL for TAKHZYRO (lanadelumab-flyo), Section 12.6.\n\n"
            "---\n"
            "**Master panel ada_value_display (verbatim):** "
            "12% (Trial 1: 10 of lanadelumab-flyo-treated patients; 26-week period; US PI §12.6)\n"
        ),
    },
    "Nirsevimab": {
        "ada_first_pct": "5.0",
        "ada_value_display": "5% (Trial 04, Day 361, 95/1778 ADA-positive); 3.3% (Trial 03, Day 361, 16/492)",
        "citation_urls": DM + "2f08fa60-f674-432d-801b-1f9514bd9b39",
        "ada_source_url_primary": DM + "2f08fa60-f674-432d-801b-1f9514bd9b39",
        "ada_source_pmids": "",
        "evidence_source": "US prescribing information (BEYFORTUS; DailyMed SPL §12.6)",
        "ada_evidence_chain_excerpt": (
            "## Nirsevimab ADA evidence (US PI, DailyMed SPL)\n\n"
            "### Data Summary\n"
            "Section 12.6 reports ADA at Day 361 after the recommended dose: **3.3% (16/492)** in Trial 03 and "
            "**5% (95/1778)** in Trial 04 (with neutralizing and anti-YTE subsets described in the label).\n\n"
            "### Source\n"
            "NIH DailyMed SPL for BEYFORTUS (nirsevimab-alip), Section 12.6.\n\n"
            "---\n"
            "**Master panel ada_value_display (verbatim):** "
            "5% (Trial 04, Day 361, 95/1778 ADA-positive); 3.3% (Trial 03, Day 361, 16/492)\n"
        ),
    },
    "Concizumab": {
        "ada_first_pct": "22.2",
        "ada_value_display": "22.2% (71/320 treated patients; anticoncizumab-mtci antibodies; US PI §12.6)",
        "citation_urls": DM + "156f6404-1f6f-417f-bcf8-f07a27a82cc1",
        "ada_source_url_primary": DM + "156f6404-1f6f-417f-bcf8-f07a27a82cc1",
        "ada_source_pmids": "",
        "evidence_source": "US prescribing information (ALHEMO; DailyMed SPL §12.6)",
        "ada_evidence_chain_excerpt": (
            "## Concizumab ADA evidence (US PI, DailyMed SPL)\n\n"
            "### Data Summary\n"
            "Section 12.6 states that across five trials, **71 of 320** treated patients (**22.2%**) developed "
            "anticoncizumab-mtci antibodies; among ADA-positive patients, **25.4%** had neutralizing antibodies.\n\n"
            "### Source\n"
            "NIH DailyMed SPL for ALHEMO (concizumab-mtci), Section 12.6.\n\n"
            "---\n"
            "**Master panel ada_value_display (verbatim):** "
            "22.2% (71/320 treated patients; anticoncizumab-mtci antibodies; US PI §12.6)\n"
        ),
    },
    "Eptinezumab": {
        "ada_first_pct": "20.6",
        "ada_value_display": (
            "20.6% (Study 1, 92/447); 18.3% (Study 2, 129/706); 18% (open-label 23/128) anti-eptinezumab antibodies (US PI §12.6)"
        ),
        "citation_urls": DM + "79065861-6aa5-4d1f-829f-3a6471286b36",
        "ada_source_url_primary": DM + "79065861-6aa5-4d1f-829f-3a6471286b36",
        "ada_source_pmids": "",
        "evidence_source": "US prescribing information (VYEPTI; DailyMed SPL §12.6)",
        "ada_evidence_chain_excerpt": (
            "## Eptinezumab ADA evidence (US PI, DailyMed SPL)\n\n"
            "### Data Summary\n"
            "Section 12.6: with VYEPTI 100 or 300 mg q3mo, anti-eptinezumab-jjmr antibody incidence was "
            "**20.6% (92/447)** in Study 1 (up to 56 weeks), **18.3% (129/706)** in Study 2 (up to 32 weeks), and "
            "**18% (23/128)** in an open-label study (up to 84 weeks), with neutralizing subsets reported in the label.\n\n"
            "### Source\n"
            "NIH DailyMed SPL for VYEPTI (eptinezumab-jjmr), Section 12.6.\n\n"
            "---\n"
            "**Master panel ada_value_display (verbatim):** "
            "20.6% (Study 1, 92/447); 18.3% (Study 2, 129/706); 18% (open-label 23/128) anti-eptinezumab antibodies (US PI §12.6)\n"
        ),
    },
    "Faricimab": {
        "ada_first_pct": "10.0",
        "ada_value_display": "8% to 10.4% (treatment-emergent anti-faricimab antibodies after dosing; US PI §12.6)",
        "citation_urls": DM + "04cc9ef7-c02a-4e92-a655-0062674e8487",
        "ada_source_url_primary": DM + "04cc9ef7-c02a-4e92-a655-0062674e8487",
        "ada_source_pmids": "",
        "evidence_source": "US prescribing information (VABYSMO; DailyMed SPL §12.6)",
        "ada_evidence_chain_excerpt": (
            "## Faricimab ADA evidence (US PI, DailyMed SPL)\n\n"
            "### Data Summary\n"
            "Section 12.6: pretreatment anti-faricimab antibodies ~0.8–1.8%; after initiation of dosing, "
            "treatment-emergent antibodies were approximately **8%** to **10.4%** across nAMD/DME/RVO studies.\n\n"
            "### Source\n"
            "NIH DailyMed SPL for VABYSMO (faricimab), Section 12.6.\n\n"
            "---\n"
            "**Master panel ada_value_display (verbatim):** "
            "8% to 10.4% (treatment-emergent anti-faricimab antibodies after dosing; US PI §12.6)\n"
        ),
    },
    "Fremanezumab": {
        "ada_first_pct": "0.4",
        "ada_value_display": "0.4% (6/1701; 3-month placebo-controlled adult studies; US PI §12.6)",
        "citation_urls": DM + "98e344ea-5916-4947-b6f2-4a76ccc04b6b",
        "ada_source_url_primary": DM + "98e344ea-5916-4947-b6f2-4a76ccc04b6b",
        "ada_source_pmids": "",
        "evidence_source": "US prescribing information (AJOVY; DailyMed SPL §12.6)",
        "ada_evidence_chain_excerpt": (
            "## Fremanezumab ADA evidence (US PI, DailyMed SPL)\n\n"
            "### Data Summary\n"
            "Section 12.6: in 3-month placebo-controlled adult studies, treatment-emergent ADAs were observed in "
            "**0.4% (6 of 1701)** AJOVY-treated patients (one patient with neutralizing antibodies at Day 84).\n\n"
            "### Source\n"
            "NIH DailyMed SPL for AJOVY (fremanezumab-vfrm), Section 12.6.\n\n"
            "---\n"
            "**Master panel ada_value_display (verbatim):** "
            "0.4% (6/1701; 3-month placebo-controlled adult studies; US PI §12.6)\n"
        ),
    },
    "Itolizumab": {
        "ada_first_pct": "15.75",
        "ada_value_display": "15.75% (antidrug antibodies; phase III psoriasis cohort per Krupashankar et al. 2014, cited in PMC5527725)",
        "citation_urls": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5527725/; https://pubmed.ncbi.nlm.nih.gov/24703722/",
        "ada_source_url_primary": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5527725/",
        "ada_source_pmids": "24703722",
        "evidence_source": "Open-access review citing Krupashankar et al., JAAD 2014 (PMID 24703722)",
        "ada_evidence_chain_excerpt": (
            "## Itolizumab ADA evidence (published clinical literature)\n\n"
            "### Data Summary\n"
            "Indian J Dermatol review (PMC5527725) summarizing Krupashankar et al. phase III plaque psoriasis data: "
            "antidrug antibodies were reported in **15.75%** of patients, without established clinical correlation to "
            "efficacy or adverse events in that summary.\n\n"
            "### Source\n"
            "PMC5527725; primary trial report PMID 24703722 (JAAD 2014).\n\n"
            "---\n"
            "**Master panel ada_value_display (verbatim):** "
            "15.75% (antidrug antibodies; phase III psoriasis cohort per Krupashankar et al. 2014, cited in PMC5527725)\n"
        ),
    },
    "Ixekizumab": {
        "ada_first_pct": "22.0",
        "ada_value_display": (
            "22% (approx.; plaque psoriasis adults, recommended regimen, antibodies by 60 weeks; US PI §6.2)"
        ),
        "citation_urls": DM + "ac96658a-d7dc-4c7c-8928-2adcdf4318b2",
        "ada_source_url_primary": DM + "ac96658a-d7dc-4c7c-8928-2adcdf4318b2",
        "ada_source_pmids": "",
        "evidence_source": "US prescribing information (TALTZ; DailyMed SPL §6.2 Immunogenicity)",
        "ada_evidence_chain_excerpt": (
            "## Ixekizumab ADA evidence (US PI, DailyMed SPL)\n\n"
            "### Data Summary\n"
            "Section 6.2 (Immunogenicity): by Week 12 ~9% of adult plaque-psoriasis subjects on TALTZ q2w developed "
            "antibodies; **approximately 22%** developed antibodies to ixekizumab during the **60-week** treatment period "
            "at the recommended dosing regimen (neutralizing antibodies ~10% of those seroconverters, ~2% of all treated).\n\n"
            "### Source\n"
            "NIH DailyMed SPL for TALTZ (ixekizumab), Section 6.2.\n\n"
            "---\n"
            "**Master panel ada_value_display (verbatim):** "
            "22% (approx.; plaque psoriasis adults, recommended regimen, antibodies by 60 weeks; US PI §6.2)\n"
        ),
    },
    "Lecanemab": {
        "ada_first_pct": "3.4",
        "ada_value_display": "3.4% (30/883; treatment-emergent anti-lecanemab-irmb antibodies, IV 18 months, Study 2; US PI §12.6)",
        "citation_urls": DM + "9d1ff786-e577-410a-a273-c4d7d0e4e975",
        "ada_source_url_primary": DM + "9d1ff786-e577-410a-a273-c4d7d0e4e975",
        "ada_source_pmids": "",
        "evidence_source": "US prescribing information (LEQEMBI; DailyMed SPL §12.6)",
        "ada_evidence_chain_excerpt": (
            "## Lecanemab ADA evidence (US PI, DailyMed SPL)\n\n"
            "### Data Summary\n"
            "Section 12.6: during 18 months in Study 2, **3.4% (30/883)** of patients on LEQEMBI 10 mg/kg q2w developed "
            "treatment-emergent anti-lecanemab-irmb antibodies (**1.9%** neutralizing).\n\n"
            "### Source\n"
            "NIH DailyMed SPL for LEQEMBI (lecanemab-irmb), Section 12.6.\n\n"
            "---\n"
            "**Master panel ada_value_display (verbatim):** "
            "3.4% (30/883; treatment-emergent anti-lecanemab-irmb antibodies, IV 18 months, Study 2; US PI §12.6)\n"
        ),
    },
    "Naxitamab": {
        "ada_first_pct": "8.0",
        "ada_value_display": "8% (Study 201: 2/24 ADA-positive after DANYELZA; US PI §6.2)",
        "citation_urls": DM + "29a80c6b-8bad-4650-8c7f-f18490c868ec",
        "ada_source_url_primary": DM + "29a80c6b-8bad-4650-8c7f-f18490c868ec",
        "ada_source_pmids": "",
        "evidence_source": "US prescribing information (DANYELZA; DailyMed SPL §6.2 Immunogenicity)",
        "ada_evidence_chain_excerpt": (
            "## Naxitamab ADA evidence (US PI, DailyMed SPL)\n\n"
            "### Data Summary\n"
            "Section 6.2 (Immunogenicity): in Study 201, **2 of 24 (8%)** patients tested positive for ADA after DANYELZA; "
            "Study 12-230 and assay caveats are described in the same section.\n\n"
            "### Source\n"
            "NIH DailyMed SPL for DANYELZA (naxitamab-gqgk), Section 6.2.\n\n"
            "---\n"
            "**Master panel ada_value_display (verbatim):** "
            "8% (Study 201: 2/24 ADA-positive after DANYELZA; US PI §6.2)\n"
        ),
    },
    "Ozoralizumab": {
        "ada_first_pct": "29.2",
        "ada_value_display": (
            "29.2% (OHZORA 80 mg+MTX TI/TB ADA by week 52); 30.8% (OHZORA 30 mg+MTX); "
            "46.8%/39.1% (NATSUZORA 30/80 mg without MTX) — Arthritis Res Ther 2023 (PMC10099673)"
        ),
        "citation_urls": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10099673/",
        "ada_source_url_primary": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10099673/",
        "ada_source_pmids": "37055803",
        "evidence_source": "Peer-reviewed publication: Arthritis Res Ther. 2023;25:60. PMC10099673 / PMID 37055803",
        "ada_evidence_chain_excerpt": (
            "## Ozoralizumab ADA evidence (peer-reviewed PK/immunogenicity analysis)\n\n"
            "### Data Summary\n"
            "Takeuchi et al. (Arthritis Res Ther 2023, PMC10099673) report week-52 TI/TB ADA incidence: OHZORA (+MTX) "
            "**30.8% (n=44)** on OZR 30 mg and **29.2% (n=45)** on OZR 80 mg; NATSUZORA (no MTX) **46.8% (n=44)** on 30 mg and "
            "**39.1% (n=18)** on 80 mg (definitions: TB-positive or TI-positive from baseline to week 52, per publication).\n\n"
            "### Source\n"
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC10099673/ (open access).\n\n"
            "---\n"
            "**Master panel ada_value_display (verbatim):** "
            "29.2% (OHZORA 80 mg+MTX TI/TB ADA by week 52); 30.8% (OHZORA 30 mg+MTX); "
            "46.8%/39.1% (NATSUZORA 30/80 mg without MTX) — Arthritis Res Ther 2023 (PMC10099673)\n"
        ),
    },
    "Ravulizumab": {
        "ada_first_pct": "0.5",
        "ada_value_display": "0.5% (1/219 PNH patients; treatment-emergent antibodies; US PI §12.6)",
        "citation_urls": DM + "a9a590d9-0217-43c7-908d-e62a71279791",
        "ada_source_url_primary": DM + "a9a590d9-0217-43c7-908d-e62a71279791",
        "ada_source_pmids": "",
        "evidence_source": "US prescribing information (ULTOMIRIS; DailyMed SPL §12.6)",
        "ada_evidence_chain_excerpt": (
            "## Ravulizumab ADA evidence (US PI, DailyMed SPL)\n\n"
            "### Data Summary\n"
            "Section 12.6: treatment-emergent antibodies to ravulizumab-cwvz were detected in **1 of 219 (0.5%)** PNH patients "
            "and **1 of 71 (1.4%)** aHUS patients; gMG and NMOSD cohorts reported no treatment-emergent antibodies in the label excerpt. "
            "Assay interference by serum drug may underestimate incidence.\n\n"
            "### Source\n"
            "NIH DailyMed SPL for ULTOMIRIS (ravulizumab-cwvz), Section 12.6.\n\n"
            "---\n"
            "**Master panel ada_value_display (verbatim):** "
            "0.5% (1/219 PNH patients; treatment-emergent antibodies; US PI §12.6)\n"
        ),
    },
    "Retifanlimab": {
        "ada_first_pct": "2.8",
        "ada_value_display": (
            "0% (SCAC POD1UM-303/202); 2.8% (3/106 MCC POD1UM-201; treatment-emergent ADAs; US PI §12.6)"
        ),
        "citation_urls": DM + "109648d0-d30a-42fc-8273-39cb1540a751",
        "ada_source_url_primary": DM + "109648d0-d30a-42fc-8273-39cb1540a751",
        "ada_source_pmids": "",
        "evidence_source": "US prescribing information (ZYNYZ; DailyMed SPL §12.6)",
        "ada_evidence_chain_excerpt": (
            "## Retifanlimab ADA evidence (US PI, DailyMed SPL)\n\n"
            "### Data Summary\n"
            "Section 12.6: **None** of SCAC patients in POD1UM-303 (n=153) or POD1UM-202 (n=94) tested positive for "
            "treatment-emergent retifanlimab ADAs. In POD1UM-201 (MCC; n=106), treatment-emergent ADAs were "
            "**2.8% (3/106)** (neutralizing antibodies in 2 of 3).\n\n"
            "### Source\n"
            "NIH DailyMed SPL for ZYNYZ (retifanlimab-dlwr), Section 12.6.\n\n"
            "---\n"
            "**Master panel ada_value_display (verbatim):** "
            "0% (SCAC POD1UM-303/202); 2.8% (3/106 MCC POD1UM-201; treatment-emergent ADAs; US PI §12.6)\n"
        ),
    },
    "Sacituzumab": {
        "ada_first_pct": "1.1",
        "ada_value_display": "1.1% (9/785; antibodies to sacituzumab govitecan; median ~4 months exposure; US PI §12.6)",
        "citation_urls": DM + "57a597d2-03f0-472e-b148-016d7169169d",
        "ada_source_url_primary": DM + "57a597d2-03f0-472e-b148-016d7169169d",
        "ada_source_pmids": "",
        "evidence_source": "US prescribing information (TRODELVY; DailyMed SPL §12.6)",
        "ada_evidence_chain_excerpt": (
            "## Sacituzumab govitecan ADA evidence (US PI, DailyMed SPL)\n\n"
            "### Data Summary\n"
            "Section 12.6: across clinical studies (median ~4 months), **9 (1.1%) of 785** TRODELVY-treated patients "
            "developed antibodies to sacituzumab govitecan (**0.8%** with neutralizing activity).\n\n"
            "### Source\n"
            "NIH DailyMed SPL for TRODELVY (sacituzumab govitecan-hziy), Section 12.6.\n\n"
            "---\n"
            "**Master panel ada_value_display (verbatim):** "
            "1.1% (9/785; antibodies to sacituzumab govitecan; median ~4 months exposure; US PI §12.6)\n"
        ),
    },
    "Tarlatamab": {
        "ada_first_pct": "8.0",
        "ada_value_display": "8% (36/445; treatment-emergent ADA; DeLLphi-300/301/304; US PI §12.6)",
        "citation_urls": DM + "1e7b6163-5d83-42ea-82c9-cf7620cdc782",
        "ada_source_url_primary": DM + "1e7b6163-5d83-42ea-82c9-cf7620cdc782",
        "ada_source_pmids": "",
        "evidence_source": "US prescribing information (IMDELLTRA; DailyMed SPL §12.6)",
        "ada_evidence_chain_excerpt": (
            "## Tarlatamab ADA evidence (US PI, DailyMed SPL)\n\n"
            "### Data Summary\n"
            "Section 12.6: during up to 3-year evaluation in DeLLphi-300/301/304, **8% (36/445)** of patients receiving "
            "the recommended step-up regimen of IMDELLTRA developed treatment-emergent ADA (**38%** of those with "
            "neutralizing antibody assessment in DeLLphi-301/304 developed neutralizing antibodies).\n\n"
            "### Source\n"
            "NIH DailyMed SPL for IMDELLTRA (tarlatamab-dlle), Section 12.6.\n\n"
            "---\n"
            "**Master panel ada_value_display (verbatim):** "
            "8% (36/445; treatment-emergent ADA; DeLLphi-300/301/304; US PI §12.6)\n"
        ),
    },
}


def main() -> None:
    rows = list(csv.DictReader(MASTER.open(encoding="utf-8")))
    fields = rows[0].keys()
    n = 0
    for r in rows:
        p = PATCHES.get(r["antibody_name"])
        if not p:
            continue
        for k, v in p.items():
            r[k] = v
        n += 1
    with MASTER.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)
    print(f"Patched {n} rows in {MASTER}")


if __name__ == "__main__":
    main()
