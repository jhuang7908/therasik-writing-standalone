Status: PENDING

# Figure Contract QA

This file is populated automatically by `scripts/qa/run_figure_contract_qa.py`.

To run manually:
  python scripts/qa/run_figure_contract_qa.py --project-root <project_dir>

Requirements for each figure:
  - figure_id: unique identifier
  - core_conclusion: the main scientific claim this figure supports (>= 5 words)
  - evidence_chain: list or description of evidence panels
  - export_format: svg, pdf, or png (editable preferred for journal submission)

Declare figures in: 00_project_database/figures.csv

Until this gate is run and passes, the workflow will not proceed to SUBMISSION_READY.
