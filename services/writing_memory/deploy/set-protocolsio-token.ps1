# Set protocols.io token on VPS without committing secrets to git.
# Run once from repo root (PowerShell):
#
#   $env:PROTOCOLSIO_ACCESS_TOKEN = "paste-your-client-access-token-here"
#   powershell -File services/writing_memory/deploy/set-protocolsio-token.ps1
#
# Optional:
#   $env:WM_DEPLOY_HOST = "root@157.180.91.72"
#   $env:PROTOCOLSIO_WORKSPACE_URI = "insynbio"

param(
    [string]$DeployHost = $(if ($env:WM_DEPLOY_HOST) { $env:WM_DEPLOY_HOST } else { "root@157.180.91.72" }),
    [string]$RemoteEnv = "/srv/services/writing_memory/.env",
    [string]$WorkspaceUri = $(if ($env:PROTOCOLSIO_WORKSPACE_URI) { $env:PROTOCOLSIO_WORKSPACE_URI } else { "insynbio" })
)

$ErrorActionPreference = "Stop"
$token = ($env:PROTOCOLSIO_ACCESS_TOKEN or "").Trim()
if (-not $token) {
    Write-Error "Set PROTOCOLSIO_ACCESS_TOKEN in your shell first (do not commit .env to git)."
}

$key = $env:WM_SSH_KEY
if (-not $key) {
    $defaultKey = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
    if (Test-Path $defaultKey) { $key = $defaultKey }
}
$sshArgs = @("-o", "ConnectTimeout=20")
if ($key) {
    $sshArgs += @("-i", $key, "-o", "IdentitiesOnly=yes")
}

# Remote: remove old lines, append new (token never printed)
$remoteScript = @"
set -e
ENV_FILE='$RemoteEnv'
touch "`$ENV_FILE"
grep -v '^PROTOCOLSIO_ACCESS_TOKEN=' "`$ENV_FILE" | grep -v '^PROTOCOLSIO_WORKSPACE_URI=' > "`$ENV_FILE.tmp" || true
mv "`$ENV_FILE.tmp" "`$ENV_FILE"
chmod 600 "`$ENV_FILE"
"@

& ssh @sshArgs $DeployHost $remoteScript
if ($LASTEXITCODE -ne 0) { throw "SSH prep failed" }

$tmp = Join-Path $env:TEMP "protocolsio_env_$(Get-Random).txt"
@(
    "PROTOCOLSIO_ACCESS_TOKEN=$token"
    "PROTOCOLSIO_WORKSPACE_URI=$WorkspaceUri"
) | Set-Content -Path $tmp -Encoding utf8NoBOM
try {
    $scpArgs = @("-o", "ConnectTimeout=20")
    if ($key) { $scpArgs += @("-i", $key, "-o", "IdentitiesOnly=yes") }
    & scp @scpArgs $tmp "${DeployHost}:/tmp/protocolsio.env.append"
    if ($LASTEXITCODE -ne 0) { throw "scp failed" }
    & ssh @sshArgs $DeployHost "cat /tmp/protocolsio.env.append >> '$RemoteEnv' && rm -f /tmp/protocolsio.env.append"
    if ($LASTEXITCODE -ne 0) { throw "SSH append failed" }
} finally {
    Remove-Item -Force $tmp -ErrorAction SilentlyContinue
}

Write-Host "Restarting writing-memory ..."
& ssh @sshArgs $DeployHost "systemctl restart writing-memory && sleep 2 && systemctl is-active writing-memory"
if ($LASTEXITCODE -ne 0) { throw "restart failed" }

Write-Host "Checking /lab/config (token not shown) ..."
$check = Invoke-RestMethod -Uri "https://write.insynbio.com/lab/config" -TimeoutSec 20
$pio = $check.protocolsio
if ($pio.configured) {
    Write-Host "OK: protocolsio.configured=true workspace=$($pio.workspace_uri)"
} else {
    Write-Warning "protocolsio still not configured — verify .env on VPS."
}
