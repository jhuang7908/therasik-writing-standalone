# Seed demo literature + patent libraries, then run Module 4 smoke test.
# From repo root:
#   powershell -File services/writing_memory/scripts/run_intelligence_library_qa.ps1

param(
    [string]$Base = "https://write.insynbio.com",
    [string]$ProjectId = "demo_m4_lit_pat",
    [string]$Username = "demo_ops"
)

$ErrorActionPreference = "Stop"
$Svc = Join-Path $PSScriptRoot ".."
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$DocsMod4 = Join-Path $RepoRoot "docs\operations\module4"
$Manifest = Join-Path $DocsMod4 "demo_library_manifest.json"
$SmokeReport = Join-Path $DocsMod4 "smoke_latest.md"

Write-Host "=== 1/2 Seed literature + patent demo instance (project=$ProjectId) ==="
Push-Location $Svc
python scripts/seed_intelligence_demo_libraries.py `
    --base $Base `
    --project-id $ProjectId `
    --username $Username `
    --sync-write `
    --out $Manifest
$seedExit = $LASTEXITCODE
Pop-Location
if ($seedExit -ne 0) {
    Write-Warning "Seed finished with warnings (check patent count in manifest)."
}

Write-Host "`n=== 2/2 Smoke test Module 4 ==="
Push-Location $Svc
python scripts/smoke_intelligence_module4.py `
    --base $Base `
    --project-id $ProjectId `
    --username $Username `
    --out $SmokeReport
$smokeExit = $LASTEXITCODE
Pop-Location

Write-Host "`nDemo instance:"
Write-Host "  IDE        : $Base/intelligence"
Write-Host "  Project ID : $ProjectId"
Write-Host "  Index      : $(Join-Path $RepoRoot 'docs\operations\MODULE4_INTELLIGENCE_QA.md')"
Write-Host "  Manifest   : $Manifest"
Write-Host "  Smoke MD   : $SmokeReport"

exit $smokeExit
