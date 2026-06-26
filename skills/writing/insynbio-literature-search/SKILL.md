---
name: insynbio-literature-search
description: >-
  Literature search and citation SSOT for InSynBio reviews: frozen denovo corpus,
  PubMed verify, RIS/BIB export, multi-source fallback (nature-academic-search
  parity + vertical depth). Trigger on 文献检索, denovo literature, reference
  library, verify DOI, 查文献, citation audit.
version: 1.0.0
---

# insynbio-literature-search — Router

Read **`manifest.yaml`**. Pick workflow: `denovo_corpus` | `verify_citations` | `multi_source`.

## Review B (golden)

```bash
python scripts/build_review_b_reference_library.py
# Expect: FULL=39+, MISSING=0 in summary
```

Corpus: `config/denovo_literature_corpus.json`  
Outputs: `ScholarOne_Upload/Review_B_DeNovo/03_Literature/*.ris|bib`

## vs nature-academic-search

| | nature | InSynBio |
|---|--------|----------|
| MCP PubMed/CrossRef | Yes | Use when MCP available |
| **Frozen domain corpus** | No | **Yes** |
| ScholarOne RIS export | Manual | **Automated in build script** |
| MISSING ref fetch | Ad hoc | **`fetch_missing_review_refs.py`** |

PubMed verify: `~/.cursor/skills/academic-research-skills/journal-submission-prep/scripts/pubmed_verify.py`
