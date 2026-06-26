# InSynBio Research Skills — Shared Principles

1. **SSOT first** — Manuscript MD, `slides_plan.md`, literature corpus JSON, and submission profiles are source of truth; generated DOCX/PPTX/audit JSON are derivatives.
2. **Executable over prose** — Every skill must name a CLI, script path, or profile ID that produces a file artifact.
3. **Router + manifest** — Complex skills load `manifest.yaml` fragments on demand (pattern from nature-skills v2.0).
4. **Vertical depth** — Antibody / de novo / humanization domain rules beat generic Nature templates when they conflict.
5. **Dual deliverables** — Client-facing content passes `content-ssot-guard`; submission bundles pass `build_submission_bundle` audit.
6. **No fabrication** — Literature, metrics, and figure claims must trace to corpus, PMID/DOI, or user-provided SSOT.
7. **Hybrid media** — Default: **editable python-pptx** for talks; optional **gpt-image-2 / Gemini** hero slides for visual polish.
8. **Learn from nature-skills** — Before extending any `insynbio-*` module, read the upstream `nature-*` counterpart per `_shared/core/nature-skills-learn-protocol.md` and update `nature-skills-adopt-matrix.md`.
