# ADA245 cohort (`data/ada245`)

## Contents

| Path | Role |
| --- | --- |
| `database/ada_master_245_curated.csv` | Master table: ADA%, sequences, `immuno_tcia_score`, genetics class, evidence fields, etc. |
| `reports/generate_report.py` | Builds static HTML summary charts from the CSV. |
| `statistics/derive_ada10_risk_thresholds.py` | Summarises metrics by **ADA first incidence ≥10%** vs **<10%** (optional per `thera_genetics_class`). Run with `--out-json` / `--out-md` to save outputs locally (not versioned by default). |
| `statistics/derive_ada_risk_index_thresholds.py` | ROC / Youden J **candidate** cutoffs for `immuno_tcia_score` and IMGT **framework-mean** proxy vs binary high ADA (default ≥10%). Optional `--join-natural384` for discovery-platform strata. Needs `scikit-learn`. |
| `statistics/METHODOLOGY_ADA_DEEP_MATRIX.md` | **ADA **：CMC  HPR + AbLang2、AbLang  TCAI ；×。 |
| `statistics/PHAGE_BCELL_SOURCE_STATS.md` / `phage_bcell_source_stats.json` | Observed values for **B-cell Sorting** and **Phage Display** source subsets. Baseline values only; **not** source-specific normal ranges. |
| `statistics/compute_platform_25plus2_stats.py` | Per **discovery_platform** (Humanized / Transgenic / Phage / VHH): **25+2** vocabulary stats — 13/25 keys from ADA rows + full 25 where Natural384 matches; + **IMGT HPR proxy**; AbLang2 pending. Writes `platform_25plus2_stats.json`, `PLATFORM_25PLUS2_STATS.md`. |

## Metric naming (do not conflate)

1. **Production “HPR Index”** (IgG CMC / humanization parity): 9-mer repertoire-style score via **`promb`** `human-oas` style computation (`core/cmc/igg_hpr_ablang.py`). Requires VH+VL sequences.

2. **“HPR” bar in the ADA245 HTML report** — **not** item 1. The chart uses a **germline identity proxy**: mean of `vh_identity_imgt` and `vl_identity_imgt` × 100 (see `generate_report.py`). It is labeled in the report as a **framework-identity display metric** to avoid confusion with the pipeline HPR Index.

3. **AbLang2 paired PLL** — computed on VH+VL in the live stack; not stored as a dedicated column in `ada_master_245_curated.csv` unless you batch-append.

4. **`immuno_tcia_score`** — TCIA-style score already present for a subset of rows; missing values are expected.

## Discovery platform — phage vs B-cell vs transgenic (**do not pool**)

**Natural384** (`natural384_cmc_per_antibody.csv`) tags each antibody with **`discovery_platform`**: `transgenic_animal`, `phage_display`, `human_b_cell_derived`, or `unlabeled`. Those are **different discovery lineages** — use separate reference logic for CMC developability, **and** separate logic when summarising **clinical ADA%** from ADA245.

**ADA245** (`ada_master_245_curated.csv`) includes **`discovery_platform`** for cohort stratification (display labels such as *Humanized (CDR Grafting)*, *Transgenic Mice*, *Phage Display*, *VHH*, etc.). **Do not** merge Natural384 keys onto ADA narratives without an explicit **mapping table** (Natural384 snake_case ≠ ADA245 display strings).

### Why ADA “ranges” cannot be unified across sources

Clinical **`ada_first_pct`** mixes indication, route, assay generation, immunosuppression, and patient population. **Additionally**, antibodies from **transgenic**, **phage**, and **B-cell–derived** backgrounds sit in **different sequence / developability baselines**. Pooling all sources into one ADA histogram or one “normal ADA band” **breaks comparability**. Summaries should be **within-source** (match ADA245 `discovery_platform` first; when joining Natural384, filter **`discovery_platform`** before attaching developability stats).

**Rule:** one source label per row — never add phage + B-cell + transgenic into a single “overall ADA range” for gate-setting.

Crosswalk for atlas-only joins:

| Natural384 `discovery_platform` | Typical meaning |
| --- | --- |
| `transgenic_animal` | Transgenic-animal (e.g. human Ig transgenic) discovery |
| `phage_display` | Phage display |
| `human_b_cell_derived` | Human B-cell lineage libraries (not interchangeable with “sorting” wording alone — use atlas label as SSOT) |
| `unlabeled` | Unknown — exclude from source-specific norms unless imputed with provenance |

## Threshold methodology (owner decision before freezing)

Goal: within each **category** (e.g. `thera_genetics_class`, or `format_type` if added), take antibodies with **ADA first incidence ≥10%** as the “high ADA” slice and derive **reference distributions** for HPR Index, AbLang2, and TCIA — then set screening cutoffs (e.g. percentiles, ROC-oriented trade-offs) from those distributions together with a low-ADA reference slice.

**Current CSV limitation:** HPR Index and AbLang2 are **not** pre-computed columns. Run `derive_ada10_risk_thresholds.py` for **TCIA-only** summaries now; extend the same script after exporting real HPR/AbLang columns from a batch job.

**Empirical note (TCIA on current file):** For rows with both `ada_first_pct` and `immuno_tcia_score`, high-ADA (≥10%) vs low-ADA (&lt;10%) **medians are similar**; do not treat TCIA alone as a strong separator without recomputing on a complete, uniform feature set. This reinforces using **HPR + AbLang + TCIA** jointly once batch scores exist.

## Governance

Frozen thresholds for product gates belong in approved `config/` or registry entries — **not** inferred silently from this README. This folder is **analysis + provenance**, not SSOT for production cutoffs.
