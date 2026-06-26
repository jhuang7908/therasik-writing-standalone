# Writing Memory — Automated Corpus Pipeline

The server can refresh the journal writing-memory corpus **without manual intervention**.
All scripts live under `services/writing_memory/ingest/`.

## MVP corpus policy — free full text first

**Goal:** every paper in the corpus must have **confirmed free PMC JATS XML**
(verified by efetch, not inferred from PubMed metadata).

| Journal | Free full text reality | MVP search window |
|---------|------------------------|-------------------|
| **PNAS** | ~6-month PMC deposit embargo on many new papers | **2010–2022** + dual OA filters |
| **eLife** | Immediate OA, full PMC | **2012–2023** |
| **PLOS Medicine** | Immediate OA, full PMC | **2010–2023** |

Default probe strategy: **`--strategy classic`** (not "last 5 years").

PubMed query always includes:
```
"free full text"[filter] AND "pubmed pmc open access"[filter]
```

Then each candidate PMID is **individually** efetch'd; only papers with
abstract + discussion/conclusion (or review body sections) qualify.

Use `--strategy recent` only for exploratory probes — PNAS often returns SHORT.


| Step | Script | API used | Output |
|------|--------|----------|--------|
| 1. Probe | `probe_pmc_hitrate.py` | PubMed eUtils (NCBI) | `_out/pmc_hitrate_<type>_*.json` |
| 2. Manifest | (in orchestrator) | — | `_out/corpus_manifest.json` |
| 3. Download | `load_papers.py` | PubMed PMC efetch | `papers_raw/<journal>/<pmid>.json` |
| 4. Article profiles | `run_article_profiles.py` | **Claude Sonnet** | `article_profiles/<journal>/<pmid>.json` |
| 5. Journal profiles | `aggregate_journal_profiles.py` | **Claude Sonnet** | `journal_profiles/<journal>.json` |
| 6. Embeddings | `embed_chunks.py` | **OpenAI** text-embedding-3-small | `embeddings/` |
| 7. Index | `build_index.py` | (local numpy) | `_index/` |

## One-command run (VPS)

From repo root (`/srv/Antibody_Engineer_Suite` or your clone):

```bash
cd /srv/services/writing_memory
source .venv/bin/activate

# Ensure .env has: ANTHROPIC_API_KEY, OPENAI_API_KEY, NCBI_API_KEY (optional)

cd /srv/Antibody_Engineer_Suite   # repo root — required for module imports
python services/writing_memory/ingest/run_corpus_pipeline.py \
  --article-types research \
  --restart-service
```

### Add Review articles (experimental)

```bash
python services/writing_memory/ingest/run_corpus_pipeline.py \
  --article-types research review \
  --target 50 \
  --review-target 20 \
  --restart-service
```

Review / Case / Letter hit-rates are lower than Original Research; the probe
uses relaxed JATS section rules and `--no-fail-on-short` for non-research types.

## systemd timer (weekly)

```bash
sudo cp deploy/writing-memory-corpus.service /etc/systemd/system/
sudo cp deploy/writing-memory-corpus.timer   /etc/systemd/system/

# Edit WorkingDirectory + python path if your layout differs
sudo systemctl daemon-reload
sudo systemctl enable --now writing-memory-corpus.timer

# Manual trigger
sudo systemctl start writing-memory-corpus.service
sudo journalctl -u writing-memory-corpus.service -f
```

Default schedule: **Sunday 03:00 UTC**.

## Cost estimate (full research refresh, 150 papers)

| Service | Approx. cost |
|---------|--------------|
| NCBI eUtils | Free (with API key) |
| Claude Sonnet (150 article + 3 journal profiles) | ~$3–8 USD |
| OpenAI embeddings (~2000 chunks) | ~$0.05 USD |

Review expansion (+60 papers) adds ~$1–3 Claude + ~$0.02 embeddings.

## Current limitation

- **150 research papers** are fully integrated into rewrite / similar search.
- **Review / Case / Letter** papers are ingested and tagged (`article_type` in JSON)
  but journal profiles are still aggregated **per journal**, not per article type.
  Phase 2 will add `journal_profiles/pnas_review.json` and wire the Write UI
  to select the matching profile when user picks 📚 Review.

## Environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Yes | Article + journal style extraction |
| `OPENAI_API_KEY` | Yes | Vector embeddings |
| `NCBI_API_KEY` | Recommended | 10 req/s vs 3 req/s |
| `NCBI_EMAIL` | Recommended | NCBI polite pool |
| `ANTHROPIC_MODEL` | No | Default `claude-sonnet-4-5` |
