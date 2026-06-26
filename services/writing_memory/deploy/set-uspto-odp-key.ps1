# Set USPTO_ODP_API_KEY on VPS without committing secrets to git.
#
#   $env:USPTO_ODP_API_KEY = "paste-key-from-data.uspto.gov"
#   powershell -File services/writing_memory/deploy/set-uspto-odp-key.ps1

param(
    [string]$DeployHost = $(if ($env:WM_DEPLOY_HOST) { $env:WM_DEPLOY_HOST } else { "root@157.180.91.72" }),
    [string]$RemoteEnv = "/srv/services/writing_memory/.env"
)

$ErrorActionPreference = "Stop"
$keyVal = ($env:USPTO_ODP_API_KEY or "").Trim()
if (-not $keyVal) {
    Write-Error "Set USPTO_ODP_API_KEY in your shell first. See deploy/USPTO_ODP_API_KEY.md"
}

$sshKey = $env:WM_SSH_KEY
if (-not $sshKey) {
    $defaultKey = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
    if (Test-Path $defaultKey) { $sshKey = $defaultKey }
}
$sshArgs = @("-o", "ConnectTimeout=20")
$scpArgs = @("-o", "ConnectTimeout=20")
if ($sshKey) {
    $sshArgs += @("-i", $sshKey, "-o", "IdentitiesOnly=yes")
    $scpArgs += @("-i", $sshKey, "-o", "IdentitiesOnly=yes")
}

$remoteScript = @"
set -e
ENV_FILE='$RemoteEnv'
touch "`$ENV_FILE"
grep -v '^USPTO_ODP_API_KEY=' "`$ENV_FILE" > "`$ENV_FILE.tmp" || true
mv "`$ENV_FILE.tmp" "`$ENV_FILE"
chmod 600 "`$ENV_FILE"
"@
& ssh @sshArgs $DeployHost $remoteScript
if ($LASTEXITCODE -ne 0) { throw "SSH prep failed" }

$tmp = Join-Path $env:TEMP "uspto_odp_env_$(Get-Random).txt"
"USPTO_ODP_API_KEY=$keyVal" | Set-Content -Path $tmp -Encoding utf8NoBOM
try {
    & scp @scpArgs $tmp "${DeployHost}:/tmp/uspto_odp.env.append"
    if ($LASTEXITCODE -ne 0) { throw "scp failed" }
    & ssh @sshArgs $DeployHost "cat /tmp/uspto_odp.env.append >> '$RemoteEnv' && rm -f /tmp/uspto_odp.env.append"
    if ($LASTEXITCODE -ne 0) { throw "SSH append failed" }
} finally {
    Remove-Item -Force $tmp -ErrorAction SilentlyContinue
}

Write-Host "Restarting writing-memory ..."
& ssh @sshArgs $DeployHost "systemctl restart writing-memory && sleep 2 && systemctl is-active writing-memory"
if ($LASTEXITCODE -ne 0) { throw "restart failed" }

$cfg = Invoke-RestMethod -Uri "https://write.insynbio.com/ip/config" -TimeoutSec 25
if ($cfg.odp_configured) {
    Write-Host "OK: odp_configured=true source=$($cfg.source)"
} else {
    Write-Warning "Key written but odp_configured=false — check .env on VPS."
}
