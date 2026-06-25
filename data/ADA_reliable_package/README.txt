ADA （ OpenClaw ）
========================================
: 2026-03-30 

（ +  + 17 ）
--------------------------------------
  qa/ ： D:\OpenClaw_Workspace\workspace  JSON， qa/README.txt
   JSON: data/ADA_reliable_package/ada_merged_multisource.json
    : python scripts/merge_ada_multisource.py
   primary_curated（.pipeline ） supplemental（QA//real17，）。
   FDA/PMC  ADA，。

 ADA （ + ，Tier A/B/C，170 INN）
------------------------------------------------
  : python scripts/build_clinical_ada_split_database.py
  : clinical_db/
    - clinical_ada_db_index.json / clinical_ada_db_index.csv  （、、）
    - clinical_ada_db_data.json  （ evidence_chain  supplemental）
  :  reliable_merged（108）； 151 （sources/）。
   skip_automatic_ada_expansion=true， INN。
   clinical_db/README.txt

（/PMID； AI ）
------------------------------------------------
  : python scripts/build_verifiable_classified_ada_db.py
  : verifiable_classified/
    - verifiable_ada_index.json / .csv  （Tier A/B； citation_urls  pmids）
    - verifiable_ada_by_tier.json  （ Tier A / B ）
    - verifiable_ada_data.json  
    - verifiable_ada_excluded.json  （：*、Tier C ）
  : evidence_tier  A/B； https  PMID；evidence_source 「」「」。
  : 108 ，62 （ 108 reliable ）。

、
------------
from_openclaw_20260330/reliable_merged/
  - reliable_ada_antibodies_database_20260330_231950.json
    ：108 ， ada_value、source_type、evidence_chain 。
  - reliable_ada_antibodies_summary_20260330_231950.md
    （、ADA、、）。
  - reliable_ada_evidence_chains_batch_*_of_3_*.md
    （ JSON  evidence_chain ）。
  - merge_report.md
    ：151  AI  89  + 250  19 ； 62  AI 。

merge_reliable_ada_antibodies.py
  （ D:/OpenClaw_Workspace/...，）。

ada_reliable_index_20260330.csv（ scripts/export_ada_reliable_index.py ）
  ： Excel 「、、//」；URL/PMID  evidence_chain 。

、
----------------------
：
  -  ADA （evidence_chain）； FDA label URL、PMC/PubMed  PMID。
  - 「」 AI （ merge_report）。

 JSON 、：
  - （gene/moiety）、、、、、「」；
  -  evidence_chain （ FDA  Section 6.2、），。

：
  1) ：ada_value （、/、）。
  2) ： FDA ，；「 ADA 」 notes 。
  3) ：「 + ADA 」 PubMed / DailyMed / EMA EPAR 。
  4) 。

（「」）：
  JSON  68  evidence_source 「A」： evidence_chain  PMC/ URL，
  「」。， CSV  value_matches_source_verified_by_human
  ，。

、 CSV
------------------------
  python scripts/export_ada_reliable_index.py

、
----------------------------
  C:\Users\NextVivo\.openclaw\workspace\ADA
   reliable_merged  CSV。

、（「 ADA 」+ ）
------------------------------------------------------
  : data/ADA_reliable_package/curated/ada_curated_tier_A.json
   CSV:     data/ADA_reliable_package/ada_curated_tier_A.csv
    : python scripts/export_ada_tier_a_csv.py
    : python scripts/export_ada_tier_a_csv.py --omit-evidence-chain

  : scripts/build_ada_reliable_database.py

  : data/ADA_reliable_package/curated/
    - ada_curated_all_with_ada.json       ADA/
    - ada_curated_tier_A.json            Tier A：PMID（//pubmed ） FDA accessdata  ClinicalTrials.gov
    - ada_curated_tier_B.json            Tier B： https， Tier A
    - ada_curated_tier_C_needs_work.json  URL  Tier A 
    - ada_curated_needs_retrieval.json   （ evidence_quality=low  FDA PDF）
    - ada_skipped_no_ada.json             ADA 

  :
    python scripts/build_ada_reliable_database.py

  https （ Tier  + ）:
    python scripts/report_ada_tier_sources.py
    : curated/ada_tier_https_audit.json

  ： needs_retrieval  PubMed  PMID（，）:
    python scripts/build_ada_reliable_database.py --pubmed --email your@email.org

  ： ADA ；， needs_retrieval + suggested_pubmed_query，
  。

  Tier A / B ：
    - Tier A： PMID（JSON pmids 、 PMID:、 pubmed.ncbi.nlm.nih.gov/ ）
               FDA  accessdata.fda.gov， ClinicalTrials.gov。
    - Tier B： https （ PMC、、EMA ）， Tier A。
    -  URL 「 ADA 」， B； PMID/FDA/ A。
