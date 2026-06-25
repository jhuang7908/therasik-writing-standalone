# Human Replacement Profiles v1

**Purpose:** Usable, scientifically attributable Kabat-position amino-acid frequency tables for humanization engineering lookup.

| File | Locus | Data type | n_positions | Source |
|---|---|---|---|---|
| `human_ighv_aa_freq_llamanade_ngs_v1.json` | IGHV | ngs_empirical_cohort | 150 | external\llamanade\Llamanade_upstream\resources\resources\ANARCI_Hum_H.json |
| `human_igkv_aa_freq_imgt_germline_v1.json` | IGKV | imgt_germline_frequency | 101 | data\germlines\human_ig_aa\igkv_numbered_cache.json |
| `human_iglv_aa_freq_imgt_germline_v1.json` | IGLV | imgt_germline_frequency | 8 | data\germlines\human_ig_aa\_cache\IGLV_kabat_cache.json |

## When to use which table

- **IGHV (Llamanade NGS):** Use as the primary human-frequency prior for VH / VHH
  humanization position-by-position frequency gate.  This is an empirical NGS cohort —
  not a germline count — and is the scientifically strongest VH reference available
  in-repo without running new sequencing.

- **IGKV (IMGT germline):** Use for κ light-chain position frequency lookups.
  These are unweighted over all functional human κ germline V genes;
  does not include somatic hypermutation diversity.

- **IGLV (IMGT germline, Vernier positions):** Use for Vernier-zone λ light-chain
  frequency lookups. Full-sequence Kabat coverage is a v2 TODO.

## Regenerate

```bash
python scripts/build_human_replacement_profiles_v1.py
```

No conda environment required.

## Version history
- v1  2026-05-06  Initial release.
