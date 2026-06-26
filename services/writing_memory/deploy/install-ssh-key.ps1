# One-time: install local ed25519 public key on the VPS (password prompt once).
# Run: powershell -File services/writing_memory/deploy/install-ssh-key.ps1

param(
    [string]$DeployHost = $(if ($env:WM_DEPLOY_HOST) { $env:WM_DEPLOY_HOST } else { "root@157.180.91.72" }),
    [switch]$AppendOnly
)

$key = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
$pub = "$key.pub"
if (-not (Test-Path $pub)) {
    Write-Error "Missing $pub — run: ssh-keygen -t ed25519 -f `"$key`" -N '""'"
}

$sshPw = @(
    "-o", "PreferredAuthentications=password",
    "-o", "PubkeyAuthentication=no",
    "-o", "ConnectTimeout=30"
)

$tmpRemote = "/tmp/insynbio_wm_key.pub"
Write-Host "Uploading public key to $DeployHost (enter root password when prompted) ..."
& scp @sshPw $pub "${DeployHost}:${tmpRemote}"
if ($LASTEXITCODE -ne 0) { throw "scp public key failed" }

# Replace broken authorized_keys (CRLF / bad echo lines). Use -AppendOnly to only append.
if ($AppendOnly) {
    $remoteCmd = "mkdir -p ~/.ssh && chmod 700 ~/.ssh && tr -d '\r' < $tmpRemote >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && rm -f $tmpRemote && wc -l ~/.ssh/authorized_keys"
} else {
    $remoteCmd = "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cp -a ~/.ssh/authorized_keys ~/.ssh/authorized_keys.bak 2>/dev/null || true && tr -d '\r' < $tmpRemote > ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && rm -f $tmpRemote && wc -l ~/.ssh/authorized_keys"
}

Write-Host "Installing into ~/.ssh/authorized_keys ..."
& ssh @sshPw $DeployHost $remoteCmd
if ($LASTEXITCODE -ne 0) { throw "ssh authorized_keys install failed" }

Write-Host "Testing key login ..."
& ssh -i $key -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=15 $DeployHost "echo key_ok"
if ($LASTEXITCODE -ne 0) {
    throw "Key login still failed. On VPS: chmod 700 ~/.ssh; chmod 600 ~/.ssh/authorized_keys; ensure PubkeyAuthentication yes in sshd_config."
}
Write-Host "OK. Run: powershell -File services/writing_memory/deploy/sync-to-vps.ps1"
