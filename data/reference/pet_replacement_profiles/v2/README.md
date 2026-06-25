# Pet Replacement Profiles

## v3 — Three-Tier Clinical Combined 

| File | Species | Locus | L1 Clinical Seqs | L2 CMC Scaffold | L3 Germline Genes |
|---|---|---|---|---|---|
| `v3/dog_ighv_clinical_combined_v1.json` | Canis lupus familiaris | IGHV | 15 | 9 (Tier-1) | 54 |
| `v3/cat_ighv_clinical_combined_v1.json` | Felis catus | IGHV | 3 | 17 (Tier-1) | 128 |

**:**  (×3) > CMC Tier-1 scaffold (×2) >  (×1)

: `{positions: {pos: {combined_preferred, combined_freq, level1_clinical_counts, level2_scaffold_counts, level3_germline_freq, 9mer_contexts}}}`

 `9mer_contexts` —  ±4 （ L1+L2 ）。
 `run_deepfreq_pet_cmc_guard.py`  9-mer 。

:
```bash
conda run --no-capture-output -n anarcii python scripts/build_pet_clinical_combined_profile.py
```

Generated: 2026-05-08

---

## v2 — Germline Frequency Only 

**Format:** Identical to `human_replacement_profiles/v1` — flat `{pos: {aa: float}}`.

| File | Species | Locus | n_positions | Weighting |
|---|---|---|---|---|
| `dog_ighv_aa_freq_kabat_v2.json` | Canis lupus familiaris | IGHV | 100 | unweighted_germline_count |
| `dog_igkv_aa_freq_kabat_v2.json` | Canis lupus familiaris | IGKV | 101 | unweighted_germline_count |
| `dog_iglv_aa_freq_kabat_v2.json` | Canis lupus familiaris | IGLV | 115 | unweighted_germline_count |
| `cat_ighv_aa_freq_kabat_v2.json` | Felis catus | IGHV | 128 | unweighted_germline_count |
| `cat_igkv_aa_freq_kabat_v2.json` | Felis catus | IGKV | 100 | unweighted_germline_count |
| `cat_iglv_aa_freq_kabat_v2.json` | Felis catus | IGLV | 109 | unweighted_germline_count |

## Regenerate

Step 1 (conda env anarcii, one-time):
```bash
conda run --no-capture-output -n anarcii python scripts/build_dog_numbered_cache.py
conda run --no-capture-output -n anarcii python scripts/build_cat_numbered_cache.py
```

Step 2 (no conda required):
```bash
python scripts/build_pet_profiles_from_cache.py
```

Generated: 2026-05-06
