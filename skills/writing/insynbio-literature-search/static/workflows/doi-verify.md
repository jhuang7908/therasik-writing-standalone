# Workflow: doi_verify

**Trigger:** User provides a list of DOIs to verify (confirm existence, fetch metadata, check OA status).

## Steps

1. **Collect DOIs** — from user message or file. Write one DOI per line to a temp file if not already.
2. **Run batch verification:**
   ```powershell
   python scripts/insynbio_openalex.py verify-dois \
     --dois-file <path/to/dois.txt> \
     --out data/denovo_literature/doi_verify_<slug>.json
   ```
3. **Parse results:**
   - `status: found` → confirm title, year, cited_by_count, oa_url
   - `status: not_found` → flag to user as "DOI not resolved in OpenAlex"
4. **Report** — show summary table: DOI | status | title (truncated) | year | citations | OA?
5. **Never fabricate** — any `not_found` DOI must be reported as unverified, not guessed from context.

## Common inputs
- Reference list from manuscript draft
- DOI list from `data/denovo_literature/papers_raw/*.json`
- DOIs from user-pasted bibliography

## Merge with corpus
After verification, confirmed DOIs can be enriched in `config/denovo_literature_corpus.json`
using `build_review_b_reference_library.py --enrich-from-openalex`.
