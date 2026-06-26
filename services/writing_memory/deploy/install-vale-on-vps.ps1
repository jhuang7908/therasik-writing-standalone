# Install Vale CLI on the writing-memory VPS (one-time).
# Run: powershell -File services/writing_memory/deploy/install-vale-on-vps.ps1

param(
    [string]$DeployHost = $(if ($env:WM_DEPLOY_HOST) { $env:WM_DEPLOY_HOST } else { "root@157.180.91.72" }),
    [string]$ValeVersion = "3.14.2"
)

$ErrorActionPreference = "Stop"
$SshKey = $env:WM_SSH_KEY
if (-not $SshKey) {
    $defaultKey = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
    if (Test-Path $defaultKey) { $SshKey = $defaultKey }
}
$sshArgs = @("-o", "ConnectTimeout=20")
if ($SshKey) {
    $sshArgs += @("-i", $SshKey, "-o", "IdentitiesOnly=yes")
}

# Single-line remote script; use single-quoted segments so PowerShell does not parse >.
$remote = 'set -e; ' +
    "if command -v vale 2>/dev/null; then vale --version; exit 0; fi; " +
    'cd /tmp; ' +
    "curl -fsSL -o vale.tgz https://github.com/errata-ai/vale/releases/download/v${ValeVersion}/vale_${ValeVersion}_Linux_64-bit.tar.gz; " +
    'tar -xzf vale.tgz vale; install -m 755 vale /usr/local/bin/vale; rm -f vale vale.tgz; vale --version'

Write-Host "Installing Vale $ValeVersion on $DeployHost ..."
& ssh @sshArgs $DeployHost $remote
if ($LASTEXITCODE -ne 0) { throw "Vale install failed" }

Write-Host "Probing https://write.insynbio.com/lint_prose ..."
$body = '{"text":"Furthermore, the results demonstrate robust engraftment."}'
$lint = Invoke-RestMethod -Uri "https://write.insynbio.com/lint_prose" -Method POST `
    -ContentType "application/json" -Body $body -TimeoutSec 20
Write-Host "vale_available=$($lint.vale_available) total=$($lint.total) by_rule=$($lint.by_rule | ConvertTo-Json -Compress)"
if (-not $lint.vale_available) {
    Write-Warning "Vale installed but API still reports unavailable — restart writing-memory:"
    Write-Host "  ssh $DeployHost systemctl restart writing-memory"
}
Write-Host "Done."
