# Workflow: material_passport — Cross-Session Manuscript State Tracker

**Adopted from:** ARS `academic-pipeline` Material Passport (Schema 9, v3.9.4).  
**Applies to:** Any biomedical domain, any multi-session manuscript project.

## Purpose

The Material Passport tracks manuscript state across sessions so long-running projects
(weeks → months) can resume cleanly. It records:

- What stage the manuscript is at (1–12, matching `pipeline-order.md`)
- Which decisions were made at each boundary
- Key artifacts (corpus JSON, manuscript MD path, FINAL.docx, bundle path)
- Style Profile reference (if style calibration was run)
- Author-facing audit log (human-readable; not algorithm internals)

## When to Use

- Projects spanning multiple sessions (>1 day of active work)
- Multi-author collaborations with hand-off points
- When using ARS `academic-pipeline` Mode B (phase-by-phase, cross-session resume)
- Any project requiring a reproducible audit trail for corresponding-author sign-off

## Passport JSON Schema (InSynBio adaptation of ARS Schema 9)

```json
{
  "passport_version": "1.0",
  "project": "<name>",
  "domain": "<biomedical domain>",
  "target_journal": "<journal name or null>",
  "created_at": "<ISO timestamp>",
  "updated_at": "<ISO timestamp>",
  "current_stage": 3,
  "stages": {
    "1": {"name": "literature_ssot", "status": "complete", "artifact": "config/corpus.json", "completed_at": "..."},
    "2": {"name": "manuscript_md", "status": "complete", "artifact": "paper/<project>/manuscript.md", "completed_at": "..."},
    "3": {"name": "fact_gate", "status": "in_progress", "artifact": null, "started_at": "..."},
    "4": {"name": "word_typeset", "status": "pending"},
    "5": {"name": "expert_signoff", "status": "pending"},
    "6": {"name": "submission_bundle", "status": "pending"},
    "7": {"name": "presentation", "status": "pending"}
  },
  "style_profile": "projects/<name>/style_profile.json",
  "decisions": [
    {"stage": 2, "decision": "Use existing FINAL.docx as SSOT", "decided_at": "...", "by": "author"}
  ],
  "claims": [
    {
      "claim_id": "C1",
      "text": "Our method reduces false positives by 40%",
      "source_section": "Results §3.2",
      "evidence": [{"type": "figure", "ref": "Fig. 3A"}, {"type": "citation", "doi": "10.xxxx/..."}],
      "status": "verified"
    }
  ],
  "artifacts": {
    "corpus_json": "config/insynbio_research_projects.json",
    "manuscript_md": "paper/<project>/manuscript.md",
    "final_docx": null,
    "bundle_dir": null,
    "pptx": null
  },
  "ars_resume_hash": null,
  "notes": []
}
```

## CLI

```powershell
# Initialize passport for a new project
python scripts/insynbio_material_passport.py --init --project my_crispr_paper --domain gene_therapy

# Record a checkpoint after completing a stage
python scripts/insynbio_material_passport.py --checkpoint --project my_crispr_paper --stage 2 \
  --artifact paper/my_crispr_paper/manuscript.md

# Add a key claim for evidence tracking
python scripts/insynbio_material_passport.py --add-claim --project my_crispr_paper \
  --claim "Off-target editing rate < 0.1%" \
  --section "Results §2.3" \
  --evidence "Fig. 2B, Table S3"

# View current state (summary)
python scripts/insynbio_material_passport.py --status --project my_crispr_paper

# Resume in new session (prints current stage + pending tasks)
python scripts/insynbio_material_passport.py --resume --project my_crispr_paper
```

## Integration with ARS academic-pipeline

When using ARS `academic-pipeline` Mode B:

1. After each ARS stage completes with `ARS_PASSPORT_RESET=1`:
   - Copy the ARS passport hash to `ars_resume_hash` in our passport
   - Update `current_stage` to match ARS stage number
2. To resume: run `--resume` first to see our state, then use ARS `resume_from_passport=<hash>`
3. Conflict rule: our passport records human decisions; ARS passport handles agent context reset

## Claim Evidence Chain

The `claims` array enables a lightweight claim-to-evidence audit:

- Each major conclusion in the manuscript should have a `claims` entry
- `status`: `pending` → `cited` → `verified` (after reviewer check)
- At submission time: run `--verify-claims` to flag any uncited claims

```powershell
python scripts/insynbio_material_passport.py --verify-claims --project my_crispr_paper
# Outputs: PASS (all claims cited) or list of uncited claims
```

## Domain-Specific Stage Notes

| Domain | Stage 6 bundle extras |
|---|---|
| Clinical / Translational | CONSORT/STROBE/PRISMA checklist required |
| Computational | Code availability statement + GitHub link |
| Structural biology | PDB accession + data deposition letter |
| Gene therapy | IND/regulatory status note |
| Antibody engineering | CMC developability note if preclinical |
