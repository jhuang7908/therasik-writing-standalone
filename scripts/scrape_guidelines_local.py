"""
scrape_guidelines_local.py
==========================
Polite, small-scale, *accumulating*, LOCAL scraper for journal "Instructions
for Authors" / submission-guideline pages.

Distinct from the existing cloud scrapers (run on GitHub Actions):
  scripts/scrape_guidelines_playwright.py         — large-batch, publisher-specific
  scripts/journal_db/scrape_journal_guidelines.py — CrossRef + Playwright DB build
This script is the *local* companion: small batches, robots.txt-respecting,
declaration-aware, provenance-tagged, resumable.

Philosophy ("慢慢积累" — accumulate gradually):
  • Curated seed list   — assets/journal_requirements/_scrape_seeds.json
  • Polite by default   — robots.txt respected, rate-limited, identifies itself
  • Small batches       — default 5 journals per run
  • Skip-recent         — re-scrapes only after --max-age-days (default 30)
  • Resumable ledger    — assets/journal_requirements/scraped/_ledger.json
  • Evidence of record  — full raw extraction saved to scraped/<slug>.json,
                          compact summary merged into journal_requirements/<slug>.json
                          so get_journal_requirements() surfaces it.

Two HTTP backends:
  requests + BeautifulSoup   (default; lightweight)
  playwright (chromium)      (--method playwright or per-seed; JS-heavy sites)

──────────────────────────────────────────────────────────────────────────────
SEARCH TERMS (检索词)
──────────────────────────────────────────────────────────────────────────────
1. Discovery queries — to FIND a guideline URL for a journal not yet seeded:
     "<journal>" author guidelines
     "<journal>" instructions for authors
     "<journal>" submission guidelines manuscript word limit
   (use --discover "<journal name>" to print ready-to-paste queries + candidates)

2. Extraction patterns — regex keywords used to PULL fields from a guideline
   page (word limits, abstract limits, reference style, declarations, ...).
   See EXTRACTION_PATTERNS below.

Usage:
  python scripts/scrape_guidelines_local.py --limit 5            # next 5 due
  python scripts/scrape_guidelines_local.py --slug nature        # one journal
  python scripts/scrape_guidelines_local.py --status             # ledger report
  python scripts/scrape_guidelines_local.py --discover "mAbs"    # search help
  python scripts/scrape_guidelines_local.py --limit 3 --delay 8  # gentler
  python scripts/scrape_guidelines_local.py --dry-run            # no writes
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

SKILL_DIR    = Path(__file__).resolve().parents[1]
JOURNAL_DIR  = SKILL_DIR / "assets" / "journal_requirements"
SCRAPED_DIR  = JOURNAL_DIR / "scraped"
SEEDS_FILE   = JOURNAL_DIR / "_scrape_seeds.json"
LEDGER_FILE  = SCRAPED_DIR / "_ledger.json"

USER_AGENT = ("TheraSIK-GuidelineBot/1.0 (academic submission-rules indexer; "
              "+contact via repository owner; respects robots.txt)")
DEFAULT_DELAY      = 6.0     # seconds between requests (polite)
DEFAULT_LIMIT      = 5
DEFAULT_MAX_AGE    = 30      # re-scrape only after N days
REQUEST_TIMEOUT    = 25

# ── Search terms / discovery query templates (检索词) ──────────────────────────
DISCOVERY_QUERY_TEMPLATES = [
    '"{journal}" author guidelines',
    '"{journal}" instructions for authors',
    '"{journal}" submission guidelines manuscript word limit',
    '"{journal}" for authors article types reference style',
]
SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q=",
    "bing":   "https://www.bing.com/search?q=",
    "ddg":    "https://duckduckgo.com/?q=",
}

# ── Extraction patterns (检索词 → fields) ──────────────────────────────────────
# Each entry: field -> list of (regex, group_index_for_value_or_None).
EXTRACTION_PATTERNS: dict[str, list[tuple[str, int | None]]] = {
    # Anchored to manuscript/article/main-text context so we don't capture the
    # abstract's word limit (handled separately below).
    "main_text_word_limit": [
        (r"(?:manuscript|main text|article|paper|full[- ]length|body of the (?:manuscript|paper)|total)[^.\n]{0,60}?(?:word limit|word count|maximum of|up to|not (?:to )?exceed|no more than|limited to)[^.\n]{0,20}?([0-9](?:[0-9,]){2,6})\s*words", 1),
        (r"(?:manuscript|main text|article|paper)[^.\n]{0,40}?([0-9](?:[0-9,]){3,6})\s*words?\s*(?:maximum|max\.?|limit|or fewer|or less)", 1),
    ],
    "abstract_word_limit": [
        (r"abstract[^.\n]{0,60}?(?:limited to|maximum of|up to|no more than|not exceed|within)\s*([0-9]{2,4})\s*words", 1),
        (r"abstract[^.\n]{0,30}?([0-9]{2,4})\s*words?\s*(?:maximum|max\.?|or fewer|or less|limit)", 1),
    ],
    "reference_limit": [
        (r"(?:references?|reference list)[^.\n]{0,40}?(?:limited to|maximum of|up to|no more than|not exceed)\s*([0-9]{1,3})", 1),
        (r"(?:maximum of|up to|no more than)\s*([0-9]{1,3})\s*references", 1),
    ],
    "figure_limit": [
        (r"(?:figures?(?:\s*and\s*tables)?)[^.\n]{0,40}?(?:limited to|maximum of|up to|no more than)\s*([0-9]{1,2})", 1),
    ],
}

# Presence-only flags (search term -> bool field).
FLAG_TERMS: dict[str, list[str]] = {
    "structured_abstract":      ["structured abstract"],
    "data_availability_required": ["data availability", "availability of data", "data sharing"],
    "ethics_statement_required":  ["ethics approval", "ethical approval", "ethics committee", "institutional review board", "irb"],
    "competing_interests_required": ["competing interests", "conflict of interest", "conflicts of interest", "declaration of interest"],
    "funding_statement_required": ["funding statement", "funding source", "role of the funding"],
    "author_contributions_required": ["author contributions", "authorship contributions", "credit taxonomy", "credit author"],
    "orcid_required":           ["orcid"],
    "graphical_abstract":       ["graphical abstract"],
    "preprint_policy":          ["preprint", "biorxiv", "medrxiv"],
    "double_blind_review":      ["double-blind", "double blind", "anonymi"],
}

# Reference-style detection (search term -> normalized style id).
REFERENCE_STYLE_TERMS: list[tuple[str, str]] = [
    (r"\bvancouver\b", "vancouver"),
    (r"\bnumbered\b.*\breferences?\b|\breferences?\b.*\bnumbered\b", "vancouver"),
    (r"\bauthor[\- ]date\b|\bharvard\b", "harvard"),
    (r"\bapa\b", "apa"),
    (r"\bama\b|american medical association", "ama"),
    (r"\bieee\b", "ieee"),
    (r"\bcouncil of science editors\b|\bcse\b", "cse"),
    (r"\bchicago\b", "chicago"),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8")


# ── Politeness: robots.txt ─────────────────────────────────────────────────────
_ROBOTS_CACHE: dict[str, urllib.robotparser.RobotFileParser] = {}


def _robots_allows(url: str) -> bool:
    try:
        parts = urlparse(url)
        base = f"{parts.scheme}://{parts.netloc}"
        rp = _ROBOTS_CACHE.get(base)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(base + "/robots.txt")
            try:
                rp.read()
            except Exception:
                # If robots.txt unreachable, default to allow (be conservative
                # elsewhere: low rate, identify UA).
                _ROBOTS_CACHE[base] = rp
                return True
            _ROBOTS_CACHE[base] = rp
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True


# ── Fetch backends ─────────────────────────────────────────────────────────────
def _fetch_requests(url: str) -> tuple[str | None, str | None]:
    try:
        import requests
    except ImportError:
        return None, "requests not installed"
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT,
                                       "Accept-Language": "en"},
                         timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        return r.text, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _fetch_playwright(url: str) -> tuple[str | None, str | None]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, "playwright not installed"
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, timeout=REQUEST_TIMEOUT * 1000,
                      wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            html = page.content()
            browser.close()
            return html, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _html_to_text(html: str) -> str:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        text = soup.get_text(" ")
    except Exception:
        text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


# ── Extraction ─────────────────────────────────────────────────────────────────
def extract_fields(text: str) -> dict:
    """Apply EXTRACTION_PATTERNS / FLAG_TERMS / styles to guideline text."""
    low = text.lower()
    out: dict = {}

    for field, patterns in EXTRACTION_PATTERNS.items():
        for rx, grp in patterns:
            m = re.search(rx, low, re.IGNORECASE)
            if m:
                val = m.group(grp) if grp else m.group(0)
                val = val.replace(",", "").strip()
                out[field] = int(val) if val.isdigit() else val
                break

    flags: dict[str, bool] = {}
    for field, terms in FLAG_TERMS.items():
        flags[field] = any(t in low for t in terms)
    out["flags"] = flags

    styles: list[str] = []
    for rx, sid in REFERENCE_STYLE_TERMS:
        if re.search(rx, low, re.IGNORECASE) and sid not in styles:
            styles.append(sid)
    if styles:
        out["reference_style_detected"] = styles

    # Article types mentioned (coarse).
    art = []
    for t in ["original research", "review", "brief report", "short communication",
              "case report", "perspective", "commentary", "editorial",
              "research article", "methods", "letter"]:
        if t in low:
            art.append(t)
    if art:
        out["article_types_detected"] = sorted(set(art))

    return out


def _compact_summary(extracted: dict) -> dict:
    """Pick the high-value fields to merge into the main journal file."""
    flags = extracted.get("flags", {})
    summary = {
        k: extracted[k] for k in
        ("main_text_word_limit", "abstract_word_limit", "reference_limit",
         "figure_limit", "reference_style_detected", "article_types_detected")
        if k in extracted
    }
    required = [name.replace("_required", "")
               for name, on in flags.items()
               if on and name.endswith("_required")]
    if required:
        summary["required_declarations"] = required
    for extra in ("structured_abstract", "graphical_abstract",
                  "double_blind_review", "preprint_policy", "orcid"):
        key = extra if extra in flags else f"{extra}_required"
        if flags.get(key):
            summary[extra] = True
    return summary


# ── Ledger / seeds ─────────────────────────────────────────────────────────────
def load_seeds() -> list[dict]:
    data = _load_json(SEEDS_FILE, {})
    return [s for s in data.get("seeds", []) if s.get("enabled", True)]


def load_ledger() -> dict:
    return _load_json(LEDGER_FILE, {})


def _days_since(iso: str) -> float:
    try:
        then = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - then).total_seconds() / 86400
    except Exception:
        return 1e9


def _due(seed: dict, ledger: dict, max_age_days: int) -> bool:
    rec = ledger.get(seed["slug"])
    if not rec:
        return True
    if rec.get("status") != "ok":
        return True  # retry failures
    return _days_since(rec.get("scraped_at", "")) >= max_age_days


# ── Merge into main journal file ───────────────────────────────────────────────
def merge_into_journal_file(seed: dict, summary: dict, source_url: str,
                            method: str, dry_run: bool) -> str:
    target = JOURNAL_DIR / f"{seed['slug']}.json"
    if target.exists():
        data = _load_json(target, {})
    else:
        data = {
            "title": seed["name"],
            "publisher": seed.get("publisher", ""),
            "schema_version": "2.0",
        }
    data["submission_guidelines"] = summary
    data.setdefault("_provenance", {})
    data["_provenance"]["guidelines"] = {
        "source_url": source_url,
        "scraped_at": _now_iso(),
        "method": method,
        "verification_status": "scraped_unverified",
    }
    if not dry_run:
        _save_json(target, data)
    return str(target)


# ── Core scrape of one seed ────────────────────────────────────────────────────
def scrape_one(seed: dict, delay: float, dry_run: bool,
               force_method: str | None = None) -> dict:
    url = seed["url"]
    method = force_method or seed.get("method", "requests")

    if not _robots_allows(url):
        return {"slug": seed["slug"], "status": "blocked_by_robots", "url": url}

    if method == "playwright":
        html, err = _fetch_playwright(url)
    else:
        html, err = _fetch_requests(url)
        # Fallback: thin/blocked page → try playwright if available.
        if (html is None or len(html) < 1500) and force_method is None:
            html2, err2 = _fetch_playwright(url)
            if html2 and len(html2) >= (len(html or "")):
                html, err, method = html2, None, "playwright"

    if html is None:
        return {"slug": seed["slug"], "status": "fetch_error",
                "error": err, "url": url}

    text = _html_to_text(html)
    if len(text) < 400:
        return {"slug": seed["slug"], "status": "too_thin",
                "chars": len(text), "url": url, "method": method}

    extracted = extract_fields(text)
    summary = _compact_summary(extracted)

    record = {
        "slug": seed["slug"],
        "name": seed["name"],
        "publisher": seed.get("publisher", ""),
        "source_url": url,
        "method": method,
        "scraped_at": _now_iso(),
        "verification_status": "scraped_unverified",
        "text_chars": len(text),
        "extracted": extracted,
        "summary": summary,
    }

    if not dry_run:
        _save_json(SCRAPED_DIR / f"{seed['slug']}.json", record)
        merge_into_journal_file(seed, summary, url, method, dry_run=False)

    fields_found = len(summary)
    return {"slug": seed["slug"], "status": "ok", "method": method,
            "fields": fields_found, "summary": summary, "url": url}


# ── Discovery helper ───────────────────────────────────────────────────────────
def discover(journal: str) -> None:
    print(f"\nDiscovery queries for: {journal}\n" + "-" * 50)
    for tmpl in DISCOVERY_QUERY_TEMPLATES:
        q = tmpl.format(journal=journal)
        print(f"  {q}")
    print("\nPaste into a search engine, then add the resulting author-")
    print("guidelines URL to assets/journal_requirements/_scrape_seeds.json")
    print("with a slug, e.g.:")
    slug = re.sub(r"[^a-z0-9]+", "_", journal.lower()).strip("_")
    print(json.dumps({"name": journal, "slug": slug, "publisher": "",
                      "url": "<paste URL>", "method": "requests",
                      "enabled": True}, ensure_ascii=False))


# ── Status report ──────────────────────────────────────────────────────────────
def status_report() -> None:
    seeds = load_seeds()
    ledger = load_ledger()
    ok = sum(1 for s in seeds if ledger.get(s["slug"], {}).get("status") == "ok")
    print(f"\nSeeds: {len(seeds)}  |  scraped OK: {ok}  |  "
          f"pending/failed: {len(seeds) - ok}")
    print("-" * 64)
    for s in seeds:
        rec = ledger.get(s["slug"], {})
        st = rec.get("status", "never")
        when = rec.get("scraped_at", "")
        nf = rec.get("fields", "")
        age = f"{_days_since(when):.0f}d" if when else ""
        print(f"  {s['slug']:<34} {st:<18} {str(nf):<3} {age}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Polite journal-guideline scraper")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                    help=f"Max journals this run (default {DEFAULT_LIMIT})")
    ap.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                    help=f"Seconds between requests (default {DEFAULT_DELAY})")
    ap.add_argument("--slug", default="", help="Scrape only this seed slug")
    ap.add_argument("--method", choices=["requests", "playwright"], default=None,
                    help="Force fetch backend")
    ap.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE,
                    help=f"Re-scrape only after N days (default {DEFAULT_MAX_AGE})")
    ap.add_argument("--status", action="store_true", help="Show ledger and exit")
    ap.add_argument("--discover", default="", help="Print search queries for a journal name")
    ap.add_argument("--dry-run", action="store_true", help="No writes")
    args = ap.parse_args()

    if args.discover:
        discover(args.discover)
        return
    if args.status:
        status_report()
        return

    seeds = load_seeds()
    if not seeds:
        print(f"No enabled seeds in {SEEDS_FILE}", file=sys.stderr)
        sys.exit(1)

    ledger = load_ledger()

    if args.slug:
        queue = [s for s in seeds if s["slug"] == args.slug]
        if not queue:
            print(f"Slug '{args.slug}' not found in seeds.", file=sys.stderr)
            sys.exit(1)
    else:
        queue = [s for s in seeds if _due(s, ledger, args.max_age_days)]
        queue = queue[: args.limit]

    if not queue:
        print("Nothing due. (Use --slug to force, or lower --max-age-days.)")
        return

    print(f"Scraping {len(queue)} journal(s)  delay={args.delay}s  "
          f"{'[DRY RUN]' if args.dry_run else ''}")
    print("=" * 64)

    results = []
    for i, seed in enumerate(queue, 1):
        print(f"\n[{i}/{len(queue)}] {seed['name']}  ({seed['url']})")
        res = scrape_one(seed, args.delay, args.dry_run, force_method=args.method)
        results.append(res)
        st = res["status"]
        if st == "ok":
            print(f"  OK  via {res['method']}  fields={res['fields']}")
            for k, v in res["summary"].items():
                print(f"      {k}: {v}")
        else:
            print(f"  {st}  {res.get('error', res.get('chars',''))}")

        if not args.dry_run:
            ledger[seed["slug"]] = {
                "status": st,
                "scraped_at": res.get("scraped_at", _now_iso())
                              if st == "ok" else _now_iso(),
                "fields": res.get("fields", 0),
                "method": res.get("method", ""),
                "url": seed["url"],
                "error": res.get("error"),
            }
            _save_json(LEDGER_FILE, ledger)

        if i < len(queue):
            time.sleep(args.delay)

    ok = sum(1 for r in results if r["status"] == "ok")
    print("\n" + "=" * 64)
    print(f"Done: {ok}/{len(results)} OK. "
          f"Ledger: {LEDGER_FILE.relative_to(SKILL_DIR)}")


if __name__ == "__main__":
    main()
