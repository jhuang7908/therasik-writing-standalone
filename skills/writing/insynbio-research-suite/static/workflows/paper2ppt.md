# Workflow: scholarone-deck

Graphical tables (matplotlib) + manuscript Figure 1/2 + AI content slides → `Review_B_DeNovo_Presentation.pptx`.

```bash
python scripts/insynbio_research.py --project review_b --workflow scholarone-deck
```

Output: `{scholarone_deck_dir}/outputs/Review_B_DeNovo_Presentation.pptx`

Fixed slides (programmatic): 6, 8, 9, 10, 11, 12, 15, 17, 21, 22 — see `deck_ppt/README.md`.

## Workflow: manuscript-to-slides from DOCX

```bash
python scripts/insynbio_research.py --project review_b --workflow manuscript-to-slides --use-docx
python scripts/insynbio_research.py --project review_b --workflow manuscript-to-slides --input paper/Submission_Package/Manuscript_FINAL.docx
```

## Full pipeline with both PPT tracks

```bash
python scripts/insynbio_research.py --project review_b --workflow full \
  --skip-literature --skip-format --skip-bundle \
  --with-scholarone-deck
```

1. Confirm input: `slides_plan.md` (preferred) or manuscript MD + figure paths
2. Load **`insynbio-paper2ppt`** skill + manifest
3. Run editable builder (mandatory):
   ```bash
   python scripts/insynbio_paper2ppt.py --plan <slides_plan.md> --out <deck.pptx>
   ```
4. Optional visual layer — `gpt-image2-ppt` with `--backend gemini-image` if OpenAI quota blocked
5. Merge heroes: re-run with `--hero-images-dir outputs/.../images`
6. Deliver: `.pptx` + `.qa.json` + optional PNG folder

Do **not** deliver image-only deck without editable version unless user explicitly waives editability.
