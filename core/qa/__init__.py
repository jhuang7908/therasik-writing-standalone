"""
core.qa — InSynBio AbEngineCore v1.0
======================================
Pipeline self-check and QA framework.

Every computational step in the antibody engineering pipeline produces
a signed, immutable QAReport that records:
  - Input/output sequence hashes (tamper detection)
  - Per-check pass/warn/fail status
  - Physical plausibility of all computed metrics
  - CDR preservation verification
  - Assembly integrity (FR+CDR = full sequence)

Quick start
-----------
    from core.qa import PipelineQA, QAViolation, qa_from_evaluator_result

    qa = PipelineQA(project="PDL1_Ab2", step="assembly")
    qa.check_sequence("vh",  vh_seq, "VH")
    qa.check_assembly("vh_asm", fr1, cdr1, fr2, cdr2, fr3, cdr3, fr4,
                      full_seq=vh_final, original_cdrs={"H1": cdr1_orig})
    qa.check_metric("pI", 7.2)
    report = qa.finalize(output_seq=vh_final)
    qa.assert_pass()   # raises QAViolation on FAIL

Stages
------
    Stage 1 — SequenceQA    : alphabet, length, gaps
    Stage 2 — NumberingQA   : ANARCII output consistency
    Stage 3 — AssemblyQA    : FR+CDR concatenation == full_seq (hard gate)
    Stage 4 — MutationQA    : only authorized positions changed
    Stage 5 — StructureQA   : PDB chain presence, ColabFold scores
    Stage 6 — MetricsQA     : physical range validation (pI, BSA, SC, TCIA ...)
    Stage 7 — CrossStepQA   : input hash == previous output hash
"""

from core.qa.pipeline_qa import (
    PipelineQA,
    QACheck,
    QAReport,
    QALevel,
    QAViolation,
    qa_from_evaluator_result,
)

__all__ = [
    "PipelineQA",
    "QACheck",
    "QAReport",
    "QALevel",
    "QAViolation",
    "qa_from_evaluator_result",
]
