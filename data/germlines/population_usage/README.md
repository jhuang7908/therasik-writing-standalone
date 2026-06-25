# Human V-gene population usage (naive-blood prior)

## What this is

Tab-separated **relative weights** (not raw counts) for **IGHV**, **IGKV**, and **IGLV** genes. The suite normalises weights **within each segment** to sum to 1, then applies **κ/λ repertoire shares** (defaults: κ 0.63, λ 0.37) so light-chain genes get a **global** `vl_population_usage_frac_global` = P(κ)×P(V|κ) or P(λ)×P(V|λ).

## Limitations

- True allele-level population frequencies differ by ancestry, age, and tissue; naive blood is only one reference.
- Weights are **literature-informed priors** (repertoire reviews + large naive BCR cohorts), **not** a single downloadable machine-readable table from one PMID. Replace this file with cohort-specific frequencies (e.g. OAS / in-house AIRR) when you need publication-grade denominators.
- OR-designation genes (e.g. `IGHV1/OR15-2`, `IGKV2/OR22-4`) are assigned **low** relative weights.

## Files

- `human_v_segment_relative_weights.tsv` — columns: `segment`, `gene`, `weight`

## Code

- `core/resources/germline_population_usage.py` — lookup + optional κ/λ global VL fraction
