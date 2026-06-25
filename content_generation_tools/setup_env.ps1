# ==============================================================================
# InSynBio Content Generation Environment Setup
# ==============================================================================
# This script creates a dedicated Conda environment for the AI content generation
# tools (DeckWeaver, Space-Design, PPT Templates).

$EnvName = "content_gen"

Write-Host "Creating Conda environment: $EnvName..." -ForegroundColor Cyan
conda create -n $EnvName python=3.11 -y

Write-Host "Activating environment and installing dependencies..." -ForegroundColor Cyan
# We use conda run to execute pip inside the new environment
conda run -n $EnvName pip install -r requirements.txt

Write-Host "==============================================================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "To use the tools, activate the environment first:" -ForegroundColor Yellow
Write-Host "conda activate $EnvName" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Green
