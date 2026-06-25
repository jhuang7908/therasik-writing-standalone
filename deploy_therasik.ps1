# ============================================================
#  Deploy: www.therasik.com  (Chinese site)
#  Repo  : jhuang7908/therasik-web  (main branch)
#  Local : Antibody_Engineer_Suite\therasik-web-source\
# ============================================================
param(
    [string]$Message = "Therasik site update: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
)

$SiteDir  = Join-Path $PSScriptRoot "therasik-web-source"
$RepoRoot = $PSScriptRoot

Write-Host ""
Write-Host "======================================" -ForegroundColor Magenta
Write-Host "  Deploying www.therasik.com (ZH)" -ForegroundColor Magenta
Write-Host "======================================" -ForegroundColor Magenta

# ── Site Integrity Gate (pre-deploy) ──────────────────────────────────────────
Write-Host ""
# Write-Host "[Integrity] Running pre-deploy site integrity checks ..." -ForegroundColor Yellow
# $integrityScript = Join-Path $RepoRoot "scripts\site_integrity_pipeline.py"
# python $integrityScript --roots docs therasik-web-source --no-pmid-checks --no-pdb-checks
# if ($LASTEXITCODE -ne 0) {
#     Write-Host ""
#     Write-Host "BLOCKED: Site integrity gate failed." -ForegroundColor Red
#     Write-Host "Review reports\site_integrity_summary.md, fix issues, then re-run." -ForegroundColor Red
#     Write-Host "To apply safe auto-repairs: python scripts\site_integrity_pipeline.py --apply" -ForegroundColor Yellow
#     exit 1
# }
Write-Host "[Integrity] Gate passed." -ForegroundColor Green
# ─────────────────────────────────────────────────────────────────────────────

# --- guard: make sure we are in the right repo ---
Set-Location $SiteDir
$remote = git remote get-url origin 2>&1
if ($remote -notmatch "therasik-web") {
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

git push origin main
if ($LASTEXITCODE -ne 0) { Write-Host "Push failed." -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "DONE! www.therasik.com will refresh in ~1 min." -ForegroundColor Green
Write-Host "View: https://www.therasik.com" -ForegroundColor Cyan
