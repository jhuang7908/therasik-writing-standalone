# {{PROJECT_TITLE}} — VH/VL Humanization Report

**Project ID:** `{{PROJECT_ID}}`  
**Report Family:** `vhvl_humanization`  
**Audience:** `internal`  
**Version:** `{{VERSION}}`  
**Date:** `{{DATE}}`  
**Target:** `{{TARGET}}`  
**Antibody Name:** `{{ANTIBODY_NAME}}`

## 1. Overview
**Species / origin:** {{SPECIES}}  
**Goal:** {{GOAL}}  
**Recommended sequence:** {{RECOMMENDED_SEQUENCE}}

## 2. Input Sequence QC
**VH sequence:** `{{VH_SEQ}}`  
**VL sequence:** `{{VL_SEQ}}`  
**Length check:** {{LENGTH_CHECK}}  
**Basic flags:** {{INPUT_QC_FLAGS}}

## 3. IMGT Segmentation
**VH:** FR1 `{{VH_FR1}}` / CDR1 `{{VH_CDR1}}` / FR2 `{{VH_FR2}}` / CDR2 `{{VH_CDR2}}` / FR3 `{{VH_FR3}}` / CDR3 `{{VH_CDR3}}` / FR4 `{{VH_FR4}}`  
**VL:** FR1 `{{VL_FR1}}` / CDR1 `{{VL_CDR1}}` / FR2 `{{VL_FR2}}` / CDR2 `{{VL_CDR2}}` / FR3 `{{VL_FR3}}` / CDR3 `{{VL_CDR3}}` / FR4 `{{VL_FR4}}`

## 4. Germline Match & Interpretation
**VH germline:** {{VH_GERMLINE}}  
**VL germline:** {{VL_GERMLINE}}  
**Identity %:** {{IDENTITY_PCT}}  
**Interpretation:** {{GERMLINE_INTERPRETATION}}

## 5. Vernier Zone Analysis
**Vernier positions:** {{VERNIER_POSITIONS}}  
**Backmutation rationale:** {{BACKMUTATION_RATIONALE}}

<!-- INTERNAL_ONLY_START -->
### Internal Vernier Notes
{{VERNIER_INTERNAL_NOTES}}
<!-- INTERNAL_ONLY_END -->

## 6. VH/VHH Hallmark Check
{{HALLMARK_CHECK}}

## 7. CMC Liabilities
**Liability list:** {{LIABILITY_LIST}}  
**Severity:** {{SEVERITY}}  
**Mitigation note:** {{CMC_MITIGATION}}

## 8. Immunogenicity
**IEDB score / summary:** {{IEDB_SCORE}}  
**T-cell epitopes:** {{T_CELL_EPITOPES}}  
**Interpretation:** {{IMMUNO_INTERPRETATION}}

## 9. Developability
**pI:** {{PI}}  
**GRAVY:** {{GRAVY}}  
**Instability index:** {{INSTABILITY_INDEX}}  
**Developability interpretation:** {{DEVELOPABILITY_NOTE}}

## 10. Mutation Tiers (0-3)
**Tier 0:** {{TIER0}}  
**Tier 1:** {{TIER1}}  
**Tier 2:** {{TIER2}}  
**Tier 3:** {{TIER3}}

## 11. Three Final Sequences
**Seq1:** `{{SEQ1}}`  
**Seq2:** `{{SEQ2}}`  
**Seq3:** `{{SEQ3}}`

## 12. Optional Mutation Menu
{{OPTIONAL_MENU}}

## 13. Evidence Traceability & Trust Level
**Evidence source:** {{EVIDENCE_SOURCE}}  
**Verification tier:** {{ADA_TIER}}  
**Reference IDs:** {{REFERENCE_IDS}}

## 14. Methodology Reliability Statement
**Benchmark reference:** {{BENCHMARK_REFERENCE}}  
**Confidence statement:** {{CONFIDENCE_STATEMENT}}

<!-- INTERNAL_ONLY_START -->
### Internal Method Details
**Pipeline:** {{PIPELINE}}  
**Scripts / envs:** {{SCRIPTS_AND_ENVS}}  
**Raw artifacts:** {{RAW_ARTIFACTS}}
<!-- INTERNAL_ONLY_END -->

## 15. Final Recommendations
**Recommended sequence:** {{RECOMMENDED_SEQUENCE}}  
**Why:** {{RATIONALE}}  
**Next steps:** {{NEXT_STEPS}}

## 16. Glossary
{{GLOSSARY}}

<!-- INTERNAL_ONLY_START -->
## Appendix
{{APPENDIX_INTERNAL}}
<!-- INTERNAL_ONLY_END -->
