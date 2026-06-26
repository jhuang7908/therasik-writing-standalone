# Workflow: openalex_search

**Trigger:** User requests topic-based literature search not covered by frozen `denovo_corpus`.

## Steps

1. **Clarify scope** — topic string, year range, max results (default 10).
2. **Run search:**
   ```powershell
   python scripts/insynbio_openalex.py search \
     --topic "<query>" \
     --per-page 10 \
     --year-from 2022 \
     --out data/denovo_literature/openalex_search_<slug>.json
   ```
3. **Review output** — present to user: title, year, DOI, cited_by_count, is_oa.
4. **Optional: add to corpus** — if user approves, append entries to `config/denovo_literature_corpus.json` via `build_review_b_reference_library.py`.
5. **Cite source** — always state "via OpenAlex" in the output; include work URLs.

## Output fields (default select)
`id · doi · title · publication_year · cited_by_count · primary_location · open_access`

## Anti-hallucination gate
- Do NOT report titles or DOIs that were not returned by the API.
- If API returns 0 results, say so — do NOT substitute from memory.
