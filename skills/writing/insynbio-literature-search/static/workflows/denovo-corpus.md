# Workflow: denovo_corpus

```bash
python scripts/build_review_b_reference_library.py
python scripts/denovo_literature/fetch_missing_review_refs.py  # if MISSING > 0
```

Gate: **MISSING=0** before manuscript cite freeze or ScholarOne upload.
