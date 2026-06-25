## VHH Design Checklist — mumab4d5_vhh_20260325

**Status:** PASS  PASS=22  WARN/REVIEW=4  FAIL=0

| ID | Phase | Gate | Description | Status | Evidence |
|----|:-----:|:----:|-------------|:------:|----------|
| 1.1 | 1 | HARD | Input sequence valid VH or VHH (length 100–14… | ✓ PASS | length=119 |
| 1.2 | 1 | HARD | Kabat numbering via kabat_from_anarcii() — no… | ✓ PASS | CDR lengths present — kabat_from_anarcii() used |
| 1.3 | 1 | HARD | Chain type confirmed as heavy chain (H)… | ✓ PASS | heavy chain (implicit — infer_from_sequence raises on non-H) |
| 1.4 | 1 | SOFT | CDR1/CDR2/CDR3 lengths extracted and in plaus… | ✓ PASS | CDR1=10 CDR2=17 CDR3=10 |
| 1.5 | 1 | SOFT | [NEW] CDR3 Cys scan: if CDR3>=14aa, check for… | — SKIP | item not evaluable from output JSON alone |
| 2.1 | 2 | HARD | Germline selected from validated whitelist (I… | ✓ PASS | IGHV1-2 identity=0.8367 |
| 2.2 | 2 | HARD | Framework strategy decided (database_germline… | ✓ PASS | surface_reshaping_first |
| 2.3 | 2 | HARD | Hallmark motif selected from validated motifs… | ✓ PASS | motifs: {'VGEL', 'VERW', 'VGRW'} |
| 2.4 | 2 | SOFT | Vernier zone classified: redline positions [4… | ✓ PASS | preserve=7 rehumanize=4 |
| 2.5 | 2 | SOFT | CDR3 tier assigned (short/medium/long/very_lo… | ? NEEDS_REVIEW | CDR3 tier not in candidate learning_bucket |
| 2.6 | 2 | HARD | [NEW] VH→VHH path: stealth mutations pos35+50… | ✓ PASS | stealth applied: ['K35_SKIP', 'K50_SKIP'] |
| 3.1 | 3 | HARD | Mutation applied via mutate_by_kabat_position… | ✓ PASS | 4 position(s) mutated via Kabat keys |
| 3.2 | 3 | HARD | CDR preservation verified via verify_cdr_pres… | ✓ PASS | all candidates _cdr_preservation=PASS |
| 3.3 | 3 | SOFT | Applied mutations logged with Kabat positions… | ✓ PASS | applied_replacements present on all candidates |
| 3.4 | 3 | SOFT | [NEW] CDR3 disulfide integrity confirmed (if … | — SKIP | item not evaluable from output JSON alone |
| 4.1 | 4 | HARD | VHH-ADI computed: sequence → CMCMetrics → com… | ✓ PASS | VHH_ADI computed for at least 1 candidate |
| 4.2 | 4 | HARD | Both VHH_ADI and human_compat_ADI in [0, 100]… | ✓ PASS | all ADI scores in [0, 100] |
| 4.3 | 4 | SOFT | Immunogenicity assessed (MHCII_Analyzer or he… | ✓ PASS | immunogenicity field present (--run-immunogenicity used) |
| 4.4 | 4 | SOFT | Developability flag (compat_flag) recorded: O… | ✓ PASS | compat_flags: {'WARN'} |
| 4.5 | 4 | SOFT | [NEW] Tm estimate checked against industry th… | — SKIP | item not evaluable from output JSON alone |
| 5.1 | 5 | HARD | PipelineQA ran and _qa block embedded in outp… | ✓ PASS | _qa status=WARN |
| 5.2 | 5 | HARD | schema_version and generated_at in output… | ✓ PASS | schema=2.0 |
| 5.3 | 5 | HARD | Reference data hashes recorded in pipeline_me… | ✓ PASS | hashes recorded: ['vhh42_ref', 'abref458_ref'] |
| 5.4 | 5 | SOFT | Structural QA run (if PDB/NB2 available): glo… | ✓ PASS | structure_qa present (--run-prediction was used) |
| 5.5 | 5 | SOFT | Candidates ranked (final_rank assigned to all… | ✓ PASS | all 3 candidates ranked |
| 5.6 | 5 | SOFT | Learning entry appended when --append-learnin… | ? NEEDS_REVIEW | learning adjustment not applied (no log data yet) |
| 6.1 | 6 | HARD | Pre-delivery gate passed (C.1–C.10 + A.1–A.6)… | ✓ PASS | pre_delivery status=PASS |
| 6.2 | 6 | HARD | Audit file generated ({project}_VHH_Audit.md)… | ? NEEDS_REVIEW | verify audit file was written alongside JSON (default: enabl |
| 6.3 | 6 | SOFT | Client report contains: Executive Summary, Ge… | ? NEEDS_REVIEW | client report content requires human review |