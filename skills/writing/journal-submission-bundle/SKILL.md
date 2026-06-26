---
name: journal-submission-bundle
description: >-
  Last-mile journal submission package: select journal + submission system profile
  (ScholarOne, Editorial Manager, etc.), build upload bundle per curated requirements,
  run PASS/WARN/FAIL audit. Use for 投稿包, ScholarOne upload, Editorial Manager,
  submission bundle audit, antibody therapeutics OUP, prepare manuscript for upload.
---

# Journal Submission Bundle (last mile)

Builds and audits **upload-ready folders** from curated **journal + platform profiles** — not generic DOCX formatting alone.

## When to use

- Manuscript is **expert-approved** (corresponding author sign-off)
- Target **journal** and **submission system** are known
- Need **ScholarOne / Editorial Manager** file layout + pre-upload audit

## Do NOT use for

- Drafting manuscript content → `academic-paper` or project pipeline
- PubMed reference verification only → `journal-submission-prep` Module 1
- Upload before internal/expert review

## Quick start

```bash
# List profiles (journal × system)
python scripts/build_submission_bundle.py --list-profiles

# Review B → Antibody Therapeutics / ScholarOne
python scripts/build_submission_bundle.py \
  --profile antibody_therapeutics_scholarone_review \
  --workspace paper/Submission_Package

# Audit only (after manual edits)
python scripts/build_submission_bundle.py \
  --profile antibody_therapeutics_scholarone_review \
  --workspace paper/Submission_Package \
  --audit-only
```

Exit codes: `0` = PASS, `1` = FAIL, `2` = WARN.

## Architecture

| Layer | Path |
|-------|------|
| **Profiles** | `services/writing_memory/submission_bundle/profiles/*.json` |
| **Content specs** | `services/writing_memory/journal_specs/specs/<journal>.json` |
| **CLI** | `scripts/build_submission_bundle.py` |
| **Audit output** | `<workspace>/submission_audit/<profile_id>/SUBMISSION_AUDIT.{json,md}` |
| **Upload folder** | `<workspace>/ScholarOne_Upload/` or `EditorialManager_Upload/` |

Profiles define: required files, forbidden types (no `.md`/`.json` in upload tree), figure DPI, upload order, build recipe.

## Workflow (mandatory order)

1. **Expert review** — corresponding author approves manuscript MD/DOCX
2. **Build** — `build_submission_bundle.py --profile …`
3. **Audit** — overall must be **PASS** (or documented WARN exceptions)
4. **Manual** — cover letter date, portal metadata, COI forms
5. **Upload** — follow `README.txt` in bundle + `SUBMISSION_AUDIT.md`

## Adding a new journal

```powershell
# Step 0 — identify which system the journal uses
python scripts/insynbio_submission_system.py identify "<Journal Name>"

# Step 1 — get submission checklist with direct links
python scripts/insynbio_submission_system.py checklist "<Journal Name>" --out checklists/<slug>.md

# Step 2 — scaffold profile skeleton (FILL_ME fields must be filled manually)
python scripts/insynbio_submission_system.py new-profile "<Journal Name>" --type review
# → creates services/writing_memory/submission_bundle/profiles/<id>.json

# Step 3 — fill FILL_ME fields from official author guidelines (URL shown in scaffold output)
# Step 4 — register in profiles/index.json
# Step 5 — test audit on a real bundle
python scripts/build_submission_bundle.py --profile <profile_id> --audit-only
```

**Platform-level technical requirements (file formats, figure DPI, upload workflow):**
- ScholarOne: `services/writing_memory/submission_bundle/platforms/scholarone_standard.md`
- Editorial Manager: `services/writing_memory/submission_bundle/platforms/editorial_manager_standard.md`

**Never LLM-generate profile JSON word counts or figure limits** — extract from official guidelines, mark `sourced_from`, owner verifies.

## Active profiles

| profile_id | Journal | System | Recipe |
|------------|---------|--------|--------|
| `antibody_therapeutics_scholarone_review` | Antibody Therapeutics (OUP) | ScholarOne | `denovo_antibody_therapeutics_review_b` |
| `plos_one_editorial_manager_research` | PLOS ONE | Editorial Manager | `generic_manuscript_bundle` |

## Integration

- Legacy: `paper/Submission_Package/prepare_scholarone_bundle.py` → calls this system
- Overlaps with `journal-submission-prep` (DOCX/PubMed) — run **content prep first**, then **this skill for upload bundle**

## Agent obligations

1. Always `--list-profiles` or read profile JSON before building
2. Never upload `submission_audit/`, source `.md`, or `Admin/` to ScholarOne
3. Report audit FAIL items with file paths
4. Cite profile `sourced_from` URLs when explaining requirements to user
