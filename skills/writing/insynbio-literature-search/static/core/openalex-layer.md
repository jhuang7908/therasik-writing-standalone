# OpenAlex API Layer — InSynBio Literature Search

Adopted from GDM science-skills `literature_search_openalex` (Apache-2.0).
See `vendor/adopted/science-skills/openalex/SKILL_mirror.md`.

## When to Use OpenAlex

| Situation | Action |
|---|---|
| Need free DOI metadata verification (title, year, citations) | `openalex_search` or `doi_verify` workflow |
| Want real-time citation counts for a set of papers | `doi_verify` workflow |
| Need papers on a topic not in the frozen `denovo_corpus` | `openalex_search` workflow |
| Need OA PDF URL for a specific paper | `doi_verify` → check `oa_url` field |
| Resolving author h-index / publication list | `resolve-author` subcommand |

## Priority vs Other Sources

```
Priority  Source               Condition
T1        denovo_corpus SSOT   paper already in corpus JSON + has embeddings
T2        PubMed / Semantic Scholar  when abstract needed + corpus miss
T3        OpenAlex              real-time DOI verify, topic discovery, citation counts
```

OpenAlex is **T3** — always check the frozen corpus and PubMed first; fall back to OpenAlex for gaps.

## Anti-Hallucination Rules (from GDM upstream)

- NEVER invent OpenAlex IDs or DOIs — use `resolve` / `get-work` to look them up
- Report empty results accurately; do NOT fill in from memory
- Always include the OpenAlex work URL in any citation sourced from this layer
- Keep output small: always `--select` key fields + `--per-page ≤ 20`

## Rate Limits

| Mode | Rate | Cost |
|---|---|---|
| Polite pool (email param) | ~10 req/s | Free |
| Premium (API key) | ~10 req/s | $1/day free budget |

Works without `OPENALEX_API_KEY` — set `OPENALEX_EMAIL` env var or edit default in `scripts/insynbio_openalex.py`.
