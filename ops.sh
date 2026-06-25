# AbEngineCore SaaS 运维脚本
# 使用：
#   bash ops.sh [command] [args]

DOMAIN="${DOMAIN:-your-domain.com}"
DATA_ROOT="${DATA_ROOT:-/opt/abenginecore}"

usage() {
    cat << EOF
Usage: bash ops.sh [command]

Commands:
  status          Show container status
  logs [N]        Tail last N lines of logs (default 50)
  restart         Restart all services
  pull            Pull latest image and restart
  stop            Stop services (data persists)
  start           Start services
  shell           Interactive bash in abenginecore container
  clean-jobs [DAYS]  Delete jobs older than N days (default 30)
  backup [DIR]    Backup jobs + auth to DIR
  stats           Show disk usage

Example:
  bash ops.sh status
  bash ops.sh logs 100
  bash ops.sh pull
  bash ops.sh clean-jobs 7
EOF
}

cd "$DATA_ROOT" || { echo "Error: $DATA_ROOT not found"; exit 1; }

case "$1" in
  status)
    echo "Service status:"
    docker-compose ps
    ;;
  logs)
    n="${2:-50}"
    docker-compose logs --tail=$n -f
    ;;
  restart)
    echo "Restarting services..."
    docker-compose restart
    sleep 5
    docker-compose ps
    ;;
  pull)
    echo "Pulling latest image..."
    docker-compose pull abenginecore
    docker-compose up -d abenginecore
    sleep 5
    docker-compose ps
    ;;
  stop)
    echo "Stopping services..."
    docker-compose down
    ;;
  start)
    echo "Starting services..."
    docker-compose up -d
    sleep 5
    docker-compose ps
    ;;
  shell)
    docker-compose exec abenginecore bash
    ;;
  clean-jobs)
    days="${2:-30}"
    echo "Deleting jobs older than $days days..."
    docker-compose exec -T abenginecore python << PYTHON
import os, time
from pathlib import Path

jobs_dir = Path('/app/.job_storage')
cutoff = time.time() - ($days * 86400)
deleted = 0

for job_dir in jobs_dir.iterdir():
    if job_dir.is_dir() and job_dir.stat().st_mtime < cutoff:
        import shutil
        shutil.rmtree(job_dir)
        deleted += 1

print(f"Deleted {deleted} old job(s)")
PYTHON
    ;;
  backup)
    backup_dir="${2:-.}"
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_file="$backup_dir/abenginecore_backup_$timestamp.tar.gz"
    echo "Backing up to $backup_file..."
    tar -czf "$backup_file" jobs/ auth/
    echo "✓ Backup complete: $(du -h $backup_file | cut -f1)"
    ;;
  stats)
    echo "Disk usage:"
    du -sh jobs/ auth/ . 2>/dev/null | sort -h
    echo ""
    echo "Job count: $(find jobs -maxdepth 1 -type d | wc -l)"
    ;;
  *)
    usage
    ;;
esac
