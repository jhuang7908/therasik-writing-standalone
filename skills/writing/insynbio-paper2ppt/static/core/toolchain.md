# Toolchain (fast path vs visual path)

## Fast path — editable deck (default)

```bash
python scripts/insynbio_paper2ppt.py \
  --plan slides_plan.md \
  --out outputs_editable/deck.pptx \
  --lang en \
  --paper-type review
```

Outputs: `.pptx` (editable text/table) + `.qa.json` + speaker notes on every slide.

## Visual path — optional hero slides

```bash
cd content_generation_tools/ppt-templates
$env:PYTHONPATH = "<repo>/scripts"
python scripts/md_to_plan.py ../../paper/.../slides_plan.md -o slides_plan.json
python scripts/generate_ppt.py \
  --plan slides_plan.json \
  --style styles/clean-tech-blue.md \
  --output ../../paper/.../outputs_hero \
  --backend gemini-image
```

Then merge:

```bash
python scripts/insynbio_paper2ppt.py \
  --plan slides_plan.md \
  --out deck_hybrid.pptx \
  --hero-images-dir outputs_hero/images
```

## When OpenAI quota available

Omit `--backend gemini-image`; use default `gpt-image-2` high for text-heavy slides per `image-text-render-policy`.

## Editable rebuild (DeckWeaver)

If user must edit image-deck text in PowerPoint: **`deckweaver`** or **`awesome-ppt-editable`** skills.
