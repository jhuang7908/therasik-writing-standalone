# Figure Legend Generator Recipe

## Purpose

Generates structured, journal-compliant figure legends from a JSON spec file.
Enforces the claim → methods → stats → data-source traceability chain.

**Anti-hallucination rule:** n-values, p-values, CI, test names must be provided
in the spec. The generator never invents statistics.

## Journal templates

| Template key | Word limit | Panel style | Stats inline |
|-------------|-----------|-------------|-------------|
| `nature`    | 350       | **a**       | Yes |
| `cell`      | 400       | **(A)**     | Yes |
| `plos`      | 300       | (A)         | No  |
| `generic`   | 300       | a.          | Yes |

## Workflow

### Step 1 — Scaffold a blank spec

```bash
python scripts/insynbio_figure.py stats --recipe legend -- \
  template --figure 1 --panels 4 --journal nature --out specs/fig1_spec.json
```

### Step 2 — Fill the spec

Open `specs/fig1_spec.json` and replace every `FILL_ME` field with actual content.
Do NOT invent statistics — copy from analysis output.

### Step 3 — Generate legend

```bash
python scripts/insynbio_figure.py stats --recipe legend -- \
  generate --legend-spec specs/fig1_spec.json --journal nature --out figures/Fig1_legend.md
```

Outputs:
- `figures/Fig1_legend.md` — formatted Markdown
- `figures/Fig1_legend.qa.json` — QA sidecar with word count and warnings

## Spec JSON fields

```json
{
  "figure_number": "1",
  "title": "Short title ≤12 words",
  "journal": "nature",
  "word_limit": 350,
  "overall_source": "data/processed/figure1.xlsx",
  "panels": [
    {
      "label": "a",
      "claim": "One-sentence scientific claim this panel supports",
      "type": "bar_chart",
      "method": "What was measured or calculated",
      "stats": {
        "test": "one-way ANOVA + Tukey post-hoc",
        "n": "n=45 per group",
        "ci": "95% CI",
        "p": "p<0.001"
      },
      "source": "Table 2 / data/processed/panel_a.csv",
      "data_availability": "Supplementary Table S1"
    }
  ]
}
```

## QA checklist

- [ ] No FILL_ME strings remain in spec
- [ ] Word count within journal limit
- [ ] All n-values from actual analysis
- [ ] All p-values from actual test output
- [ ] Panel labels match figure file
- [ ] `overall_source` points to a real SSOT file
- [ ] QA sidecar shows no FAIL items

## List templates

```bash
python scripts/insynbio_figure.py stats --recipe legend -- list-templates
```
