# Install Quarto on the VPS (Ubuntu/Debian) and verify.
#
# Usage:
#   powershell -File services/writing_memory/deploy/install-quarto-on-vps.ps1

param(
    [string]$DeployHost = $(if ($env:WM_DEPLOY_HOST) { $env:WM_DEPLOY_HOST } else { "root@157.180.91.72" }),
    [string]$SshKey    = $env:WM_SSH_KEY,
    # Quarto version — set to "latest" to always fetch newest
    [string]$QuartoVer = "1.5.57"
)

$defaultKey = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
if (-not $SshKey -and (Test-Path $defaultKey)) { $SshKey = $defaultKey }
if (-not $SshKey) { Write-Error "No SSH key. Set WM_SSH_KEY." }

$sshArgs = @(
    "-o", "ConnectTimeout=20",
    "-o", "PreferredAuthentications=publickey",
    "-o", "PasswordAuthentication=no",
    "-i", $SshKey, "-o", "IdentitiesOnly=yes"
)

Write-Host "Testing SSH …"
& ssh @sshArgs $DeployHost "echo ok"
if ($LASTEXITCODE -ne 0) { Write-Error "SSH failed" }

$ver = $QuartoVer
Write-Host "Installing Quarto $ver on $DeployHost …"
& ssh @sshArgs $DeployHost "bash -lc `"set -e; ARCH=\$(dpkg --print-architecture 2>/dev/null || uname -m); if [ \`"\`$ARCH\`" = 'x86_64' ] || [ \`"\`$ARCH\`" = 'amd64' ]; then PKG=quarto-${ver}-linux-amd64.deb; else PKG=quarto-${ver}-linux-arm64.deb; fi; URL=https://github.com/quarto-dev/quarto-cli/releases/download/v${ver}/\`$PKG; cd /tmp; wget -q \`"\`$URL\`" -O \`"\`$PKG\`" || curl -fsSL \`"\`$URL\`" -o \`"\`$PKG\`"; dpkg -i \`"\`$PKG\`"; rm -f \`"\`$PKG\`"; quarto --version; echo Quarto_install_DONE\`""
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Quarto install returned non-zero — checking if already installed"
    & ssh @sshArgs $DeployHost "quarto --version"
    if ($LASTEXITCODE -ne 0) { Write-Error "Quarto not available after install attempt" }
}

Write-Host ""
Write-Host "Verifying DOCX render …"
& ssh @sshArgs $DeployHost "bash -lc `"cd /tmp && printf -- '---\ntitle: Test\nformat: docx\n---\nHello **world**.\n' > tq.qmd && quarto render tq.qmd --to docx --quiet && ls -lh tq.docx && echo DOCX_OK; rm -f tq.qmd tq.docx\`""
if ($LASTEXITCODE -ne 0) {
    Write-Warning "DOCX render test failed"
} else {
    Write-Host "DOCX render verified."
}

Write-Host "Done. Quarto $QuartoVer installed on $DeployHost"
