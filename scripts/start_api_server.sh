#!/usr/bin/env bash
# Production API start — fixes conda PATH for hmmscan / ImmuneBuilder subprocesses.
#
# Usage:
#   chmod +x scripts/start_api_server.sh
#   ./scripts/start_api_server.sh
#
# systemd example (/etc/systemd/system/abenginecore-api.service):
#   [Unit]
#   Description=InSynBio AbEngineCore API
#   After=network.target
#
#   [Service]
#   Type=simple
#   User=root
#   WorkingDirectory=/root/Antibody_Engineer_Suite
#   Environment=INSYNBIO_CONDA_ENV=anarcii
#   Environment=INSYNBIO_API_PORT=8000
#   Environment=INSYNBIO_WARMUP_ABNATIV=1
#   Environment=PATH=/root/miniconda3/envs/anarcii/bin:/usr/local/bin:/usr/bin:/bin
#   # InSynBio mail (existing)
#   Environment=INSYNBIO_SMTP_HOST=...
#   Environment=INSYNBIO_SMTP_USER=contact@insynbio.com
#   Environment=INSYNBIO_SMTP_PASS=...
#   # Therasik — Namecheap Private Email (separate mailbox; do not share InSynBio creds)
#   Environment=THERASIK_SMTP_HOST=mail.privateemail.com
#   Environment=THERASIK_SMTP_PORT=465
#   Environment=THERASIK_SMTP_USER=contact@therasik.com
#   Environment=THERASIK_SMTP_PASS=...
#   Environment=THERASIK_EMAIL_SENDER=contact@therasik.com
#   # Therasik AI assistant (DeepSeek-chat only; never expose key to browser)
#   Environment=DEEPSEEK_API_KEY=sk-...
#   Environment=DEEPSEEK_API_BASE=https://api.deepseek.com/v1
#   Environment=DEEPSEEK_MODEL=deepseek-chat
#   Environment="STRIPE_SECRET_KEY=sk_live_..."
#   Environment="STRIPE_WEBHOOK_SECRET=whsec_..."
#   # Drop-in recommended: /etc/systemd/system/abenginecore-api.service.d/killmode.conf
#   #   KillMode=mixed
#   #   TimeoutStartSec=600
#   ExecStart=/root/Antibody_Engineer_Suite/scripts/start_api_server.sh
#   Restart=on-failure
#   RestartSec=5
#
#   [Install]
#   WantedBy=multi-user.target

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_NAME="${INSYNBIO_CONDA_ENV:-anarcii}"
PORT="${INSYNBIO_API_PORT:-8000}"
CONDA="${CONDA_EXE:-/root/miniconda3/bin/conda}"

if [[ ! -x "$CONDA" ]]; then
  CONDA="$(command -v conda || true)"
fi
if [[ -z "$CONDA" ]]; then
  echo "conda not found" >&2
  exit 1
fi

ENV_BIN="$("$CONDA" run -n "$ENV_NAME" python -c 'import sys; from pathlib import Path; print(Path(sys.executable).resolve().parent)')"
export PATH="${ENV_BIN}:${PATH}"
export INSYNBIO_EXTRA_PATH="${ENV_BIN}"

cd "$REPO_ROOT"

if [[ "${INSYNBIO_WARMUP_ABNATIV:-1}" == "1" ]]; then
  echo "[start] AbNatiV warm-up (may take ~2–3 min on cold boot)…"
  "$CONDA" run -n "$ENV_NAME" python scripts/warmup_abnativ.py || {
    echo "[start] WARN: AbNatiV warm-up failed — check hmmscan on PATH" >&2
  }
fi

if [[ "${INSYNBIO_FREE_PORT_ON_START:-1}" == "1" ]]; then
  # shellcheck source=scripts/lib/free_port_8000.sh
  source "${REPO_ROOT}/scripts/lib/free_port_8000.sh"
  free_port_for_abenginecore "$PORT" || {
    echo "[start] ERROR: port ${PORT} busy — run: sudo bash scripts/fix_api_port_ghost.sh" >&2
    exit 1
  }
fi

echo "[start] uvicorn on 0.0.0.0:${PORT} (env=${ENV_NAME}, repo=${REPO_ROOT})"
exec "$CONDA" run -n "$ENV_NAME" uvicorn api.main:app --host 0.0.0.0 --port "$PORT"
