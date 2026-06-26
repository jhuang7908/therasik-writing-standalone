---
name: insynbio-paper-reader
description: >-
  Bilingual paper reader with figure map, Kimi/DeepSeek translation, and rigor QC
  (nature-reader parity+). Trigger on paper reader, 全文对照, bilingual reader.
version: 1.1.0
---

# insynbio-paper-reader

Read **`manifest.yaml`**.

## CLI

```bash
python scripts/insynbio_paper_reader.py \
  --input paper/Submission_Package/Manuscript_DeNovo_AI_Landscape_Review_AT.md \
  --out paper/Submission_Package/reader/manuscript_reader.md \
  --translate kimi \
  --qc-out paper/Submission_Package/reader/manuscript_reader.qc.json
```

## Rigor (Layer F)

- Auto **figure/table map**
- Translation: no new facts; uncertain → `[未验证]`
- Pair with `insynbio_rigor.py manuscript` on EN source

## vs nature-reader

| | nature-reader | insynbio-paper-reader |
|---|---------------|----------------------|
| Anchor TOC | Yes | Yes |
| Figure map | Yes | **+ qc.json** |
| Bilingual | Yes | **Kimi/DeepSeek** |
| Rigor link | Manual | **insynbio-rigor** |
