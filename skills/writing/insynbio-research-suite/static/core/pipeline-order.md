# Mandatory pipeline order (do not skip gates)

> Applies to **all PubMed-indexed biomedical / life science domains** — 80+ sub-domains
> across 12 MeSH categories. See `static/core/biomedical-domains.md` for full taxonomy.
> Domain-specific bundle gates are noted in Step 11 and the domains file.

## Full manuscript → submission → talk

1. **Domain detect** — Read `static/core/biomedical-domains.md`; identify domain from user context.
2. **Literature SSOT** — `insynbio-literature-search` → corpus JSON; verify missing = 0 (or documented).
   - T1: frozen corpus (if domain has one)  →  T2: PubMed / Semantic Scholar  →  T3: OpenAlex
3. **Manuscript MD** — single SSOT under `paper/<project>/` or user-specified path.
4. **Style Calibration (optional)** — `style_calibration` workflow if user provides ≥ 3 past papers.
5. **Write / draft** — `academic-paper` (ARS) + `writing_memory`; 12-agent pipeline, all 6 paper types.
6. **Fact gate** — `content-ssot-guard` / `content_studio_rigor.py` on MD (exit 0).
   - Antibody papers: additionally run `insynbio-rigor` AbEngineCore gate.
7. **Integrity audit** — `academic-paper-reviewer` pre-submission review (ARS).
8. **Word typeset** — journal formatter; FINAL via Pandoc when required.
9. **Expert sign-off** — corresponding author approval (human gate).
10. **Material Passport snapshot** — `scripts/insynbio_material_passport.py --snapshot` (optional; enables cross-session resume).
11. **Submission bundle** — `journal-submission-bundle` → audit **PASS**.
    Domain-specific reporting checklist (see `biomedical-domains.md` §Domain-Specific Gates):
    - Clinical trials: CONSORT / STROBE / PRISMA
    - Epidemiology / Systematic review: PRISMA, GRADE evidence level
    - Computational / Methods: code + data availability, reproducibility statement
    - Structural biology: PDB deposition accession
    - Gene therapy / Editing: biosafety statement, off-target reporting
    - Animal studies: ARRIVE 2.0, IACUC statement
    - Human studies: IRB/ethics statement, informed consent declaration
    - Omics datasets: GEO / dbGaP / ENA accession
    - Vaccines: regulatory classification note
12. **Presentation** — `insynbio-paper2ppt` editable deck + optional `gpt-image2-ppt` heroes.

## Presentation-only (from finished manuscript)

1. Write / update `slides_plan.md` (human review).
2. `python scripts/insynbio_paper2ppt.py --plan slides_plan.md --out deck.pptx`
3. Optional: `--backend gemini-image` → hero images.
4. QA JSON must be PASS or documented WARN.

## Style Calibration path (new project with author sample papers)

1. User provides 3+ past papers (PDF, DOCX, MD, or pasted text).
2. `style_calibration` workflow → 6-dimension Style Profile JSON.
3. Profile stored in project folder, consumed by `academic-paper` draft agent.
4. Discipline conventions always override personal style preferences.

## Material Passport path (long multi-session project)

1. Initialize: `python scripts/insynbio_material_passport.py --init --project <name> --domain <domain>`
2. After each major stage: `--checkpoint --stage <n>`
3. Resume in new session: `--resume --project <name>`
4. Exports cross-session state compatible with ARS `resume_from_passport`.

## Anti-patterns

- Upload to ScholarOne before bundle audit PASS
- Image-only PPTX as sole deliverable when user needs editable slides
- LLM-invented references without corpus or OpenAlex verify
- Running antibody-specific modules (AbEngineCore) on non-antibody manuscripts
- Skipping domain detection step — leads to wrong fact-gate and bundle-audit profiles
- Skipping Style Calibration on manuscripts where author has past papers available
