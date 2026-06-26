# KM Survival / Step-Trend Plot Recipe

## When to use

| Situation | Mode |
|-----------|------|
| Time-to-event data (OS, PFS, EFS, DFS) | `survival` (Kaplan-Meier) |
| Sequential dose steps, viral load over time, tumor burden | `trend` |
| Comparing two treatment arms (log-rank p-value) | `survival` + 2 groups |

## Survival mode CSV schema

```csv
time,event,group
12.5,1,Treatment
8.2,0,Treatment
15.1,1,Control
20.0,0,Control
```

- `event=1` → event occurred; `event=0` → censored
- `group` column optional; omit for single-curve

## Trend mode CSV schema

```csv
time,value,group,ci_low,ci_high
0,1.00,Treatment,1.00,1.00
3,0.82,Treatment,0.76,0.88
6,0.71,Treatment,0.64,0.78
```

## CLI

```bash
# KM survival, two groups, with at-risk table
python scripts/insynbio_figure.py stats --recipe km \
  --csv data/survival.csv --out figures/Figure3a.svg -- \
  --time-col time --event-col event --group-col group

# Trend, no censors
python scripts/insynbio_figure.py stats --recipe km \
  --csv data/trend.csv --out figures/Figure3b.svg -- \
  --mode trend --no-censors --no-at-risk --y-label "Tumor burden (cm²)"

# Single-column figure (86 mm)
python scripts/insynbio_figure.py stats --recipe km \
  --csv data/survival.csv --out figures/km_single.svg
```

## Outputs

| File | Description |
|------|-------------|
| `*.svg` | Editable vector, Arial text, publication-ready |
| `*.tiff` | 300 dpi for journal upload |

## Features

- Pure matplotlib + scipy — no lifelines dependency
- Greenwood 95% CI bands (log-log transformed)
- Log-rank p-value (two-group only)
- At-risk table auto-sized below plot
- Censor tick marks (+)
- Step-function rendering with `where="post"`
- Single- and double-column width modes

## QA checklist

- [ ] Event column contains only 0/1
- [ ] At-risk numbers decrease monotonically
- [ ] CI bands do not exceed [0, 1]
- [ ] Log-rank p shown only for exactly 2 groups
- [ ] SVG text is editable (fonttype = none)
- [ ] n per group stated in figure legend (via `legend` recipe)
