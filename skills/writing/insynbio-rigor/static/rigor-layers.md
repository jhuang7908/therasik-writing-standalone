# Rigor layers A–F

## Layer A — Architecture (writing_memory)

**Question:** Can the system invent references or numbers?

- LLM output schema has no free-form `references[]`
- Only `[CITATION_NEEDED: topic]` placeholders in rewrite
- Corpus rows re-verified via PubMed/Crossref before UI insert
- Doc: `services/writing_memory/docs/ANTI_HALLUCINATION_POLICY.md`

**Evaluated by:** Server code (not prompt trust alone)  
**Verdict format:** API rejection + audit logs

---

## Layer B — Manuscript local gate (insynbio_rigor)

**Question:** Does the prose overclaim or smell like generic AI?

Dimensions:
- `ai_tone` — AI_MARKER_PHRASES count (FAIL ≥ threshold)
- `authenticity` — PMID/DOI density → manual verify reminder
- `scientific_rigor` — superlative/absolute language density
- `evidence_tagging` — quant tokens without `[verified]` tags

**Evaluated by:** Deterministic heuristics + optional `insynbio_polishing scan`  
**CLI:** `python scripts/insynbio_rigor.py manuscript --input FILE.md`

---

## Layer C — Multi-model content gate (NextVivo / social)

**Question:** Do deck/social claims match `article.json` source?

Dimensions (each PASS/FAIL + 0–100 score):
1. **format** — nextvivo_format_spec field limits
2. **authenticity** — every number traceable to source excerpt
3. **scientific_rigor** — terminology, no overclaim beyond data

**Chain default:** OpenAI → Claude → Gemini (`openai_content_rigor.py`)  
**Draft chain:** DeepSeek write → Kimi review → DeepSeek fix (`content-ssot-guard`)

**Evaluated by:** LLM JSON gate; FAIL blocks image render  
**Artifact:** `rigor_report.json`

---

## Layer D — Formal report contract

**Question:** Is this deliverable audit-ready for external clients?

Requires markdown sections:
- `## Verification Status` with `[verified]` / `[unverified]` tags
- `## Adversarial Checks` (≥3 bullets, PASS/WARN/FAIL)
- `## Sources` (≥2)

**CLI:** `validate_report_reliability.py --client`  
**Evaluated by:** Rule-based validator

---

## Layer E — Submission physical audit

**Question:** Will ScholarOne reject the folder?

- Required artifacts present
- Forbidden extensions absent
- `figure_min_dpi` **FAIL** at 300 for OUP

**CLI:** `build_submission_bundle.py --audit-only`  
**Artifact:** `SUBMISSION_AUDIT.json`

---

## Layer F — Reader bilingual QC

**Question:** Does the Chinese reader add facts?

- Section anchors + figure map in `reader_qc.json`
- Translation prompt: no new facts; `[未验证]` if uncertain
- Optional Kimi/DeepSeek per section

**CLI:** `insynbio_paper_reader.py --translate kimi --qc-out reader.qc.json`

---

## When to run which layer

| Deliverable | Minimum gates |
|-------------|---------------|
| Invited review MD | B + E (+ D if client-facing report) |
| WeChat / 小红书 | C + content-ssot-guard |
| Bilingual reader | F + B on EN source |
| CRO formal report | D + B |
| ScholarOne upload | E (must PASS) |
