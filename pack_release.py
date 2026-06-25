"""
AbEngineCore Release Packager
Creates two ZIP assets for GitHub Releases:
  1. AbEngineCore_Console_v{VER}.zip  — API + core code + essential data (~50 MB)
  2. AbEngineCore_Data_v{VER}.zip     — heavy reference data (~200-250 MB)

Usage:
    python pack_release.py [--version 1.0.0] [--dry-run]
"""

import os
import sys
import zipfile
import argparse
from pathlib import Path

VERSION_DEFAULT = "1.0.0"

# ── What goes into the Console package ───────────────────────────────────────
CONSOLE_CODE_DIRS = [
    "api",
    "core",
    "config",
    "pipeline",
]

CONSOLE_CODE_FILES = [
    "requirements.txt",
    "config.yaml",
    "README.md",
    "SYSTEM_OVERVIEW.md",
]

# Only these data sub-dirs are needed for the console to run
CONSOLE_DATA_DIRS = [
    "data/germlines",
    "data/humanization_assay",
    "data/thera_sabdab",
    "data/vhh_39_clinical_atlas",
    "data/vhh_clinical_39_union",
    "data/vhh_clinical_40_anarci",
    "data/vhh_database_b_union",
    "data/vhh_analytics_reports",
    "data/vhh_structural_union",
    "data/vhh_structural_microenv",
    "data/vhh_weak_cases",
    "data/natural_380_atlas",
    "data/engineered_459_atlas",
    "data/clinical_kb",
    "data/ADA_reliable_package",
    "data/sabdab_nano",
    "data/scfv_52_atlas",
    "data/bispecific_75_atlas",
    "data/cmc_rules",
    "data/design_rules",  # rules JSON, not huge PDB
    "data/species_profiles",
    "data/vernier_zones",
    "data/reference",
    "data/actes_sequences",
    "data/CAR",
    "data/adc_atlas",
    "data/thera_not_analyzed",
]

# Heavy data that goes into the Data package
DATA_HEAVY_DIRS = [
    "data/structures",
    "data/immunogenicity_knowledge_base",
    "data/pet_antibody_atlas",
    "data/vhh_cli_runs",
    "data/features",
    "data/knowledge",
    "data/repertoire",
    "data/templates",
]

EXCLUDE_PATTERNS = {
    "__pycache__", ".pyc", ".DS_Store", ".git",
    ".job_storage", "archive", ".agent", ".cursor",
    ".tmp", ".bak", ".log",
}


def should_exclude(path_str: str) -> bool:
    for pat in EXCLUDE_PATTERNS:
        if pat in path_str:
            return True
    return False


def add_dir(zipf: zipfile.ZipFile, src_dir: str, base: str, dry: bool) -> int:
    """Add src_dir into zip, paths relative to base. Returns file count."""
    count = 0
    if not os.path.exists(src_dir):
        print(f"  [SKIP] {src_dir} — not found")
        return 0
    for root, dirs, files in os.walk(src_dir):
        dirs[:] = [d for d in dirs if not should_exclude(d)]
        for fname in files:
            fp = os.path.join(root, fname)
            if should_exclude(fp):
                continue
            arcname = os.path.relpath(fp, start=base)
            if not dry:
                zipf.write(fp, arcname)
            count += 1
    return count


def add_file(zipf: zipfile.ZipFile, fpath: str, dry: bool) -> bool:
    if not os.path.exists(fpath):
        print(f"  [SKIP] {fpath} — not found")
        return False
    if not dry:
        zipf.write(fpath, fpath)
    return True


def pack(out_name: str, code_dirs, code_files, data_dirs, base: str, dry: bool):
    total = 0
    if dry:
        print(f"\n[DRY-RUN] Would create: {out_name}")
        zipf = None
    else:
        print(f"\n[PACK] Creating: {out_name}")
        zipf = zipfile.ZipFile(out_name, "w", zipfile.ZIP_DEFLATED, compresslevel=7)

    for d in code_dirs:
        n = add_dir(zipf, d, base, dry)
        print(f"  + {d:<40s} ({n} files)")
        total += n

    for f in code_files:
        ok = add_file(zipf, f, dry)
        if ok:
            print(f"  + {f}")
            total += 1

    for d in data_dirs:
        n = add_dir(zipf, d, base, dry)
        sz_mb = sum(
            os.path.getsize(os.path.join(r, f))
            for r, _, fs in os.walk(d)
            for f in fs
        ) / 1024 / 1024 if os.path.exists(d) else 0
        print(f"  + {d:<40s} ({n} files, {sz_mb:.1f} MB raw)")
        total += n

    if not dry:
        zipf.close()
        zip_mb = os.path.getsize(out_name) / 1024 / 1024
        print(f"\n  => {out_name}  [{zip_mb:.1f} MB compressed, {total} files]\n")
    else:
        print(f"\n  => {total} files would be included\n")


def main():
    parser = argparse.ArgumentParser(description="AbEngineCore Release Packager")
    parser.add_argument("--version", default=VERSION_DEFAULT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    v = args.version
    dry = args.dry_run
    base = os.getcwd()

    # Add install script to console package
    write_install_scripts(v)

    pack(
        out_name=f"AbEngineCore_Console_v{v}.zip",
        code_dirs=CONSOLE_CODE_DIRS,
        code_files=CONSOLE_CODE_FILES + ["install.ps1", "install.sh"],
        data_dirs=CONSOLE_DATA_DIRS,
        base=base,
        dry=dry,
    )

    pack(
        out_name=f"AbEngineCore_Data_v{v}.zip",
        code_dirs=[],
        code_files=[],
        data_dirs=DATA_HEAVY_DIRS,
        base=base,
        dry=dry,
    )

    if not dry:
        print("=" * 60)
        print("Next: create GitHub Release and upload both ZIPs:")
        print(f"  gh release create v{v} \\")
        print(f"      AbEngineCore_Console_v{v}.zip \\")
        print(f"      AbEngineCore_Data_v{v}.zip \\")
        print(f'      --title "AbEngineCore v{v}" \\')
        print(f'      --notes "Console + API release. See INSTALL.md for setup."')


def write_install_scripts(ver: str):
    """Generate install.ps1 and install.sh that users run on a fresh machine."""

    ps1 = f"""# AbEngineCore Console — Windows (PowerShell) installer
# Usage: .\\install.ps1 [-Version {ver}] [-DataPackage]
param([string]$Version="{ver}", [switch]$DataPackage)

$BASE  = "https://github.com/YOUR_ORG/AbEngineCore/releases/download/v$Version"
$CON   = "AbEngineCore_Console_v$Version.zip"
$DATA  = "AbEngineCore_Data_v$Version.zip"

Write-Host "AbEngineCore Console v$Version installer" -ForegroundColor Cyan

# 1. Download console package
if (-not (Test-Path $CON)) {{
    Write-Host "Downloading $CON ..."
    Invoke-WebRequest -Uri "$BASE/$CON" -OutFile $CON -UseBasicParsing
}}
Expand-Archive -Path $CON -DestinationPath . -Force
Write-Host "Console package extracted." -ForegroundColor Green

# 2. Optionally download data package
if ($DataPackage) {{
    if (-not (Test-Path $DATA)) {{
        Write-Host "Downloading $DATA ..."
        Invoke-WebRequest -Uri "$BASE/$DATA" -OutFile $DATA -UseBasicParsing
    }}
    Expand-Archive -Path $DATA -DestinationPath . -Force
    Write-Host "Data package extracted." -ForegroundColor Green
}}

# 3. Python environment
Write-Host "`nSetting up Python environment (anarcii)..."
conda create -n anarcii python=3.10 -y
conda activate anarcii
pip install -r requirements.txt

# 4. Start API server
Write-Host "`nStart server with:  uvicorn api.main:app --port 8000" -ForegroundColor Yellow
Write-Host "Then open:          http://localhost:8000" -ForegroundColor Yellow

# ── Future: AlphaFold2 + RFdiffusion ─────────────────────────────────────────
# AF2 / RFdiffusion are large (~2–5 GB model weights each) — install separately:
#
#   AF2:
#     git clone https://github.com/google-deepmind/alphafold
#     conda create -n af2 python=3.10 && pip install -r alphafold/requirements.txt
#     # Download weights from https://storage.googleapis.com/alphafold/alphafold_params_*.tar
#
#   RFdiffusion:
#     git clone https://github.com/RosettaCommons/RFdiffusion
#     conda create -n rfdiff python=3.9 && pip install -r RFdiffusion/requirements.txt
#     # Download weights from https://files.ipd.uw.edu/pub/RFdiffusion/...
#
# Once installed, update config/tools_registry.json with new tool paths.
"""

    sh = f"""#!/usr/bin/env bash
# AbEngineCore Console — Linux/macOS installer
# Usage: bash install.sh [--version {ver}] [--with-data]

VERSION="{ver}"
WITH_DATA=0

for arg in "$@"; do
    case $arg in
        --version=*) VERSION="${{arg#*=}}" ;;
        --with-data) WITH_DATA=1 ;;
    esac
done

BASE="https://github.com/YOUR_ORG/AbEngineCore/releases/download/v$VERSION"
CON="AbEngineCore_Console_v${{VERSION}}.zip"
DATA="AbEngineCore_Data_v${{VERSION}}.zip"

echo "AbEngineCore Console v$VERSION installer"

# 1. Console package
[ ! -f "$CON" ] && curl -L -o "$CON" "$BASE/$CON"
unzip -q -o "$CON"
echo "Console package extracted."

# 2. Data package (optional)
if [ "$WITH_DATA" = "1" ]; then
    [ ! -f "$DATA" ] && curl -L -o "$DATA" "$BASE/$DATA"
    unzip -q -o "$DATA"
    echo "Data package extracted."
fi

# 3. Python environment
conda create -n anarcii python=3.10 -y
conda activate anarcii
pip install -r requirements.txt

echo ""
echo "Start:  uvicorn api.main:app --port 8000"
echo "Open:   http://localhost:8000"

# ── Future: AlphaFold2 + RFdiffusion ─────────────────────────────────────────
# AF2 / RFdiffusion: model weights are 2–5 GB each, install separately.
#
# AF2 (CPU-only demo):
#   git clone https://github.com/google-deepmind/alphafold && pip install -e alphafold
#   wget https://storage.googleapis.com/alphafold/alphafold_params_colab_2022-12-06.tar
#
# RFdiffusion:
#   git clone https://github.com/RosettaCommons/RFdiffusion
#   conda create -n rfdiff python=3.9 && pip install -e RFdiffusion
#   bash RFdiffusion/scripts/download_models.sh models/
#
# Then update config/tools_registry.json with new entrypoints.
"""

    with open("install.ps1", "w", encoding="utf-8") as f:
        f.write(ps1)
    with open("install.sh", "w", encoding="utf-8") as f:
        f.write(sh)
    print("[INFO] Generated install.ps1 and install.sh")


if __name__ == "__main__":
    main()
