# Antibody Engineer Suite

A comprehensive suite for antibody engineering, focusing on VHH (single-domain antibody) design and optimization.

## Project Structure

- `app/`: Application entry points (CLI, API, UI)
- `core/`: Core modules (numbering, immunogenicity, CMC, scoring, utilities, config)
- `engines/`: Engineering engines for different antibody types
- `data/`: Data files (germlines, CMC rules, immunogenicity data, etc.)
- `protocols/`: Documentation for software and wet lab protocols
- `tests/`: Test suite

## Installation

```bash
pip install -r requirements.txt
```

## Usage

TBD - Documentation will be added as features are implemented.

## Local demo console (localhost:8000)Start the FastAPI demo from the suite root:- Windows: `START_DEMO.bat`
- Or: `conda activate anarcii` then `python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`Open `http://localhost:8000/` for the bundled **InSynBio Console** (`api/static/console.html`). API docs: `http://localhost:8000/docs`. Health metadata (Python version, optional `git_sha`): `GET /health`. Set `ABENGINECORE_GIT_SHA` in CI if `git` is not available on the server.### Console UI ↔ API capability matrix| Console runner | HTTP endpoint | Notes |
|----------------|---------------|--------|
| Structure (Fv) | — | Sidebar workflow step only; Fv prediction runs inside VH/VL humanization |
| VH/VL segmentation | `POST /annotate/vh_vl` | Body: `vh_sequence`, `vl_sequence`, `scheme`, `species`, `include_germline`. Response includes `vh_regions` / `vl_regions`, **`vh_numbering` / `vl_numbering`** (`pos`, `ins`, `aa` per residue, same scheme as `scheme`). `germline` optional. Console **browser Lite** only when scheme is IMGT and server is off |**404 / “Not Found” on segmentation:** The console calls the API via `apiJoin()`. If the HTML is opened from **Vite** (ports 5173, 5174, 3000, 4173), requests are sent to the **same host on port 8000** automatically. Otherwise set `<meta name="insynbio-api-base" content="http://127.0.0.1:8000">` (or your deployed API origin) in `console.html`, or `window.__INSYNBIO_API_BASE__`.
| VH/VL humanization (mouse/rat/rabbit) | `POST /humanize/vh_vl` | Default sync; UI can use **Background job** → `POST /humanize/vh_vl/async` + `GET /jobs/{job_id}` |
| VHH humanization | `POST /humanize/vhh` | Sync |
| IgG CMC / liability view | `POST /cmc/igg` | Same endpoint; UI switches result layout |
| VHH CMC | `POST /cmc/vhh` | Sync |
| Bispecific VHH CMC | `POST /cmc/bispecific` | Sync |
| Pre-check / segmentation / cDNA | Client-side demo helpers | No server route for these lightweight flows |Offline menu entries submit a **browser-only** request form (no backend).### Version labels (Governance vs. product UI)The console may list **product / pipeline** analysis versions (for example VH/VL design line labels shown in the UI). **Authoritative, binding standard versions** for compliance work are defined in `docs/STANDARDS_INDEX.md` and the locked standards under `docs/` — do not infer governance version from the console marketing copy alone.