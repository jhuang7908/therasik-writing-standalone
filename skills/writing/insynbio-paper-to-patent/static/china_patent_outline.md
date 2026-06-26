# China patent outline — evidence constraints

## Allowed inputs

- Manuscript MD SSOT (Methods, Results, Discussion sections)
- User-provided claim seeds
- Figure/table captions (mechanism only if stated in SSOT)

## Forbidden outputs

- New numerical results not in manuscript
- Fabricated embodiments or examples
- Prior art citations invented by LLM

## Required human gates

1. Patent attorney claim scope review
2. Map each claim element → figure/table in manuscript
3. Prior art search (separate workflow — not this CLI)

## Jurisdiction note

Default `jurisdiction: CN` in JSON; US/EPO requires different skill extension (not in v1.0).
