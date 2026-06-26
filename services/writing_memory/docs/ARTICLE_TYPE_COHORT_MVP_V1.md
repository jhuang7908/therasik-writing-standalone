# Article-Type Cohort MVP (v1.0) — Design Note

**Status:** PROPOSED (awaiting Owner approval for implementation phases)  
**Date:** 2026-05-28  
**Scope:** `services/writing_memory` — shift from “many full texts per journal” to “5–10 QC’d exemplars per article type”.

---

## Problem (current)

| Layer | Today | Pain |
|-------|--------|------|
| Style learning | Per **journal** pack; recommends 5+5 PDFs; accumulates up to ~80/journal | Data volume explodes; confuses journal voice vs article structure |
| Structure | `schemas/article_types/*.json` (curated) | Good logic, weak **empirical** envelopes |
| Submission rules | `journal_specs/specs/*.json` (human-curated) | Correct SSOT; should **not** be learned from PDFs |
| References | `journal_specs/reference_styles/*.json` + `format_reference.py` | **Plugin / deterministic** — LLM must not invent citation strings |
| Corpus | `papers_raw/` (~150 PMC JSON) + `article_profiles/` | Journal-tagged (pnas/elife/plos_med), **no article_type tag** yet |

---

## MVP target architecture

### Three SSOT layers (do not merge)

1. **Article-type cohort** — 5–10 full texts **per canonical type** → quantitative **writing metrics** (sections, words, refs, citation density).
2. **Journal surface** — `journal_specs` + reference style plugins → submission checklist & `format_reference()` only.
3. **Optional journal tone pack** — small (≤3) target-journal PDFs when user picks a specific journal for Polish (secondary to type cohort).

### Cohort size

| Canonical type | MVP target n | Priority |
|----------------|-------------|----------|
| `original_research` | 8 | P0 (partially in `papers_raw`) |
| `review_narrative` | 6 | P0 |
| `systematic_review` | 5 | P1 |
| `methods_protocols` | 6 | P1 |
| `case_report` | 5 | P1 |
| `brief_communication` | 5 | P1 |
| Others (perspective, clinical_trial, …) | 5 each | P2 |

**Rule:** Reuse local JSON if present; download only when `inventory[type].count < target_min`.

---

## Exemplar QC metrics (per paper)

Stored in `data/article_type_cohorts/{canonical_id}/papers/{paper_id}.metrics.json`:

| Metric | Source | Gate (example — calibrate from cohort) |
|--------|--------|----------------------------------------|
| `article_type` | LLM classifier + human spot-check | Must match cohort |
| `sections_present` | Parser / JATS | ⊆ `sections_required` from type schema |
| `word_count_by_section` | Tokenizer | Within schema `word_targets_default` ± band |
| `reference_count` | Regex + optional GROBID | Within journal spec band when journal known |
| `citations_per_1000_words` | In-text cite markers / `[CITE]` density | Compare to cohort median ± 2σ |
| `abstract_format` | Label detection (Background/Methods/…) | Match type + journal spec when linked |
| `quality_gate` | Existing `upload_intake.quality_gate` | PASS required |

**Cohort aggregate:** `cohort_stats.json` — median, p10, p90 per metric → used as **execution targets** for new drafts (QC panel: PASS/WARN/FAIL vs envelope).

---

## Ingest pipeline (phased)

### Phase A — Inventory (read-only)

- CLI: `python scripts/audit_writing_cohort_inventory.py --out cohort_inventory.json`
- Scans: `papers_raw/`, `article_profiles/`, `schemas/article_types_index.json`
- Output: per-type counts, per-journal counts, download gaps

### Phase B — Tag & dedupe

- Classify each local full text → `canonical_article_type` (store on manifest; never re-download same PMID)
- Dedupe by `pmid` / `content_hash`

### Phase C — Fill gaps

- Only types below `target_min`: fetch PMC OA PDF/JATS (existing ingest path)
- Skip if manifest already has ≥5 PASS papers

### Phase D — Quantify & freeze

- Run metric extractor → append to cohort
- Owner freeze: `data/article_type_cohorts/RELEASE_v1.json` (versioned, referenced by API)

### Phase E — Runtime

- `plan_paper` / `draft_section`: inject `cohort_stats` + type schema (not 80 journal PDFs)
- `rewrite` / Polish: journal profile + type envelope check
- `format_check`: **only** `journal_specs` + reference plugin
- New: `POST /qc_vs_cohort` — score user manuscript vs frozen envelope

---

## Reference & submission “plugins”

Already implemented (keep as SSOT):

- `journal_specs/format_reference.py` — in-text + bibliography rendering
- `GET /journal_specs/{key}` — word limits, abstract rules

**MVP rule:** Citation strings in client output must go through `format_reference()`; cohort learning does **not** change reference format.

---

## UI / product (aligned)

- Draft: article type drives sections (done in v15.57+)
- Learn style (journal): demote to “optional tone (≤3 PDFs)” in help text once cohort MVP ships
- New panel (future): “Type benchmark” — show cohort medians vs your draft counts

---

## Not in MVP v1

- Per-journal 80-paper packs
- Auto desk-reject without human-curated `journal_specs`
- iThenticate-grade similarity (keep exemplar anti-copy only)

---

## Owner decisions needed

1. Approve cohort sizes (5 vs 10 per type).
2. Approve frozen release path under `data/article_type_cohorts/`.
3. Approve Phase C download bot for missing types (PMC only).

---

## Verification

- Inventory script output committed or logged per run
- Each cohort paper: `verification_status` + `metrics` JSON
- Adversarial: type mis-label → FAIL intake; unverified journal spec field → hidden in UI (existing policy)
