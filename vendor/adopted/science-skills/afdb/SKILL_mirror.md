<!-- ADOPTED FROM: vendor/science-skills/skills/alphafold_database_fetch_and_analyze/SKILL.md
     UPSTREAM COMMIT: 33557e0f1faf0f281d255940de58935c61b2143b (2026-06-08)
     MIRRORED: 2026-06-21
     ADAPTER: insynbio-figure recipe "afdb_plddt" — matplotlib pLDDT per-residue ribbon
     SCOPE: AFDB pLDDT QC figure for VHH/VH-VHH structure reports
-->

# AFDB pLDDT Fetch — InSynBio Adoption Summary

## Source
`vendor/science-skills/skills/alphafold_database_fetch_and_analyze` (GDM science-skills, Apache-2.0)

## What We Adopted

| GDM concept | Our implementation |
|---|---|
| Fetch `.cif` + `_predicted_aligned_error.json` | `core/figure/afdb_plddt.py fetch_afdb_plddt(uniprot_id)` |
| pLDDT per-residue confidence plot | `insynbio-figure` recipe `afdb_plddt` (matplotlib_nature style) |
| Domain boundary heuristic | Visual coloring only (VHH FR/CDR overlay) |

## Usage in insynbio-figure

```
recipe: afdb_plddt
input:
  uniprot_id: "P0DTC2"      # spike protein example
  highlight_regions:
    - {label: "CDR3", start: 99, end: 113}
output: figures/afdb_plddt.pdf
```

## Notes

- No `uv` required: uses `requests` + `matplotlib` (both in `affmat` env)
- Rate limit: AFDB public API, no key required, ~1 req/s polite
- pLDDT < 50 = disordered (red), 50–70 = low (orange), 70–90 = confident (blue), >90 = very high (dark blue)
