# Workflow: journal_format — On-Demand Journal Formatting

**Trigger:** User asks to format for a specific journal, check OA policy, or apply citation style.

We do NOT self-build format logic. Three public authoritative APIs handle everything:

| Source | Coverage | What it provides |
|---|---|---|
| **CrossRef REST API** | 30,000+ journals | Publisher, ISSN, article types, subjects |
| **Zotero CSL Library** | 9,000+ journals | Full citation style (.csl file), downloads on demand |
| **Sherpa RoMEO v2** | 3,000+ journals | OA policy, embargo, permitted versions, license |

## Commands

```powershell
# 1. Look up any journal metadata
python scripts/insynbio_journal_format.py lookup "Nature Methods"
python scripts/insynbio_journal_format.py lookup --issn 1548-7091

# 2. Download citation style for pandoc / Word
python scripts/insynbio_journal_format.py get-csl "Nature Methods" --out styles/nature-methods.csl

# 3. Check OA/embargo policy
python scripts/insynbio_journal_format.py oa-policy "Nature Methods"

# 4. Full spec (CrossRef + CSL + Sherpa) in one JSON
python scripts/insynbio_journal_format.py full-spec "Journal of Clinical Investigation" --out specs/jci.json
```

## Apply CSL to manuscript

### Via pandoc (any format)
```powershell
pandoc manuscript.md `
  --bibliography refs.bib `
  --csl styles/nature-methods.csl `
  --output manuscript.docx
```

### Via ARS change_style.ps1 (if submission package already set up)
```powershell
cd paper/<project>/
.\change_style.ps1 -CslUrl https://www.zotero.org/styles/nature-methods
```

## Coverage note

Zotero hosts ~9,000 CSL styles for journals from all major publishers. The full list is browsable at:
- https://www.zotero.org/styles (browse / search by journal name)
- https://github.com/citation-style-language/styles (raw repository, 9,000+ files)

If a journal is not found by slug, use `--issn` + CrossRef to get the official title, then search Zotero manually.

## Sherpa API key (optional but recommended)

```powershell
# Register free: https://v2.sherpa.ac.uk/api/registration
$env:SHERPA_API_KEY = "your-key"
python scripts/insynbio_journal_format.py oa-policy "Nature Methods"
```

## Decision tree

```
User: "format for <journal>"
  ↓
1. get-csl <journal>        → download .csl file
2. Apply via pandoc or ARS change_style.ps1
3. If OA submission needed → oa-policy <journal>
4. If need detailed requirements → full-spec <journal>
```

## Anti-hallucination rule

Never state journal word limits, page charges, figure specs, or manuscript types from memory.
Use CrossRef + publisher homepage as authoritative sources.
Tag all format claims as `[verified via CrossRef/Zotero]` or `[unverified — check publisher page]`.
