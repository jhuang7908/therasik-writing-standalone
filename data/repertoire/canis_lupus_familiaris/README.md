## Canine population priors (BCR repertoire + DLA)

This folder is a **data support layer** for dog caninization decisions.

It is intended to host **large-scale** population statistics exported from external sources
(e.g., curated tables that Gemini found from papers / supplementary datasets), so that:

- **V/J usage priors** can be used as a population-level scaffold prior.
- **DLA allele frequencies** can define a realistic “core allele panel” for dog immunogenicity checks,
  optionally stratified by breed / population.

### Recommended canonical files

- `vj_usage_by_population_v1.csv`
- `dla_allele_frequencies_by_population_v1.csv`
- `dog_population_priors_v1.json` (normalized aggregate used by scripts)

### CSV schema: `vj_usage_by_population_v1.csv`

Minimum columns (header row required):

- `dataset_id`: string (e.g., `paper_2018_IGH_repertoire_ngs`)
- `population`: string (e.g., `AKC_25_breeds`, `Labrador`, `Mixed`)
- `n_samples`: integer (number of dogs / repertoires)
- `locus`: string (e.g., `IGHV`, `IGHJ`, `IGKV`, `IGKJ`, `IGLV`, `IGLJ`)
- `gene`: string (IMGT gene id preferred, e.g., `IGHV3-67*01`)
- `count`: integer (raw observations; optional if `frequency` provided)
- `frequency`: float (0..1; optional if `count` provided)
- `notes`: string (optional)

### CSV schema: `dla_allele_frequencies_by_population_v1.csv`

Minimum columns:

- `dataset_id`: string (e.g., `AKC_2005_25breeds`)
- `population`: string (breed name or pooled group)
- `n_samples`: integer
- `locus`: string (`DLA-DRB1`, `DLA-DQA1`, `DLA-DQB1`)
- `allele`: string (e.g., `DLA-DRB1*01501`)
- `count`: integer (optional if `frequency` provided)
- `frequency`: float (0..1; optional if `count` provided)
- `notes`: string (optional)

### Integration points in this repo

- `data/germlines/canis_lupus_familiaris_ig_aa/dog_repertoire_and_dla_stats.json`
  stores the **curated “core” facts** (summary + core panel) used in reports.
- `scripts/build_dog_decision_support_v1.py` (added by AbEngineCore)
  merges:
  - clinical anchors (`dog_production_germline_library_v1.json`)
  - population priors / DLA panel (`dog_repertoire_and_dla_stats.json`)

### Decision policy note

- This repo treats **Tier1 (clinical anchors)** and **Tier2 (population priors)** as the primary scaffold evidence layers.
- If an antibody cannot be satisfactorily adapted under Tier1/Tier2 scaffolds, the recommended fallback is
  **surface reshaping ** + structure-gated rescue (Phase4→5), rather than expanding to a large Tier3 search.

### Notes

- This layer is meant for **transparent provenance**: keep dataset_id, population, sample size.
- Do not store copyrighted PDFs here; store only normalized tables (CSV/JSON) with citations in metadata.

