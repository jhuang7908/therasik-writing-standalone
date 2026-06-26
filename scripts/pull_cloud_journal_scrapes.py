"""
pull_cloud_journal_scrapes.py
=============================
Pull journal guideline scrape results from the cloud MVP repo
(jhuang7908/Antibody-Engineer-Suite-MVP) and merge them into the
local assets/journal_requirements/ tree.

The cloud GitHub Actions workflow (scrape_guidelines_playwright.yml) runs
scripts/journal_db/scrape_journal_guidelines.py and commits results directly
to master — there are no downloadable artifacts. This script is the bridge.

Merge policy (non-destructive):
  - Never overwrite non-empty curated fields (article_types dict with word limits,
    reference_style, format_hints, etc.).
  - Always fill empty cloud fields: guidelines_url, scraped_at, word_limits,
    article_types (if local empty), cover_letter_required, reference_limit.
  - Preserve local submission_guidelines + _provenance from scrape_guidelines_local.
  - Record merge audit in assets/journal_requirements/scraped/_cloud_pull_report.json

Usage:
  python scripts/pull_cloud_journal_scrapes.py              # pull all known cloud scrapes
  python scripts/pull_cloud_journal_scrapes.py --dry-run    # preview only
  python scripts/pull_cloud_journal_scrapes.py --audit-only # count cloud vs local without writing
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR   = Path(__file__).resolve().parents[1]
JOURNAL_DIR = SKILL_DIR / "assets" / "journal_requirements"
SCRAPED_DIR = JOURNAL_DIR / "scraped"
REPORT_PATH = SCRAPED_DIR / "_cloud_pull_report.json"

CLOUD_REPO  = "jhuang7908/Antibody-Engineer-Suite-MVP"
CLOUD_REF   = "master"

# Fields written by cloud journal_db scraper
CLOUD_SCRAPE_KEYS = (
    "article_types", "word_limits", "figure_requirements",
    "reference_limit", "cover_letter_required",
    "guidelines_url", "scraped_at",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gh_api(path: str) -> dict | list:
    out = subprocess.check_output(
        ["gh", "api", path], text=True, stderr=subprocess.STDOUT)
    return json.loads(out)


def _cloud_file_list() -> list[str]:
    """Find journal JSON filenames on cloud that contain guidelines_url."""
    try:
        data = _gh_api(
            f"search/code?q=guidelines_url+repo:{CLOUD_REPO}"
            f"+path:assets/journal_requirements")
        items = data.get("items", [])
        names = sorted({
            it["path"].split("/")[-1]
            for it in items
            if it["path"].endswith(".json")
            and not it["name"].startswith("_")
        })
        return names
    except Exception as exc:
        print(f"WARN: code search failed ({exc}); falling back to scrape commits")
        return _files_from_scrape_commits()


def _files_from_scrape_commits() -> list[str]:
    commits = _gh_api(
        f"repos/{CLOUD_REPO}/commits?per_page=50")
    names: set[str] = set()
    for c in commits:
        msg = c.get("commit", {}).get("message", "")
        if "scrape article_types" not in msg and "scrape journal submission" not in msg.lower():
            continue
        sha = c["sha"]
        detail = _gh_api(f"repos/{CLOUD_REPO}/commits/{sha}")
        for f in detail.get("files", []):
            p = f.get("filename", "")
            if p.startswith("assets/journal_requirements/") and p.endswith(".json"):
                names.add(p.split("/")[-1])
    return sorted(names)


def _fetch_cloud_json(filename: str) -> dict | None:
    path = f"repos/{CLOUD_REPO}/contents/assets/journal_requirements/{filename}?ref={CLOUD_REF}"
    try:
        data = _gh_api(path)
        return json.loads(base64.b64decode(data["content"]))
    except Exception as exc:
        print(f"  SKIP fetch {filename}: {exc}")
        return None


def _is_empty(val) -> bool:
    return val is None or val == "" or val == [] or val == {}


def _merge_record(local: dict, cloud: dict) -> tuple[dict, list[str]]:
    """Return merged dict + list of fields applied from cloud."""
    merged = dict(local)
    applied: list[str] = []

    for key in CLOUD_SCRAPE_KEYS:
        cloud_val = cloud.get(key)
        if _is_empty(cloud_val):
            continue
        local_val = merged.get(key)
        if _is_empty(local_val):
            merged[key] = cloud_val
            applied.append(key)
        elif key in ("guidelines_url", "scraped_at"):
            # Always refresh URL/timestamp if cloud is newer
            if key == "scraped_at":
                merged[key] = cloud_val
                applied.append(f"{key}(updated)")
            elif _is_empty(local_val):
                merged[key] = cloud_val
                applied.append(key)

    merged.setdefault("_provenance", {})
    if applied:
        merged["_provenance"]["cloud_pull"] = {
            "source_repo": CLOUD_REPO,
            "pulled_at": _now_iso(),
            "fields_applied": applied,
            "cloud_scraped_at": cloud.get("scraped_at"),
            "verification_status": "cloud_pulled_unverified",
        }

    return merged, applied


def audit_cloud(names: list[str]) -> dict:
    stats = {"total": len(names), "has_guidelines_url": 0,
             "has_article_types": 0, "has_word_limits": 0,
             "has_reference_limit": 0}
    for fn in names:
        cloud = _fetch_cloud_json(fn)
        if not cloud:
            continue
        if cloud.get("guidelines_url"):
            stats["has_guidelines_url"] += 1
        at = cloud.get("article_types")
        if at and (isinstance(at, list) and at or isinstance(at, dict) and at):
            stats["has_article_types"] += 1
        wl = cloud.get("word_limits") or {}
        if isinstance(wl, dict) and wl.get("main_text"):
            stats["has_word_limits"] += 1
        if cloud.get("reference_limit"):
            stats["has_reference_limit"] += 1
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description="Pull cloud journal scrape results into local DB")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--audit-only", action="store_true")
    args = ap.parse_args()

    print(f"Querying cloud repo: {CLOUD_REPO} @ {CLOUD_REF}")
    names = _cloud_file_list()
    print(f"Cloud files with scrape footprint: {len(names)}")

    cloud_stats = audit_cloud(names)
    print("\nCloud scrape quality:")
    for k, v in cloud_stats.items():
        print(f"  {k}: {v}")

    if args.audit_only:
        return

    SCRAPED_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "pulled_at": _now_iso(),
        "cloud_repo": CLOUD_REPO,
        "cloud_ref": CLOUD_REF,
        "cloud_stats": cloud_stats,
        "merged": [],
        "skipped_missing_local": [],
        "no_changes": [],
    }

    merged_n = 0
    for fn in names:
        cloud = _fetch_cloud_json(fn)
        if not cloud:
            continue
        local_path = JOURNAL_DIR / fn
        if not local_path.exists():
            report["skipped_missing_local"].append(fn)
            continue
        local = json.loads(local_path.read_text(encoding="utf-8"))
        merged, applied = _merge_record(local, cloud)
        if not applied:
            report["no_changes"].append(fn)
            continue
        merged_n += 1
        report["merged"].append({"file": fn, "fields": applied,
                                  "guidelines_url": cloud.get("guidelines_url")})
        if not args.dry_run:
            local_path.write_text(
                json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
            # Keep cloud snapshot for audit
            snap = SCRAPED_DIR / f"cloud_{fn}"
            snap.write_text(
                json.dumps(cloud, indent=2, ensure_ascii=False), encoding="utf-8")

    report["summary"] = {
        "files_on_cloud": len(names),
        "merged": merged_n,
        "no_changes": len(report["no_changes"]),
        "missing_local": len(report["skipped_missing_local"]),
        "dry_run": args.dry_run,
    }

    if not args.dry_run:
        REPORT_PATH.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Merge summary:")
    print(f"  merged: {merged_n}  no_changes: {len(report['no_changes'])}  "
          f"missing_local: {len(report['skipped_missing_local'])}")
    if report["merged"][:5]:
        print("  sample merges:")
        for m in report["merged"][:5]:
            print(f"    {m['file']}: {m['fields']}")
    if not args.dry_run:
        print(f"  report: {REPORT_PATH.relative_to(SKILL_DIR)}")


if __name__ == "__main__":
    main()
