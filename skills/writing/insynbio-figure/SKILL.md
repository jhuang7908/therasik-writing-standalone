---
name: insynbio-figure
description: >-
  Publication-grade figures for journal submission: matplotlib infographics, 300 dpi
  TIFF export, DPI audit, ScholarOne figure recipes. Forest plot, volcano, heatmap,
  KM survival curve, figure legend generator. Trigger on publication figure, 投稿图,
  DPI audit, TIFF export, graphical table, KM curve, survival plot, figure legend,
  图例, 生存曲线, insynbio figure, matplotlib figure.
version: 1.4.0
---

# insynbio-figure — Router

Read **`manifest.yaml`**. Status: **Stable** (chart-atlas v1.4.0).  
**Learn upstream:** `nature-figure` Stable — figure contract, SVG rcParams, chart-atlas (see adopt matrix).

## CLI

```bash
# Submission DPI audit (≥300 for OUP)
python scripts/insynbio_figure.py audit paper/Submission_Package/ScholarOne_Upload/**/*.tiff --out figure_audit.json

# PNG → TIFF for ScholarOne upload
python scripts/insynbio_figure.py png-to-tiff --input fig.png --output Figure_1.tiff

# KM survival curve
python scripts/insynbio_figure.py stats --recipe km --csv data/survival.csv --out figures/km.svg

# Forest / volcano / heatmap
python scripts/insynbio_figure.py stats --recipe forest --csv data/or.csv --out figures/forest.svg
python scripts/insynbio_figure.py stats --recipe volcano --csv data/de.csv --out figures/volcano.svg
python scripts/insynbio_figure.py stats --recipe heatmap --csv data/expr.csv --out figures/heatmap.svg

# Figure legend
python scripts/insynbio_figure.py stats --recipe legend -- template --figure 1 --panels 3 --out specs/fig1.json
python scripts/insynbio_figure.py stats --recipe legend -- generate --legend-spec specs/fig1.json --out figures/Fig1_legend.md
```

## vs nature-figure (v1.4.0 parity)

| Capability | nature-figure | insynbio-figure v1.4.0 |
|------------|---------------|------------------------|
| Python/R plots | General | Antibody review + biomedical palettes |
| DPI / upload | Manual | `figure_min_dpi` bundle audit + CLI |
| TIFF LZW | User | `png-to-tiff` recipe |
| Forest plot | Yes | **Yes** (v1.3.0) |
| Volcano plot | Yes | **Yes** (v1.3.0) |
| Z-score heatmap | Yes | **Yes** (v1.3.0) |
| Stats annotation | Yes | **Yes** (v1.3.0) |
| KM survival curve | Yes | **Yes** (v1.4.0) — Greenwood CI + log-rank |
| Figure legend gen | Yes | **Yes** (v1.4.0) — Nature/Cell/PLOS templates |
| AlphaFold pLDDT | Yes (GDM) | **Yes** (adopted v1.2.0) |

**Gap closed.** insynbio-figure now matches or exceeds nature-figure chart-atlas for biomedical publications.

Style SSOT: `core/figure/matplotlib_nature.py` (rcParams) · `deck_ppt/deck_style.py` (Review B).
