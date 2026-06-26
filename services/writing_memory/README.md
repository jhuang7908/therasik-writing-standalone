# Journal-Aware Scientific Writing Memory (MVP)

> Standalone subsystem. **Not** part of AbEngineCore. No locked AbEngineCore files
> are modified by this service. Lives under `services/writing_memory/` so the
> Antibody Engineer Suite pipelines remain untouched.

---

## What this service is

A **writing memory and style coach** that learns the personality, logic,
phrasing, and reviewer-attack patterns of selected biomedical journals from
their **full text (PMC JATS XML)**, and uses that memory to:

1. Rewrite a user paragraph in the style of a target journal.
2. Reduce generic AI-like tone.
3. Simulate likely reviewer concerns (style-based, inferred only).
4. Check claim strength and flag overclaiming.

It is **not** an autonomous paper generator. It does not invent references,
data, mechanisms, author names, PMIDs, or DOIs.

---

## MVP scope (v0.1)

| Item | Value |
|------|-------|
| Journals (3) | **PNAS**, **eLife**, **PLOS Medicine** |
| Papers per journal | 50 with confirmed PMC JATS full text |
| Total corpus | 150 papers |
| Required sections | abstract + (discussion or conclusion); figure legends optional |
| Vector store | PostgreSQL 15+ with `pgvector` |
| Embedding model | OpenAI `text-embedding-3-small` (1536 dim) — single model only |
| LLM | Anthropic Claude Messages API |
| Backend | FastAPI |
| Frontend | Minimal HTML/JS — one input box, one journal selector, four buttons |

### Hard non-goals for v0.1

- No 10-journal expansion.
- No paywalled full-text scraping.
- No model-generated references (any kind, ever).
- No claim about predicting real peer reviewers.
- No "AI detection" verdict; only `reduce_ai_tone` rewrite.

---

## Why these 3 journals

| Journal | Role | Full-text availability |
|---------|------|------------------------|
| PNAS | Generalist biology+medicine flagship | All articles deposited to PMC; **6-month embargo** common — use older + immediate-OA pool |
| eLife | Modern life-science research articles | Immediate OA, Full PMC participation, clean JATS |
| PLOS Medicine | Clinical / public health / translational | Immediate OA, Full PMC, strong "limitations" sections |

This combination yields three **distinct writing personalities** while keeping
every paper retrievable via `efetch db=pmc retmode=xml`.

---

## Directory layout

```
services/writing_memory/
├── README.md                          # this file
├── requirements.txt
├── docs/
│   ├── ANTI_HALLUCINATION_POLICY.md   # architectural rules for LLM I/O
│   └── JOURNAL_SPECS_POLICY.md        # curation rules for submission specs
├── schemas/                           # LLM-extracted profile schemas
│   ├── article_profile.schema.json
│   └── journal_profile.schema.json
├── prompts/
│   ├── article_profile.system.md
│   ├── journal_aggregate.system.md
│   ├── rewrite.system.md
│   ├── claim_check.system.md
│   ├── reduce_ai_tone.system.md
│   └── reviewer_sim.system.md
├── journal_specs/                     # HUMAN-CURATED, never LLM-generated
│   ├── submission_spec.schema.json
│   ├── reference_style.schema.json
│   ├── specs/
│   │   ├── pnas.json
│   │   ├── elife.json
│   │   └── plos_med.json
│   ├── reference_styles/
│   │   ├── pnas_numbered.json
│   │   ├── elife_author_year.json
│   │   └── plos_vancouver.json
│   ├── format_reference.py            # deterministic renderer
│   └── __init__.py
├── db/
│   └── schema.sql                     # PostgreSQL + pgvector DDL
├── ingest/
│   ├── probe_pmc_hitrate.py           # Week-1 deliverable
│   └── jats_extract.py                # JATS XML section extractor
└── api/                               # FastAPI (later phases)
```

### Two-layer journal knowledge

| Layer | What it captures | Source | Trust |
|-------|------------------|--------|-------|
| `journal_profiles` | Writing personality (rhetoric, logic, sentence style, phrase bank) | PMC full text, aggregated by Claude | `verified` / `inferred` |
| `journal_specs` | Submission requirements + reference style | Journal's official Instructions for Authors | **Curated by a human** |

Wrong style profile = imperfect rewrite. Wrong submission rule = desk
reject. The two layers exist precisely so the second never relies on the
first. See `docs/JOURNAL_SPECS_POLICY.md`.

---

## Week-by-week execution

| Week | Deliverable |
|------|-------------|
| 1 | `probe_pmc_hitrate.py` returns ≥50 PMC-resolvable papers per journal. JATS section extraction validated on 10 papers/journal. |
| 2 | Claude `article_profile` JSON generated for all 150 papers (schema-validated). |
| 3 | Aggregated `journal_profile` per journal. pgvector tables loaded. FastAPI exposes `/rewrite`, `/claim_check`, `/reduce_ai_tone`, `/reviewer_sim`. |
| 4 | Minimal UI page. End-to-end demo: paragraph in → 4 outputs out, each tagged with profile version and evidence source. |

---

## Anti-hallucination contract

See `docs/ANTI_HALLUCINATION_POLICY.md`. Summary:

1. The LLM **never generates references**. Only `[CITATION_NEEDED: <topic>]`
   placeholders are allowed in rewrite output.
2. Any reference shown to the user must come from a row in the `papers` table
   and be re-verified against PubMed/Crossref before display.
3. The LLM **never adds numbers, percentages, or author names** that did not
   appear in the input paragraph.
4. Every `journal_profile` field carries an `evidence_paper_count` and
   `verification_status` (`verified` / `inferred` / `unverified`).
5. Reviewer simulation output is always labelled
   `style-based simulation (inferred)`; never `prediction`.

---

## Local development

```powershell
# Recommended conda env (independent from anarcii/affmat)
conda create -n writing_memory python=3.11
conda activate writing_memory
pip install -r services/writing_memory/requirements.txt

# Required environment variables
$env:NCBI_API_KEY = "..."          # raises eUtils to 10 req/s
$env:NCBI_TOOL    = "insynbio_writing_memory"
$env:NCBI_EMAIL   = "<contact email>"  # PubMed polite-pool requirement
$env:ANTHROPIC_API_KEY = "..."
$env:OPENAI_API_KEY    = "..."     # only for embeddings; can be swapped later
$env:WRITING_MEMORY_PG = "postgresql://user:pass@host:5432/writing_memory"
```
