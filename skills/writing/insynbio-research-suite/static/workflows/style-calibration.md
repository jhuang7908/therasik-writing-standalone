# Workflow: style_calibration — Author Voice Profiling

**Adopted from:** ARS `shared/style_calibration_protocol.md` (academic-paper Step 10).  
**Applies to:** Any biomedical domain, any paper type.

## When to Trigger

Activate when:
- User provides past papers / writing samples (3+ recommended)
- User says "learn my writing style", "match my voice", "风格校准", "style calibration"
- Starting a major new manuscript for which author has prior publications

## What This Is NOT

- NOT an AI humanizer / AI-detection evader
- NOT a rewriter — it is a soft guide during drafting only
- Discipline + journal conventions always override personal style (see priority system below)

## Steps

### Step 1 — Sample Collection

Ask the user (if samples not already provided):

> "请提供 3 篇以上您自己写的论文（PDF/DOCX/Markdown/粘贴均可），以便分析您的写作风格。越多越好，建议来自同一领域。"

**Requirements:**
- Minimum 3 samples (1–2 produce unreliable profiles)
- Author's own writing sections preferred (avoid co-authored sections not written by them)
- Same language as target paper preferred
- Same biomedical domain preferred but not required

### Step 2 — 6-Dimension Analysis

Analyze samples across these 6 dimensions (see ARS `shared/style_calibration_protocol.md` for full spec):

| Dimension | What to measure |
|---|---|
| 1. Sentence length distribution | Mean words/sentence, stddev, rhythm (variable vs. steady) |
| 2. Paragraph length distribution | Mean sentences/paragraph, variation by section |
| 3. Vocabulary preferences | Hedging patterns, transition words, reporting verbs, formality level |
| 4. Citation integration style | Narrative ratio, citation density, placement (beginning/end of paragraph) |
| 5. Modifier style | Minimal vs. elaborate, abstract vs. concrete |
| 6. Register shifts | How tone changes across Introduction → Methods → Results → Discussion |

### Step 3 — Style Profile JSON

Generate a **Style Profile** artifact and write to `<project>/style_profile.json`:

```json
{
  "project": "<name>",
  "domain": "<biomedical domain>",
  "generated_at": "<ISO timestamp>",
  "samples_analyzed": 3,
  "profile": {
    "sentence_length": {"mean": 22, "stddev": 8, "rhythm": "variable"},
    "paragraph_length": {"mean_sentences": 5, "variation": "moderate"},
    "vocabulary": {
      "hedging": ["suggests", "appears to", "may indicate"],
      "transitions": ["However", "In contrast", "Notably"],
      "reporting_verbs": ["found", "demonstrated", "showed"],
      "formality": "moderate-formal"
    },
    "citation_integration": {
      "narrative_ratio": 0.4,
      "density_per_paragraph": 2.3,
      "placement": "mixed"
    },
    "modifier_style": "minimal — lean prose",
    "register_shifts": "noticeable — cautious Methods, assertive Discussion"
  },
  "summary": "1-sentence summary of most distinctive trait",
  "consumption_note": "Soft guide only. Discipline > Journal > Personal style."
}
```

### Step 4 — Report to User

Summarize in 3 bullets:
> "I've analyzed [N] writing samples across 6 dimensions. Key traits:
> - [Most distinctive trait]
> - [Second distinctive trait]  
> - [Citation style note]
> I'll apply this as a soft guide during drafting."

### Step 5 — Apply in Drafting

When `academic-paper` drafts the manuscript:
- Load `style_profile.json`
- Apply personal style at Priority 3 (below discipline and journal conventions)
- Log any conflicts in Draft Metadata:
  `"style_conflict": "Author prefers first-person; journal requires third-person → journal norm applied"`

## Priority System (must not violate)

```
Priority 1 (HARD):   Discipline conventions
Priority 2 (STRONG): Target journal conventions
Priority 3 (SOFT):   Author's personal style from Style Profile
```

## CLI

```powershell
python scripts/insynbio_research.py --project <name> --workflow style-calibration \
  --samples paper1.pdf paper2.pdf paper3.pdf \
  --out <project>/style_profile.json
```

Or as a standalone script:
```powershell
python scripts/insynbio_style_calibration.py \
  --samples paper1.pdf paper2.pdf paper3.pdf \
  --domain oncology \
  --out projects/<name>/style_profile.json
```
