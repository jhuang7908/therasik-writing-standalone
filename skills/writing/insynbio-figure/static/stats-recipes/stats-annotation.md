# Recipe: stats-demo — Statistical Annotation Utility

## When to use
Add to any existing bar/violin/box/line plot:
- p-value significance brackets between groups
- n-labels below each bar/group
- CI error bars (when not using seaborn/plotly)
- Confidence bands on line plots

## API (import into your figure script)
```python
from core.figure.templates.stats_annotator import (
    add_stat_brackets,   # p-value brackets
    add_n_labels,        # n= labels below groups
    add_ci_bars,         # CI whiskers on bar plots
    add_confidence_band, # shaded CI band on line plots
    format_pvalue,       # p → stars/numeric string
)

# After creating bar/box/violin plot:
add_stat_brackets(ax, comparisons=[(0, 1, 0.001), (0, 2, 0.042)])
add_n_labels(ax, ns=[45, 32, 28], y=-0.12)
add_ci_bars(ax, x_pos=[0,1,2], means=[0.72,0.65,0.81],
            ci_low=[0.65,0.58,0.74], ci_high=[0.79,0.72,0.88])
```

## Demo
```powershell
python scripts/insynbio_figure.py stats --recipe stats-demo --out figures/stats_demo.svg
```

## p-value display styles
| style | output |
|---|---|
| `"stars"` (default) | n.s. / * / ** / *** |
| `"numeric"` | p=0.042 / p<0.001 |
| `"combined"` | ** \n p=0.003 |

## QA checklist
- [ ] p-values trace to statistical test results (not invented)
- [ ] Test type stated in figure legend
- [ ] n per group verified against source data
- [ ] y-axis expanded to accommodate brackets (automatic)
- [ ] Non-significant comparisons omitted by default (n.s. skipped)

## Implementation
`core/figure/templates/stats_annotator.py`
