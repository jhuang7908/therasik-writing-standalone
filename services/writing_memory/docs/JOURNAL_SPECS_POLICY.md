# Journal Submission Specs & Reference Styles — Curation Policy

> **Rule:** Submission requirements and reference-formatting rules in this
> service are **curated, not generated**. The LLM never authors these
> values. They must always be traceable to the journal's own current
> Instructions for Authors.

This document explains why, and how to maintain them.

---

## Why this is separate from `journal_profiles`

| Concern | `journal_profiles` (LLM-extracted) | `journal_specs` (human-curated) |
|---------|------------------------------------|----------------------------------|
| Source | Aggregated from PMC full text via Claude | Journal's official Instructions for Authors |
| Update cadence | Each profile rebuild (every N new papers) | Whenever the journal updates its rules |
| Confidence | `verified` or `inferred` | `verified` only after a human reads the source page |
| Failure mode | Slightly wrong style profile = imperfect rewrite | Wrong word limit / wrong reference style = **desk reject** |

If a journal changes a rule (e.g., new structured-abstract requirement), the
fix happens in `journal_specs/specs/<journal>.json`, not in Claude prompts.

---

## What lives where

```
services/writing_memory/journal_specs/
├── submission_spec.schema.json              # JSON Schema for /specs/*.json
├── reference_style.schema.json              # JSON Schema for /reference_styles/*.json
├── specs/
│   ├── pnas.json
│   ├── elife.json
│   └── plos_med.json
├── reference_styles/
│   ├── pnas_numbered.json
│   ├── elife_author_year.json
│   └── plos_vancouver.json
├── format_reference.py                      # deterministic renderer
└── __init__.py
```

Each `specs/<journal>.json` references one `reference_styles/<id>.json` by
its `reference_style_id` field.

---

## The Field envelope

Every value inside `specs/<journal>.json` is an instance of:

```json
{
  "value": "...",
  "verification_status": "verified | unverified | out_of_date",
  "source_url": "https://...",
  "verified_by": "<curator handle>",
  "verified_at": "2026-05-24T18:00:00Z",
  "notes": "..."
}
```

Rules:

1. A field starts as `value: null, verification_status: "unverified"` until
   a human reads the journal's official page and fills it in.
2. `verification_status: "verified"` requires `source_url` AND
   `verified_at` AND `verified_by` to be set.
3. Stale specs are flagged `out_of_date`; the API layer must hide them
   from client output until re-verified.
4. The API layer **must refuse** to render `unverified` fields to a
   client-facing surface (e.g., "Submission Checklist" panel). Internal
   tooling may show them with a yellow warning.

---

## Reference styles

Each style file describes:

- **In-text citation** mode (numbered parenthetical / numbered bracketed /
  numbered superscript / author-year parenthetical / author-year narrative).
- **List order** (by appearance, alphabetical, alphabetical-then-chrono).
- **List entry** rules: author list format, et-al threshold, journal title
  abbreviation policy, year position, italics policy, DOI format, etc.

`format_reference.py` is rule-based and deterministic. Given a `Paper`
dataclass (populated from the `papers` table) and a loaded style, it
returns the rendered string for that one entry. The LLM never composes
this string.

For client-facing surfaces, the API layer must:

1. Reject styles whose top-level rule blocks are not all `verified`.
2. Always render references through `format_reference()` against a row
   that was confirmed real (PMID/DOI re-verified per the
   anti-hallucination policy).

---

## Curation workflow

Recommended steps to graduate a journal spec from `unverified` to
`verified`:

1. Open the journal's current Instructions for Authors page (linked under
   `sourced_from`). Capture the URL.
2. Fill in each `value` field. If the journal expresses a value as a
   range (e.g., abstract 250-300 words), store it as a 2-element array.
3. Set `verification_status: "verified"`, `verified_by`, `verified_at`,
   and a precise `source_url` per field (the page that states *this*
   specific rule, not just the home page).
4. Add at least one concrete `examples` entry under
   `reference_styles/<id>.json.list_entry.examples`, copied from the
   journal's own published example or a real PMC article you have read.
5. Add a regression test fixture under `tests/fixtures/references/` (one
   JSON-formatted `Paper` plus its expected rendered string in this
   style). The CI test asserts the renderer output matches.

---

## Sources to consult (starting points only)

These URLs are entry points; the exact subpages with binding rules vary
and must be captured on each curation pass.

- **PNAS** — https://www.pnas.org/author-center
- **eLife** — https://elifesciences.org/author-guide
- **PLOS Medicine** — https://journals.plos.org/plosmedicine/s/submission-guidelines

Additional checklists that the spec may reference but does not embed:

- ICMJE Recommendations (Vancouver) — https://www.icmje.org/recommendations/
- CONSORT, PRISMA, STROBE, ARRIVE, etc. via the EQUATOR Network —
  https://www.equator-network.org/

---

## Versioning

- `spec_version` follows semantic versioning.
- Patch bump (`x.y.Z+1`) on minor wording fixes.
- Minor bump (`x.Y+1.0`) when adding new fields or changing a value.
- Major bump (`X+1.0.0`) when the journal restructures its requirements
  (e.g., introducing a new mandatory article type).
- The active spec for a journal is determined by the API layer reading
  the highest semver in `specs/<journal>.json`. Older versions remain in
  git history for audit.

---

## What is intentionally **out of scope**

- Auto-fetching journal pages and parsing them with an LLM. Doing this
  silently is exactly how out-of-date or hallucinated rules sneak in.
  If a tool is needed, it should produce a **diff against the existing
  spec** for a human to approve, not write the file.
- Cover letters. These are not rules; they belong to writing style.
