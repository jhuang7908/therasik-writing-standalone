# Grouped bar with CI (nature-figure chart family — recipe spec)

## Input CSV schema

```text
group,series,value,ci_low,ci_high
Platform A,RFantibody,0.72,0.65,0.79
...
```

All rows must trace to manuscript table or `[user-provided]` sidecar.

## When to use

- Group comparison across ≤8 categories
- Evidence tier: Primary or Derived only

## Anti-patterns (nature)

- Do not pair with identical data as heatmap on same page
- Y-axis: tight range; avoid 0–100 if all values in 80–95

## Script entry (future)

```bash
python scripts/insynbio_figure.py stats --recipe grouped-bar --csv data.csv --out figure.svg
```

Until CLI `stats` lands: copy template from `core/figure/templates/grouped_bar.py`.

## QA

- [ ] Error bars match source table
- [ ] `n` in caption or axis label
- [ ] Palette coherent across panels
