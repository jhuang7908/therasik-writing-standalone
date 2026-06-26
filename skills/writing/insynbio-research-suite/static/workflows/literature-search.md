# Workflow: literature_search

## De novo / Review B vertical (preferred)

```bash
python scripts/build_review_b_reference_library.py
python scripts/denovo_literature/fetch_missing_review_refs.py  # when corpus has MISSING
```

SSOT: `config/denovo_literature_corpus.json` — target FULL, MISSING=0.

## Generic multi-source (nature-academic-search parity)

- PubMed / Europe PMC via project scripts
- Citation verify: `journal-submission-prep/scripts/pubmed_verify.py`
- Export: RIS/BIB under `ScholarOne_Upload/.../03_Literature/`

Delegate: **`insynbio-literature-search`** skill.
