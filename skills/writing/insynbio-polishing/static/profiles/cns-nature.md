# CNS / Nature polishing profile v2.0 (nature-polishing Stable parity)

> Router axes: paper_type · section · language · journal  
> Priority: architecture → section job → journal frame → sentence polish

## Core stance (always)

1. **Evidence first** — never invent data, n, p-values, mechanisms, or novelty claims.
2. **Claim → evidence → boundary** — every major sentence triangulates what is shown vs inferred.
3. **Fix structure before diction** — if paragraph logic fails, flag; do not cosmetic-polish.
4. **One job per section** — abstract ≠ discussion; do not paste intro tone into results.

## Voice

- Open with the gap, not field encyclopedia
- One claim per paragraph; supporting sentence follows
- Active verbs: show, demonstrate, reveal, indicate — not "it is important to note"
- Em dashes ≤1 per page; prefer commas or parentheses
- Limit "In contrast" / "However" chains — vary transitions

## Forbidden (auto-scanned via insynbio_polishing.py scan)

`services/writing_memory/style_safety.py` → `AI_MARKER_PHRASES`  
Additional CNS clichés to avoid: delve, tapestry (metaphor), showcase, testament, embark, holistic (undefined)

## Summary paragraph funnel (Nature research / nat-comms intro)

1. Broad context (1 sentence, field scale)
2. Specific bottleneck (1 sentence)
3. Prior attempts + residual gap (1–2 sentences)
4. This work — what was done (1 sentence)
5. Key result + boundary (1–2 sentences)

## Section jobs

| Section | Job | Fail if |
|---------|-----|---------|
| **Abstract** | Background → gap → approach → result → significance | Methods dump or hype without data |
| **Introduction** | Funnel to gap; cite field not textbook | Last paragraph lacks "here we" |
| **Results** | Evidence ladder; figure-led | Experiment laundry list |
| **Discussion** | Interpret ≤ claim; limitations explicit | Restates results without mechanism context |
| **Methods** | Module motivation + forward flow | Parameter list without design rationale |
| **Title** | Specific + outcome hint | Cute but unsearchable |

## Review paper addendum (antibody_therapeutics / invited review)

- Use **evidence grades** (Table 6 style): verified / vendor / indirect / preprint
- Vendor-only claims tagged; no approved-drug language for generative-only pipelines
- Platform names exact; no conflation of training-data access vs weight release

## zh-to-en workflow

- Translate **intent and argument**, not Chinese sentence order
- Keep gene/model/platform tokens in English
- Run `insynbio_rigor.py manuscript` after polish batch

## Platform integration

- Local gate: `python scripts/insynbio_polishing.py scan --input FILE.md`
- Production: write.insynbio.com `/rewrite`, `/reduce_ai_tone` with `<journal_context>`

## LaTeX layout

For float/placement issues (not prose), see nature-polishing `references/latex-layout.md pattern — compile and visually inspect; do not judge from .tex alone.
