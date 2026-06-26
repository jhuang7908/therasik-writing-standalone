#!/usr/bin/env python3
"""
Mirror free/open scientific illustration libraries to the server.

Usage (from services/writing_memory):
  python scripts/download_science_asset_libraries.py --all
  python scripts/download_science_asset_libraries.py --library bioicons,healthicons
  python scripts/download_science_asset_libraries.py --library servier_smart --dry-run

Requires: git (for bioicons, healthicons), network access.
Servier PPTX URLs are defined in data/science_assets/manifest.json (CC BY 4.0).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import unquote

try:
    import requests
except ImportError:
    requests = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "data" / "science_assets" / "manifest.json"
LIBS_ROOT = ROOT / "data" / "science_assets" / "libraries"

HEADERS = {
    "User-Agent": "InSynBio-ScienceAssets/1.0 (+https://insynbio.com; research mirror)",
}


def _load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _git_shallow_clone(repo: str, dest: Path, dry_run: bool) -> bool:
    if dest.exists() and any(dest.iterdir()):
        print(f"  skip clone (exists): {dest}")
        return True
    if dry_run:
        print(f"  [dry-run] git clone {repo} -> {dest}")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "git", "clone", "--depth", "1", "--single-branch",
        repo, str(dest),
    ]
    print(f"  git clone {repo} ...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr or r.stdout, file=sys.stderr)
        return False
    return True


def _discover_http_files(lib: dict) -> list[dict[str, str]]:
    """Resolve file list from manifest entries or a discover_url HTML page."""
    files = list(lib.get("files") or [])
    if files:
        return files
    page = (lib.get("discover_url") or "").strip()
    if not page:
        return []
    if requests is None:
        print("  ERROR: pip install requests (needed for http_discover)", file=sys.stderr)
        return []
    pattern = lib.get("discover_pattern") or r"https://smart\.servier\.com/wp-content/uploads/[^\s\"']+\.pptx"
    print(f"  discover {page} ...")
    try:
        r = requests.get(page, headers=HEADERS, timeout=90)
        r.raise_for_status()
    except Exception as exc:
        print(f"  FAIL discover: {exc}", file=sys.stderr)
        return []
    urls = sorted(set(re.findall(pattern, r.text, flags=re.I)))
    out: list[dict[str, str]] = []
    for url in urls:
        name = unquote(Path(url.split("?")[0]).name)
        out.append({"name": name, "url": url})
    print(f"  found {len(out)} files")
    return out


def _download_file(url: str, dest: Path, dry_run: bool) -> bool:
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"  skip (exists): {dest.name}")
        return True
    if dry_run:
        print(f"  [dry-run] GET {url}")
        return True
    if requests is None:
        print("  ERROR: pip install requests", file=sys.stderr)
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = requests.get(url, headers=HEADERS, timeout=120, stream=True)
        if r.status_code != 200:
            print(f"  FAIL {r.status_code}: {url}")
            return False
        with dest.open("wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        print(f"  OK {dest.name} ({dest.stat().st_size // 1024} KB)")
        return True
    except Exception as exc:
        print(f"  FAIL {url}: {exc}", file=sys.stderr)
        return False


def install_library(lib: dict, dry_run: bool) -> bool:
    lid = lib.get("id") or "unknown"
    method = lib.get("method") or ""
    install_dir = ROOT / "data" / "science_assets" / (lib.get("install_dir") or f"libraries/{lid}")

    print(f"\n=== {lib.get('name', lid)} ({method}) ===")

    if method == "git_shallow":
        repo = lib.get("repo") or ""
        if not repo:
            return False
        return _git_shallow_clone(repo, install_dir, dry_run)

    if method in ("http_files", "http_discover"):
        ok_all = True
        entries = _discover_http_files(lib) if method == "http_discover" else (lib.get("files") or [])
        for ent in entries:
            url = ent.get("url") or ""
            name = ent.get("name") or Path(url).name
            if not url:
                continue
            dest = install_dir / name
            if not _download_file(url, dest, dry_run):
                ok_all = False
            time.sleep(0.3)
        return ok_all

    print(f"  unknown method: {method}")
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Download science illustration libraries")
    ap.add_argument("--all", action="store_true", help="Install all libraries in manifest")
    ap.add_argument(
        "--library",
        type=str,
        default="",
        help="Comma-separated library ids (bioicons, healthicons, servier_smart)",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list", action="store_true", help="List library ids and exit")
    args = ap.parse_args()

    if not MANIFEST.is_file():
        print(f"Missing manifest: {MANIFEST}", file=sys.stderr)
        return 1

    manifest = _load_manifest()
    libs = manifest.get("libraries") or []

    if args.list:
        for lib in libs:
            print(f"{lib.get('id')}: {lib.get('name')} [{lib.get('method')}]")
        return 0

    if args.all:
        ids = [x.get("id") for x in libs if x.get("id")]
    elif args.library.strip():
        ids = [x.strip() for x in args.library.split(",") if x.strip()]
    else:
        ap.print_help()
        return 1

    lib_map = {x["id"]: x for x in libs if x.get("id")}
    ok = True
    for lid in ids:
        if lid not in lib_map:
            print(f"Unknown library: {lid}", file=sys.stderr)
            ok = False
            continue
        if not install_library(lib_map[lid], args.dry_run):
            ok = False

    if not args.dry_run and ok:
        stamp = ROOT / "data" / "science_assets" / "installed_at.txt"
        stamp.write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), encoding="utf-8")
        print(f"\nDone. Open Figure Studio: /figures on writing-memory service.")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
