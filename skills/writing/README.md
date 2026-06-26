# InSynBio Writing Suite — Cursor Skills

**11 skills covering the full academic writing pipeline.**  
No antibody-engineering content. No social-media content. Writing only.

> Install path: copy each skill folder into your Cursor skills directory  
> Windows: `%USERPROFILE%\.cursor\skills\`  
> macOS/Linux: `~/.cursor/skills/`

---

## Skills Map

| Skill | Role in pipeline | Backed by CLI script |
|---|---|---|
| `insynbio-research-suite` | **Master router** — entry point for all writing tasks | `scripts/insynbio_research.py` |
| `insynbio-literature-search` | OpenAlex full-text search, OA filter, domain classification | `scripts/insynbio_openalex.py` |
| `insynbio-citation` | Citation corpus, DOI verify, RIS/BIB export | `scripts/insynbio_citation.py` |
| `insynbio-figure` | Figure audit, stats recipes (forest/volcano/heatmap/KM/legend), journal compliance | `scripts/insynbio_figure.py` |
| `insynbio-paper-reader` | Bilingual paper reading, figure map, Kimi/DeepSeek translation | `scripts/insynbio_paper_reader.py` |
| `insynbio-paper2ppt` | Paper → PPTX slide deck (hybrid recipe) | `scripts/insynbio_paper2ppt.py` |
| `insynbio-paper-to-patent` | Evidence-constrained CN patent outline from manuscript | `scripts/insynbio_paper_to_patent.py` |
| `insynbio-polishing` | AI-marker scan + LanguageTool grammar API (free) | `scripts/insynbio_polishing.py` |
| `insynbio-rigor` | Scientific rigor & accuracy multi-layer gates | `scripts/insynbio_rigor.py` |
| `journal-submission-bundle` | Abstract · Highlights · Cover letter · FAIR data statement · Response to reviewers | `scripts/insynbio_submission_writer.py` |
| `llm-verifier-agent` | Adversarial verifier — challenges every factual claim | *(prompt-only, no CLI)* |
| `_shared` | Shared fragments used across multiple skills | *(internal)* |

---

## Pipeline Flow

```
insynbio-research-suite (router)
    │
    ├── literature    → insynbio-literature-search  →  insynbio-citation
    │
    ├── format        → insynbio-journal-format      →  journal-submission-bundle
    │
    ├── rigor-audit   → insynbio-rigor               →  llm-verifier-agent
    │
    ├── polish        → insynbio-polishing (scan + grammar)
    │
    ├── figure        → insynbio-figure (audit + stats + concordance + comply)
    │
    └── submission-writer → journal-submission-bundle
                            (abstract + highlights + cover-letter +
                             data-statement + response)
```

---

## CLI Scripts (no Cursor required)

The skills call these Python scripts, which work standalone:

```bash
# Literature search
python scripts/insynbio_openalex.py search --query "de novo antibody design" --limit 20

# Semantic Scholar citation context
python scripts/insynbio_semantic_scholar.py cite-context --id 10.1038/s41586-023-06415-8

# Grammar check (LanguageTool public API, free)
python scripts/insynbio_polishing.py grammar --input paper/manuscript.md --out reports/grammar.json

# Figure concordance
python scripts/insynbio_figure.py concordance --manuscript paper/manuscript.docx --figures-dir paper/figures

# FAIR data statement
python scripts/insynbio_submission_writer.py data-statement --journal at --template --out paper/data_avail.md

# Structured abstract
python scripts/insynbio_submission_writer.py abstract --spec specs/abstract_spec.json --journal at --out paper/abstract.md

# Full pipeline (project-based)
python scripts/insynbio_research.py --project my_project --workflow literature
python scripts/insynbio_research.py --project my_project --workflow submission-writer
```

---

## Install (Cursor)

```bash
# Clone the repo
git clone https://github.com/jhuang7908/Antibody-Engineer-Suite-MVP.git

# Copy writing skills to Cursor skills directory
# Windows
xcopy /E /I skills\writing\* %USERPROFILE%\.cursor\skills\

# macOS/Linux
cp -r skills/writing/* ~/.cursor/skills/
```

After copying, restart Cursor. Skills appear in the skills panel automatically.

---

## Dependencies

```bash
pip install pillow scipy matplotlib requests
```

No API keys required for core functionality (LanguageTool, OpenAlex, Semantic Scholar all have free public tiers).

Optional (for richer citation lookup):
- Semantic Scholar Partner API key → set `S2_API_KEY` env var for higher rate limits
- OpenAI API key → for `insynbio-paper2ppt` image generation

---

## What is NOT here

| Excluded | Reason |
|---|---|
| `antibody-cmc-assessment` | Proprietary antibody engineering |
| `vhh-humanization`, `vhvl-humanization` | Proprietary antibody engineering |
| `vam-exemplar-playbook` | Proprietary virtual affinity maturation |
| `nextvivo-*`, `therasik-*` | CN social media content marketing |
| `content-studio-*`, `xhs-*` | Social media image rendering |
| `ppt-voice`, `ppt-studio-router` | Multimedia production |
