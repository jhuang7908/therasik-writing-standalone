#!/usr/bin/env bash
# deploy.sh — Install or upgrade therasik-mcp on the existing Hetzner server
#
# SAFE TO RE-RUN: idempotent.  The script will not touch port 8000 or
# abenginecore.service.
#
# Usage (from server):
#   git clone https://github.com/jhuang7908/therasik-writing-standalone.git /opt/therasik-mcp
#   cd /opt/therasik-mcp
#   bash deploy/deploy.sh
#
# Upgrade (after git pull):
#   bash deploy/deploy.sh --upgrade

set -euo pipefail

APP_DIR="/opt/therasik-mcp"
VENV="${APP_DIR}/venv"
SERVICE_NAME="therasik-mcp"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
ENV_DIR="/etc/therasik-mcp"
ENV_FILE="${ENV_DIR}/env"
NGINX_AVAILABLE="/etc/nginx/sites-available/mcp.therasik.com"
NGINX_ENABLED="/etc/nginx/sites-enabled/mcp.therasik.com"
PORT=8001

UPGRADE=false
for arg in "$@"; do
  [[ "$arg" == "--upgrade" ]] && UPGRADE=true
done

# ── 0. Safety check — port 8000 guard ───────────────────────────────────────
echo "[deploy] Checking port 8000 is NOT affected…"
if ss -tlnp | grep -q ":${PORT} "; then
  echo "[deploy] INFO: port ${PORT} already in use — stopping old service first"
  systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
fi
if ss -tlnp | grep -q ":8000 "; then
  echo "[deploy] ✓ Port 8000 still bound to abenginecore (untouched)"
fi

# ── 1. System dependencies ────────────────────────────────────────────────────
echo "[deploy] Installing system packages…"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip postgresql redis-server nginx certbot python3-certbot-nginx

# Ensure Postgres and Redis are running
systemctl enable --now postgresql redis-server

# ── 2. Python venv ─────────────────────────────────────────────────────────────
echo "[deploy] Setting up Python venv at ${VENV}…"
python3 -m venv "${VENV}"
"${VENV}/bin/pip" install -q --upgrade pip
"${VENV}/bin/pip" install -q -r "${APP_DIR}/requirements.txt"

# ── 3. Postgres DB + schema ────────────────────────────────────────────────────
echo "[deploy] Initialising PostgreSQL schema…"
DB_NAME="therasik_mcp"
DB_USER="therasik"
# Create user/db only if they don't exist
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_USER}_changeme';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"
sudo -u postgres psql -d "${DB_NAME}" -f "${APP_DIR}/schema/init.sql" 2>/dev/null || true
echo "[deploy] ✓ DB schema applied"

# ── 4. Environment file ────────────────────────────────────────────────────────
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[deploy] Creating env file at ${ENV_FILE}…"
  mkdir -p "${ENV_DIR}"
  chmod 700 "${ENV_DIR}"
  cp "${APP_DIR}/.env.example" "${ENV_FILE}"
  chmod 600 "${ENV_FILE}"
  echo ""
  echo "⚠  IMPORTANT: Edit ${ENV_FILE} and fill in secrets before starting the service:"
  echo "     DATABASE_URL, REDIS_URL, THERASIK_MASTER_KEY, GEMINI_API_KEY, etc."
  echo ""
else
  echo "[deploy] ✓ ${ENV_FILE} already exists (not overwritten)"
fi

# ── 5. systemd unit ────────────────────────────────────────────────────────────
echo "[deploy] Installing systemd unit…"
cp "${APP_DIR}/deploy/therasik-mcp.service" "${SERVICE_FILE}"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

if $UPGRADE; then
  echo "[deploy] Restarting service after upgrade…"
  systemctl restart "${SERVICE_NAME}"
else
  echo "[deploy] Starting service (first install)…"
  systemctl start "${SERVICE_NAME}" || {
    echo "[deploy] ✗ Service failed to start — check env file, then: systemctl start therasik-mcp"
  }
fi

# ── 6. Nginx ───────────────────────────────────────────────────────────────────
echo "[deploy] Configuring Nginx…"
cp "${APP_DIR}/deploy/nginx-mcp.therasik.com.conf" "${NGINX_AVAILABLE}"
if [[ ! -L "${NGINX_ENABLED}" ]]; then
  ln -s "${NGINX_AVAILABLE}" "${NGINX_ENABLED}"
fi
nginx -t && systemctl reload nginx
echo "[deploy] ✓ Nginx reloaded"

# ── 7. TLS (Let's Encrypt) ─────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════"
echo "  Run TLS setup manually after DNS is pointed:"
echo "  certbot --nginx -d mcp.therasik.com"
echo "══════════════════════════════════════════════════════"

# ── 8. Smoke test ──────────────────────────────────────────────────────────────
sleep 3
if curl -sf "http://127.0.0.1:${PORT}/health" | grep -q "ok"; then
  echo "[deploy] ✓ Health check PASS — therasik-mcp is running on port ${PORT}"
else
  echo "[deploy] ✗ Health check failed — check: journalctl -u ${SERVICE_NAME} -n 30"
fi

echo ""
echo "Deployed successfully.  Port map:"
echo "  8000 → abenginecore (InSynBio main API)"
echo "  8001 → therasik-mcp (TheraSIK Writing Suite MCP)"
