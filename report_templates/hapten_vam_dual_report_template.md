# {{PROJECT_TITLE}} — Hapten VAM Report

**Project ID:** `{{PROJECT_ID}}`  
**Report Family:** `hapten_vam`  
**Audience:** `internal`  
**Version:** `{{VERSION}}`  
**Date:** `{{DATE}}`  
**Antibody Name:** `{{ANTIBODY_NAME}}`  
**Hapten:** `{{HAPTEN}}`

## 1. Executive Summary
**Top candidate:** {{TOP_CANDIDATE}}  
**ΔΔG improvement:** {{DDG_IMPROVEMENT}}  
**CMC status:** {{CMC_STATUS}}  
**Recommended sequence:** {{RECOMMENDED_SEQUENCE}}

## 2. Structure Modeling & Docking
**Structure tool:** {{STRUCTURE_TOOL}}  
**Docking tool:** {{DOCKING_TOOL}}  
**Best pose score:** {{BEST_POSE_SCORE}}  
**Cluster concentration:** {{CLUSTER_CONCENTRATION}}

## 3. IMGT-Linear Position Map
**IMGT positions:** {{IMGT_POSITIONS}}  
**Linear positions:** {{LINEAR_POSITIONS}}  
**Numbering tool:** {{NUMBERING_TOOL}}

## 4. Contact Interface Analysis
**Contact residues:** {{CONTACT_RESIDUES}}  
**CDR contact ratio:** {{CDR_CONTACT_RATIO}}  
**Cutoff (A):** {{CUTOFF_ANGSTROM}}

## 5. Alanine Scan (EvoEF2)
**Scan positions:** {{SCAN_POSITIONS}}  
**Alanine ΔΔG range:** {{ALA_DDG_RANGE}}  
**Hotspot residues:** {{HOTSPOT_RESIDUES}}

## 6. Saturation Scan
**Hotspot positions:** {{HOTSPOT_POSITIONS}}  
**Best mutations:** {{BEST_MUTATIONS}}  
**Top-10 EvoEF2 ΔΔG:** {{EVOEF2_DDG_TOP10}}

## 7. Combination Mutation Scan
**Combo candidates:** {{COMBO_CANDIDATES}}  
**Combo ΔΔG:** {{COMBO_DDG}}  
**Epistasis flag:** {{EPISTASIS_FLAG}}

## 8. CMC Developability Gate
**WT pI:** {{PI_WT}}  
**Mutant pI:** {{PI_MUTANT}}  
**WT II:** {{II_WT}}  
**Mutant II:** {{II_MUTANT}}  
**CMC status:** {{CMC_STATUS}}

## 9. HallucinationGuard Audit
**Audit file:** {{AUDIT_FILE}}  
**Hard abort count:** {{HARD_ABORT_COUNT}}  
**Warn count:** {{WARN_COUNT}}

## 10. Evidence Traceability & Trust Level
**Evidence source:** {{EVIDENCE_SOURCE}}  
**Verification tier:** {{ADA_TIER}}  
**Reference IDs:** {{REFERENCE_IDS}}

## 11. Methodology Reliability Statement
**Benchmark reference:** {{BENCHMARK_REFERENCE}}  
**Confidence statement:** {{CONFIDENCE_STATEMENT}}

<!-- INTERNAL_ONLY_START -->
### Internal Method Details
**Ala scan CSV:** {{ALA_SCAN_CSV}}  
**Sat scan CSV:** {{SAT_SCAN_CSV}}  
**Combo scan CSV:** {{COMBO_SCAN_CSV}}  
**Hallucination audit JSON:** {{HALLUCINATION_AUDIT_JSON}}
<!-- INTERNAL_ONLY_END -->

## 12. Risks & Limitations
**Vina accuracy:** {{VINA_ACCURACY}}  
**EvoEF2 accuracy:** {{EVOEF2_ACCURACY}}  
**Experimental validation:** {{EXPERIMENTAL_VALIDATION}}

## 13. Final Candidate Sequences
**Candidate rank:** {{CANDIDATE_RANK}}  
**Sequences:** {{SEQUENCES}}  
**Mutations:** {{MUTATIONS}}  
**Final ΔΔG:** {{DDG_FINAL}}  
**CMC pI:** {{CMC_PI}}  
**CMC II:** {{CMC_II}}

## 14. Conclusions
**Recommended candidate:** {{RECOMMENDED_CANDIDATE}}  
**Next steps:** {{NEXT_STEPS}}

<!-- INTERNAL_ONLY_START -->
## Appendix
{{APPENDIX_INTERNAL}}
<!-- INTERNAL_ONLY_END -->
