---
name: therasik-academic-writing-suite
description: Strict academic writing workflow for reviews, research manuscripts, thesis literature reviews, and submission rescue. Use when building, revising, QA-checking, rendering, or packaging scholarly manuscripts with evidence databases, citation verification, figure/table QA, journal formatting, AI-style control, workflow audit, and release gates.
version: 0.3.0
lifecycle: Released
---

# Therasik Academic Writing Suite

## Operating Rules

Never release a manuscript only because the prose looks polished. Run the workflow, inspect the audit, and block delivery when any machine-detectable QA gate fails.

Before any drafting step, apply the AI usage boundary from `references/qa-gates.md`. Red actions block the workflow immediately.

## AI Usage Boundary (Summary)

Green: grammar, clarity, outline options, translation with terminology checks.
Yellow: methods wording support, reviewer-response frameworks with line-by-line human review.
Red (BLOCK): drafting core scientific argument from scratch, inserting unverified AI references or data, uploading unpublished manuscripts to public models.

## Workflow

1. Create or load a project folder.
2. Apply AI usage boundary check. Block if any Red action is requested.
3. Build a project database: references, claims, evidence units, figures/tables, journal rules, and QA gates.
4. Draft or revise the manuscript from evidence. Follow recommended section order: Results → Introduction → Title → Discussion → Methods → Abstract.
5. Verify references by DOI/PMID/PMCID/URL and check citation relevance. Produce a claim-evidence map with Status for each major claim.
6. Before any figure is generated or accepted, declare a figure contract: core conclusion, evidence chain per panel, export contract (dimensions, editable text, source data, statistics).
7. Generate or update figures and tables only after the figure contract is satisfied.
8. Run manuscript QA: structure, paragraph rhythm, AI-style, figure contract, retargeting originality, and journal fit.
9. Build DOCX and render to PDF/full-page PNG for visual QA.
10. Run the strict release gate and workflow execution audit.
11. Return final status as one of:
    - `MACHINE_QA_FAILED`
    - `MACHINE_QA_PASSED_HUMAN_PENDING`
    - `SUBMISSION_READY_AFTER_AUTHOR_CONFIRMATION`

## Required References

Read these files when the task reaches the corresponding stage:

- `references/workflow.md`: end-to-end manuscript workflow including section writing order and figure contract steps.
- `references/qa-gates.md`: AI traffic light, claim-evidence map format, figure contract requirements, reviewer red lines, and all release blockers.
- `references/versioning.md`: version ledger and skill lifecycle states.
- `references/case-learning.md`: use after user criticism, external review, or failure analysis.
- `references/mcp-roadmap.md`: use when preparing local MCP, cloud MCP, API access, or third-party integration.

## Version and Lifecycle Management

Every material change must be recorded in the version ledger. Do not silently overwrite prior drafts. Preserve enough history to compare:

- manuscript version
- skill version and lifecycle state
- workflow/rules version
- QA results
- reason for change
- source of criticism or new evidence

Skill lifecycle states: Raw → Candidate → Draft → Verified → Released → Degraded → Deprecated.
This skill is currently: **Released**.
A skill becomes Degraded when recurring QA failures are detected that the current rules do not prevent.

## Release Boundary

Machine QA can clear technical blockers. It cannot create author ownership or external domain expertise. Keep author declarations and external expert sign-off as explicit human gates.
