#!/usr/bin/env python3
"""
：，。

/（ VectorBuilder 、Addgene  GenBank ）：
  -  URL：，（）。
  - ：，。
  - （）：， stdout。

：
  # URL 
  python scripts/actes_fetch_double_verify.py --url "https://..." --out promoter_EF1A.txt

  # （ FASTA）
  python scripts/actes_fetch_double_verify.py --file path/to/seq.fasta --out verified.fasta

  # （）：--dry-run
  python scripts/actes_fetch_double_verify.py --url "https://..." --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None


def normalize_sequence(text: str, is_dna: bool = True) -> str:
    """ FASTA ，，。"""
    out = re.sub(r"\s+", "", text)
    if "\n" in text or text.strip().startswith(">"):
        lines = [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith(">")]
        out = re.sub(r"\s+", "", "".join(lines))
    return out.upper() if is_dna else out


def fetch_url_twice(url: str, timeout: int = 30) -> tuple[str, str]:
    if requests is None:
        raise RuntimeError(" requests: pip install requests")
    r1 = requests.get(url, timeout=timeout)
    r1.raise_for_status()
    r2 = requests.get(url, timeout=timeout)
    r2.raise_for_status()
    return r1.text, r2.text


def read_file_twice(path: Path) -> tuple[str, str]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    return p.read_text(encoding="utf-8", errors="replace"), p.read_text(
        encoding="utf-8", errors="replace"
    )


def run_cmd_twice(cmd: list[str], timeout: int = 60) -> tuple[str, str]:
    out1 = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, check=True, cwd=None
    )
    out2 = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, check=True, cwd=None
    )
    return out1.stdout, out2.stdout


def main() -> int:
    ap = argparse.ArgumentParser(description="//，")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--url", metavar="URL", help=" URL ")
    g.add_argument("--file", metavar="PATH", help="")
    g.add_argument("--cmd", metavar="CMD", nargs="+", help=" stdout（ python get_seq.py）")
    ap.add_argument("--out", metavar="PATH", help="（）")
    ap.add_argument("--dry-run", action="store_true", help="")
    ap.add_argument("--no-normalize", action="store_true", help="，")
    ap.add_argument("--timeout", type=int, default=30, help="URL （）")
    args = ap.parse_args()

    if args.url:
        raw1, raw2 = fetch_url_twice(args.url, timeout=args.timeout)
    elif args.file:
        raw1, raw2 = read_file_twice(Path(args.file))
    else:
        raw1, raw2 = run_cmd_twice(args.cmd, timeout=args.timeout)

    if args.no_normalize:
        s1, s2 = raw1, raw2
    else:
        s1 = normalize_sequence(raw1)
        s2 = normalize_sequence(raw2)

    if s1 != s2:
        print("FAIL: ，。", file=sys.stderr)
        print(f"  : {len(s1)}, : {len(s2)}", file=sys.stderr)
        if len(s1) == len(s2):
            diff = sum(1 for a, b in zip(s1, s2) if a != b)
            print(f"  : {diff}", file=sys.stderr)
        return 1

    print("OK: 。")
    print(f"  : {len(s1)} ")
    h = hashlib.sha256(s1.encode("utf-8")).hexdigest()[:16]
    print(f"  SHA256(16): {h}")

    if args.out and not args.dry_run:
        out_path = Path(args.out)
        out_path.write_text(raw1, encoding="utf-8")
        print(f"  : {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
