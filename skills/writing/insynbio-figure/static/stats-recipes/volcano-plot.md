# Recipe: volcano — Volcano Plot

## When to use
- Differential expression (RNA-seq, proteomics)
- Mutation significance
- Drug effect screening
- Any log2FC vs -log10(p) visualization

## CSV schema
```text
gene,log2fc,pval[,padj,mean_expr]
FOXP3,2.8,0.000005
PD1,2.4,0.00001
CD19,-2.1,0.0001
```
Required: one label column + `log2fc` + `pval` (or `padj`)

## CLI
```powershell
python scripts/insynbio_figure.py stats --recipe volcano \
  --csv data.csv --out figures/volcano.svg \
  -- --fc-thresh 1.0 --p-thresh 0.05 --top-labels 15 \
     --label-col gene --fc-col log2fc --pval-col padj
```

## QA checklist
- [ ] Using adjusted p-value (padj) not raw p if available
- [ ] FC threshold justified (typically |log2FC| > 1 = 2-fold change)
- [ ] Top labels verified against source table
- [ ] Color legend counts match data
- [ ] n total reported in caption

## Colors
- Up-regulated: `#C0392B` (red)
- Down-regulated: `#2A6496` (blue)  
- NS: `#CCCCCC` (grey, rasterized for large datasets)

## Implementation
`core/figure/templates/volcano_plot.py`
