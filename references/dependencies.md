# Dependencies

## Dependency Classes

Use three classes:

- `REQUIRED`: the workflow cannot run its current Phase 1 checks without it.
- `RECOMMENDED`: needed for submission-grade output or stronger QA.
- `OPTIONAL_PROVIDER`: needed only when a specific external service is enabled.

## Required For Phase 1 Internal Self-Use

| Dependency | Class | Purpose | Install / Configure |
| --- | --- | --- | --- |
| Python 3.10+ | REQUIRED | Run project creation, workflow runner, validation, and regression tests | Use the bundled Codex Python or system Python |
| `python-docx` | REQUIRED | Generate baseline DOCX output | `pip install -r requirements.txt` |
| `reportlab` | REQUIRED | Generate baseline PDF output from Markdown | `pip install -r requirements.txt` |
| `PyYAML` | REQUIRED | Skill metadata and future config parsing | `pip install -r requirements.txt` |

## Recommended For Submission-Grade Rendering

| Dependency | Class | Purpose | Install / Configure |
| --- | --- | --- | --- |
| LibreOffice / `soffice` | RECOMMENDED | Convert DOCX to PDF with Word-like layout fidelity | Install LibreOffice and ensure `soffice` is on PATH |
| `pypdfium2` | RECOMMENDED | Render PDF pages to images for full-page visual QA | `pip install -r requirements.txt` |
| Poppler | RECOMMENDED | Alternative PDF rendering and inspection | Install via OS package manager |
| Journal Word templates | RECOMMENDED | Journal-specific formatting and layout QA | Store under a future `assets/journal-templates/` directory |

## Recommended For Literature and Reference QA

| Dependency | Class | Purpose | Configure |
| --- | --- | --- | --- |
| PubMed/Entrez | RECOMMENDED | PMID/PMCID lookup, publication metadata, related articles | API key optional; put in `.env` if used |
| Crossref or DOI resolver | RECOMMENDED | DOI validation and metadata comparison | Configure endpoint/key if needed |
| OpenAlex | RECOMMENDED | Bibliographic metadata, citation context, similar literature | Configure endpoint/key if needed |
| Unpaywall | OPTIONAL_PROVIDER | Full-text discovery by DOI | Requires email/API configuration |

## Optional For Figure Generation

| Dependency | Class | Purpose | Configure |
| --- | --- | --- | --- |
| OpenAI image generation | OPTIONAL_PROVIDER | Raster publication-style figure drafts | Provider API key in `.env` |
| Other image provider | OPTIONAL_PROVIDER | Alternative raster figure generation | Provider-specific key in `.env` |
| BioRender | OPTIONAL_PROVIDER | Human-editable final figure production | User-side account/license |
| SVG/vector editor | OPTIONAL_PROVIDER | Post-generation editable figure reconstruction | Inkscape, Illustrator, Figma, or equivalent |

## Deployment Profiles

### Profile A: Internal Codex Self-Use

Minimum viable setup:

1. Keep `therasik-academic-writing-suite/` as the skill package.
2. Use bundled Codex Python or install Python 3.10+.
3. Install `requirements.txt`.
4. Run `validate_basic_skill.py`.
5. Run `run_regression_tests.py`.

### Profile B: Local MCP For Claude/Codex/Other Clients

Additional setup:

1. Keep the skill package local.
2. Expose `create_project_from_template.py`, `run_full_workflow.py`, and `record_learning_event.py` through an MCP server.
3. Mount project folders with read/write permission.
4. Keep `.env` local and never expose raw keys to clients.
5. Return workflow audit JSON as the MCP response.

### Profile C: Cloud Sandbox / Remote API

Additional setup:

1. Install all Phase 1 required dependencies in the sandbox image.
2. Add LibreOffice and PDF rendering dependencies for submission-grade output.
3. Store API keys in server-side secrets.
4. Expose a reverse-proxy API key to clients, not provider keys.
5. Save project artifacts in isolated per-customer workspaces.
6. Enforce deletion/retention policy before external use.

## Secret Handling

- Never commit `.env`.
- Never commit provider API keys.
- Use `.env.example` for configuration names only.
- In MCP/cloud mode, clients should receive only your issued access token, not upstream provider keys.
