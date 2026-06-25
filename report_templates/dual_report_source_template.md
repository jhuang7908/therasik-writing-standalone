# {{PROJECT_TITLE}}

<!--
InSynBio dual-report source template
------------------------------------
1. Save as: {project_id}_{family}_internal_v{n}.md
2. Keep internal-only material inside INTERNAL_ONLY blocks
3. Render with:
   python scripts/report_cli.py dual <this_file> --outdir <output_dir>
4. Align chapter list to core/reporting/spec.py -> ReportSpec.chapter_schema()
-->

**Project ID:** `{{PROJECT_ID}}`  
**Report Family:** `{{REPORT_FAMILY}}`  
**Audience:** `internal`  
**Version:** `{{VERSION}}`  
**Date:** `{{DATE}}`  
**Target / Program:** `{{TARGET}}`  
**Prepared By:** `{{AUTHOR}}`

## 1. Executive Summary
{{EXECUTIVE_SUMMARY}}

## 2. Project Context
**Objective:** {{OBJECTIVE}}  
**Input:** {{INPUT_SUMMARY}}  
**Primary decision:** {{PRIMARY_DECISION}}

## 3. Main Analysis
### 3.1 Input QC
{{INPUT_QC}}

### 3.2 Core Results
{{CORE_RESULTS}}

### 3.3 Interpretation
{{INTERPRETATION}}

## 4. Evidence Traceability & Trust Level
**Evidence source:** {{EVIDENCE_SOURCE}}  
**Verification tier:** {{ADA_TIER_OR_EQUIVALENT}}  
**External references:** {{PMID_DOI_OR_DATASET_IDS}}  
**Traceability note:** {{TRACEABILITY_NOTE}}

## 5. Methodology Reliability Statement
**Confidence statement:** {{CONFIDENCE_STATEMENT}}  
**Benchmark / validation reference:** {{BENCHMARK_REFERENCE}}  
**Important limitations:** {{LIMITATIONS_SUMMARY}}

<!-- INTERNAL_ONLY_START -->
### Internal Method Details
**Pipeline / scripts:** {{PIPELINE_AND_SCRIPTS}}  
**Tool versions / envs:** {{TOOLS_AND_ENVS}}  
**Raw files / artifacts:** {{RAW_OUTPUT_PATHS}}  
**Reproducibility note:** {{REPRO_NOTE}}
<!-- INTERNAL_ONLY_END -->

## 6. Risks & Limitations
- {{RISK_1}}
- {{RISK_2}}
- {{RISK_3}}

## 7. Conclusions & Recommendations
**Recommended action:** {{FINAL_RECOMMENDATION}}  
**Why:** {{RATIONALE}}  
**Next step:** {{NEXT_STEP}}

## 8. Appendix
### Data Snapshot
{{OPTIONAL_TABLE_OR_BULLETS}}

<!-- INTERNAL_ONLY_START -->
### Internal Appendix
{{RAW_TABLES_OR_DEBUG_NOTES}}
<!-- INTERNAL_ONLY_END -->

---

## Family-Specific Swap Guide
- `vhvl_humanization`: add `IMGT Segmentation`, `Germline Match`, `Vernier Zone`, `Mutation Tiers`, `Three Final Sequences`
- `vhh_humanization`: add `Tier Position Analysis`, `Three Humanization Strategies`
- `vhh_cmc`: add `15-Metric CMC Panel`, `ADI Score`
- `bispecific_cmc`: add `Arm A / Arm B`, `Fusion Matrix`, `SmartLink Recommendation`
- `vam` / `hapten_vam`: add `Mutation Ranking`, `Multi-tool Consensus`, `Top Candidate Table`
- `adc_design`: add `Target Tier`, `Linker/Payload Decision`, `Safety / FTO Alerts`
- `car_design`: add `Construct Architecture`, `Domain Choices`, `Safety Modules`
- `vaccine_design` / `epidesign`: add `Epitope Selection`, `Coverage`, `Junction / Binder Checks`

## Minimal Validation Checklist
- Naming follows `{project_id}_{family}_{audience}_v{n}.md|pdf|html`
- Internal-only content is wrapped in `INTERNAL_ONLY` markers
- `Evidence Traceability` section is present
- `Methodology Reliability Statement` section is present
- Final recommendation is explicit and actionable
