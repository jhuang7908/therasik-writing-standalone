# P0 — write.insynbio.com smoke test (production)

**Date:** 2026-05-26  
**Build:** write.html v15.24, `vector_backend: npz` (1947 chunks)

## Modes (UI)

| UI label | Internal `activeMode` | Quota class | What to test |
|----------|----------------------|-------------|--------------|
| **Polish** | `draft` | polish (10/day/IP) | Paste existing prose → ✍ Rewrite / Safety / Claim check |
| **Draft** (was “Write”) | `plan` | plan (2) + draft (6) | Outline → Draft section (no paste required) |

## Corpus reality (important)

| Target journal key | Profile used | Dedicated OA corpus in npz? |
|------------------|--------------|------------------------------|
| `pnas` | pnas (48 papers) | Yes (`pnas`) |
| `elife` | elife (48 papers) | Yes (`elife`) |
| `plos_med` | plos_med (50 papers) | Yes (`plos_med`) |
| `nature_communications` | **generic** (nature_like family) | No — semantic search only |
| `frontiers_immunology` | **generic** + plos_med spec | No — semantic search only |

**Polish mode already auto-queries** the vector index: `/rewrite` pulls top discussion exemplars by embedding similarity (not journal name match). So Nature/Frontiers rewrites work but are **style-family proxies**, not true Nature/Frontiers profiles until you **Learn style** with customer PDFs.

## Sample input (eLife discussion excerpt)

Use discussion from PMC eLife meta-analysis (PMID 42132124) — first ~2 sentences:

```
Our findings indicate that HITS is a promising method to achieve memory enhancement via noninvasive stimulation. Effects were specific to episodic memory versus other cognitive tests and were greater for recollection than recognition.
```

## P0 matrix — Polish (manual in browser)

1. Open https://write.insynbio.com — hard refresh (Ctrl+F5).
2. Mode **Polish**, section **Discussion**, paste sample text.
3. For each target journal, run **✍ Rewrite** (optional: Anti-copy + Anti-AI on).

| # | Target journal | Pass criteria |
|---|----------------|---------------|
| A | eLife | Output JSON; different cadence; `_meta.profile_key` = `elife`; `_evidence` ≥ 1 |
| B | PNAS | `profile_key` = `pnas`; significance framing tighter |
| C | Nature Communications | `profile_key` = `generic`; mapping shows `nature_like` |
| D | Frontiers in Immunology | `profile_key` = `generic`; mapping `plos_bmc_open` |
| E | Safety | **⚖ Safety** → `style_safety.overall_verdict` pass/warn (not 500) |

**API note:** `POST /rewrite` body field is `target_journal`, not `journal_key`.

## P0 matrix — Draft-from-scratch

1. Mode **Draft**, paste a short **user intent** (English): meta-analysis of HITS and episodic memory.
2. Target journal: PNAS → **Plan paper** → one section **Draft this section**.
3. Repeat with Nature Communications (expect generic profile warning in mapping).

Pass: outline JSON, drafted prose, no fabricated PMIDs in output (placeholders only).

## P0 — Learn style (Frontiers, hybrid)

Requires **login** + **≥2 target-journal PDFs** per batch.

1. Learn panel → Journal name: `Frontiers in Immunology`
2. Linked journal (optional): `plos_med` (best corpus neighbor today)
3. Upload **2+** Frontiers PDFs (full text); enable **Vector DB supplement**
4. Submit → intake report: accepted / archived / rejected
5. Select learned pack `learned:…` in journal picker → Polish rewrite

Pass: `journal_select_key` starts with `learned:`; message mentions corpus supplement counts.

## Automated probe (PowerShell, quota-limited)

```powershell
# Similar search (does not consume polish quota)
$q = @{ query = "Frontiers in Immunology cancer immunotherapy discussion"; top_k = 5 } | ConvertTo-Json
Invoke-RestMethod https://write.insynbio.com/similar -Method POST -ContentType application/json -Body $q

# One polish rewrite (consumes quota)
$body = @{
  paragraph = "Our findings indicate that HITS is a promising method to achieve memory enhancement via noninvasive stimulation."
  target_journal = "pnas"
  section = "discussion"
  check_plagiarism = $false
  check_ai_tone = $true
} | ConvertTo-Json
Invoke-RestMethod https://write.insynbio.com/rewrite -Method POST -ContentType application/json -Body $body
```

**2026-05-26 automated run:** `/similar` for Frontiers returned top hits from `pnas` / `plos_med` (sim ~0.44–0.56). `/rewrite` → PNAS **200** with safety checks off; repeated calls hit **429** (IP polish quota).

## Failures to watch

| Symptom | Likely cause |
|---------|----------------|
| 429 | Daily IP quota — wait UTC midnight or use `WM_TRUSTED_IPS` on VPS |
| 500 on rewrite + safety on | Check `journalctl -u writing-memory`; embedding batch / Claude parse |
| Learn 400 | Fewer than 2 target PDFs, or intake rejected spam |
| Nature/Frontiers “flat” style | Expected until dedicated profile or learned pack |

## After P0

1. **Frontiers / Nature corpus** — extend `ingest/probe_pmc_hitrate.py` + pipeline for OA Frontiers/Nature PMC (then pgvector optional).
2. **pgvector** — when chunk count or multi-instance needs grow.
3. Train **nature_like** family profile from 5+5 exemplars (not only generic seed).
