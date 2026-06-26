# Bootstrap eLabFTW on the same VPS as write.insynbio.com

# Run from repo root:

#   powershell -File services/writing_memory/deploy/install-elabftw-on-vps.ps1

#

# After install: open https://lab.insynbio.com (or SSH tunnel below), complete setup wizard,

# create API key in Settings, add ELABFTW_* to /srv/services/writing_memory/.env, restart writing-memory.



param(

    [string]$DeployHost = "root@157.180.91.72",

    [string]$RemoteElabDir = "/srv/elabftw",

    [string]$ServerName = "lab.insynbio.com",

    [string]$LocalPort = "4430",

    [switch]$SkipNginx,

    [switch]$SkipDockerUp

)



$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path

$DeployDir = Join-Path $RepoRoot "services\writing_memory\deploy"



$key = Join-Path $env:USERPROFILE ".ssh\id_ed25519"

if (-not (Test-Path $key)) { throw "SSH key not found: $key" }

$ssh = @("-i", $key, "-o", "IdentitiesOnly=yes", "-o", "ConnectTimeout=25")

$scp = @("-i", $key, "-o", "IdentitiesOnly=yes", "-o", "ConnectTimeout=25")



Write-Host "Checking Docker on $DeployHost ..."

& ssh @ssh $DeployHost "docker --version && docker compose version" 2>$null

if ($LASTEXITCODE -ne 0) {

    Write-Host "Docker missing — installing docker.io + docker-compose-v2 (Ubuntu) ..." -ForegroundColor Yellow

    & ssh @ssh $DeployHost "export DEBIAN_FRONTEND=noninteractive; apt-get update -qq && apt-get install -y -qq docker.io docker-compose-v2 && systemctl enable --now docker"

    if ($LASTEXITCODE -ne 0) { throw "Docker install failed" }

    & ssh @ssh $DeployHost "docker --version && docker compose version"

    if ($LASTEXITCODE -ne 0) { throw "Docker not available after install" }

}



Write-Host "Creating $RemoteElabDir and fetching official docker-compose from get.elabftw.net ..."

& ssh @ssh $DeployHost "mkdir -p '$RemoteElabDir'"

$remoteFetch = @"

set -e

cd '$RemoteElabDir'

curl -fsSL -o docker-compose.yml 'https://get.elabftw.net/?config'

sed -i 's/SERVER_NAME=localhost/SERVER_NAME=$ServerName/' docker-compose.yml

sed -i 's|443:443|127.0.0.1:${LocalPort}:443|' docker-compose.yml

"@

& ssh @ssh $DeployHost $remoteFetch

if ($LASTEXITCODE -ne 0) { throw "Failed to download or patch docker-compose.yml" }



if (-not $SkipDockerUp) {

    Write-Host "Starting eLabFTW (first run may take several minutes) ..."

    & ssh @ssh $DeployHost "cd '$RemoteElabDir' && docker compose pull && docker compose up -d"

    if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

    Write-Host "Waiting for local HTTPS (127.0.0.1:${LocalPort}) ..."

    & ssh @ssh $DeployHost "sleep 45; curl -sk -o /dev/null -w 'HTTP %{http_code}\n' https://127.0.0.1:${LocalPort}/ || true"

}



if (-not $SkipNginx) {

    Write-Host "Installing nginx site $ServerName (requires DNS + SSL cert) ..."

    & scp @scp (Join-Path $DeployDir "nginx-lab.insynbio.com.example.conf") "${DeployHost}:/etc/nginx/sites-available/lab.insynbio.com"

    $nginxOk = @"

if test -f /etc/letsencrypt/live/$ServerName/fullchain.pem; then

  ln -sf /etc/nginx/sites-available/lab.insynbio.com /etc/nginx/sites-enabled/lab.insynbio.com

  nginx -t && systemctl reload nginx

  echo NGINX_OK

else

  echo NGINX_SKIP_NO_CERT

fi

"@

    $nginxOut = & ssh @ssh $DeployHost $nginxOk

    if ($nginxOut -match "NGINX_SKIP") {

        Write-Warning "SSL cert not found. After DNS: certbot --nginx -d $ServerName"

        Write-Host "SSH tunnel until then: ssh -L ${LocalPort}:127.0.0.1:${LocalPort} $DeployHost"

        Write-Host "Then open: https://127.0.0.1:${LocalPort}/ (accept self-signed if prompted)"

    }

}



Write-Host ""

Write-Host "Next steps:" -ForegroundColor Cyan

Write-Host "  1. DNS A record: $ServerName -> VPS IP (157.180.91.72)"

Write-Host "  2. First-time wizard in browser (creates DB tables)"

Write-Host "  3. Settings -> API -> create key -> ELABFTW_* in writing_memory .env"

Write-Host "  4. systemctl restart writing-memory"

Write-Host "  5. write.insynbio.com Plan -> From eLabFTW"


