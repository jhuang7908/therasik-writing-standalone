# Workflow: full_pipeline

Run in order (see `static/core/pipeline-order.md`):

1. `insynbio-literature-search`
2. Manuscript MD SSOT + `content-ssot-guard`
3. `format_*_submission.py` or journal-submission-prep
4. `academic-paper-reviewer` (optional pre-submission)
5. Expert sign-off
6. `journal-submission-bundle`
7. `insynbio-paper2ppt`

For orchestrated multi-stage with checkpoints: **`academic-pipeline`** (ARS).

Golden reference: Review B `paper/Submission_Package/` tree.
