#!/usr/bin/env bash
# diag_port8000_respawn.sh — locate what keeps respawning uvicorn on :8000.
#
# Symptom: fix_api_port_ghost.sh kills the listener but a new orphaned
# python -m uvicorn --host 127.0.0.1 --port 8000 (PPID=1) appears seconds later.
#
# Usage: sudo bash scripts/diag_port8000_respawn.sh

set -u
PORT="${INSYNBIO_API_PORT:-8000}"

echo "==============================================================="
echo " AbEngineCore :${PORT} respawn diagnostic"
echo " run as root to inspect /proc/*/environ and systemd state"
echo "==============================================================="
echo

echo "[1] Current listener on :${PORT}"
ss -tlnp 2>/dev/null | grep ":${PORT} " || echo "  (nothing listening)"
echo

GHOST=$(ss -tlnp 2>/dev/null | grep ":${PORT} " | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1)
if [[ -n "$GHOST" ]]; then
  echo "[2] Listener PID=$GHOST"
  ps -fp "$GHOST" 2>/dev/null || true
  echo
  echo "  /proc/$GHOST/status (PPid/Tgid):"
  grep -E '^(Name|Pid|PPid|Tgid|Uid):' "/proc/$GHOST/status" 2>/dev/null || true
  echo
  echo "  /proc/$GHOST/cgroup (which systemd unit owns it):"
  cat "/proc/$GHOST/cgroup" 2>/dev/null || true
  echo
  echo "  Has STRIPE_SECRET_KEY?"
  tr '\0' '\n' < "/proc/$GHOST/environ" 2>/dev/null | grep -E '^STRIPE_' || echo "  (none)"
  echo
fi

echo "[3] All uvicorn / api.main processes"
ps -ef | grep -E 'uvicorn|api\.main' | grep -v grep || echo "  (none)"
echo

echo "[4] All abengine* systemd units (any state)"
systemctl list-units --type=service --all --no-pager 2>/dev/null | grep -iE 'abengine|uvicorn' || echo "  (none)"
echo
echo "  Unit files installed:"
ls -la /etc/systemd/system/ 2>/dev/null | grep -iE 'abengine|uvicorn' || true
ls -la /etc/systemd/system/multi-user.target.wants/ 2>/dev/null | grep -iE 'abengine|uvicorn' || true
echo

echo "[5] Drop-in overrides"
for d in /etc/systemd/system/abenginecore.service.d /etc/systemd/system/abenginecore-api.service.d; do
  if [[ -d "$d" ]]; then
    echo "  $d:"
    ls -la "$d"
    for f in "$d"/*.conf; do
      [[ -f "$f" ]] || continue
      echo "  --- $f ---"
      sed 's/\(KEY=\)[A-Za-z0-9_]*/\1***/g; s/\(secret=\)[A-Za-z0-9_]*/\1***/g' "$f"
    done
    echo
  fi
done

echo "[6] cron jobs that might respawn uvicorn"
for f in /etc/crontab /etc/cron.d/* /var/spool/cron/crontabs/* /etc/cron.hourly/* /etc/cron.daily/*; do
  [[ -f "$f" ]] || continue
  if grep -lE 'uvicorn|api\.main|8000' "$f" 2>/dev/null; then
    echo "  --- $f ---"
    grep -nE 'uvicorn|api\.main|8000' "$f" 2>/dev/null || true
  fi
done
crontab -l 2>/dev/null | grep -E 'uvicorn|api\.main|8000' && echo "  (above is root crontab)" || true
echo

echo "[7] supervisor / pm2 / docker"
command -v supervisorctl >/dev/null && supervisorctl status 2>/dev/null | grep -iE 'uvicorn|api|abengine' || true
command -v pm2 >/dev/null && pm2 list 2>/dev/null | grep -iE 'uvicorn|api' || true
command -v docker >/dev/null && docker ps 2>/dev/null | grep -iE 'abengine|uvicorn|8000' || true
echo

echo "[8] Recent journal for abenginecore-api (last 20)"
journalctl -u abenginecore-api -n 20 --no-pager 2>/dev/null | tail -25 || true
echo

echo "[9] Recent journal for legacy abenginecore (last 20)"
journalctl -u abenginecore -n 20 --no-pager 2>/dev/null | tail -25 || true
echo

echo "[10] Any tmux/screen sessions running uvicorn?"
command -v tmux >/dev/null && tmux ls 2>/dev/null || true
command -v screen >/dev/null && screen -ls 2>/dev/null || true
echo

echo "==============================================================="
echo " Done. The respawn source is shown by section [2] cgroup."
echo " - If cgroup says 'abenginecore.service' -> legacy still enabled,"
echo "   run: systemctl disable --now abenginecore"
echo " - If cgroup says '0::/' (no unit) -> respawn is from cron/pm2/screen"
echo "   inspect sections [6][7][10]."
echo " - If cgroup says 'abenginecore-api.service' -> our service is"
echo "   itself starting with --host 127.0.0.1; show systemd unit body."
echo "==============================================================="
