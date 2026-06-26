# Python matplotlib SSOT (from nature-figure Stable — adopted)

Apply to all **new** publication scripts under `paper/` and `scripts/insynbio_figure` recipes.

## Required rcParams (SVG editable text)

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"  # keep <text> nodes editable
```

## Default style bundle

```python
plt.rcParams.update({
    "font.size": 8,           # journal dense panels: 5–8 pt at final size
    "axes.spines.right": False,
    "axes.spines.top": False,
    "axes.linewidth": 1.5,
    "legend.frameon": False,
    "xtick.major.width": 1.0,
    "ytick.major.width": 1.0,
})
```

## Export

```python
fig.savefig("figure.svg", bbox_inches="tight")
fig.savefig("figure.tiff", dpi=300, bbox_inches="tight", format="tiff")
plt.close(fig)
```

## Panel labels

Lowercase bold `a`, `b`, `c` at `transAxes` (-0.05, 1.06).

## Semantic palette (nature-figure PALETTE — use when no vertical SSOT)

```python
PALETTE = {
    "blue_main": "#0F4D92",
    "blue_secondary": "#3775BA",
    "green_3": "#8BCF8B",
    "red_strong": "#B64342",
    "neutral_mid": "#767676",
    "neutral_dark": "#4D4D4D",
}
```

Review B / OUP decks: prefer `deck_style.py` colors over generic PALETTE.

## Helper module

```python
from core.figure.matplotlib_nature import apply_nature_rcparams, save_publication_figure
```

## Chart families to port (nature chart-atlas → insynbio stats-recipes)

| Priority | Type | Recipe file |
|----------|------|-------------|
| P0 | Grouped bar + CI | `static/stats-recipes/grouped-bar.md` |
| P1 | Forest / effect interval | `static/stats-recipes/forest-plot.md` |
| P1 | Kaplan–Meier style trend | `static/stats-recipes/km-trend.md` |
| P2 | Volcano / bubble | `static/stats-recipes/bubble-scatter.md` |
| P2 | Z-score heatmap | `static/stats-recipes/zscore-heatmap.md` |

Each recipe: input CSV schema + matplotlib script template + QA checklist.

## Repro checklist (before commit)

- [ ] Figure contract filled (claim, tier, panel map)
- [ ] SVG + 300 dpi raster/TIFF
- [ ] `plt.close(fig)` called
- [ ] `insynbio_figure.py audit` PASS
- [ ] Legend not duplicating every panel
