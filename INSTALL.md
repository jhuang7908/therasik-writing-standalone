# AbEngineCore — Installation Guide

## Quick Start (Windows)

```powershell
# 1. Download installer (or clone this repo)
# 2. Run installer — fetches Console package from GitHub Releases
.\install.ps1 -Version 1.0.0

# Also pull heavy data (structures, immunogenicity KB) — optional but recommended
.\install.ps1 -Version 1.0.0 -DataPackage
```

## Quick Start (Linux / macOS / WSL)

```bash
bash install.sh --version 1.0.0
# With heavy data:
bash install.sh --version 1.0.0 --with-data
```

## What gets downloaded

| Package | Contents | Compressed size |
|---|---|---|
| `AbEngineCore_Console_v*.zip` | API, core code, pipeline, config, essential data (germlines, atlases, rules) | ~50–70 MB |
| `AbEngineCore_Data_v*.zip` | PDB structures, immunogenicity KB, pet/feature datasets | ~80–100 MB |

## Manual Installation

```powershell
# Create conda environment
conda create -n anarcii python=3.10 -y
conda activate anarcii
pip install -r requirements.txt

# Start API server
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Open console
# Browser → http://localhost:8000
```

## Future: AlphaFold2 + RFdiffusion

These tools have large model weights (2–5 GB each) and must be installed separately.

### AlphaFold2

```bash
conda create -n af2 python=3.10 -y
conda activate af2
git clone https://github.com/google-deepmind/alphafold
pip install -r alphafold/requirements.txt
# Download model parameters (~3.5 GB)
wget https://storage.googleapis.com/alphafold/alphafold_params_colab_2022-12-06.tar
```

After installation, update `config/tools_registry.json`:

```json
"AlphaFold2": {
  "type": "python_script",
  "conda_env": "af2",
  "entrypoint": "/path/to/alphafold/run_alphafold.py"
}
```

### RFdiffusion

```bash
conda create -n rfdiff python=3.9 -y
conda activate rfdiff
git clone https://github.com/RosettaCommons/RFdiffusion
pip install -e RFdiffusion/
bash RFdiffusion/scripts/download_models.sh models/
```

After installation, update `config/tools_registry.json`:

```json
"RFdiffusion": {
  "type": "python_script",
  "conda_env": "rfdiff",
  "entrypoint": "/path/to/RFdiffusion/scripts/run_inference.py"
}
```

## Private SaaS & Docker (GHCR)

Do **not** rely on a public GitHub Release if algorithms must stay private: make the **repository private** (Releases then follow repo visibility), or ship **only** a private container.

See **`docs/operations/PRIVATE_SAAS_DOCKER.md`** for:

- Private repo + private GHCR pull
- `docker compose` single-server SaaS (build from source **or** pull-only via `docker-compose.ghcr.yml`)
- Tag-triggered image build (`.github/workflows/abenginecore-docker-publish.yml` at repo root)

```bash
cd Antibody_Engineer_Suite
docker compose up -d --build
# http://localhost:8000
```

**Pull-only (no checkout on server):** set `IMAGE=ghcr.io/<owner>/abenginecore:latest` and run `docker compose -f docker-compose.ghcr.yml up -d` (after `docker login ghcr.io`).

---

## Re-packaging (for maintainers)

```powershell
# Dry run — check file list and sizes
python pack_release.py --version 1.0.0 --dry-run

# Build both ZIPs
python pack_release.py --version 1.0.0

# Publish to GitHub Releases
gh release create v1.0.0 `
    AbEngineCore_Console_v1.0.0.zip `
    AbEngineCore_Data_v1.0.0.zip `
    --title "AbEngineCore v1.0.0" `
    --notes "See INSTALL.md for setup instructions."
```

## GitHub Releases vs. Object Storage

| Feature | GitHub Releases | OSS / S3 |
|---|---|---|
| Cost | **Free** (public repo) | Pay per GB-month + egress |
| CDN speed | GitHub global CDN, ~50–300 Mb/s typical | Alibaba OSS / AWS S3 similar |
| File size limit | 2 GB per asset | No practical limit |
| Auth required | No (public release) | No (public bucket) |
| `wget` / `curl` friendly | Yes | Yes |
| Recommended for this project | **Yes** | Only if >2 GB single file |

> **Recommendation**: GitHub Releases covers everything needed here.
> Object storage only becomes necessary if a single file exceeds 2 GB
> (e.g. bundled AF2 weights — keep those separate).
