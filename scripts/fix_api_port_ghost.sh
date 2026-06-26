#!/usr/bin/env bash
# fix_api_port_ghost.sh — stop dual-service port fights on MVP console servers.
#
# Symptom: journal shows "address already in use" on 8000; health works but Stripe
# returns "not configured" because an orphaned uvicorn (PPID=1, --host 127.0.0.1)
# from legacy abenginecore.service is still serving traffic.
#
# Usage (on insynbio-console-mvp):
#   cd ~/Antibody-Engineer-Suite-MVP
#   git pull origin master
#   sudo bash scripts/fix_api_port_ghost.sh
#
set -euo pipefail

API_SERVICE="${INSYNBIO_API_SERVICE:-abenginecore-api}"
LEGACY_SERVICE="${INSYNBIO_LEGACY_SERVICE:-abenginecore}"
PORT="${INSYNBIO_API_PORT:-8000}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIB="${REPO_ROOT}/scripts/lib/free_port_8000.sh"

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi
if [[ ! -f "$LIB" ]]; then
  echo "Missing $LIB — git pull and retry." >&2
  exit 1
fi
# shellcheck source=scripts/lib/free_port_8000.sh
source "$LIB"

echo "==============================================================="
echo " AbEngineCore port-8000 ghost repair"
echo " canonical service: ${API_SERVICE}"
echo " legacy service:    ${LEGACY_SERVICE} (will disable)"
echo "==============================================================="
echo

echo "[1/7] Stopping both API units..."
systemctl stop "$API_SERVICE" 2>/dev/null || true
systemctl stop "$LEGACY_SERVICE" 2>/dev/null || true
sleep 2

echo "[2/7] Disabling legacy unit (prevents re-spawn)..."
systemctl disable "$LEGACY_SERVICE" 2>/dev/null || echo "   (no ${LEGACY_SERVICE} unit — OK)"
systemctl enable "$API_SERVICE" 2>/dev/null || {
  echo "ERROR: ${API_SERVICE} unit not found. Install systemd unit first." >&2
  exit 1
}

echo "[3/7] Ensuring KillMode=mixed on ${API_SERVICE}..."
mkdir -p "/etc/systemd/system/${API_SERVICE}.service.d"
cat > "/etc/systemd/system/${API_SERVICE}.service.d/killmode.conf" << 'EOF'
[Service]
KillMode=mixed
TimeoutStartSec=600
EOF

echo "[4/7] Killing orphaned uvicorn listeners on port ${PORT}..."
pkill -f 'uvicorn api.main:app' 2>/dev/null || true
free_port_for_abenginecore "$PORT"

echo "[5/7] Starting ${API_SERVICE}..."
systemctl daemon-reload
systemctl start "$API_SERVICE"

echo "[6/7] Waiting for /api/health (up to 6 min)..."
for i in $(seq 1 36); do
  if curl -sf "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    echo "   API up after ${i}0s"
    break
  fi
  if [[ "$i" -eq 36 ]]; then
    echo "ERROR: health check timed out" >&2
    journalctl -u "$API_SERVICE" -n 40 --no-pager >&2 || true
    exit 1
  fi
  echo "   waiting ${i}/36..."
  sleep 10
done

echo "[7/7] Verifying listener + Stripe env..."
ss -tlnp | grep ":${PORT} " || true
UVPID=$(ss -tlnp 2>/dev/null | grep ":${PORT} " | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1)
if [[ -z "$UVPID" ]]; then
  echo "ERROR: no listener on port ${PORT}" >&2
  exit 1
fi
ps -fp "$UVPID" || true
if tr '\0' '\n' < "/proc/${UVPID}/environ" | grep -q '^STRIPE_SECRET_KEY=.'; then
  echo "   STRIPE_SECRET_KEY: present in listener environ"
else
  echo "WARN: STRIPE_SECRET_KEY missing from listener PID=${UVPID}" >&2
  echo "      Add to /etc/systemd/system/${API_SERVICE}.service then rerun." >&2
fi

HEALTH=$(curl -sf "http://127.0.0.1:${PORT}/api/health" || true)
echo "$HEALTH" | python3 -m json.tool 2>/dev/null | grep -E 'git_sha|stripe_configured|pricing_version' || echo "$HEALTH"

if journalctl -u "$API_SERVICE" -n 30 --no-pager | grep -q 'address already in use'; then
  echo "ERROR: bind conflict still in journal — inspect:" >&2
  echo "  journalctl -u ${API_SERVICE} -n 50 --no-pager" >&2
  exit 1
fi

echo
echo "==============================================================="
echo " DONE — retry Top up in browser (Ctrl+Shift+R)"
echo " Legacy ${LEGACY_SERVICE} is disabled; only ${API_SERVICE} owns :${PORT}"
echo "==============================================================="
