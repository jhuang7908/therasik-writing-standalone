<!-- version: workflow_2026-06-26d | last_updated: 2026-06-26 | changed: REDESIGN v2 — 4-phase "Scan First · Edit Once" structure; Issue Registry mandatory before any edit; fixed Step-order within single edit session; read-back after each edit category (not just at end); reduces target version count from 6+ to 2 (original → final) -->
# End-to-End Manuscript Workflow

## Core Principle: Scan First · Edit Once

**The cause of multi-version churn is not bad editing — it is discovering problems in the wrong order.**

When citation issues, structural errors, and AI-style markers are found during or after content revision, each discovery forces another version. The fix is simple: discover everything before touching the manuscript.

**Target: original → 1 revised version → submission.**

Rules that enforce this:
- All scans are **read-only**. No edit is made until the Issue Registry is complete.
- The single edit session follows a **fixed execution order** (see Phase 3). Steps within a session do not reorder.
- After each edit category, a **targeted read-back** confirms no new errors were introduced before moving to the next category.
- Expert review runs **once, on the final version**. Never on an intermediate.
- The Audit Gate Document is opened at Phase 1 and updated prospectively. No step is marked complete without updating it.
- **PASS or BLOCKED only.** PARTIAL is not a valid status.

---

## AI Usage Boundary

Apply the traffic-light boundary before any drafting step.

**Green** — acceptable: grammar/clarity/tone improvements, outline generation, title/abstract alternatives, literature summarization for categorization, translation with terminology checks.

**Yellow** — allowed only with line-by-line author verification: methods/results wording support, reviewer-response frameworks, code/statistics explanations.

**Red** — block; do not proceed: drafting core scientific argument from scratch, inserting unverified AI-generated references/data/claims, uploading unpublished manuscripts to public models, fabricating image content.

---

## Mode A — From Scratch

Use when the author has data, figures, or partial literature but no manuscript.

Steps: Intake → AI boundary check → Build DB → Search literature → Ingest full text → Extract claims/figures/methods → Plan thesis + figure contracts → Draft (Results first) → Phase 2–4 below → Human sign-off.

---

## Mode B — Revision and Rescue

Use when a manuscript already exists and must be corrected, de-AI-styled, reformatted, or retargeted.

---

### Phase 1 — Archive and Lock (read-only, ≤ 30 min)

**B1 — Preserve Original**

- Copy original to `*_ORIGINAL.docx`, record SHA-256 hash in `version_ledger.jsonl`
- Open Audit Gate Document with all gates in BLOCKED state

Exit: original archived · hash recorded · audit doc opened

**B2 — Lock Journal Target**

- Record in `project_config.json`: journal name, article type, word limit, figure limit, citation format, section headings required

Exit: all journal constraints recorded · no ambiguous targets remain

---

### Phase 2 — Comprehensive Pre-Flight Scan (read-only)

**Run all four scans before making any edit. Output is the Issue Registry.**

**B3 — Reference and Citation Scan**

1. Count all reference list entries (N_list).
2. Extract every in-text citation number. Count unique cited refs (N_cited).
3. Floating = N_list − N_cited. Must reach zero. List every floating ref by number and title.
4. Scan reference list for non-reference content: editor notes, word counts, revision markers. List each.
5. For each in-text citation group: note sentence context. Flag any citation whose subject visibly mismatches the sentence (preliminary pre-commit check — full check happens in Phase 3 Step D).
6. Check BIB/RIS file exists and entry count matches reference list.

**B4 — AI Style and Format Scan**

1. Run `python scripts/insynbio_polishing.py scan` on full DOCX text. Record per-section marker count.
2. Scan for Markdown syntax in body: `**`, `##`, `^`, `---`, `\*`, `-` at line start.
3. Check citation format against journal requirement (parenthetical vs superscript).

**B5 — Paragraph Structure Scan**

1. Extract full body text. Read every paragraph.
2. Flag: content from one section appearing in another (e.g., Limitations text inside Results).
3. Flag: fused paragraphs (sentence splice joining two distinct items without paragraph break).
4. Flag: orphan sentences (incomplete thought without context).

**B6 — Claim-Evidence Scan**

1. List every major claim (one per row): claim text · supporting citation(s) · status (supported / needs evidence / weak / contradicted).
2. Flag any claim with status other than "supported".

---

**Issue Registry (required output of Phase 2)**

Before Phase 3 begins, compile a numbered list of every finding:

```
Issue #  | Category       | Description                          | Phase 3 Step
---------|----------------|--------------------------------------|-------------
001      | REF-FLOAT      | Ref 19 (Goldsmith) has no cited home | B  (delete)
002      | REF-FLOAT      | Ref 33 (Ferrari) has no cited home   | B  (delete)
003      | FORMAT         | Markdown ** in title paragraph       | C
004      | STRUCTURE      | Limitations text embedded in Results | C
005      | CITATION-WEAK  | Ref 34 cited at NKG2D sentence, CAR  | D  (remove citation)
...
```

**Phase 2 exit: Issue Registry is complete. Zero issues have unknown status. Phase 3 does not begin until this exit criterion is met.**

---

### Phase 3 — Single Edit Session (fixed execution order)

**All issues from the Issue Registry are resolved in this session. The order below is mandatory — later steps depend on earlier ones being complete.**

**Step A — Remove Non-Reference Content from List**

Delete editor notes, word-count markers, revision comments from the reference list only. Do not touch body text yet.

Read-back: confirm list contains only reference entries.

**Step B — Delete References with No Evidential Home**

For each REF-FLOAT issue marked "delete": remove from reference list. Do not insert at a weak sentence to avoid deletion.

After all deletions: renumber reference list sequentially (1 to N_new). Verify every in-text citation number maps correctly under the new numbering. Record mapping in `version_ledger.jsonl`.

Read-back: spot-check 10 in-text citation groups against renumbered list. Count = N_new confirmed.

**Step C — Fix Structural and Format Errors**

In order: (1) paragraph boundary fixes (cross-section leakage, fused paragraphs), then (2) Markdown artifact removal, then (3) citation format conversion (if required by journal).

Read-back: re-read every paragraph in affected sections. Confirm zero boundary violations and zero Markdown artifacts.

**Step D — Insert Floating References (Pre-Commit Checklist)**

For each REF-FLOAT issue marked "insert": apply the Citation Insertion Pre-Commit Checklist (qa-gates.md) before inserting:
- Sentence-level evidential match (not topic-level)
- Subject match (same biological entity / modality / system)
- No double-citation of same claim
- Relevance tier logged (EVIDENTIAL / TOPICAL / REVIEW)
- Verify ref appears in renumbered list at correct position

If no evidential home exists: delete from list (Step B). Do not force-insert.

Read-back: re-read every sentence where a citation was added or removed.

**Step E — Content Revision**

Revise in section order: Results → Introduction → Conclusion → Title → Discussion → Methods → Abstract.

For each section: complete revision, then read-back that section before starting the next.

**Step F — AI Style Fixes**

Address any AI marker issues flagged in B4. Fix overused transitions, uniform hedging, Markdown artifacts not already removed in Step C.

Read-back: re-run `insynbio_polishing.py scan` on revised text. Confirm marker count below threshold.

---

**Phase 3 exit criteria (ALL must be true):**
- [ ] Issue Registry: every issue marked RESOLVED or AUTHOR-REQUIRED
- [ ] Reference list sequentially numbered, in-text citations verified
- [ ] BIB/RIS synchronized with final reference list
- [ ] Per-step read-backs completed with zero unresolved anomalies
- [ ] Citation pre-commit log complete (one entry per inserted citation)
- [ ] AI marker count < 3 per 500-word window in every section

---

### Phase 4 — Figure Contracts, Expert Review, Release Gate

**B7 — Figure Contracts**

For each figure: declare core conclusion, panel-to-evidence mapping, export contract (dimensions, DPI, editable text, source data path, n and p values). Block if any field is missing.

Exit: every figure has complete contract · zero [AUTHOR_REQUIRED] fields

**B8 — Final Verification and Expert Review**

1. Render DOCX → PDF. Visually inspect every page.
2. Extract full text, read every paragraph (final structural read-back).
3. Run `python scripts/multi_expert_review.py` on this version.
4. For each MAJOR/CRITICAL finding: resolve here or log as author-required with justification.

Exit: PDF renders clean · full read-back complete · expert review run on this file · statistician ≥ 7/10 or all sub-7 items documented

**B9 — Release Gate**

Complete the Audit Gate Document. Every gate is PASS or BLOCKED. State final release status.

Exit: all Phase 1–4 exit criteria confirmed · zero machine-resolvable blockers · remaining human-required actions listed with owner

---

## Audit Gate Document

Opened at B1. Updated at each phase exit. Never written retrospectively.

Template: one row per gate — Gate | Exit Criteria | Status (PASS/BLOCKED) | Evidence | Date

---

## Non-Skippable Outputs

Every Mode B run must produce:

1. Archived original with hash
2. Issue Registry (all findings, all statuses)
3. Citation pre-commit log (per inserted citation: relevance tier, subject match)
4. Renumbering event record in version_ledger.jsonl
5. Per-step read-back log (step, anomalies found, resolved Y/N)
6. AI style scan report (per section, marker count, PASS/FAIL)
7. Claim-evidence map (per claim: text, citation, status)
8. Figure contracts (per figure: all fields complete)
9. Expert review output on final version
10. Release gate audit document

---

## Recommended Section Writing Order

Results → Introduction → Conclusion → Title → Discussion → Methods → Abstract

This prevents Discussion from drifting into Results and keeps the argument coherent across sections.
