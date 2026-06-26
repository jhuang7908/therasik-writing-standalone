# Recipe: afdb_plddt — AlphaFold pLDDT Per-Residue Confidence Plot

Adopted from GDM science-skills `alphafold_database_fetch_and_analyze` (Apache-2.0).
See `vendor/adopted/science-skills/afdb/SKILL_mirror.md`.

## Purpose

Generate a publication-ready per-residue pLDDT confidence ribbon plot from the AlphaFold Database
for a given UniProt accession. Useful for:

- VHH / VH-VHH structure QC (highlight FR/CDR confidence zones)
- Target antigen disorder assessment
- pLDDT-gated structure selection in humanization reports

## Quick Start

```powershell
python core/figure/afdb_plddt.py \
  --uniprot P0DTC2 \
  --out figures/afdb_plddt_P0DTC2.pdf \
  --highlight "CDR3:99:113" "FR3:66:94"
```

## Input Schema

```yaml
recipe: afdb_plddt
input:
  uniprot_id: "Q9Y6R7"           # required
  highlight_regions:             # optional VHH FR/CDR overlays
    - {label: "CDR1", start: 26, end: 35}
    - {label: "CDR2", start: 50, end: 65}
    - {label: "CDR3", start: 95, end: 113}
output:
  path: figures/afdb_plddt.pdf
  dpi: 300
  format: pdf                    # or png, svg
```

## pLDDT Color Scale (AFDB standard)

| Range | Color | Interpretation |
|---|---|---|
| > 90 | `#0053D6` (dark blue) | Very high confidence |
| 70–90 | `#65CBF3` (light blue) | Confident |
| 50–70 | `#FFDB13` (yellow) | Low confidence |
| < 50 | `#FF7D45` (orange) | Very low / disordered |

## API Source

```
GET https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}
→ pdbUrl, cifUrl, paeImageUrl, confidenceScore (pLDDT) list
```

No authentication required. Rate limit: ~1 req/s (polite).

## VHH Overlay Logic

When `highlight_regions` are provided, semi-transparent grey bars mark each region using
IMGT linear numbering (0-indexed). CDR bars use `alpha=0.25`, FR bars `alpha=0.12`.

## matplotlib_nature Style Compliance

- Figure width: 8.5 cm (single column) or 17.4 cm (double column)
- Font: Arial / Helvetica, 7 pt axis labels, 8 pt title
- No right/top spine
- Legend outside right (bbox_to_anchor)
- File formats: PDF (vector) + PNG 300 dpi for submission
