# Boltz-2 Integration for VAM Stage 0

**Status:** Reference deployment for VAM V1.6.1 Stage 0 complex modelling.
**License:** Boltz-1 / Boltz-2 are MIT-licensed (code AND model weights). **Commercial use is fully allowed without per-org negotiation.**

---

## Why Boltz-2

| Tool | License | Commercial-safe | Affinity head | AF3-class accuracy |
|------|---------|-----------------|---------------|---------------------|
| **Boltz-2** | **MIT** | ✅ | ✅ (built-in) | ✅ |
| Boltz-1 | MIT | ✅ | ❌ | ✅ |
| Chai-1 | non-commercial | ❌ requires license | ❌ | ✅ |
| AF3 server | non-commercial only | ❌ **PROHIBITED for production** | ❌ | ✅ |

Boltz-2 is the AbEngineCore-approved Stage 0 PRIMARY tool. See `docs/VIRTUAL_AFFINITY_MATURATION_STANDARD_V1.6.md` §2.4 and `config/vam_antigen_profile.json::_meta.stage0_tool_governance`.

---

## Deployment paths

### Path A — Colab (default for all VAM projects)

For `< 300` aa total complex (PAG-1 + Fv ~250 aa fits comfortably): **Colab free-tier T4 16 GB is sufficient**.

- Notebook: `tools/Boltz/colab/run_boltz2_pag1.ipynb`
- Mount Google Drive for `~/.boltz/` weights cache to avoid re-download every session
- Free tier: ~12 hr session limit, can run ~150 mutants per day with `msa: empty`
- Pro ($10/month): stable T4, 24 hr session, recommended for batch ≥ 50 mutants

### Path B — Local `affmat` env (optional, advanced users only)

```bash
conda activate affmat
pip install boltz
# First run auto-downloads weights to ~/.boltz/ (~2-3 GB)
boltz predict <input.yaml> --out_dir <out>
```

GPU requirement: NVIDIA card with ≥ 16 GB VRAM (RTX 4090 / A4000 or better) for typical antibody complexes.

---

## YAML configuration template (PAG-1 / Scenario A short peptide)

```yaml
version: 1
sequences:
  - protein:
      id: A
      sequence: "<VH_sequence>GGGGSGGGGSGGGGSGGGGS<VL_sequence>"
      msa: empty
  - protein:
      id: B
      sequence: "<PAG1_8aa_ECD>GGGGSGGGGSGGGGS"
      msa: empty
constraints:
  - contact:
      token1: [B, 4]
      token2: [A, 105]   # CDR-H3 centre, project-specific
      max_distance: 8.0
properties:
  - affinity:
      binder: B
```

**Critical settings (per V1.6.1 §2.4):**

- `msa: empty` on **all chains** for Scenario A (short peptide). Antibody MSA pulls germline homologs that contaminate CDR pairing; short peptides have no meaningful homologs.
- `contact` constraint is a *soft* guidance, not a hard restraint. Use to bias search toward known epitope geometry without over-fixing the pose.
- `properties.affinity.binder: B` enables the affinity head; output `affinity_pred_value` and `affinity_probability_binary` feed Stage 7 ensemble vote (weight 0.25, **relative ranking only**).

---

## Acceptance gates (Scenario A short peptide)

V1.6.1 enforces a dual gate for short peptides because AF3-class models exhibit optimistic ipTM bias on `< 15` aa ligands:

| Metric | Threshold | Source |
|--------|-----------|--------|
| ipTM (interface predicted-TM) | ≥ 0.80 | tightened from V1.5.2 default 0.70 |
| PAE (predicted aligned error) at antigen ↔ CDR pairs | < 5.0 Å | V1.6.1 new gate |

If either gate fails:

1. Re-run Boltz-2 with different seed (often resolves convergence issues)
2. If still failing, escalate to HADDOCK3 with sampling = 200 + active-residue restraints (per Scenario A profile)

For Scenarios B / C / D, see `config/vam_antigen_profile.json` for relaxed thresholds.

---

## Affinity head ensemble policy

| Use | Allowed | Forbidden |
|-----|---------|-----------|
| Relative ranking among same-WT mutants | ✅ | — |
| Stage 7 ensemble vote (weight 0.25) | ✅ | — |
| Single-decision metric | — | ❌ |
| Absolute IC50 / Kd predictor | — | ❌ |
| Hapten affinity (Scenario D) | — | ❌ — `affinity` property must be omitted from yaml in Scenario D |

The affinity head training data is sparse on short peptides (`< 15` aa) and not validated on haptens. Always combine with at least 2 orthogonal signals (ESM-IF1 complex score, EvoEF2 reverse-veto residual, MM/GBSA).

---

## Forbidden tools (commercial production)

Per V1.6.1 governance:

- **AF3 server (alphafoldserver.com)** — `non-commercial only` ToS; logged-in jobs are auditable by Isomorphic Labs. **PROHIBITED**. Allowed only for one-off sanity checks that **never** enter any deliverable.
- **Chai-1** without confirmed commercial license — log license artefact in `docs/EVOLUTION_LOG.md` `[OBSERVATION]` before any production run.

Deviations require owner + legal sign-off recorded in EVOLUTION_LOG.

---

## Storage hygiene

Each Boltz prediction emits:

- `predictions/<job_id>.pdb` (~ 50–100 KB)
- `predictions/<job_id>_confidence.json`
- `predictions/<job_id>_pae.npz` (~ 1–10 MB depending on size)
- `predictions/<job_id>_affinity.json` (when affinity head enabled)

Per-mutation runs accumulate quickly. Recommended: stream outputs to Google Drive after each prediction; clean Colab `/content/` between batches.

---

## References

- Boltz GitHub: https://github.com/jwohlwend/boltz (MIT)
- Boltz-2 paper: Boltz Team 2025 (preprint)
- VAM V1.6 standard: `docs/VIRTUAL_AFFINITY_MATURATION_STANDARD_V1.6.md`
- Tools registry: `config/tools_registry.json::tools.Boltz-2`
- Antigen profile: `config/vam_antigen_profile.json`
