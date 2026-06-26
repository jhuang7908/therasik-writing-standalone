# Module 5 — Patent & sequence IP search

**Status:** Planned (portal listed on [platform.html](https://www.insynbio.com/platform.html))  
**Host:** `write.insynbio.com` (same VPS as Module 2)  
**Project link:** `project_id` → `data/hub/{project_id}.json` asset type `patent` / `patent_sequence`

## Scope (two tracks)

| Track | User goal | External sources (verify API terms) |
|-------|-----------|--------------------------------------|
| **6A Patent search** | Prior art, assignee, CPC/IPC, filing dates | [USPTO PatentsView](https://patentsview.org/apis/api-endpoints), [EPO OPS](https://www.epo.org/en/searching-for-patents/data/web-services/ops), [WIPO PATENTSCOPE](https://www.wipo.int/patentscope/en/), [Lens.org](https://www.lens.org/lens/user/subscriptions) |
| **6B Sequence / molecular** | Antibody CDR, protein, nucleotide hits in patent sequences | WIPO sequence search, USPTO bulk sequence + BLAST, NCBI Patents (E-utilities), optional Abysis / IMGT for antibody numbering crosswalk |

Outputs append to **Facts Summary** (Module 2) — same discipline as protocols.io: **writing material**, not legal conclusions.

## API sketch (writing_memory)

```
GET  /ip/config
POST /ip/patent/search          { username, query, project_id?, limit? }
POST /ip/sequence/search        { username, sequence, seq_type, project_id? }
POST /ip/import_to_facts        { username, hits[], project_id? }
```

Env (future):

- `LENS_API_TOKEN`, `EPO_OPS_CONSUMER_KEY` / `SECRET`, `PATENTSVIEW_API_KEY` (if required)

## Phases

1. **Portal + hub schema** — asset types `patent`, `patent_sequence` (done in repo).
2. **PatentsView keyword MVP** — free-tier patent metadata search → Facts block.
3. **Sequence BLAST** — delegate to NCBI/WIPO with rate limits; antibody projects use ANARCI numbering in reports only.
4. **FTO memo template** — export Markdown from Facts + hits (no automated legal opinion).

## Not in scope (v1)

- Automated freedom-to-operate legal opinions
- Full-text PDF mining of all jurisdictions
- Replacing professional IP counsel

## Related modules

- Module 4 literature → papers; Module 5 → patents & claimed sequences
- Module 1 design → sequence liability / FTO screening before commit
