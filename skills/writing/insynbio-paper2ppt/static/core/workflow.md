# 9-step workflow (nature-paper2ppt v2.0 adapted)

1. **Accept input** — MD manuscript, `slides_plan.md`, PDF (extract text via agent), or reading notes
2. **Classify paper_type** — state one line; default `review` for landscape/invited reviews
3. **Build terminology ledger** — `_shared/core/terminology-ledger.md`
4. **Design slide spine** — use loaded `paper_type` arc, NOT manuscript section order
5. **Write `slides_plan.md`** — human review; h2 = slide; body = bullets/table
6. **Convert** — `md_to_plan.py` → JSON
7. **Build editable PPTX** — `insynbio_paper2ppt.py` (mandatory)
8. **Optional heroes** — `generate_ppt.py` → merge with `--hero-images-dir`
9. **QA** — read `.qa.json`; fix FAIL; WARN documented for user

Self-review loop: if QA WARN on title overflow or empty bullets, shorten `slides_plan.md` and re-run step 7.
