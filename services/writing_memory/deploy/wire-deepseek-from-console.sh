#!/bin/bash
# Copy DEEPSEEK_API_KEY from abenginecore-api (console) into writing_memory .env.
# Run on VPS as root: bash /srv/services/writing_memory/deploy/wire-deepseek-from-console.sh

set -euo pipefail

WM_ENV="/srv/services/writing_memory/.env"
OVERRIDE_INSYN="/etc/systemd/system/insynbio-api.service.d/deepseek.conf"
OVERRIDE_ABE="/etc/systemd/system/abenginecore-api.service.d/deepseek.conf"
API_SERVICE="${INSYNBIO_API_SERVICE:-insynbio-api}"

KEY=""
for OVERRIDE in "$OVERRIDE_INSYN" "$OVERRIDE_ABE"; do
  if [[ -f "$OVERRIDE" ]]; then
    KEY=$(grep -E 'DEEPSEEK_API_KEY=' "$OVERRIDE" | head -1 \
      | sed -E 's/.*DEEPSEEK_API_KEY=([^" ]+).*/\1/' | tr -d '"')
    [[ -n "$KEY" ]] && break
  fi
done

if [[ -z "$KEY" ]]; then
  PID=$(systemctl show -p MainPID --value "${API_SERVICE}.service" 2>/dev/null || true)
  if [[ -n "$PID" && "$PID" != "0" && -r "/proc/${PID}/environ" ]]; then
    KEY=$(tr '\0' '\n' < "/proc/${PID}/environ" | grep '^DEEPSEEK_API_KEY=' | cut -d= -f2- || true)
  fi
fi

if [[ -z "$KEY" ]]; then
  echo "ERROR: DEEPSEEK_API_KEY not found in ${OVERRIDE} or ${API_SERVICE} process" >&2
  exit 1
fi

touch "$WM_ENV"
for var in DEEPSEEK_API_KEY DEEPSEEK_BASE_URL DEEPSEEK_MODEL WM_LLM_FALLBACK WM_LLM_PROVIDER; do
  if grep -q "^${var}=" "$WM_ENV" 2>/dev/null; then
    sed -i "/^${var}=/d" "$WM_ENV"
  fi
done

{
  echo "DEEPSEEK_API_KEY=${KEY}"
  echo "DEEPSEEK_BASE_URL=https://api.deepseek.com/v1"
  echo "DEEPSEEK_MODEL=deepseek-chat"
  echo "WM_LLM_FALLBACK=deepseek"
  echo "WM_LLM_PROVIDER=anthropic"
} >> "$WM_ENV"

chmod 600 "$WM_ENV"
echo "OK: DeepSeek wired into writing_memory (.env key length ${#KEY})"
systemctl restart writing-memory.service
sleep 2
systemctl is-active writing-memory.service
curl -s http://127.0.0.1:8100/health | python3 -c "import sys,json; d=json.load(sys.stdin); print('provider',d.get('llm_provider'),'fallback',d.get('llm_fallback'),'backup',d.get('backup_model'))"
