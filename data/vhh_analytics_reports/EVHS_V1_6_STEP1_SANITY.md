# Engineered VH Similarity — V1.6 Step-1 Sanity

- Prior version: `atlas24_v1.0_2026-04-30`
- Module under test: `core/vh2vhh/engineered_vh_similarity.py`
- Scoring is **additive evidence only**; no V1.5 thresholds were modified.

## 1. Atlas-24 Self-Regression

| Statistic | Value |
|---|---:|
| n | 24 |
| mean | 0.816 |
| median | 0.875 |
| stdev | 0.124 |
| min | 0.455 |
| max | 0.95 |
| high_pct | 83.3 |
| medium_pct | 16.7 |
| low_pct | 0.0 |

| Atlas-24 entry | Score | Band | Motif | CDR3 len | CDR3 charge | Liability flags | Notes |
|---|---:|---|---|---:|---:|---|---|
| `8di5` | 0.95 | high | `VALW` | 10 | -2 | - | Candidate sits inside the Atlas-24 success envelope. |
| `7vnd` | 0.95 | high | `VALW` | 10 | -1 | - | Candidate sits inside the Atlas-24 success envelope. |
| `7ooi` | 0.925 | high | `VGEL` | 16 | 0 | - | Candidate sits inside the Atlas-24 success envelope. |
| `7jwb` | 0.925 | high | `VGEL` | 16 | -2 | - | Candidate sits inside the Atlas-24 success envelope. |
| `7whi` | 0.913 | high | `VTPW` | 10 | -1 | - | Candidate sits inside the Atlas-24 success envelope. |
| `3zhd` | 0.913 | high | `VGPV` | 10 | -1 | - | Candidate sits inside the Atlas-24 success envelope. |
| `7vne` | 0.913 | high | `VAQW` | 10 | -1 | - | Candidate sits inside the Atlas-24 success envelope. |
| `7zf4` | 0.9 | high | `VGPW` | 13 | -2 | - | Candidate sits inside the Atlas-24 success envelope. |
| `7omn` | 0.875 | high | `VGEL` | 16 | -2 | - | Candidate sits inside the Atlas-24 success envelope. |
| `7d5u` | 0.875 | high | `VGRW` | 3 | 1 | - | Candidate sits inside the Atlas-24 success envelope. |
| `6jsz` | 0.875 | high | `VGRW` | 3 | 1 | - | Candidate sits inside the Atlas-24 success envelope. |
| `7f1g` | 0.875 | high | `VGRW` | 3 | 1 | - | Candidate sits inside the Atlas-24 success envelope. |
| `7d5b` | 0.875 | high | `VGRW` | 3 | 1 | - | Candidate sits inside the Atlas-24 success envelope. |
| `6sge` | 0.85 | high | `FERF` | 15 | 0 | any_cdr_nglyc | Candidate sits inside the Atlas-24 success envelope. |
| `7azb` | 0.85 | high | `FERF` | 12 | 3 | - | Candidate sits inside the Atlas-24 success envelope. |
| `3b9v` | 0.776 | high | `VGEW` | 11 | -2 | any_cdr_deamid | Candidate sits inside the Atlas-24 success envelope. |
| `1ol0` | 0.76 | high | `FERI` | 12 | 0 | - | Candidate sits inside the Atlas-24 success envelope. |
| `6j7w` | 0.747 | high | `VGPW` | 10 | -2 | - | Candidate sits inside the Atlas-24 success envelope. |
| `3p9w` | 0.723 | high | `VGEL` | 14 | 2 | any_cdr_deamid | Candidate sits inside the Atlas-24 success envelope. |
| `7eow` | 0.711 | high | `FGRL` | 19 | 0 | - | Candidate sits inside the Atlas-24 success envelope. |
| `5dmj` | 0.685 | medium | `VGLR` | 7 | -2 | - | - |
| `7nfr` | 0.672 | medium | `VGRW` | 8 | -1 | - | - |
| `7vke` | 0.583 | medium | `VERW` | 15 | -1 | cdr3_anchor_risk | - |
| `2x89` | 0.455 | medium | `FERW` | 19 | 1 | any_cdr_deamid,cdr3_anchor_risk | - |

## 2. PD-1 Anti-PD-1 Antibody Control (input VH only)

| Statistic | Value |
|---|---:|
| n | 6 |
| mean | 0.618 |
| median | 0.616 |
| stdev | 0.049 |
| min | 0.552 |
| max | 0.7 |
| high_pct | 16.7 |
| medium_pct | 83.3 |
| low_pct | 0.0 |

| Drug | Score | Band | Motif | CDR3 len | CDR3 charge | Liability flags | Notes |
|---|---:|---|---|---:|---:|---|---|
| Pembrolizumab | 0.616 | medium | `VGLW` | 11 | -1 | any_cdr_deamid | - |
| Nivolumab | 0.552 | medium | `VGLW` | 4 | -2 | any_cdr_deamid | - |
| Toripalimab | 0.7 | high | `VGLW` | 16 | -2 | - | Candidate sits inside the Atlas-24 success envelope. |
| Tislelizumab | 0.65 | medium | `IGLW` | 10 | -1 | - | - |
| Pembrolizumab-alt | 0.616 | medium | `VGLW` | 11 | -1 | any_cdr_deamid | - |
| Camrelizumab | 0.573 | medium | `VGLW` | 7 | -1 | - | - |

## 3. Verification Status

- [verified] Atlas-24 was scored against its own frozen prior (provenance: `vhh_design_atlas_v3.json`).
- [verified] PD-1 VH inputs come from `Reference_Antibodies/` PDBs already used by `scripts/validate_vh2vhh_pd1_panel.py`.
- [inferred] Score banding (high >=0.70 / medium >=0.40 / low <0.40) is a draft mapping for V1.6 reporting.

## 4. Adversarial Checks

- Self-regression bias: scoring Atlas-24 against its own prior is not a proper validation. The check is meant to ensure no degenerate behavior, not accuracy. WARN
- Score saturation: Atlas-24 medians may stay below 1.0 because hallmark/stealth components peak at distinct sub-populations. PASS
- PD-1 input VHs are conventional VH and should score lower; if any score very high, the prior is too permissive. PASS

## 5. Sources

- `data/vhh_design_atlas_v3.json`
- `data/vhh_analytics_reports/ENGINEERED_VH24_SITE_MAP.json`
- `docs/VH_TO_VHH_CONVERSION_STANDARD_V1.5.md`
