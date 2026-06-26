"""
InSynBio OpenAlex CLI — polite-pool wrapper (no uv, no budget tracking).

Adopted from GDM science-skills/literature_search_openalex (Apache-2.0).
See vendor/adopted/science-skills/openalex/SKILL_mirror.md for diff notes.

Usage:
    python scripts/insynbio_openalex.py search --topic "de novo antibody design"
    python scripts/insynbio_openalex.py get-work --doi "10.1038/s41586-023-06415-8"
    python scripts/insynbio_openalex.py verify-dois --dois-file data/dois.txt [--out results.json]
    python scripts/insynbio_openalex.py resolve-author --name "Jennifer Doudna"
    python scripts/insynbio_openalex.py filter-works --filter "publication_year:2024,topics.id:T10001" [--per-page 10]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    sys.exit("ERROR: 'requests' not installed. Run: pip install requests")

BASE_URL = "https://api.openalex.org"
DEFAULT_SELECT_WORKS = "id,doi,title,publication_year,cited_by_count,primary_location,open_access"
DEFAULT_PER_PAGE = 10
POLITE_EMAIL = os.environ.get("OPENALEX_EMAIL", "research@insynbio.com")
API_KEY = os.environ.get("OPENALEX_API_KEY", "")


def _params(extra: dict | None = None) -> dict[str, Any]:
    p: dict[str, Any] = {"mailto": POLITE_EMAIL}
    if API_KEY:
        p["api_key"] = API_KEY
    if extra:
        p.update(extra)
    return p


def _get(endpoint: str, params: dict | None = None, retries: int = 3) -> Any:
    url = f"{BASE_URL}/{endpoint}"
    p = _params(params)
    for attempt in range(retries):
        resp = requests.get(url, params=p, timeout=20)
        if resp.status_code == 429:
            wait = 5 * (attempt + 1)
            print(f"[OpenAlex] Rate limited — waiting {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"OpenAlex {endpoint}: failed after {retries} retries")


def cmd_search(args: argparse.Namespace) -> None:
    """Full-text search for works by topic string."""
    params = {
        "search": args.topic,
        "per_page": args.per_page,
        "select": args.select or DEFAULT_SELECT_WORKS,
        "sort": "cited_by_count:desc",
    }
    if args.year_from or args.year_to:
        year_filter = ""
        if args.year_from and args.year_to:
            year_filter = f"publication_year:{args.year_from}-{args.year_to}"
        elif args.year_from:
            year_filter = f"publication_year:>{args.year_from - 1}"
        elif args.year_to:
            year_filter = f"publication_year:<{args.year_to + 1}"
        params["filter"] = year_filter
    data = _get("works", params)
    results = data.get("results", [])
    print(f"[OpenAlex] search '{args.topic}' → {data.get('meta', {}).get('count', '?')} total, showing {len(results)}")
    _output(results, args.out)


def cmd_get_work(args: argparse.Namespace) -> None:
    """Retrieve full metadata for one work by DOI."""
    doi = args.doi.lstrip("https://doi.org/").lstrip("doi.org/")
    data = _get(f"works/https://doi.org/{doi}")
    _output(data, args.out)


def cmd_verify_dois(args: argparse.Namespace) -> None:
    """Batch verify a list of DOIs — report found / not found."""
    dois_file = Path(args.dois_file)
    if not dois_file.exists():
        sys.exit(f"ERROR: file not found: {dois_file}")
    dois = [ln.strip() for ln in dois_file.read_text().splitlines() if ln.strip() and not ln.startswith("#")]
    if not dois:
        sys.exit("ERROR: no DOIs found in file")
    print(f"[OpenAlex] verifying {len(dois)} DOIs …")
    results = []
    for i, doi in enumerate(dois):
        clean = doi.lstrip("https://doi.org/").lstrip("doi.org/")
        try:
            data = _get(f"works/https://doi.org/{clean}", retries=2)
            results.append({
                "doi": doi,
                "status": "found",
                "id": data.get("id"),
                "title": data.get("title"),
                "year": data.get("publication_year"),
                "cited_by_count": data.get("cited_by_count"),
                "is_oa": data.get("open_access", {}).get("is_oa"),
                "oa_url": data.get("open_access", {}).get("oa_url"),
            })
        except Exception as exc:
            results.append({"doi": doi, "status": "not_found", "error": str(exc)})
        if i % 10 == 9:
            time.sleep(0.5)
    found = sum(1 for r in results if r["status"] == "found")
    print(f"[OpenAlex] {found}/{len(dois)} DOIs verified")
    _output(results, args.out)


def cmd_resolve_author(args: argparse.Namespace) -> None:
    """Resolve an author name to OpenAlex author ID candidates."""
    params = {
        "search": args.name,
        "per_page": args.per_page or 5,
        "select": "id,display_name,hint,works_count,cited_by_count",
    }
    data = _get("authors", params)
    results = data.get("results", [])
    print(f"[OpenAlex] resolve author '{args.name}' → {len(results)} candidates")
    _output(results, args.out)


def cmd_filter_works(args: argparse.Namespace) -> None:
    """Filter works by OpenAlex filter expression (e.g. 'publication_year:2024')."""
    params = {
        "filter": args.filter,
        "per_page": args.per_page or DEFAULT_PER_PAGE,
        "select": args.select or DEFAULT_SELECT_WORKS,
        "sort": args.sort or "cited_by_count:desc",
    }
    data = _get("works", params)
    results = data.get("results", [])
    print(f"[OpenAlex] filter '{args.filter}' → {data.get('meta', {}).get('count', '?')} total, showing {len(results)}")
    _output(results, args.out)


def _output(data: Any, out_path: str | None) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if out_path:
        Path(out_path).write_text(text, encoding="utf-8")
        print(f"[OpenAlex] written → {out_path}")
    else:
        print(text)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="insynbio_openalex",
        description="InSynBio OpenAlex CLI — literature search & DOI verification",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # search
    p_search = sub.add_parser("search", help="Full-text search for works")
    p_search.add_argument("--topic", required=True, help="Search query string")
    p_search.add_argument("--per-page", type=int, default=DEFAULT_PER_PAGE)
    p_search.add_argument("--year-from", type=int, default=None)
    p_search.add_argument("--year-to", type=int, default=None)
    p_search.add_argument("--select", default=None)
    p_search.add_argument("--out", default=None, help="Write JSON to file")

    # get-work
    p_get = sub.add_parser("get-work", help="Fetch one work by DOI")
    p_get.add_argument("--doi", required=True)
    p_get.add_argument("--out", default=None)

    # verify-dois
    p_verify = sub.add_parser("verify-dois", help="Batch verify DOIs from a text file")
    p_verify.add_argument("--dois-file", required=True, help="One DOI per line")
    p_verify.add_argument("--out", default=None, help="Write JSON results to file")

    # resolve-author
    p_author = sub.add_parser("resolve-author", help="Resolve author name → ID candidates")
    p_author.add_argument("--name", required=True)
    p_author.add_argument("--per-page", type=int, default=5)
    p_author.add_argument("--out", default=None)

    # filter-works
    p_filter = sub.add_parser("filter-works", help="Filter works by OpenAlex filter expression")
    p_filter.add_argument("--filter", required=True)
    p_filter.add_argument("--per-page", type=int, default=DEFAULT_PER_PAGE)
    p_filter.add_argument("--select", default=None)
    p_filter.add_argument("--sort", default=None)
    p_filter.add_argument("--out", default=None)

    args = parser.parse_args()

    dispatch = {
        "search": cmd_search,
        "get-work": cmd_get_work,
        "verify-dois": cmd_verify_dois,
        "resolve-author": cmd_resolve_author,
        "filter-works": cmd_filter_works,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
