# Workflow: submission_bundle

Prerequisites: expert-approved manuscript DOCX/MD.

```bash
python scripts/build_submission_bundle.py --list-profiles
python scripts/build_submission_bundle.py \
  --profile antibody_therapeutics_scholarone_review \
  --workspace paper/Submission_Package
```

- Exit 0 = PASS only for upload
- Read `submission_audit/<profile>/SUBMISSION_AUDIT.md`
- Never copy `.md`/`.json` into `ScholarOne_Upload/`

Delegate: **`journal-submission-bundle`** skill.
