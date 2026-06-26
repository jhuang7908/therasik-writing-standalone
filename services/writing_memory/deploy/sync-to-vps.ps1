# Sync writing_memory code to VPS and restart the service.
# Run from repo root:
#   powershell -File services/writing_memory/deploy/sync-to-vps.ps1
#
# Optional env:
#   $env:WM_DEPLOY_HOST = "root@157.180.91.72"
#   $env:WM_DEPLOY_DIR  = "/srv/services/writing_memory"
#   $env:WM_SSH_KEY     = "C:\Users\You\.ssh\id_ed25519"

param(
    [string]$DeployHost = $(if ($env:WM_DEPLOY_HOST) { $env:WM_DEPLOY_HOST } else { "root@157.180.91.72" }),
    [string]$RemoteDir = $(if ($env:WM_DEPLOY_DIR) { $env:WM_DEPLOY_DIR } else { "/srv/services/writing_memory" }),
    [string]$SshKey = $env:WM_SSH_KEY,
    [switch]$SkipRestart,
    [switch]$SkipReferences,
    [switch]$MirrorScienceAssets
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$Svc = Join-Path $RepoRoot "services\writing_memory"

$defaultKey = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
if (-not $SshKey -and (Test-Path $defaultKey)) {
    $SshKey = $defaultKey
}

$sshArgs = @(
    "-o", "ConnectTimeout=20",
    "-o", "PreferredAuthentications=publickey",
    "-o", "PasswordAuthentication=no"
)
$scpArgs = @("-o", "ConnectTimeout=20")
if ($SshKey) {
    $sshArgs += @("-i", $SshKey, "-o", "IdentitiesOnly=yes")
    $scpArgs += @("-i", $SshKey, "-o", "IdentitiesOnly=yes")
} else {
    Write-Error "No SSH private key found. Set WM_SSH_KEY or create $defaultKey"
}

Write-Host "Testing SSH to $DeployHost ..."
& ssh @sshArgs $DeployHost "echo ok"
if ($LASTEXITCODE -ne 0) {
    Write-Error @"
SSH failed (no key or wrong host). Fix once, then re-run this script:

  1. Generate a key (if needed):
       ssh-keygen -t ed25519 -f `"$env:USERPROFILE\.ssh\id_ed25519`"
  2. Copy to VPS (enter root password when prompted):
       ssh-copy-id -i `"$env:USERPROFILE\.ssh\id_ed25519.pub`" $DeployHost
  3. Re-run:
       powershell -File services/writing_memory/deploy/sync-to-vps.ps1

Or set WM_SSH_KEY to your private key path.
"@
}

$pyFiles = @(
    "app.py", "user_style.py", "vector_store.py", "corpus_augment.py",
    "upload_intake.py", "style_safety.py", "pdf_text.py", "quota.py",
    "manuscript_qc.py", "journal_context.py",
    "vale_runner.py", "quarto_runner.py",
    "article_type_context.py", "account_style.py", "reference_library.py",
    "article_type_benchmarks.py", "language_tool.py",
    "submission_formatter.py", "reference_exporter.py",
    "reporting_guidelines.py", "feedback_store.py",
    "elabftw_client.py", "protocolsio_client.py", "openalex_client.py",
    "patent_client.py", "patent_sequences.py", "platform_modules.py",
    "lab_report_generator.py", "lab_progress_hub.py",
    "lab_report_postprocess.py", "lab_report_analytics.py",
    "intelligence_store.py",
    "reference_import.py",
    "intelligence_refs.py",
    "unpaywall_client.py",
    "library_bridge.py",
    "qa_summary.py",
    "intelligence_radar.py",
    "intelligence_demo_seed.py",
    "science_assets_hub.py"
)

Write-Host "Uploading Python modules ..."
foreach ($f in $pyFiles) {
    $local = Join-Path $Svc $f
    if (-not (Test-Path $local)) { throw "Missing $local" }
    & scp @scpArgs $local "${DeployHost}:${RemoteDir}/"
    if ($LASTEXITCODE -ne 0) { throw "scp failed for $f" }
}

Write-Host "Uploading db/intelligence_schema.sql (Module 4 pgvector schema) ..."
& ssh @sshArgs $DeployHost "mkdir -p '$RemoteDir/db'"
if ($LASTEXITCODE -ne 0) { Write-Warning "mkdir db failed — Module 4 PG schema not uploaded" }
else {
    & scp @scpArgs (Join-Path $Svc "db\intelligence_schema.sql") "${DeployHost}:${RemoteDir}/db/"
    if ($LASTEXITCODE -ne 0) { Write-Warning "scp failed for intelligence_schema.sql — continuing" }
}

Write-Host "Uploading data/qa/smoke_latest.json (IDE smoke summary) ..."
& ssh @sshArgs $DeployHost "mkdir -p '$RemoteDir/data/qa'"
if ($LASTEXITCODE -eq 0) {
    $qaJson = Join-Path $Svc "data\qa\smoke_latest.json"
    if (Test-Path $qaJson) {
        & scp @scpArgs $qaJson "${DeployHost}:${RemoteDir}/data/qa/"
        if ($LASTEXITCODE -ne 0) { Write-Warning "scp failed for smoke_latest.json — QA panel will be empty until next smoke run" }
    } else {
        Write-Warning "Missing $qaJson — run smoke_intelligence_module4.py first"
    }
}

Write-Host "Uploading data/intelligence_demo_samples.json (Module 4 builtin samples) ..."
& ssh @sshArgs $DeployHost "mkdir -p '$RemoteDir/data'"
if ($LASTEXITCODE -eq 0) {
    $demoJson = Join-Path $Svc "data\intelligence_demo_samples.json"
    if (Test-Path $demoJson) {
        & scp @scpArgs $demoJson "${DeployHost}:${RemoteDir}/data/"
        if ($LASTEXITCODE -ne 0) { Write-Warning "scp failed for intelligence_demo_samples.json — seed-samples API may fail" }
    } else {
        Write-Warning "Missing $demoJson"
    }
}

Write-Host "Uploading science_assets manifest + download script (libraries mirrored on VPS) ..."
& ssh @sshArgs $DeployHost "mkdir -p '$RemoteDir/data/science_assets' '$RemoteDir/scripts'"
if ($LASTEXITCODE -eq 0) {
    foreach ($sa in @("manifest.json", "ATTRIBUTION.md")) {
        $local = Join-Path $Svc "data\science_assets\$sa"
        if (Test-Path $local) {
            & scp @scpArgs $local "${DeployHost}:${RemoteDir}/data/science_assets/"
            if ($LASTEXITCODE -ne 0) { Write-Warning "scp failed for science_assets/$sa" }
        }
    }
    $dlScript = Join-Path $Svc "scripts\download_science_asset_libraries.py"
    if (Test-Path $dlScript) {
        & scp @scpArgs $dlScript "${DeployHost}:${RemoteDir}/scripts/"
        if ($LASTEXITCODE -ne 0) { Write-Warning "scp failed for download_science_asset_libraries.py" }
    }
} else {
    Write-Warning "mkdir science_assets failed — Figure Studio libraries not uploaded"
}

Write-Host "Uploading static/write.html, lab.html, platform.html, intelligence.html, figure_studio.html, grant_studio.html ..."
foreach ($hf in @("write.html", "lab.html", "platform.html", "intelligence.html", "figure_studio.html", "grant_studio.html")) {
    $local = Join-Path $Svc "static\$hf"
    if (-not (Test-Path $local)) {
        if ($hf -eq "lab.html") { Write-Warning "Missing $hf — skip" ; continue }
        throw "Missing $local"
    }
    & scp @scpArgs $local "${DeployHost}:${RemoteDir}/static/"
    if ($LASTEXITCODE -ne 0) { throw "scp failed for $hf" }
}

if (-not $SkipReferences) {
    Write-Host "Uploading references/ module ..."
    & ssh @sshArgs $DeployHost "mkdir -p '$RemoteDir/references'" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "mkdir references failed — retry with -SkipReferences or fix SSH"
    } else {
        Get-ChildItem -Path (Join-Path $Svc "references") -Filter "*.py" -ErrorAction SilentlyContinue | ForEach-Object {
            & scp @scpArgs $_.FullName "${DeployHost}:${RemoteDir}/references/" 2>$null
            if ($LASTEXITCODE -ne 0) { Write-Warning "scp failed for references/$($_.Name) — continuing" }
        }
    }
} else {
    Write-Host "Skipping references/ upload (-SkipReferences)."
}

# v15.44 B1 — upload per-journal section_phrases.json (demo seeds; A1 will replace)
Write-Host "Uploading journal_profiles/*.section_phrases.json ..."
$phraseFiles = Get-ChildItem -Path (Join-Path $Svc "journal_profiles") -Filter "*.section_phrases.json" -ErrorAction SilentlyContinue
foreach ($pf in $phraseFiles) {
    & scp @scpArgs $pf.FullName "${DeployHost}:${RemoteDir}/journal_profiles/"
    if ($LASTEXITCODE -ne 0) { throw "scp failed for $($pf.Name)" }
}

# Vale style pack + config (optional on server if `vale` binary installed)
Write-Host "Uploading Vale config (vale_styles + .vale.ini) ..."
& ssh @sshArgs $DeployHost "mkdir -p '$RemoteDir/vale_styles'"
if ($LASTEXITCODE -ne 0) { throw "mkdir vale_styles failed" }
& scp @scpArgs (Join-Path $Svc ".vale.ini") "${DeployHost}:${RemoteDir}/"
if ($LASTEXITCODE -ne 0) { throw "scp failed for .vale.ini" }
& scp @scpArgs -r (Join-Path $Svc "vale_styles") "${DeployHost}:${RemoteDir}/"
if ($LASTEXITCODE -ne 0) { throw "scp failed for vale_styles" }

Write-Host "Uploading cohort/ + RELEASE_v1.json ..."
& ssh @sshArgs $DeployHost "mkdir -p '$RemoteDir/cohort' '$RemoteDir/data/article_type_cohorts'"
if ($LASTEXITCODE -ne 0) { throw "mkdir cohort failed" }
Get-ChildItem -Path (Join-Path $Svc "cohort") -Filter "*.py" | ForEach-Object {
    & scp @scpArgs $_.FullName "${DeployHost}:${RemoteDir}/cohort/"
    if ($LASTEXITCODE -ne 0) { throw "scp failed for cohort/$($_.Name)" }
}
foreach ($cf in @("RELEASE_v1.json", "SEED_FAMOUS_V1.json")) {
    $cp = Join-Path $Svc "data\article_type_cohorts\$cf"
    if (Test-Path $cp) {
        & scp @scpArgs $cp "${DeployHost}:${RemoteDir}/data/article_type_cohorts/"
        if ($LASTEXITCODE -ne 0) { throw "scp failed for $cf" }
    }
}

Write-Host "Uploading schemas/ (article types + journal surface + grant templates) ..."
& ssh @sshArgs $DeployHost "mkdir -p '$RemoteDir/schemas/article_types' '$RemoteDir/schemas/grant_templates'"
if ($LASTEXITCODE -ne 0) { throw "mkdir schemas failed" }
& scp @scpArgs -r (Join-Path $Svc "schemas\article_types") "${DeployHost}:${RemoteDir}/schemas/"
if ($LASTEXITCODE -ne 0) { throw "scp failed for article_types" }
if (Test-Path (Join-Path $Svc "schemas\grant_templates")) {
    Get-ChildItem (Join-Path $Svc "schemas\grant_templates") -Filter "*.json" | ForEach-Object {
        & scp @scpArgs $_.FullName "${DeployHost}:${RemoteDir}/schemas/grant_templates/"
        if ($LASTEXITCODE -ne 0) { throw "scp failed for grant_templates/$($_.Name)" }
    }
}
if (Test-Path (Join-Path $Svc "schemas\project_asset_hub_v1.json")) {
    & scp @scpArgs (Join-Path $Svc "schemas\project_asset_hub_v1.json") "${DeployHost}:${RemoteDir}/schemas/"
}
foreach ($jf in @("article_types_index.json", "journal_surface.json")) {
    & scp @scpArgs (Join-Path $Svc "schemas\$jf") "${DeployHost}:${RemoteDir}/schemas/"
    if ($LASTEXITCODE -ne 0) { throw "scp failed for $jf" }
}

if ($MirrorScienceAssets) {
    Write-Host "Mirroring science asset libraries on VPS (git + HTTP; may take several minutes) ..."
    & ssh @sshArgs $DeployHost "cd '$RemoteDir' && (test -f .venv/bin/python && .venv/bin/python scripts/download_science_asset_libraries.py --all || python3 scripts/download_science_asset_libraries.py --all)"
    if ($LASTEXITCODE -ne 0) { Write-Warning "Science asset mirror failed — run manually on VPS: python scripts/download_science_asset_libraries.py --all" }
}

if (-not $SkipRestart) {
    Write-Host "Restarting writing-memory ..."
    & ssh @sshArgs $DeployHost "cd '$RemoteDir' && (test -f .venv/bin/pip && .venv/bin/pip install -q 'pypdf>=4.0' 'requests-oauthlib>=2.0.0' 'requests>=2.31' 'textstat>=0.7' 'python-docx>=1.1' || pip3 install -q 'pypdf>=4.0' 'requests-oauthlib>=2.0.0' 'requests>=2.31' 'textstat>=0.7' 'python-docx>=1.1') && systemctl restart writing-memory && sleep 2 && systemctl is-active writing-memory"
    if ($LASTEXITCODE -ne 0) { throw "restart failed" }
}

Write-Host "Checking https://write.insynbio.com/health ..."
try {
    $h = Invoke-RestMethod -Uri "https://write.insynbio.com/health" -TimeoutSec 20
    $h | ConvertTo-Json -Compress | Write-Host
    $lint = $null
    try {
        $lintProbe = @{ text = "Furthermore, Moreover, Taken together, these findings demonstrate that X." } | ConvertTo-Json
        $lint = Invoke-RestMethod -Uri "https://write.insynbio.com/lint_prose" -Method POST `
            -ContentType "application/json" -Body $lintProbe -TimeoutSec 15
        Write-Host "lint_prose probe: total=$($lint.total) vale_available=$($lint.vale_available)"
    } catch {
        Write-Warning "lint_prose probe failed (install vale on VPS?): $_"
    }
    if ($lint -and -not $lint.vale_available) {
        Write-Warning "Vale binary missing on VPS. Run: powershell -File services/writing_memory/deploy/install-vale-on-vps.ps1"
    }
    if ($h.vector_backend) {
        Write-Host "vector_backend: $($h.vector_backend | ConvertTo-Json -Compress)"
    } else {
        Write-Warning "Health has no vector_backend field — confirm app.py deployed."
    }
} catch {
    Write-Warning "Could not reach public health URL: $_"
}

try {
    $mods = Invoke-RestMethod -Uri "https://write.insynbio.com/platform/modules/status" -TimeoutSec 20
    Write-Host "platform/modules/status:"
    foreach ($m in $mods.modules) {
        Write-Host ("  Module {0}: {1}" -f $m.id, $m.status)
    }
} catch {
    Write-Warning "platform/modules/status not reachable yet: $_"
}

Write-Host "Done."
