# Phage Display / B-cell Sorting ADA Source Statistics

## Verification Status

- [verified] Source file: `data/ada245/database/ada_master_245_curated.csv` currently contains **245** rows and an explicit `discovery_platform` column.
- [verified] Source split used here: `B-cell Sorting` and `Phage Display` only. These categories are **not merged**.
- [verified] This file stores **observed values only**. It does **not** define source-specific normal ranges or production thresholds.
- [inferred] `hpr_proxy_imgt_mean` is used as a temporary 0-1 humanness proxy from `(vh_identity_imgt + vl_identity_imgt) / 2` because the current CSV does not include true `promb` HPR Index or AbLang2 columns.

## Summary

| Source platform | N total | N with ADA | Mean ADA% | Median ADA% | ADA range |
| --- | ---: | ---: | ---: | ---: | ---: |
| B-cell Sorting | 8 | 7 | 2.443 | 3.4 | 0.0-5.0 |
| Phage Display | 7 | 7 | 7.329 | 4.8 | 2.0-20.4 |

## Current Metric Means

| Source platform | hpr_proxy_imgt_mean | GRAVY | Instability index | pI | TCIA |
| --- | ---: | ---: | ---: | ---: | ---: |
| B-cell Sorting | 0.9382 | -0.2903 | 44.1429 | 8.1143 | 0.6668 |
| Phage Display | 0.8827 | -0.2344 | 39.5000 | 7.7514 | 0.6833 |

## ADA Threshold Slices

### B-cell Sorting

| ADA threshold | N_high | hpr_proxy_imgt_mean | GRAVY | Instability index | pI | TCIA |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| >=5% | 1 | 0.8765 | -0.1700 | 44.5000 | 4.6000 | 0.6782 |
| >=10% | 0 | - | - | - | - | - |
| >=15% | 0 | - | - | - | - | - |

### Phage Display

| ADA threshold | N_high | hpr_proxy_imgt_mean | GRAVY | Instability index | pI | TCIA |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| >=5% | 3 | 0.9065 | -0.2480 | 38.7000 | 7.6767 | 0.7698 |
| >=10% | 2 | 0.9238 | -0.2095 | 39.5000 | 8.3450 | 0.7781 |
| >=15% | 1 | 0.9045 | -0.1670 | 38.4000 | 7.8500 | 0.7646 |

## Antibody Lists

**B-cell Sorting:** Bezlotoxumab, Cilgavimab, Nirsevimab, Tixagevimab, Lecanemab, Aducanumab, Atoltivimab, Maftivimab.

**Phage Display:** Lanadelumab, Necitumumab, Camrelizumab, Ranibizumab, Belimumab, Ramucirumab, Sintilimab.

## Interpretation

- B-cell Sorting has very low observed ADA in this snapshot: no antibody is `ADA >= 10%`; only one reaches `ADA >= 5%`.
- Phage Display remains a small cohort and has a higher observed ADA tail in this snapshot, driven by a small number of examples.
- These values are useful as a **baseline table** for later source-aware CMC reference work, but **not enough** to define a source-specific normal range.
- True `promb` HPR Index and AbLang2 should be batch-computed before freezing any normal interval or cutoff.

## Adversarial Checks

- Alternative explanation: lower ADA may reflect indication, dosing, route, assay format, immunosuppression, or follow-up duration rather than discovery platform alone. PASS
- Failure mode: B-cell Sorting (`n_with_ada=7`) and Phage Display (`n_with_ada=7`) are too small for stable percentile normal ranges. PASS
- Boundary condition: `hpr_proxy_imgt_mean` is not the production HPR Index; results must be recomputed once true `promb` HPR and AbLang2 are exported. PASS

## Sources

- `data/ada245/database/ada_master_245_curated.csv`
- `data/ada245/README.md`
