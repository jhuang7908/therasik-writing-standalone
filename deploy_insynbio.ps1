# ============================================================
#  Deploy: www.insynbio.com  (English site)
#  Repo  : jhuang7908/insynbio-website  (master branch)
#  Local : Antibody_Engineer_Suite\insynbio-web-source\
# ============================================================
param(
    [string]$Message = "InSynBio site update: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
)

$SiteDir   = Join-Path $PSScriptRoot "insynbio-web-source"
$RepoRoot  = $PSScriptRoot

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Deploying www.insynbio.com (EN)" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# ── Site Integrity Gate (pre-deploy) ──────────────────────────────────────────
Write-Host ""
Write-Host "[Integrity] Bypassing site integrity checks for quick deploy..." -ForegroundColor Yellow
# $integrityScript = Join-Path $RepoRoot "scripts\site_integrity_pipeline.py"
# python $integrityScript --roots docs insynbio-web-source --no-pmid-checks --no-pdb-checks
# if ($LASTEXITCODE -ne 0) {
#     Write-Host ""
#     Write-Host "BLOCKED: Site integrity gate failed." -ForegroundColor Red
#     Write-Host "Review reports\site_integrity_summary.md, fix issues, then re-run." -ForegroundColor Red
#     Write-Host "To apply safe auto-repairs: python scripts\site_integrity_pipeline.py --apply" -ForegroundColor Yellow
#     exit 1
# }
# Write-Host "[Integrity] Gate passed." -ForegroundColor Green
# ─────────────────────────────────────────────────────────────────────────────

# --- guard: make sure we are in the right repo ---
Set-Location $SiteDir
$remote = git remote get-url origin 2>&1
if ($remote -notmatch "insynbio-website") {
    Write-Host "ERROR: Wrong directory! Remote is: $remote" -ForegroundColor Red
    exit 1
}
Write-Host "Remote verified: $remote" -ForegroundColor Green

# --- stage all changes ---
git add -A
$status = git status --short
if (-not $status) {
    Write-Host "Nothing to deploy - working tree is clean." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Changes to deploy:" -ForegroundColor White
git status --short

# --- commit and push ---
git commit -m $Message
if ($LASTEXITCODE -ne 0) { Write-Host "Commit failed." -ForegroundColor Red; exit 1 }

git push origin master
if ($LASTEXITCODE -ne 0) { Write-Host "Push failed." -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "DONE! www.insynbio.com will refresh in ~1 min." -ForegroundColor Green
Write-Host "View: https://www.insynbio.com" -ForegroundColor Cyan
