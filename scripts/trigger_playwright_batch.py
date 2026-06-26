"""
trigger_playwright_batch.py
===========================
Trigger GitHub Actions workflow_dispatch for batch Playwright scraping.

Runs 4 sequential batches (Frontiers → Elsevier → Wiley → Springer, 500 each)
via the GitHub API.

Prerequisites:
  Set env var: GITHUB_TOKEN=ghp_...
  (or pass --token on CLI)

  The token needs: repo scope (to trigger workflow_dispatch).

Usage:
  python scripts/trigger_playwright_batch.py --token ghp_...
  python scripts/trigger_playwright_batch.py  # reads GITHUB_TOKEN from env
  python scripts/trigger_playwright_batch.py --dry-run  # show what would run

  # Single publisher only:
  python scripts/trigger_playwright_batch.py --publisher Frontiers --limit 200
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from typing import Optional

REPO_OWNER = "jhuang7908"
REPO_NAME  = "Antibody-Engineer-Suite-MVP"
WORKFLOW   = "scrape_guidelines_playwright.yml"
BRANCH     = "master"
API_BASE   = "https://api.github.com"

BATCHES = [
    {"publisher": "Frontiers", "limit": "500", "delay": "2.0"},
    {"publisher": "Elsevier",  "limit": "500", "delay": "2.5"},
    {"publisher": "Wiley",     "limit": "500", "delay": "2.5"},
    {"publisher": "Springer",  "limit": "500", "delay": "2.5"},
]


def _dispatch(token: str, inputs: dict, dry_run: bool = False) -> dict:
    url  = f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{WORKFLOW}/dispatches"
    body = json.dumps({"ref": BRANCH, "inputs": inputs}).encode()
    if dry_run:
        print(f"  [DRY RUN] POST {url}")
        print(f"  inputs: {inputs}")
        return {"dry_run": True}

    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization":  f"Bearer {token}",
            "Accept":         "application/vnd.github+json",
            "Content-Type":   "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            # 204 No Content = success
            return {"status": resp.status, "success": True}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"error": f"HTTP {e.code}: {body[:200]}"}
    except Exception as exc:
        return {"error": str(exc)}


def _list_runs(token: str) -> list[dict]:
    """List recent workflow runs (for status check)."""
    url = (f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/"
           f"{WORKFLOW}/runs?per_page=5")
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("workflow_runs", [])
    except Exception:
        return []


def run_batches(
    token: str,
    batches: list[dict] | None = None,
    wait_between: int = 30,
    dry_run: bool = False,
) -> list[dict]:
    """
    Trigger each batch sequentially via GitHub Actions workflow_dispatch.

    Args:
        token:          GitHub personal access token with repo scope.
        batches:        List of input dicts (publisher, limit, delay).
                        Defaults to BATCHES (4 publishers × 500).
        wait_between:   Seconds to wait between dispatches (default 30s).
        dry_run:        If True, print what would be dispatched without sending.

    Returns:
        List of result dicts per batch.
    """
    if batches is None:
        batches = BATCHES

    results = []
    for i, batch in enumerate(batches, 1):
        pub   = batch.get("publisher", "all")
        limit = batch.get("limit",     "500")
        delay = batch.get("delay",     "2.5")

        print(f"\nBatch {i}/{len(batches)}: {pub}  limit={limit}  delay={delay}s")
        result = _dispatch(token, {"publisher": pub, "limit": limit, "delay": delay}, dry_run=dry_run)
        result["batch"] = i
        result["publisher"] = pub

        if "error" in result:
            print(f"  ERROR: {result['error']}")
        elif not dry_run:
            print(f"  Dispatched (HTTP {result.get('status',204)})")

        results.append(result)

        if i < len(batches) and not dry_run:
            print(f"  Waiting {wait_between}s before next batch…")
            time.sleep(wait_between)

    return results


def check_status(token: str):
    """Print status of recent workflow runs."""
    runs = _list_runs(token)
    if not runs:
        print("No recent runs found (or token lacks repo scope).")
        return
    print(f"\nRecent runs for {WORKFLOW}:")
    for r in runs:
        status     = r.get("status", "?")
        conclusion = r.get("conclusion") or "in_progress"
        created    = r.get("created_at", "")[:16]
        run_id     = r.get("id")
        print(f"  [{created}] #{run_id}  {status}/{conclusion}")


def main():
    parser = argparse.ArgumentParser(description="Trigger Playwright batch scraping via GitHub Actions")
    parser.add_argument("--token",     default=os.environ.get("GITHUB_TOKEN", ""),
                        help="GitHub PAT (or set GITHUB_TOKEN env var)")
    parser.add_argument("--publisher", default="",
                        help="Single publisher (default: run all 4 batches)")
    parser.add_argument("--limit",     default="500", help="Journals per batch (default 500)")
    parser.add_argument("--delay",     default="2.5", help="Seconds between requests")
    parser.add_argument("--wait",      type=int, default=30,
                        help="Seconds between batch dispatches (default 30)")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Print what would be dispatched without sending")
    parser.add_argument("--status",    action="store_true",
                        help="Show recent workflow run status and exit")
    args = parser.parse_args()

    if not args.token and not args.dry_run:
        print("ERROR: No GitHub token. Set GITHUB_TOKEN env var or pass --token.", file=sys.stderr)
        print("  export GITHUB_TOKEN=ghp_...", file=sys.stderr)
        sys.exit(1)

    if args.status:
        check_status(args.token)
        return

    if args.publisher:
        batches = [{"publisher": args.publisher, "limit": args.limit, "delay": args.delay}]
    else:
        batches = BATCHES

    print(f"Triggering {len(batches)} Playwright scraping batch(es)")
    print(f"Repo: {REPO_OWNER}/{REPO_NAME}  |  Workflow: {WORKFLOW}")
    if args.dry_run:
        print("[DRY RUN MODE — nothing will be dispatched]\n")

    results = run_batches(args.token, batches=batches, wait_between=args.wait, dry_run=args.dry_run)

    errors = [r for r in results if "error" in r]
    ok     = [r for r in results if "error" not in r]
    print(f"\nSummary: {len(ok)} dispatched, {len(errors)} errors")
    if errors:
        for e in errors:
            print(f"  Batch {e['batch']} ({e['publisher']}): {e['error']}")
    elif not args.dry_run:
        print("Monitor progress at:")
        print(f"  https://github.com/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{WORKFLOW}")


if __name__ == "__main__":
    main()
