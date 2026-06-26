#!/bin/bash
# fix_deepseek_env.sh
#
# Diagnose and restore the assistant API key for the abenginecore service.
# Run on the server with sudo when the assistant returns:
#     "Therasik assistant is temporarily unavailable; credits refunded"
#
# Usage:
#     sudo bash scripts/fix_deepseek_env.sh --key sk-xxxxxxxxxxxx
#     sudo bash scripts/fix_deepseek_env.sh
#
# The override file is the persistent source of truth:
#     /etc/systemd/system/abenginecore-api.service.d/deepseek.conf
#
# Legacy abenginecore.service must be disabled — use scripts/fix_api_port_ghost.sh.

set -euo pipefail

SERVICE_NAME="${INSYNBIO_API_SERVICE:-abenginecore-api}"
OVERRIDE_DIR="/etc/systemd/system/${SERVICE_NAME}.service.d"
OVERRIDE_FILE="${OVERRIDE_DIR}/deepseek.conf"

KEY=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --key)
            KEY="$2"
            shift 2
            ;;
        --help|-h)
            grep '^#' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "Unknown arg: $1" >&2
            exit 2
            ;;
    esac
done

if [[ $EUID -ne 0 ]]; then
    echo "This script needs root (sudo bash $0)" >&2
    exit 1
fi

echo "==============================================================="
echo " Therasik assistant env diagnostic & repair"
echo "==============================================================="
echo

echo "[1/6] Checking systemd override file..."
if [[ -f "$OVERRIDE_FILE" ]]; then
    echo "   FOUND: $OVERRIDE_FILE"
    if grep -q "DEEPSEEK_API_KEY=" "$OVERRIDE_FILE"; then
        EXISTING=$(grep -E '^Environment="DEEPSEEK_API_KEY=' "$OVERRIDE_FILE" | head -1 | sed 's/.*=\(.*\)"$/\1/')
        if [[ -n "$EXISTING" ]]; then
            MASK="${EXISTING:0:6}...${EXISTING: -4}"
            echo "   Existing key: $MASK"
            if [[ -z "$KEY" ]]; then KEY="$EXISTING"; fi
        else
            echo "   WARN: override file has DEEPSEEK_API_KEY line but value is empty"
        fi
    else
        echo "   WARN: override file does NOT contain DEEPSEEK_API_KEY line"
    fi
else
    echo "   MISSING: $OVERRIDE_FILE"
fi
echo

echo "[2/6] Checking running service environment..."
PID=$(systemctl show -p MainPID "$SERVICE_NAME" 2>/dev/null | cut -d= -f2 || echo 0)
if [[ "$PID" =~ ^[0-9]+$ ]] && [[ "$PID" -gt 0 ]] && [[ -r "/proc/$PID/environ" ]]; then
    LIVE_KEY=$(tr '\0' '\n' < "/proc/$PID/environ" | grep -E '^DEEPSEEK_API_KEY=' | head -1 | cut -d= -f2- || true)
    if [[ -n "$LIVE_KEY" ]]; then
        MASK="${LIVE_KEY:0:6}...${LIVE_KEY: -4}"
        echo "   Running PID=$PID has key: $MASK"
    else
        echo "   Running PID=$PID does NOT have DEEPSEEK_API_KEY in environ"
    fi
else
    echo "   Could not read /proc/$PID/environ (PID=$PID)"
fi
echo

if [[ -z "$KEY" ]]; then
    echo "[3/6] No key supplied and none found in override file."
    echo "      Re-run with: sudo bash $0 --key sk-xxxxxxxx"
    exit 1
else
    echo "[3/6] Using key: ${KEY:0:6}...${KEY: -4}"
fi
echo

echo "[4/6] Writing systemd override..."
mkdir -p "$OVERRIDE_DIR"
cat > "$OVERRIDE_FILE" <<EOF
[Service]
Environment="DEEPSEEK_API_KEY=$KEY"
# KillMode=mixed ensures uvicorn child processes are killed on restart,
# preventing ghost processes from holding port 8000.
KillMode=mixed
EOF
chmod 600 "$OVERRIDE_FILE"
chown root:root "$OVERRIDE_FILE"
echo "   $OVERRIDE_FILE written (mode 600)"
echo

echo "[5/6] Clearing stale port-8000 processes safely..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
sleep 2

PORT_PIDS=""
if command -v lsof >/dev/null 2>&1; then
    PORT_PIDS=$(lsof -t -iTCP:8000 -sTCP:LISTEN 2>/dev/null || true)
fi
if [[ -z "$PORT_PIDS" ]] && command -v fuser >/dev/null 2>&1; then
    PORT_PIDS=$(fuser 8000/tcp 2>/dev/null || true)
fi
if [[ -z "$PORT_PIDS" ]]; then
    PORT_PIDS=$(ss -tlnp 2>/dev/null | awk '/:8000 /{match($0,/pid=([0-9]+)/,a); if(a[1]) print a[1]}' || true)
fi

for GHOST_PID in $PORT_PIDS; do
    if [[ "$GHOST_PID" =~ ^[0-9]+$ ]]; then
        CMD=$(ps -p "$GHOST_PID" -o args= 2>/dev/null || true)
        if echo "$CMD" | grep -Eq 'uvicorn|api\.main|Antibody-Engineer-Suite|Antibody_Engineer_Suite'; then
            echo "   Killing ghost process on port 8000 (PID=$GHOST_PID): $CMD"
            kill -TERM "$GHOST_PID" 2>/dev/null || true
            sleep 1
            kill -KILL "$GHOST_PID" 2>/dev/null || true
        else
            echo "   WARN: Port 8000 is held by an unknown process; not killing automatically:"
            echo "         PID=$GHOST_PID CMD=$CMD"
            echo "         Stop it manually, then rerun this script."
            exit 1
        fi
    fi
done

systemctl daemon-reload
systemctl restart "$SERVICE_NAME"
sleep 3
echo "   systemctl daemon-reload + restart $SERVICE_NAME done"
echo

echo "[6/6] Verifying key is loaded in new process..."
NEW_PID=$(systemctl show -p MainPID "$SERVICE_NAME" 2>/dev/null | cut -d= -f2 || echo 0)
if [[ "$NEW_PID" =~ ^[0-9]+$ ]] && [[ "$NEW_PID" -gt 0 ]] && [[ -r "/proc/$NEW_PID/environ" ]]; then
    NEW_KEY=$(tr '\0' '\n' < "/proc/$NEW_PID/environ" | grep -E '^DEEPSEEK_API_KEY=' | head -1 | cut -d= -f2- || true)
    if [[ -n "$NEW_KEY" ]]; then
        MASK="${NEW_KEY:0:6}...${NEW_KEY: -4}"
        echo "   NEW PID=$NEW_PID has key: $MASK"
        echo
        echo "==============================================================="
        echo " DONE - try the assistant again in the browser (Ctrl+Shift+R)"
        echo "==============================================================="
        exit 0
    else
        echo "   NEW PID=$NEW_PID still missing the key"
    fi
else
    echo "   Could not read environ for new PID=$NEW_PID"
fi
echo
echo "Troubleshooting:"
echo "  systemctl status $SERVICE_NAME"
echo "  journalctl -u $SERVICE_NAME -n 50 --no-pager"
exit 1
