# setup_humatch_wsl.ps1
# ─────────────────────────────────────────────────────────────────────────────
# Windows PowerShell wrapper: installs HuMAtch inside WSL2 Ubuntu-22.04
#
# Why WSL?  bioconda (needed for hmmer/ANARCI) does NOT support Windows natively.
# WSL2 Ubuntu-22.04 is already present on this machine.
#
# Usage (run from Antibody_Engineer_Suite root):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\scripts\setup_humatch_wsl.ps1
# ─────────────────────────────────────────────────────────────────────────────
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$WSL_DISTRO  = "Ubuntu-22.04"
$SCRIPT_WSL  = "/mnt/d/InSynBio-AI-Research/Antibody_Engineer_Suite/scripts/setup_humatch_wsl.sh"

Write-Host "`n>>> Converting line endings (CRLF -> LF) for WSL bash script" -ForegroundColor Cyan
$scriptPath = "$PSScriptRoot\setup_humatch_wsl.sh"
(Get-Content $scriptPath -Raw) -replace "`r`n", "`n" | Set-Content $scriptPath -NoNewline

Write-Host ">>> Running setup inside WSL ($WSL_DISTRO)" -ForegroundColor Cyan
wsl -d $WSL_DISTRO -- bash "$SCRIPT_WSL"

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] WSL install failed (exit $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== HuMAtch WSL setup complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "To run HuMAtch from PowerShell:" -ForegroundColor Yellow
Write-Host "  wsl -d $WSL_DISTRO -- bash -c 'source ~/.venvs/humatch/bin/activate && Humatch-classify -H <VH_SEQ> -L <VL_SEQ> -s'"
Write-Host ""
Write-Host "To run the full triple evaluation:" -ForegroundColor Yellow
Write-Host "  conda run -n anarcii python projects\clinical_ref_mAbs_smart_cmc\run_triple_immunotools.py"
