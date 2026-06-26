# Open-source integrations (writing_memory)

## Installed locally (Windows dev)

| Tool | Role | Endpoints |
|------|------|-----------|
| **Vale 3.14** | AI tone / boilerplate / FILL marker lint | `POST /lint_prose`, auto in `/draft_section` via `purge_boilerplate` |
| **Quarto 1.9** | JSON → QMD → DOCX/HTML/JATS | `POST /render_quarto` |
| **python-docx** | Legacy package export | `POST /export_docx` |

Config: `.vale.ini`, `vale_styles/AbEngineCore/`, `vale_runner.py`, `quarto_runner.py`.

## VPS (systemd deploy) — optional binaries

After `sync-to-vps.ps1`, install on the Linux host if endpoints should work in production:

```bash
# Vale (~12 MB)
curl -fsSL https://github.com/errata-ai/vale/releases/download/v3.14.2/vale_3.14.2_Linux_64-bit.tar.gz \
  | tar -xz -C /usr/local/bin vale

# Quarto (~500 MB) — only if using /render_quarto on server
wget -q https://github.com/quarto-dev/quarto-cli/releases/download/v1.9.38/quarto-1.9.38-linux-amd64.deb
sudo apt install -y ./quarto-1.9.38-linux-amd64.deb

systemctl restart writing-memory
```

Without Vale: `/lint_prose` returns `vale_available: false`; `/purge_boilerplate` still works (regex).

## sciwrite-lint — deferred (Step C)

**Use case:** claim–citation alignment, bibliography integrity, SciLint score.

**Why not on VPS yet:**

- Requires Docker/Podman + **GROBID** + optional **vLLM** (16 GB+ VRAM GPU).
- Heavy for a 2 vCPU / 4 GB writing-memory box.
- Our `/insert_citations` + PubMed already cover existence checks, not full-text claim verification.

**Recommended path:** run sciwrite-lint on owner workstation for final QC; expose results as JSON upload to `/manuscript_qc_score` later.

## academic-research-skills (Cursor)

Installed under `.cursor/skills/academic-research-skills/` for IDE-side paper pipelines (plan → draft → review). Complements API, does not replace `write.insynbio.com`.

## Article-type deep structure (v1.0 — deployed)

- **12 canonical types** in `schemas/article_types/*.json`
- **Journal surface** (abstract BMRC vs single paragraph) in `schemas/journal_surface.json`
- Injected into `/plan_paper` and `/draft_section` via `article_type_context.py`
- **API:** `GET /article_types` — list types and aliases
- **Legacy aliases still work:** `research` → `original_research`, `review` → `review_narrative`, `letter` → `brief_communication`

Example: `target_journal=frontiers_immunology` + `article_type=research` + `section_key=abstract` forces **Background / Methods / Results / Conclusion** subheadings.

Customer workflow (assistive, not autonomous paper factory):

```
客户摘要 + 实验设计 + Figure → /plan_paper → /analyze_figure_quantitative → /draft_section
→ purge_boilerplate → /lint_prose → /export_docx or /render_quarto
```

## Tools we do NOT use for customer drafts

| Project | Why not default |
|---------|-----------------|
| **NanoResearch** | Generates idea → runs synthetic Python experiments → paper. Wrong when customer already has real data/figures. |
| **Idea2Paper** | Paradigm/story skeleton from a one-line idea; no figure upload or wet-lab grounding. |
| **research-agent** | Autonomous literature + thesis from topic; 1–8 h run; not anchored to supplied abstract/figures. |

**Our fit:** customer abstract + figures → `/plan_paper` → `/analyze_figure_quantitative` → `/draft_section` → Vale purge → Quarto DOCX.
