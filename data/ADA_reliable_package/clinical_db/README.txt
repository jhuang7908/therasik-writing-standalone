 ADA （ / ）
====================================

（ Antibody_Engineer_Suite ）:
  python scripts/build_clinical_ada_split_database.py

:
  - from_openclaw_20260330/reliable_merged/reliable_ada_antibodies_database_20260330_231950.json（108，）
  - sources/151_antibody_evidence_database.json（151 ； 108  170  INN）
  -  ada_merged_multisource.json（QA/17  data  supplemental_multisource）


--------
- clinical_ada_db_index.json / .csv  
  ：evidence_tier (A/B/C)、ada_status、ada 、 URL、PMID、。
- clinical_ada_db_data.json  
  ：records[<data_record_key>] = primary_record  + index_snapshot + supplemental。

Tier 
---------
 scripts/ada_tier_utils.py：
  A = PMID（//PubMed URL） FDA accessdata  ClinicalTrials.gov
  B =  https  A
  C =  A （ ada ）

skip_automatic_ada_expansion
----------------------------
   true： INN ， ADA ，。


----
   citation_urls /  PDF / ；qa/ 「 ADA」。
