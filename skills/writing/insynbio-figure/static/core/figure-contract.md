# Figure contract (adapted from nature-figure Stable)

Before any plotting code runs, document or infer:

## 1. Scientific claim

- **One-sentence takeaway** the figure must support
- Figure type: mechanism schematic | result atlas | comparison | workflow | table-graphic

## 2. Evidence tier

| Tier | Use |
|------|-----|
| Primary | Direct experimental/computational data from SSOT |
| Derived | Aggregated from tables in manuscript |
| Illustrative | Conceptual only — label as schematic |

Antibody reviews: align with **Table 6 evidence grades** (verified / vendor / indirect / preprint).

## 3. Panel map (multi-panel)

Each panel answers **one unique question**. Run anti-redundancy check:

- No duplicate absolute + absolute (stacked bar + same % heatmap)
- No ranked bar duplicating a stacked column

## 4. Backend gate

- **Python (matplotlib)** — default in InSynBio; Review B SSOT
- **R (ggplot2)** — adopt when user/project specifies; do not silently mix backends

If runtime missing → stop and report; no cross-backend substitute.

## 5. Statistics & source data

Record in figure legend or sidecar JSON:

- `n`, test, CI method (if applicable)
- Source file: table ID, CSV path, or `[user-provided]`
- No stats invented by LLM

## 6. Export package

| Output | Purpose |
|--------|---------|
| `.svg` | Editable text (`svg.fonttype=none`) |
| `.png` @ 300 dpi | Preview / slide |
| `.tiff` LZW @ 300 dpi | ScholarOne upload |

Run: `python scripts/insynbio_figure.py audit --min-dpi 300 ...`

## 7. Privacy

Do not expose private template paths in client-facing captions unless audit trail requested.

## InSynBio vertical overrides

- Review B palette: `deck_ppt/deck_style.py` (OUP infographic, not generic NMI pastel)
- Graphical tables: `render_graphical_tables.py` recipes
- Manuscript Fig1/2: `render_figure1_ecosystem.py`, `render_figure2_*.py`

When vertical palette conflicts with nature PALETTE_NMI_PASTEL → **vertical wins**; log in adopt matrix.
