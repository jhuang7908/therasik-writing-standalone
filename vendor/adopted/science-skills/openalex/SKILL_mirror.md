<!-- ADOPTED FROM: vendor/science-skills/skills/literature_search_openalex/SKILL.md
     UPSTREAM COMMIT: 33557e0f1faf0f281d255940de58935c61b2143b (2026-06-08)
     MIRRORED: 2026-06-21
     ADAPTER: scripts/insynbio_openalex.py (InSynBio wrapper, no uv dependency)
     SCOPE: OpenAlex free/premium API for literature search & DOI verification
-->

# OpenAlex — InSynBio Adoption Summary

## Source
`vendor/science-skills/skills/literature_search_openalex` (GDM science-skills, Apache-2.0)

## What We Adopted

| GDM concept | Our implementation |
|---|---|
| `resolve <entity> <query>` | `insynbio_openalex.py resolve --query` |
| `filter works --search` | `insynbio_openalex.py search --topic` |
| DOI batch lookup | `insynbio_openalex.py verify-dois --dois-file` |
| No hallucination rule | Enforced by `core/integrity/hallucination_guard.py` |
| `--select` + `--per-page` for small output | Default `per_page=10`, `select=id,doi,title,publication_year,cited_by_count` |

## Key differences from GDM upstream

- Uses `requests` directly (no `uv` dependency) — standard `affmat`/`anarcii` envs have requests
- API key read from `config/standards_ssot.json → openalex_email` (polite-pool) or env var `OPENALEX_API_KEY`
- Output is JSON that feeds directly into `build_review_b_reference_library.py` citation pipeline
- Rate-limit: polite pool (email param), no budget tracking needed for < 1000 queries/day

## CLI Entry Point

```powershell
python scripts/insynbio_openalex.py search --topic "de novo antibody design" --per-page 10
python scripts/insynbio_openalex.py verify-dois --dois-file data/denovo_literature/dois.txt
python scripts/insynbio_openalex.py get-work --doi "10.1038/s41586-023-06415-8"
```
