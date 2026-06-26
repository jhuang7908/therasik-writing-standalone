---
name: insynbio-citation
description: >-
  Citation corpus, DOI extract, PubMed verify, RIS/BIB export for reviews
  (nature-citation parity + frozen denovo corpus). Trigger on citation, Zotero,
  RIS export, verify DOI, 查文献, reference library.
version: 1.0.0
---

# insynbio-citation — Router

Read **`manifest.yaml`**. Delegates to `insynbio-literature-search` for corpus depth.

## CLI

```bash
python scripts/insynbio_citation.py build-library
python scripts/insynbio_citation.py extract-dois --input paper/.../Manuscript.md --out dois.json
python scripts/insynbio_citation.py verify --input paper/.../Manuscript.md --out verify_report.json
python scripts/insynbio_citation.py export-zotero-rdf
```

## vs nature-citation

| | nature-citation | insynbio-citation |
|---|---------------|-------------------|
| CNS-focused search | Yes | Via PubMed + corpus |
| Zotero RDF | Yes | **RIS/BIB/RDF in ScholarOne folder + `export-zotero-rdf` CLI** |
| Frozen domain corpus | No | **denovo_literature + Review B library** |
| MISSING ref fetch | Ad hoc | **build_review_b_reference_library.py** |

Golden path: `FULL=39+, MISSING=0` in library summary.
