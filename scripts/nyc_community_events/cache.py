"""Event cache management with 30-day rolling window eviction."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def cache_root(out_root: Path | None = None) -> Path:
    base = out_root or Path(
        os.environ.get("NYC_COMMUNITY_OUT_ROOT", ROOT / "outputs" / "nyc_community_events")
    )
    return base / "_events_cache"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_daily_cache(
    payload: dict[str, Any],
    *,
    out_root: Path | None = None,
) -> Path:
    root = cache_root(out_root)
    root.mkdir(parents=True, exist_ok=True)
    day = datetime.now().strftime("%Y%m%d")
    dated = root / f"digest_{day}.json"
    latest = root / "latest.json"
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    dated.write_text(body, encoding="utf-8")
    latest.write_text(body, encoding="utf-8")
    return latest


def load_latest_cache(*, out_root: Path | None = None) -> dict[str, Any] | None:
    latest = cache_root(out_root) / "latest.json"
    if not latest.exists():
        return None
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def evict_expired_cache(*, out_root: Path | None = None, retention_days: int = 30) -> int:
    """Remove cache files older than retention_days. Returns count of removed files."""
    root = cache_root(out_root)
    if not root.exists():
        return 0
    cutoff = datetime.now() - timedelta(days=retention_days)
    removed = 0
    for f in root.glob("digest_*.json"):
        date_part = f.stem.replace("digest_", "")
        try:
            file_date = datetime.strptime(date_part, "%Y%m%d")
            if file_date < cutoff:
                f.unlink()
                removed += 1
        except ValueError:
            continue
    return removed
