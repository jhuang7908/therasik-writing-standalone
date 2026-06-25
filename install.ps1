# AbEngineCore Console — Windows (PowerShell) installer
# Usage: .\install.ps1 [-Version 1.0.1] [-DataPackage]
param([string]$Version="1.0.1", [switch]$DataPackage)

$BASE  = "https://github.com/YOUR_ORG/AbEngineCore/releases/download/v$Version"
$CON   = "AbEngineCore_Console_v$Version.zip"
$DATA  = "AbEngineCore_Data_v$Version.zip"

Write-Host "AbEngineCore Console v$Version installer" -ForegroundColor Cyan

# 1. Download console package
if (-not (Test-Path $CON)) {
    Write-Host "Downloading $CON ..."
    Invoke-WebRequest -Uri "$BASE/$CON" -OutFile $CON -UseBasicParsing
}
Expand-Archive -Path $CON -DestinationPath . -Force
Write-Host "Console package extracted." -ForegroundColor Green

# 2. Optionally download data package
if ($DataPackage) {
    if (-not (Test-Path $DATA)) {
        Write-Host "Downloading $DATA ..."
        Invoke-WebRequest -Uri "$BASE/$DATA" -OutFile $DATA -UseBasicParsing
    }
    Expand-Archive -Path $DATA -DestinationPath . -Force
    Write-Host "Data package extracted." -ForegroundColor Green
}

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
