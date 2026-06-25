# {{PROJECT_TITLE}} — Virtual Affinity Maturation Report

**Project ID:** `{{PROJECT_ID}}`  
**Report Family:** `vam`  
**Audience:** `internal`  
**Version:** `{{VERSION}}`  
**Date:** `{{DATE}}`  
**Target:** `{{TARGET}}`  
**Antibody Name:** `{{ANTIBODY_NAME}}`

## 1. Executive Summary
**Top candidate:** {{TOP_CANDIDATE}}  
**ΔΔG improvement:** {{DDG_IMPROVEMENT}}  
**Key conclusion:** {{KEY_CONCLUSION}}

## 2. Structure Quality Assessment
**Structure source:** {{STRUCTURE_SOURCE}}  
**ipTM:** {{IPTM}}  
**pLDDT interface:** {{PLDDT_INTERFACE}}  
**BSA:** {{BSA}}  
**Cluster concentration:** {{CLUSTER_CONCENTRATION}}

## 3. Interface Contact Analysis
**Contact residues:** {{CONTACT_RESIDUES}}  
**Per-residue contact count:** {{CONTACT_COUNT_PER_RESIDUE}}  
**Total BSA:** {{BSA_TOTAL}}

## 4. Mutation Scan — Tier 1 (EvoEF2)
**Scan scope:** {{SCAN_SCOPE}}  
**Total mutations evaluated:** {{TOTAL_MUTATIONS_EVALUATED}}  
**L1 candidates:** {{L1_CANDIDATES}}  
**EvoEF2 ΔΔG range:** {{EVOEF2_DDG_RANGE}}

## 5. Stability & Sequence Filter (L2)
**ThermoMPNN vetoes:** {{THERMOMPNN_VETOES}}  
**AbLang / AntiFold warnings:** {{ABLANG_WARNINGS}}  
**L2 passing set:** {{L2_PASSING}}

## 6. CMC Developability Gate
**pI shifts:** {{PI_SHIFTS}}  
**CMC vetoes:** {{CMC_VETOES}}  
**CMC passing set:** {{CMC_PASSING}}

## 7. Precision Energy (MM/GBSA)
**WT baseline:** {{WT_BASELINE}}  
**Candidate ΔΔG table:** {{CANDIDATES_DDG}}  
**Batch ID:** {{BATCH_ID}}

## 8. Double Mutation Epistasis
**Pair candidates:** {{PAIR_CANDIDATES}}  
**Nonadditivity term:** {{NONADDITIVITY_TERM}}  
**Epistasis flag:** {{EPISTASIS_FLAG}}

## 9. Final Candidate Sequences
**Candidate rank:** {{CANDIDATE_RANK}}  
**Sequences:** {{SEQUENCES}}  
**Mutations:** {{MUTATIONS}}  
**Final ΔΔG:** {{DDG_FINAL}}

## 10. Evidence Traceability & Trust Level
**Evidence source:** {{EVIDENCE_SOURCE}}  
**Verification tier:** {{ADA_TIER}}  
**Reference IDs:** {{REFERENCE_IDS}}

## 11. Methodology Reliability Statement
**Benchmark reference:** {{BENCHMARK_REFERENCE}}  
**Confidence statement:** {{CONFIDENCE_STATEMENT}}

<!-- INTERNAL_ONLY_START -->
### Internal Tool Trace
**Pipeline:** {{PIPELINE}}  
**Tools / envs:** {{TOOLS_AND_ENVS}}  
**Raw EvoEF2 CSV:** {{RAW_EVOEF2_CSV}}  
**Raw MM/GBSA CSV:** {{RAW_MMGBSA_CSV}}  
**ThermoMPNN results:** {{THERMOMPNN_RESULTS}}  
**AbLang results:** {{ABLANG_RESULTS}}
<!-- INTERNAL_ONLY_END -->

## 12. Risks & Limitations
**Structure confidence:** {{STRUCTURE_CONFIDENCE}}  
**Tool limitations:** {{TOOL_LIMITATIONS}}  
**Experimental validation note:** {{VALIDATION_NOTE}}

## 13. Conclusions & Recommendations
**Recommended candidate:** {{RECOMMENDED_CANDIDATE}}  
**Next steps:** {{NEXT_STEPS}}

<!-- INTERNAL_ONLY_START -->
## Appendix
{{APPENDIX_INTERNAL}}
<!-- INTERNAL_ONLY_END -->
