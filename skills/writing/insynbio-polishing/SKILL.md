---
name: insynbio-polishing
description: >-
  Journal-aware polish: local AI-marker scan + write.insynbio.com rewrite/reduce_ai_tone
  (nature-polishing parity). Trigger on polish, reduce AI tone, Nature style, 润色,
  academic polishing, insynbio polish.
version: 1.0.0
---

# insynbio-polishing

Read **`manifest.yaml`**.

## Two-tier workflow

### Tier 1 — Local gate (no API)

```bash
python scripts/insynbio_polishing.py scan \
  --input paper/Submission_Package/Manuscript_DeNovo_AI_Landscape_Review_AT.md \
  --journal antibody_therapeutics \
  --out polish_scan.json
```

Exit 0 = PASS (AI marker count below threshold).

### Tier 2 — Platform (production)

```bash
python scripts/insynbio_polishing.py platform --journal nature --section discussion
# → use write.insynbio.com POST /rewrite, /reduce_ai_tone, /draft_section
```

Injects `<journal_context>` from `services/writing_memory/journal_context.py` (citation rule + forbidden phrases + section phrase bank).

## Profiles

| Journal key | Use when |
|-------------|----------|
| `nature` | CNS sentence polish |
| `antibody_therapeutics` | OUP invited review (Review B) |
| `elife`, `pnas`, `plos_med` | Corpus-verified profiles |

Static CNS rules: `static/profiles/cns-nature.md` (nature-polishing Stable parity v2.0)

Post-polish: `python scripts/insynbio_rigor.py manuscript --with-polish-scan --input FILE.md`

## vs nature-polishing

| | nature-polishing (Stable) | insynbio-polishing |
|---|---------------------------|---------------------|
| CNS voice rules | Embedded in skill | **cns-nature.md v2.0 + journal_context** |
| AI marker scan | Implicit | **Explicit CLI + FAIL threshold** |
| Scientific rigor scan | Manual | **insynbio_rigor dimensions** |
| SaaS API | No | **write.insynbio.com** |
| Antibody/OUP | Generic | **antibody_therapeutics profile** |
