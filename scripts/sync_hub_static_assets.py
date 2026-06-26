#!/usr/bin/env python3
"""Copy hub static assets (YP bundle, SEO files) from suite into insynbio-website checkout."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = ROOT / "insynbio-web-source"
DEFAULT_DST = ROOT / "insynbio-web-source"

COPY_FILES = (
    "us-chinese-life-hub.html",
    "robots.txt",
    "_headers",
    "sitemap.xml",
    "yellow_pages.json",
    "yellow_pages_reports.json",
    "yellow_page_ratings.json",
    "hub_search_index.json",
    "hub_market_snapshot.json",
    "hub-link-viewer.html",
    "wechat-qr.png",
    "images/wechat-qr.png",
)
COPY_DIRS = ("yp_data", "images")
SKIP_YP_FILES = frozenset({"manifest_internal.json", "yellow_pages_by_region.json"})


def sync(src: Path, dst: Path) -> None:
    if not src.is_dir():
        print(f"FAIL: source missing: {src}", file=sys.stderr)
        sys.exit(1)
    dst.mkdir(parents=True, exist_ok=True)
    if src.resolve() == dst.resolve():
        print("  skip  src == dst (already in place)")
        return
    for name in COPY_FILES:
        s = src / name
        if s.is_file():
            d = dst / name
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
            print(f"  file  {name}")
    for name in COPY_DIRS:
        s = src / name
        if s.is_dir():
            d = dst / name
            if d.exists():
                try:
                    shutil.rmtree(d)
                except OSError:
                    import time
                    time.sleep(0.5)
                    shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True, exist_ok=True)
            n = 0
            for fp in s.rglob("*"):
                if fp.is_dir():
                    continue
                rel = fp.relative_to(s)
                if rel.name in SKIP_YP_FILES:
                    continue
                out = d / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(fp, out)
                n += 1
            print(f"  dir   {name}/ ({n} files)")


def main() -> None:
    p = argparse.ArgumentParser(description="Sync hub YP + SEO assets to website repo folder")
    p.add_argument("--src", type=Path, default=DEFAULT_SRC)
    p.add_argument("--dst", type=Path, default=DEFAULT_DST)
    args = p.parse_args()
    print(f"Sync {args.src} -> {args.dst}")
    sync(args.src, args.dst)
    print("Done.")


if __name__ == "__main__":
    main()
