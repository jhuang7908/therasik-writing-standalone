---
name: insynbio-paper2ppt
description: >-
  Hybrid paper-to-PPTX for antibody/de novo and general academic manuscripts.
  Primary: editable python-pptx + speaker notes + QA JSON (beats nature-paper2ppt
  on editability). Optional: gpt-image-2/Gemini hero slides. Paper-type router
  (review evidence-map, discovery, methods). Trigger on paper2ppt, 论文汇报,
  组会PPT, journal club slides, review deck, insynbio ppt.
version: 1.0.0
---

# insynbio-paper2ppt — Router

Read **`manifest.yaml`** first. Load `always_load` + one `paper_type` fragment.

## Mandatory CLI

```bash
python scripts/insynbio_paper2ppt.py \
  --plan <slides_plan.md> \
  --out <deck.pptx> \
  [--paper-type review] \
  [--lang en|zh] \
  [--hero-images-dir <png_folder>]
```

## Agent steps

1. Classify `paper_type` → tell user in one line
2. Draft or update **`slides_plan.md`** (SSOT); use arc from `static/paper_types/`
3. User confirms outline (abbreviated OK for internal runs)
4. Run **`insynbio_paper2ppt.py`** → must get QA **PASS** or explain WARN
5. Optional visual pass via **`gpt-image2-ppt`** → re-run with `--hero-images-dir`

## Exceeds nature-paper2ppt

| Feature | nature-paper2ppt | insynbio-paper2ppt |
|---------|------------------|---------------------|
| Editable text | Yes | Yes (primary path) |
| Speaker notes | Yes | Yes (all slides) |
| QA JSON | Manual self-review | **Automated `.qa.json`** |
| Visual heroes | N/A | **gpt-image2 merge** |
| Domain tables | Generic | Table 6/7 evidence-map arcs |
| SSOT | PDF-centric | **`slides_plan.md` + manuscript MD** |

## Review B example

Plan: `paper/Submission_Package/deck_denovo_review_ppt/slides_plan.md`  
Hero PNGs: `outputs_therasik_gemini_full/images/`
