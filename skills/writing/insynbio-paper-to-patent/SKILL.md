---
name: insynbio-paper-to-patent
description: >-
  Evidence-constrained CN patent outline from manuscript SSOT (nature-paper-to-patent
  parity). Attorney review required. Trigger on paper to patent, 论文转专利,
  patent draft, 权利要求书 outline.
version: 1.0.0
---

# insynbio-paper-to-patent

Read **`manifest.yaml`**.

## CLI

```bash
python scripts/insynbio_paper_to_patent.py \
  --input paper/Submission_Package/Manuscript_DeNovo_AI_Landscape_Review_AT.md \
  --out paper/Submission_Package/internal/patent_outline_draft.json
```

## Output

JSON with `invention_title`, `technical_field`, `claims.independent/dependent`, `evidence_constraints`, `disclaimer`.

**Never** ship to CNIPA without patent attorney review.

## vs nature-paper-to-patent

| | nature | insynbio |
|---|--------|----------|
| CN patent format | Yes | **JSON outline + next_steps** |
| Evidence bound | Stated | **source_sections_used + must_not_add** |
| Antibody domain | Generic | **VHH/auto-detect technical_field** |

Outline only — no autonomous full specification generation.
