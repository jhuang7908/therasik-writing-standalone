# Llamanade local run — console VHH demo sequence

## Demo sequence (from `api/static/console.html` → `DEMOS["alpaca-vhh"]`)

The file **`alpaca_vhh_console.fasta`** is the same **Alpaca VHH demo** used in the InSynBio web console (VHH segmentation / humanization / CMC services).

- **Source label in UI:** `Alpaca VHH demo`  
- **Length:** 117 aa (single VHH chain)

## What “full Llamanade” requires (upstream `NbHumanization_main.py`)

The published pipeline is **Linux-oriented** and, in the vendored tree, depends on **hardcoded paths** in `NbHumanization/params.py` and `Annotation.py` (originally `/opt/...`, `/data/BlastDB/...`).

In addition, **`humanizer.humanize()`** calls **Protinter** at `/opt/protinter/protinter` (see `NbHumanization/humanizer.py`). The **Zenodo code bundle** used here includes `Dockerfile` `COPY protinter`, but a **`protinter/`** directory is **not** present in the extracted zip — so a **naïve local run will fail at the humanization step** unless you obtain/build that component the same way the authors’ Docker image does.

Other dependencies (typical):

- **ANARCI** (CLI `ANARCI` on `PATH`)
- **NCBI `blastp`** + the bundled `BlastDB/FR` and `BlastDB/full` indices
- **Modeller** (Python `import modeller`) for comparative modeling
- **Python packages** used in code: `prody`, `pandas`, `numpy`, `biopython`
- Unpacked **`resources.zip`** → should provide `resources/ANARCI_Hum_H.json` and `resources/modeller_data/` (PDBs + `Modeller_VH` BLAST index) under the path expected after you patch or mirror Docker layout

## What you *can* do on this machine without the full stack

1. **Use the FASTA as the canonical test input** for any future fully wired environment (Docker/WSL with all artifacts).
2. **Optional quick check:** run **ANARCI** on the FASTA (if your conda env exposes the `ANARCI` command) to confirm numbering only — this is *not* the full Llamanade pipeline, but validates the **same input sequence** the console uses.
3. **Web server (if available):** the paper/public site referenced a **Llamanade web instance** for accessibility; that is the lowest-friction way to get an end-to-end “paper-style” result if local dependencies are not installed.

## InSynBio boundary (reminder)

This `external/llamanade/` tree is a **parallel, optional reference track**. It is **not** called from AbEngineCore `core/vhh_humanization.py` or the API.
