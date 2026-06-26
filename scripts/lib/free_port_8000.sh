#!/usr/bin/env bash
# Shared helper: free TCP port 8000 from orphaned AbEngineCore uvicorn listeners.
# Sourced by start_api_server.sh and fix_api_port_ghost.sh.

free_port_for_abenginecore() {
  local port="${1:-8000}"
  local pids=""

  if command -v ss >/dev/null 2>&1; then
    pids=$(ss -tlnp 2>/dev/null | grep ":${port} " | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | sort -u)
  fi
  if [[ -z "$pids" ]] && command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -t -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null | sort -u || true)
  fi

  if [[ -z "$pids" ]]; then
    echo "[port] ${port} is free"
    return 0
  fi

  for ghost_pid in $pids; do
    [[ "$ghost_pid" =~ ^[0-9]+$ ]] || continue
    local cmd
    cmd=$(ps -p "$ghost_pid" -o args= 2>/dev/null || true)
    if echo "$cmd" | grep -Eq 'uvicorn|api\.main|Antibody-Engineer-Suite|Antibody_Engineer_Suite'; then
      echo "[port] killing stale listener PID=${ghost_pid}: ${cmd}"
      kill -TERM "$ghost_pid" 2>/dev/null || true
      sleep 1
      kill -KILL "$ghost_pid" 2>/dev/null || true
    else
      echo "[port] ERROR: port ${port} held by non-API process PID=${ghost_pid}: ${cmd}" >&2
      return 1
    fi
  done

  sleep 1
  if ss -tlnp 2>/dev/null | grep -q ":${port} "; then
    echo "[port] ERROR: port ${port} still in use after cleanup" >&2
    ss -tlnp 2>/dev/null | grep ":${port} " >&2 || true
    return 1
  fi

  echo "[port] ${port} is free"
  return 0
}
