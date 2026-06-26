# Recipe: forest — Forest Plot (effect sizes / benchmark comparison)

## When to use
- Displaying effect sizes (OR, HR, mean difference, Cohen's d) with 95% CI
- Meta-analysis pooled estimate
- Multi-model benchmark comparison (e.g., antibody design platform scores)
- Subgroup analysis

## CSV schema
```text
label,effect,ci_low,ci_high[,group,n,p_value,weight,is_pooled]
RFantibody,0.72,0.65,0.79,Platform,142,0.001,,
DiffAb,0.68,0.61,0.75,Platform,98,0.003,,
Pooled,0.70,0.64,0.76,,,,,1
```
Required: `label`, `effect`, `ci_low`, `ci_high`

## CLI
```powershell
python scripts/insynbio_figure.py stats --recipe forest \
  --csv data.csv --out figures/forest.svg \
  -- --null 0.0 --null-label "No effect" --title "Model comparison"

# For OR/HR: set null=1.0
python scripts/insynbio_figure.py stats --recipe forest \
  --csv data.csv --out figures/hr_forest.svg -- --null 1.0 --null-label "HR=1"
```

## QA checklist
- [ ] `null` value matches effect scale (0 for mean diff, 1 for OR/HR)
- [ ] Error bars traced to source table (not invented)
- [ ] n reported per row if applicable
- [ ] Pooled estimate row (diamond) only if meta-analysis
- [ ] Figure contract: claim stated before rendering

## Evidence tier
Must be Primary or Derived — never Illustrative for forest plots.

## Implementation
`core/figure/templates/forest_plot.py`
