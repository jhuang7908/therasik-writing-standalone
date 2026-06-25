# Llamanade (external reference track)

This directory holds the **Zenodo-archived** Llamanade nanobody humanization pipeline as a **separate, optional line** for customers or internal benchmarking.

## Policy (owner)

- **Not part of AbEngineCore VHH humanization.** Do not import this tree from `core/vhh_humanization.py`, the VH/VL engine, or API routers.
- **Parallel choice only:** offer as “reference / third-party reproducible pipeline” side by side with InSynBio VHH humanization; keep outputs and contracts distinct.
- **No mixing of configs:** do not merge Llamanade templates, scores, or residue rules into `config/tier_system_config.json` or SSOT without an explicit governance upgrade.

## What was placed here

| Item | Description |
|------|-------------|
| `llamanade_zenodo_5575933.zip` | Original Zenodo download (≈100 MB). Repository `.gitignore` ignores `*.zip`; keep locally or store outside git if policies require. |
| `Llamanade_upstream/` | Extracted upstream bundle (commit-ish folder name normalized to this path). Contains `NbHumanization/`, `scripts/`, `Dockerfile`, `README.md` (paper abstract), `resources.zip`, etc. |

## Source & citation

- Publication: *Structure* / companion PMC entry — PMID [34373858](https://pubmed.ncbi.nlm.nih.gov/34373858/), PMC [PMC8351782](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8351782/).
- Zenodo record used for this drop: **5575933** (filename `5575933.zip`).

## Local use

Follow **`Llamanade_upstream/README.md`**, **`Dockerfile`**, and shell installers (`install_*.sh`) inside `Llamanade_upstream/`. This environment is **Linux-oriented** (Shell + Python); on Windows, prefer **WSL2** or Docker per upstream docs.

If upstream expects **`resources.zip`** unpacked next to the tools, unzip it in **`Llamanade_upstream/`** (same folder as that file).

## Web-console VHH demo (parallel input)

Under **`examples/`**:

- `alpaca_vhh_console.fasta` — same sequence as `api/static/console.html` → `DEMOS["alpaca-vhh"]`.
- `LLAMANADE_RUN_NOTES.md` — prerequisites and known gaps (Zenodo bundle vs full Docker context).
- `verify_console_fasta_only.py` — stdlib-only sanity check for that FASTA (does **not** invoke Llamanade).

## License

Software license (if any) is in the upstream tree (e.g. `LICENSE` if present). Treat distribution terms as **per upstream**; the PMC article uses CC BY-NC-ND for the *paper text*, which is not necessarily the software license.
