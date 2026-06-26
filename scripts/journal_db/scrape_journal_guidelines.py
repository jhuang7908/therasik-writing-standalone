"""
Job 1 — Scrape per-journal author guidelines via Playwright.

Strategy (3-step per journal):
  1. CrossRef /journals/{issn}  →  journal homepage URL
  2. Playwright: find "Instructions for Authors" link on homepage
  3. Playwright: extract article_types, word_limits, figure_requirements

Incremental mode (default): only processes journals where article_types == []
Full mode (--full):          re-scrapes every journal

Usage:
    python scripts/journal_db/scrape_journal_guidelines.py
    python scripts/journal_db/scrape_journal_guidelines.py --publisher Elsevier --limit 500
    python scripts/journal_db/scrape_journal_guidelines.py --publisher Frontiers --limit 500
    python scripts/journal_db/scrape_journal_guidelines.py --full --limit 100
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Playwright import (installed at runtime in GHA)
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False

INDEX_PATH = Path("assets/journal_requirements/_index.json")
REQ_DIR    = Path("assets/journal_requirements")
CROSSREF_UA = "InSynBio-JournalDB/2.0 (mailto:jhuang@genomab.com)"
CROSSREF_DELAY = 0.12
NAV_TIMEOUT = 20_000   # ms
MAX_RETRIES = 2

# ── Known URL patterns by system/publisher (fast path — skips CrossRef) ────────
# {system} → lambda(journal_record) → guidelines_url or ""
FAST_URL_PATTERNS: dict[str, callable] = {
    "Frontiers": lambda j: (
        f"https://www.frontiersin.org/journals/"
        f"{_frontiers_slug(j['title'])}/article-types"
    ),
    "MDPI Submission": lambda j: (
        f"https://www.mdpi.com/{_mdpi_slug(j['abbreviation'] or j['title'])}/instructions"
    ),
    "NPG / Snapp": lambda j: (
        f"https://www.nature.com/{_nature_slug(j['title'])}/for-authors"
        if _nature_slug(j['title']) else ""
    ),
}


def _frontiers_slug(title: str) -> str:
    t = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    # remove "frontiers in " prefix
    t = re.sub(r"^frontiers-in-", "", t)
    return t


def _mdpi_slug(abbr: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", abbr.lower()).strip("-")


# Nature journal slug map (title → slug for nature.com URLs)
_NATURE_SLUG_MAP = {
    "nature medicine": "nm", "nature biotechnology": "nbt",
    "nature methods": "nmeth", "nature communications": "ncomms",
    "nature cell biology": "ncb", "nature chemical biology": "nchembio",
    "nature chemistry": "nchem", "nature genetics": "ng",
    "nature immunology": "ni", "nature neuroscience": "nn",
    "nature structural & molecular biology": "nsmb",
    "nature aging": "s43587", "nature cancer": "s43018",
    "nature metabolism": "s42255", "nature microbiology": "nmicrobiol",
    "nature plants": "nplants", "nature physics": "nphys",
    "nature materials": "nmat", "nature nanotechnology": "nnano",
    "nature photonics": "nphoton", "nature energy": "nenergy",
    "nature sustainability": "s41893",
    "nature human behaviour": "s41562",
    "nature biomedical engineering": "s41551",
    "nature computational science": "s43588",
    "nature machine intelligence": "s42256",
    "nature electronics": "s41928",
    "scientific reports": "srep",
    "communications biology": "s42003",
    "communications medicine": "s43856",
}


def _nature_slug(title: str) -> str:
    return _NATURE_SLUG_MAP.get(title.lower().strip(), "")


# ── CrossRef lookup ─────────────────────────────────────────────────────────────

def crossref_journal_url(issns: list[str]) -> str:
    """Return journal homepage URL from CrossRef."""
    for issn in issns:
        issn = issn.strip()
        if not issn:
            continue
        try:
            req = urllib.request.Request(
                f"https://api.crossref.org/journals/{issn}",
                headers={"User-Agent": CROSSREF_UA}
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            url = data.get("message", {}).get("URL", "")
            if url:
                time.sleep(CROSSREF_DELAY)
                return url
        except Exception:
            pass
        time.sleep(CROSSREF_DELAY)
    return ""


# ── Playwright helpers ──────────────────────────────────────────────────────────

# Patterns for finding "Instructions for Authors" / "Author Guidelines" links
GUIDELINES_LINK_PATTERNS = [
    re.compile(p, re.I) for p in [
        r"instructions?\s+for\s+authors?",
        r"author\s+(guidelines?|instructions?|information)",
        r"guide\s+for\s+authors?",
        r"submission\s+guidelines?",
        r"how\s+to\s+submit",
        r"prepare\s+your\s+manuscript",
    ]
]

# Article type patterns
ARTICLE_TYPE_KEYWORDS = [
    "original article", "original research", "research article",
    "review article", "systematic review", "meta-analysis",
    "case report", "case study",
    "short communication", "brief communication", "brief report", "rapid communication",
    "letter", "letter to the editor", "correspondence",
    "commentary", "opinion", "perspective", "viewpoint",
    "editorial", "book review", "erratum", "correction",
    "methods", "methodology", "technical note", "protocol",
    "hypothesis", "concept paper",
]
_AT_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in ARTICLE_TYPE_KEYWORDS) + r")\b",
    re.I,
)

# Word count patterns: "3000 words", "up to 4,500 words", "≤5000 words"
_WORD_RE = re.compile(
    r"(?:up\s+to|maximum|max\.?|≤|no\s+more\s+than)?\s*"
    r"(\d[\d,]*)\s*words?",
    re.I,
)

# Figure patterns
_FIG_RE = re.compile(
    r"(?:tiff|eps|pdf|png|jpeg?)\s*[\(\,\/]?\s*(?:300|600|1200)\s*dpi",
    re.I,
)

# Reference limit
_REF_RE = re.compile(
    r"(?:up\s+to|maximum|max\.?|≤|no\s+more\s+than)?\s*(\d+)\s*references?",
    re.I,
)


def find_guidelines_url(page, home_url: str) -> str:
    """Navigate to home_url and find author guidelines link."""
    try:
        page.goto(home_url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
    except PWTimeout:
        return ""
    except Exception:
        return ""

    # Try all <a> tags
    links = page.query_selector_all("a[href]")
    for link in links:
        try:
            text = (link.inner_text() or "").strip()
            href = link.get_attribute("href") or ""
            for pat in GUIDELINES_LINK_PATTERNS:
                if pat.search(text) or pat.search(href):
                    if href.startswith("http"):
                        return href
                    elif href.startswith("/"):
                        from urllib.parse import urlparse
                        base = urlparse(home_url)
                        return f"{base.scheme}://{base.netloc}{href}"
        except Exception:
            continue
    return ""


def extract_guidelines(page, url: str) -> dict:
    """Navigate to guidelines page and extract structured data."""
    result = {
        "article_types": [],
        "word_limits": {},
        "figure_requirements": "",
        "reference_limit": None,
        "cover_letter_required": None,
        "guidelines_url": url,
        "scraped_at": _now(),
    }
    if not url:
        return result

    try:
        page.goto(url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        # JS-heavy publishers (Frontiers): wait for content or network settle.
        if "frontiersin.org" in url:
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            page.wait_for_timeout(1500)
    except (PWTimeout, Exception):
        return result

    # Get all text
    try:
        text = page.inner_text("body")
    except Exception:
        text = ""

    # Fallback: Playwright often sees <200 chars on Frontiers SPAs.
    if len(text) < 400:
        text = _fetch_text_requests(url) or text

    # Article types
    found_types = set()
    for m in _AT_RE.finditer(text):
        found_types.add(m.group(1).title())
    result["article_types"] = sorted(found_types)

    # Word limits — take the most common / largest numeric value near "words"
    word_matches = _WORD_RE.findall(text)
    if word_matches:
        counts = [int(w.replace(",", "")) for w in word_matches]
        # Heuristic: main article limit is likely the largest up to 15000
        valid = [c for c in counts if 500 <= c <= 15000]
        if valid:
            result["word_limits"]["main_text"] = max(set(valid), key=valid.count)

    # Figure requirements
    fig_matches = _FIG_RE.findall(text)
    if fig_matches:
        result["figure_requirements"] = "; ".join(dict.fromkeys(fig_matches))

    # Reference limit
    ref_m = _REF_RE.search(text)
    if ref_m:
        result["reference_limit"] = int(ref_m.group(1))

    # Cover letter
    if re.search(r"cover\s+letter\s+(?:is\s+)?(?:required|mandatory|must)", text, re.I):
        result["cover_letter_required"] = True
    elif re.search(r"cover\s+letter", text, re.I):
        result["cover_letter_required"] = "optional"

    decl = _extract_declarations(text)
    if decl:
        result["submission_guidelines"] = decl

    return result


def _fetch_text_requests(url: str) -> str:
    """Lightweight fallback when Playwright sees an empty SPA shell."""
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": CROSSREF_UA, "Accept-Language": "en"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    except Exception:
        return re.sub(r"<[^>]+>", " ", raw)


_DECL_TERMS: dict[str, list[str]] = {
    "data_availability":   ["data availability", "availability of data", "data sharing"],
    "ethics_statement":    ["ethics approval", "ethical approval", "ethics committee", "irb"],
    "competing_interests": ["competing interests", "conflict of interest", "conflicts of interest"],
    "funding_statement":   ["funding statement", "funding source", "role of the funding"],
    "author_contributions":["author contributions", "credit taxonomy", "credit author"],
    "orcid":               ["orcid"],
}
_FLAG_TERMS: dict[str, list[str]] = {
    "structured_abstract": ["structured abstract"],
    "graphical_abstract":  ["graphical abstract"],
    "double_blind_review": ["double-blind", "double blind"],
    "preprint_policy":     ["preprint", "biorxiv", "medrxiv"],
}


def _extract_declarations(text: str) -> dict:
    low = text.lower()
    required = [n for n, terms in _DECL_TERMS.items() if any(t in low for t in terms)]
    out: dict = {}
    if required:
        out["required_declarations"] = required
    for name, terms in _FLAG_TERMS.items():
        if any(t in low for t in terms):
            out[name] = True
    ref_styles = []
    for pat, sid in [(r"\bvancouver\b", "vancouver"), (r"\bharvard\b", "harvard"),
                     (r"\bapa\b", "apa"), (r"\bama\b", "ama")]:
        if re.search(pat, low) and sid not in ref_styles:
            ref_styles.append(sid)
    if ref_styles:
        out["reference_style_detected"] = ref_styles
    return out


def _apply_provenance(rec: dict, guidelines_url: str, method: str = "playwright") -> None:
    rec.setdefault("_provenance", {})
    rec["_provenance"]["guidelines"] = {
        "source_url": guidelines_url,
        "scraped_at": _now(),
        "method": method,
        "parser": "journal_db",
        "verification_status": "scraped_unverified",
    }


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Main ────────────────────────────────────────────────────────────────────────

def load_journal_record(slug: str) -> dict | None:
    path = REQ_DIR / f"{slug}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_journal_record(slug: str, rec: dict):
    path = REQ_DIR / f"{slug}.json"
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publisher", default="",
                    help="Filter by publisher name substring (case-insensitive)")
    ap.add_argument("--limit", type=int, default=200,
                    help="Max journals to process per run (default 200)")
    ap.add_argument("--full", action="store_true",
                    help="Re-scrape all journals, not just missing article_types")
    ap.add_argument("--system", default="",
                    help="Filter by submission system (e.g. Frontiers)")
    args = ap.parse_args()

    if not PLAYWRIGHT_OK:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    if not INDEX_PATH.exists():
        print(f"ERROR: {INDEX_PATH} not found.")
        sys.exit(1)

    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    print(f"Total journals in index: {len(index)}")

    # ── Filter ─────────────────────────────────────────────────────────────────
    candidates = []
    for entry in index:
        slug = entry["slug"]
        rec = load_journal_record(slug)
        if not rec:
            continue

        # Publisher filter
        if args.publisher:
            pub = rec.get("publisher", "").lower()
            cr_pub = rec.get("crossref_publisher", "").lower()
            if (args.publisher.lower() not in pub and
                    args.publisher.lower() not in cr_pub and
                    args.publisher.lower() not in rec.get("submission_system", "").lower()):
                continue

        # System filter
        if args.system:
            if args.system.lower() not in rec.get("submission_system", "").lower():
                continue

        # Incremental: skip journals that already have article_types
        if not args.full and rec.get("article_types"):
            continue

        # Skip unknown system (no portal to scrape)
        if rec.get("submission_system") == "unknown":
            continue

        candidates.append((slug, rec))

    print(f"Candidates after filter: {len(candidates)} (limit: {args.limit})")
    candidates = candidates[: args.limit]

    # ── Scrape ─────────────────────────────────────────────────────────────────
    stats = {"ok": 0, "no_url": 0, "no_guidelines": 0, "error": 0}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (compatible; InSynBio-JournalDB/2.0)",
            viewport={"width": 1280, "height": 900},
        )
        page = ctx.new_page()
        page.set_default_timeout(NAV_TIMEOUT)

        for i, (slug, rec) in enumerate(candidates):
            print(f"[{i+1}/{len(candidates)}] {rec.get('title', slug)[:60]}", flush=True)

            issns = rec.get("issn", [])
            system = rec.get("submission_system", "")
            title  = rec.get("title", "")

            # Step 1: derive or fetch homepage URL
            home_url = ""
            fast_fn = FAST_URL_PATTERNS.get(system)
            if fast_fn:
                # Fast path: known pattern → go directly to guidelines page
                guidelines_url = fast_fn(rec)
                home_url = guidelines_url  # treat as final URL
            else:
                guidelines_url = ""
                home_url = crossref_publisher(issns) if issns else ""

            # Step 2: find guidelines link (only if we have a homepage, not a direct URL)
            if home_url and not fast_fn:
                guidelines_url = find_guidelines_url(page, home_url)
                if not guidelines_url:
                    print(f"  ↳ No guidelines link found on {home_url}")
                    stats["no_guidelines"] += 1
                    continue

            if not guidelines_url:
                print(f"  ↳ No URL available")
                stats["no_url"] += 1
                continue

            # Step 3: extract data
            print(f"  ↳ {guidelines_url[:80]}", flush=True)
            try:
                extracted = extract_guidelines(page, guidelines_url)
                # Non-destructive merge: fill empty fields only.
                for key, val in extracted.items():
                    if key == "submission_guidelines":
                        existing = rec.get(key) or {}
                        if isinstance(existing, dict) and isinstance(val, dict):
                            merged = dict(existing)
                            for dk, dv in val.items():
                                if dk not in merged or not merged[dk]:
                                    merged[dk] = dv
                            if merged:
                                rec[key] = merged
                        elif not existing:
                            rec[key] = val
                    elif val is not None and val != "" and val != [] and val != {}:
                        if not rec.get(key):
                            rec[key] = val
                _apply_provenance(rec, guidelines_url)
                save_journal_record(slug, rec)
                n_types = len(extracted.get("article_types", []))
                print(f"  ✓ {n_types} article types | "
                      f"words: {extracted.get('word_limits',{}).get('main_text','?')} | "
                      f"refs: {extracted.get('reference_limit','?')}")
                stats["ok"] += 1
            except Exception as e:
                print(f"  ✗ Error: {e}")
                stats["error"] += 1

            time.sleep(0.5)

        page.close()
        ctx.close()
        browser.close()

    print(f"\nDone. ok={stats['ok']} no_url={stats['no_url']} "
          f"no_guidelines={stats['no_guidelines']} error={stats['error']}")
    return stats["ok"]


def crossref_publisher(issns: list[str]) -> str:
    """Return CrossRef journal URL (reused from build_requirements)."""
    for issn in issns:
        try:
            req = urllib.request.Request(
                f"https://api.crossref.org/journals/{issn.strip()}",
                headers={"User-Agent": CROSSREF_UA}
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
            url = data.get("message", {}).get("URL", "")
            if url:
                time.sleep(CROSSREF_DELAY)
                return url
        except Exception:
            pass
        time.sleep(CROSSREF_DELAY)
    return ""


if __name__ == "__main__":
    n = main()
    sys.exit(0 if n >= 0 else 1)
