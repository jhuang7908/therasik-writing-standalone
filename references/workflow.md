# End-to-End Manuscript Workflow

## AI Usage Boundary

Apply the traffic-light boundary (see qa-gates.md) before any drafting step.
Red actions block the workflow. Do not draft core scientific arguments from scratch
or insert unverified AI-generated references.

## Recommended Section Writing Order

For research articles, revise sections in this order to keep the argument coherent
and prevent Discussion from drifting into Results:

1. Results
2. Introduction and Conclusion
3. Title
4. Discussion
5. Materials and Methods
6. Abstract

For methods papers, begin with Methods, then Results, Introduction, Conclusion, Discussion, Abstract.

## Modes

### Mode A - From Scratch

Use when the author has ideas, data, partial literature, or figures but no manuscript.

Required sequence:

1. Intake author goal, article type, target journal, and available data.
2. Apply AI usage boundary check (qa-gates.md, Traffic Light section).
3. Build project database.
4. Search and expand literature.
5. Download or ingest full text where legally available.
6. Extract claims, methods, figures, legends, datasets, and limitations.
7. Compare similar articles in target or adjacent journals.
8. Plan thesis, structure, and novelty. For each planned figure, declare a figure contract (core conclusion, evidence chain, export contract) before any figure is generated.
9. Draft manuscript in recommended section order (Results first).
10. Run QA gates.
11. Revise until machine blockers are zero.
12. Generate DOCX/PDF and full QA bundle.
13. Stop at human author/expert sign-off if needed.

### Mode B - Revision and Rescue

Use when a manuscript already exists and must be corrected, de-AI-styled, reformatted, or retargeted.

Required sequence:

1. Preserve original draft.
2. Identify target journal and article type.
3. Apply AI usage boundary check.
4. Build reference and claim database from existing manuscript. Produce a claim-evidence map for each major claim.
5. Detect hallucinated, irrelevant, duplicate, missing, or misordered references.
6. Detect AI-style prose, fragmented paragraph rhythm, manual checklist leakage, old-journal traces, and retargeting artifacts.
7. Revise content and structure before formatting. Follow recommended section writing order.
8. For each figure: verify figure contract exists (core conclusion, evidence chain, export contract). Redraw or replace if contract cannot be satisfied.
9. Build DOCX/PDF and render all pages.
10. Run strict release gate and workflow audit.

## Non-Skippable Outputs

- project database manifest
- references table
- claim-source matrix with status (supported / needs evidence / weak / contradicted) for each major claim
- figure contract for each figure
- figure/table inventory
- journal requirement record
- QA reports (paragraph structure, AI style, reference/claim, figure contract, render)
- DOCX
- PDF render
- full-page PNG render or equivalent visual QA
- workflow execution audit

## Failure Policy

If any machine QA fails, revise and rerun. Do not describe the draft as ready.
