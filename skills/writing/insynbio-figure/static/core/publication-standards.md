# Publication figure standards

## Submission (OUP / ScholarOne)

- Raster figures: **≥300 dpi** TIFF preferred; PNG acceptable if dpi embedded
- No `.md` / `.json` in upload tree — figures only in `04_Figures_Tables/`
- Bundle audit: `figure_min_dpi` rule severity **FAIL** for `antibody_therapeutics_scholarone_review`

## InSynBio palette (Review B)

- Open stack: `#2A9D8F`
- Hybrid: `#E9A319`
- Closed: `#1D3557`
- Stage: `#457B9D`

## Workflow

1. Render vector/matplotlib → PNG preview
2. `insynbio_figure.py audit` on all upload candidates
3. `png-to-tiff` for portal upload
4. Re-run `build_submission_bundle.py --audit-only`

## Forbidden

- Decorative clip-art in manuscript figures
- Unlabeled axes or invented data points
- Downscaling below 300 dpi for final TIFF
