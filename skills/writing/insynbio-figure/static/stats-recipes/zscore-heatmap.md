# Recipe: heatmap — Z-score Heatmap

## When to use
- Gene expression panels (RNA-seq, scRNA-seq signatures)
- Antibody/protein binding profiles across targets/samples
- Immune cell phenotyping panels
- Multi-parameter clinical data

## CSV schema
```text
gene,Sample_A,Sample_B,Sample_C,Sample_D,group
CD19,5.2,1.1,4.8,1.3,B_cell
CD20,4.9,0.9,5.1,1.0,B_cell
PD1,1.0,3.8,1.2,4.1,T_cell
```
- Column 0: feature name (required)
- Remaining numeric columns: samples/conditions
- Optional last meta-column: row group labels (pass via `--row-group-col`)

## CLI
```powershell
python scripts/insynbio_figure.py stats --recipe heatmap \
  --csv data.csv --out figures/heatmap.svg --double-column \
  -- --row-group-col group --top-n 50

# No clustering:
python scripts/insynbio_figure.py stats --recipe heatmap \
  --csv data.csv --out figures/heatmap.svg -- --no-cluster-rows
```

## QA checklist
- [ ] Z-score normalization applied (row-wise, clipped ±3)
- [ ] Feature selection criterion stated (top N by variance, or pre-filtered)
- [ ] Color scale bar labeled "Z-score"
- [ ] Row group labels verified against source metadata
- [ ] n samples per group in caption

## Colormap
Blue (`#2A6496`) → White → Red (`#C0392B`)  
Diverging, centered at 0, clipped at ±3.

## Implementation
`core/figure/templates/zscore_heatmap.py`  
Requires: scipy (for hierarchical clustering) — available in `affmat` env.
