---
name: insynbio-research-suite
description: >-
  Master router for InSynBio general biomedical academic research: literature search,
  manuscript writing (any domain), style calibration, fact gate, cross-session Material
  Passport, ScholarOne submission bundle, and hybrid paper2ppt. Covers oncology,
  immunology, gene therapy, drug discovery, structural biology, clinical trials,
  computational biology, and more — not limited to antibody engineering.
  Trigger on: 科研全流程、综述投稿、ScholarOne、paper2ppt、文献库、投稿包、
  insynbio research suite、论文汇报、组会PPT、写论文、biomedical writing、
  style calibration、author voice、material passport、稿件护照、风格校准.
version: 1.2.0
---

# InSynBio Research Suite — General Biomedical Writing Router

**Scope:** Any peer-reviewed biomedical / life science manuscript indexed or indexable by PubMed.
80+ sub-domains across 12 MeSH categories — diseases, therapeutics, immunology, genomics,
structural biology, cell biology, computational, epidemiology, clinical medicine, bioengineering,
nutrition, and cross-cutting methods.
See `static/core/biomedical-domains.md` for the full domain taxonomy and auto-detection signals.

Do not run modules from memory. **Read `manifest.yaml`** and load only the workflow fragment for the detected task.

## Routing protocol (6 steps)

1. **Load manifest** — `.cursor/skills/insynbio-research-suite/manifest.yaml`
2. **Load always_load** — `_shared/core/principles.md`, `static/core/module-index.md`, `static/core/pipeline-order.md`, `static/core/biomedical-domains.md`
3. **Detect domain** — one line to user: e.g. `domain=oncology`, `domain=structural_biology`
4. **Detect workflow** — one line: e.g. `workflow=paper2ppt`, `workflow=style_calibration`
5. **Load workflow fragment** — `static/workflows/<name>.md` + delegate to child skill in `modules`
6. **Run executable** — every step must produce a file path or audit JSON

## Quick commands

```bash
# List all projects (any domain)
python scripts/insynbio_research.py --list-projects

# Full pipeline for any project
python scripts/insynbio_research.py --project <name> --workflow full

# Style Calibration (new — provide past papers to learn author voice)
python scripts/insynbio_research.py --project <name> --workflow style-calibration --samples paper1.pdf paper2.pdf paper3.pdf

# Material Passport — initialize cross-session state tracking
python scripts/insynbio_material_passport.py --init --project <name> --domain oncology
python scripts/insynbio_material_passport.py --checkpoint --stage 3
python scripts/insynbio_material_passport.py --resume --project <name>

# Review B de novo antibody paper (existing golden path)
python scripts/insynbio_research.py --project review_b --workflow full
python scripts/insynbio_research.py --project review_b --workflow manuscript-to-slides

# Individual steps
python scripts/build_submission_bundle.py --profile <journal_profile> --workspace paper/<project>/
python scripts/insynbio_paper2ppt.py --plan <slides_plan.md> --out deck.pptx
python scripts/insynbio_openalex.py search --topic "<query>" --per-page 10
```

Project registry: `config/insynbio_research_projects.json`

## vs nature-skills (v1.1.0 parity)

| We exceed | We inherit |
|-----------|------------|
| General biomedical domain routing | Router + manifest + static/dynamic split |
| Style Calibration (6-dimension author voice) | Paper-type narrative arcs (in insynbio-paper2ppt) |
| Material Passport (cross-session state JSON) | Terminology ledger discipline |
| OpenAlex T3 free literature layer | Self-review QA concept (automated in CLI) |
| ScholarOne PASS/FAIL audit | nature module names + workflows |
| Kimi/DeepSeek fact gate (domain-agnostic) | |
| AbEngineCore (antibody-specific, optional) | |
| Editable PPTX primary | |

Master router: **`insynbio-therasik-suite`** · Brand: `config/insynbio_therasik_brands.json`

Child skills: `insynbio-literature-search`, `insynbio-citation`, `insynbio-polishing`, `insynbio-figure`, `insynbio-paper-reader`, `insynbio-paper-to-patent`, `insynbio-paper2ppt`, `journal-submission-bundle`, `content-ssot-guard`, `gpt-image2-ppt`.
