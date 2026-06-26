# Output and quality rules

## Deliverables (minimum)

| Artifact | Required |
|----------|----------|
| `slides_plan.md` | Yes (SSOT) |
| `*.pptx` editable | Yes |
| `*.qa.json` | Yes |
| Speaker notes | Yes (auto on all slides) |
| `prompts.json` / PNGs | Only if visual path run |

## QA rules (`insynbio_paper2ppt.py`)

- **FAIL** — empty slides, missing pptx, zero bytes
- **WARN** — slide count <8 or >30; title >90 chars; content slides without bullets
- **PASS** — ready for journal club / Zhang review

## Integrity

- No fabricated PMIDs, affinities, or platform claims
- Table numbers and evidence grades must match manuscript SSOT
- Figure slides: embed from `data and figure/Figures/` when files exist; else text summary only

## Language

- Default **English** for OUP/international reviews
- `--lang zh` for internal组会; bilingual notes optional in speaker notes block
