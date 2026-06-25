#!/usr/bin/env bash
# AbEngineCore — 一键 SaaS 部署脚本
# 运行：bash deploy-saas.sh your-domain.com [ghcr_owner]
#
# 前置条件：
#   - 新装 Ubuntu/Debian VPS（root 或 sudo 权限）
#   - 域名已指向此 VPS IP（A 记录或 CNAME）
#   - GitHub Container Registry 访问 Token（可选，若镜像私有）

set -e

DOMAIN="${1:-your-domain.com}"
GHCR_OWNER="${2:-jhuang7908}"
IMAGE="ghcr.io/${GHCR_OWNER}/abenginecore:latest"
DATA_ROOT="/opt/abenginecore"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PIN="${ADMIN_PIN:-123456}"  # 改成你的
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

echo "═══════════════════════════════════════════════════════════════"
echo "  AbEngineCore SaaS Deployment"
echo "  Domain: $DOMAIN"
echo "  Image:  $IMAGE"
echo "═══════════════════════════════════════════════════════════════"

# ── Step 1: System updates ─────────────────────────────────────────
echo ""
echo "[1/6] Updating system packages..."
apt-get update
apt-get upgrade -y
apt-get install -y curl wget git

# ── Step 2: Install Docker & Docker Compose ────────────────────────
echo ""
echo "[2/6] Installing Docker & Docker Compose..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    bash get-docker.sh
    rm get-docker.sh
fi
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi
docker --version
docker-compose --version

# ── Step 3: GitHub Container Registry login (if private) ───────────
echo ""
echo "[3/6] Logging into GHCR..."
if [ -n "$GITHUB_TOKEN" ]; then
    echo "$GITHUB_TOKEN" | docker login ghcr.io -u "${GHCR_OWNER}" --password-stdin
    echo "✓ GHCR login successful"
else
    echo "⚠ No GITHUB_TOKEN set. Public images only."
fi

# ── Step 4: Setup data directories ─────────────────────────────────
echo ""
echo "[4/6] Setting up data directories..."
mkdir -p "$DATA_ROOT"/{jobs,auth,caddy}
chmod 755 "$DATA_ROOT"

cat > "$DATA_ROOT/docker-compose.yml" << 'COMPOSE_EOF'
version: "3.9"
services:
  # Caddy reverse proxy + HTTPS
  caddy:
    image: caddy:latest
    container_name: caddy-abenginecore
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - ./caddy_data:/data
      - ./caddy_config:/config
    restart: unless-stopped
    depends_on:
      - abenginecore

  # AbEngineCore API
  abenginecore:
    image: ${IMAGE:-ghcr.io/jhuang7908/abenginecore:latest}
    container_name: abenginecore-api
    pull_policy: always
    environment:
      INSYNBIO_PUBLIC_SITE: "InSynBio"
      INSYNBIO_PUBLIC_LOCALE: "en"
      INSYNBIO_TRIAL_CREDITS: "500"
      INSYNBIO_OWNER_UNLIMITED: "1"
    volumes:
      - ./jobs:/app/.job_storage
      - ./auth:/app/api/.data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 40s
    networks:
      - web

networks:
  web:
    driver: bridge

volumes:
  caddy_data:
  caddy_config:
COMPOSE_EOF

# ── Step 5: Create Caddy config (auto HTTPS) ───────────────────────
echo ""
echo "[5/6] Configuring Caddy (reverse proxy + TLS)..."
cat > "$DATA_ROOT/Caddyfile" << CADDY_EOF
$DOMAIN {
    reverse_proxy abenginecore:8000 {
        header_up X-Forwarded-For {http.request.remote.host}
        header_up X-Forwarded-Proto {http.request.proto}
    }
    encode gzip
}
CADDY_EOF

echo "✓ Caddy config created at $DATA_ROOT/Caddyfile"

# ── Step 6: Start services ──────────────────────────────────────────
echo ""
echo "[6/6] Starting services..."
cd "$DATA_ROOT"
export IMAGE
docker-compose pull abenginecore
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready (30s)..."
sleep 30

# ── Check health ───────────────────────────────────────────────────
if docker-compose ps | grep -q "healthy"; then
    echo "✓ Services are healthy"
else
    echo "⚠ Checking service status..."
    docker-compose ps
fi

# ── Initialize admin account (SQLite) ──────────────────────────────
echo ""
echo "Initializing admin account..."
docker-compose exec -T abenginecore python << PYTHON_INIT
import sys, os, sqlite3, hashlib, secrets
from pathlib import Path

db_path = Path('/app/api/.data/insynbio_auth.db')
db_path.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(str(db_path))
conn.executescript("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
    pin_salt BLOB NOT NULL,
    pin_hash TEXT NOT NULL,
    credits INTEGER NOT NULL DEFAULT 0,
    role TEXT NOT NULL DEFAULT 'trial',
    created_at TEXT NOT NULL,
    credits_unlimited INTEGER NOT NULL DEFAULT 0
);
""")

# Remove existing admin if present
conn.execute("DELETE FROM users WHERE username = ?", ("$ADMIN_USER",))

# Create new admin
import datetime
salt = secrets.token_bytes(16)
pin_str = "$ADMIN_PIN"
pin_hash = hashlib.sha256(salt + pin_str.encode()).hexdigest()
conn.execute(
    "INSERT INTO users (username, pin_salt, pin_hash, role, credits_unlimited, created_at) VALUES (?, ?, ?, ?, ?, ?)",
    ("$ADMIN_USER", salt, pin_hash, "admin", 1, datetime.datetime.utcnow().isoformat())
)
conn.commit()
conn.close()
print("✓ Admin account created: $ADMIN_USER / $ADMIN_PIN")
PYTHON_INIT

# ── Summary ────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✓ Deployment Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  URL:        https://$DOMAIN"
echo "  Admin:      $ADMIN_USER / $ADMIN_PIN"
echo "  Data dir:   $DATA_ROOT"
echo "  Logs:       docker-compose -f $DATA_ROOT/docker-compose.yml logs -f"
echo ""
echo "  Next steps:"
echo "  1. Test: open browser to https://$DOMAIN"
echo "  2. Change admin PIN in $DATA_ROOT/.env (re-run init on update)"
echo "  3. Monitor: cd $DATA_ROOT && docker-compose ps"
echo ""
echo "═══════════════════════════════════════════════════════════════"
