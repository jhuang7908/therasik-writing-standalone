---
name: insynbio-rigor
description: >-
  Scientific rigor & accuracy framework: multi-layer gates (architecture, local scan,
  multi-model content rigor, formal report validator, submission audit). How DeepSeek,
  Kimi, Claude, Gemini each evaluate format/authenticity/science. Trigger on 严谨性,
  科学性, rigor gate, fact check, verification status, content-ssot-guard.
version: 1.0.0
---

# insynbio-rigor — Scientific accuracy framework

Read **`manifest.yaml`** and `static/rigor-layers.md`.

## Quick CLI

```bash
# Manuscript MD — 4 local dimensions + optional polish/reliability
python scripts/insynbio_rigor.py manuscript \
  --input paper/Submission_Package/Manuscript_DeNovo_AI_Landscape_Review_AT.md \
  --with-polish-scan --out submission_internal/manuscript_rigor.json

# Document the full stack (layers A–F)
python scripts/insynbio_rigor.py stack --out docs/insynbio_rigor_stack.json

# Social / NextVivo bundle (3 dimensions)
python scripts/openai_content_rigor.py --article ... --deck ... --social ...

# Formal client report
python scripts/validate_report_reliability.py --file report.md --client

# Submission physical audit
python scripts/build_submission_bundle.py --profile ... --audit-only
```

## Four dimensions (content gate)

| Dimension | What it checks | Typical owner |
|-----------|----------------|---------------|
| **Format** | SSOT fields, section structure, brand rules | Gemini / OpenAI chain |
| **Authenticity** | Numbers/PMIDs trace to source; no fabrication | Kimi + corpus |
| **Scientific rigor** | Terminology, overclaim, evidence grade | Claude + domain SSOT |
| **AI tone** | Marker phrases, hedge abuse | Local scan + reduce_ai_tone |

## Model roles (independent evaluators)

| Model | Primary rigor role | Not sole authority for |
|-------|-------------------|------------------------|
| **DeepSeek** | Draft + fix loop; cheap iteration | Final PMID verification |
| **Kimi** | Long-context fact compare; CN translation check | English journal polish |
| **Claude** | Platform polish; rigor chain; prose QC | Corpus ingest |
| **Gemini** | Rigor chain fallback; slide visual QC | Citation database |

**Rule:** No single model SHIPs alone — chain or layered JSON gates required.

## Exit codes

- `insynbio_rigor.py manuscript` → 0 PASS, 1 FAIL
- `openai_content_rigor.py` → FAIL blocks render
- `build_submission_bundle.py` → 0 PASS, 1 FAIL, 2 WARN
