#!/usr/bin/env bash
# AbEngineCore Console — Linux/macOS installer
# Usage: bash install.sh [--version 1.0.1] [--with-data]

VERSION="1.0.1"
WITH_DATA=0

for arg in "$@"; do
    case $arg in
        --version=*) VERSION="${arg#*=}" ;;
        --with-data) WITH_DATA=1 ;;
    esac
done

BASE="https://github.com/YOUR_ORG/AbEngineCore/releases/download/v$VERSION"
CON="AbEngineCore_Console_v${VERSION}.zip"
DATA="AbEngineCore_Data_v${VERSION}.zip"

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
