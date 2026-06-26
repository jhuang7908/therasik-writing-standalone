"""
scrape_guidelines_playwright.py
================================
Playwright-based scraper for journal submission guidelines.

Replaces the urllib-based fetching in build_journal_db.py with a full browser,
allowing JavaScript-rendered pages to load completely.

Publisher-specific parsers (structured extraction):
  - Elsevier  (guide-for-authors template)
  - Springer / Nature (for-authors pages)
  - Wiley (onlinelibrary.wiley.com)
  - Oxford / OUP (academic.oup.com)
  - Taylor & Francis (tandfonline.com)
  - Frontiers (frontiersin.org)
  - PLOS (journals.plos.org)
  - Generic fallback (regex on visible text)

Usage:
  python scripts/scrape_guidelines_playwright.py [options]

  --limit N        Process at most N journals (0 = all with empty article_types)
  --publisher P    Only process journals matching publisher substring
  --delay F        Seconds to wait between requests (default: 2.0)
  --headless       Run browser in headless mode (default: True)
  --dry-run        Show what would be scraped without writing files
  --journal-dir D  Path to assets/journal_requirements/

GitHub Actions: install with
  pip install playwright
  playwright install chromium
  playwright install-deps chromium
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

SKILL_DIR   = Path(__file__).resolve().parents[1]
JOURNAL_DIR = SKILL_DIR / "assets" / "journal_requirements"

try:
    from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PWTimeout
except ImportError:
    print("Install: pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)


# ── Regex helpers ──────────────────────────────────────────────────────────────

def _find_numbers_near(text: str, keyword: str, window: int = 120) -> list[int]:
    """Find integers within `window` chars of `keyword` (case-insensitive)."""
    pattern = re.compile(
        rf"(\d[\d,]*)\s*(?:words?)?(?:\s*[-–]?\s*\w+){{0,4}}\s*{re.escape(keyword)}"
        rf"|{re.escape(keyword)}[^.{{0,{window}}}?(\d[\d,]+)",
        re.IGNORECASE,
    )
    nums: list[int] = []
    for m in pattern.finditer(text):
        for g in m.groups():
            if g and g.replace(",", "").isdigit():
                n = int(g.replace(",", ""))
                if 50 < n < 50000:
                    nums.append(n)
    # Also: scan a window around each keyword occurrence
    kw_lower = keyword.lower()
    txt_lower = text.lower()
    pos = 0
    while True:
        idx = txt_lower.find(kw_lower, pos)
        if idx == -1:
            break
        chunk = text[max(0, idx - window): idx + window]
        for m in re.finditer(r"\b(\d[\d,]*)\b", chunk):
            n = int(m.group(1).replace(",", ""))
            if 50 < n < 50000:
                nums.append(n)
        pos = idx + 1
    return sorted(set(nums))


def _extract_word_limit(text: str) -> Optional[int]:
    """Best-effort main text word limit extraction."""
    patterns = [
        r"(?:main\s+text|body|manuscript|article).*?(\d[\d,]+)\s*words?",
        r"(\d[\d,]+)\s*words?\s*(?:maximum|max|limit|or\s+fewer|or\s+less)",
        r"maximum\s+(?:of\s+)?(\d[\d,]+)\s*words?",
        r"not\s+exceed\s+(\d[\d,]+)\s*words?",
        r"up\s+to\s+(\d[\d,]+)\s*words?",
        r"limited\s+to\s+(\d[\d,]+)\s*words?",
        r"word\s+limit.*?(\d[\d,]+)",
        r"(\d[\d,]+)[- ]word\s+limit",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            n = int(m.group(1).replace(",", ""))
            if 200 < n < 30000:
                return n
    return None


def _extract_abstract_limit(text: str) -> Optional[int]:
    patterns = [
        r"abstract.*?(\d[\d,]+)\s*words?",
        r"(\d[\d,]+)\s*words?\s*(?:abstract|summary)",
        r"abstract\s+(?:should\s+be\s+)?(?:no\s+more\s+than|limited\s+to|not\s+exceed|up\s+to)\s+(\d[\d,]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            n = int(m.group(1).replace(",", ""))
            if 50 < n < 1000:
                return n
    return None


def _extract_ref_limit(text: str) -> Optional[int]:
    patterns = [
        r"(?:no\s+more\s+than|maximum\s+of|up\s+to|limit\s+of)\s+(\d+)\s*references?",
        r"(\d+)\s*references?\s*(?:maximum|max|or\s+fewer)",
        r"references?\s+(?:should\s+)?not\s+exceed\s+(\d+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            n = int(m.group(1))
            if 5 < n < 500:
                return n
    return None


def _extract_figure_limit(text: str) -> Optional[int]:
    patterns = [
        r"(?:up\s+to|maximum\s+of|no\s+more\s+than)\s+(\d+)\s*(?:display\s+)?figures?",
        r"(\d+)\s*figures?\s*(?:maximum|max|or\s+fewer)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            n = int(m.group(1))
            if 1 < n < 50:
                return n
    return None


def _extract_figure_dpi(text: str) -> Optional[int]:
    patterns = [
        r"(\d{3})\s*dpi",
        r"resolution\s+of\s+(\d{3})",
        r"(\d{3})\s+dots\s+per\s+inch",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            n = int(m.group(1))
            if 100 < n < 2400:
                return n
    return None


def _extract_ref_style(text: str) -> str:
    styles = [
        (r"\bvancouver\b", "Vancouver (numbered)"),
        (r"\bharvard\b", "Harvard (author-date)"),
        (r"\bapa\b", "APA"),
        (r"\bapa\s*7\b", "APA 7th edition"),
        (r"\bchicago\b", "Chicago"),
        (r"\bacs\b(?!\s+publications)", "ACS (numbered superscript)"),
        (r"\bnlm\b|\bmedline\b", "NLM/MEDLINE"),
        (r"\bnature\s+style\b|superscript\s+number", "Nature (numbered superscript)"),
        (r"\bnumbered\s+reference", "Numbered"),
        (r"\bauthor.{1,5}date\b", "Author-date"),
        (r"\bendnote\b|\bmendelay\b|\bzotero\b", "Any (use reference manager)"),
    ]
    for pat, label in styles:
        if re.search(pat, text, re.IGNORECASE):
            return label
    return ""


# Presence-only declaration flags (search term -> normalized declaration name).
# Mirrors scrape_guidelines_local.py so the cloud scraper produces the same
# richer fields (data availability / ethics / COI / funding / contributions ...).
_DECLARATION_TERMS: dict[str, list[str]] = {
    "data_availability":   ["data availability", "availability of data", "data sharing"],
    "ethics_statement":    ["ethics approval", "ethical approval", "ethics committee",
                            "institutional review board", "irb approval"],
    "competing_interests": ["competing interests", "conflict of interest",
                            "conflicts of interest", "declaration of interest"],
    "funding_statement":   ["funding statement", "funding source", "role of the funding"],
    "author_contributions":["author contributions", "authorship contributions",
                            "credit taxonomy", "credit author"],
    "orcid":               ["orcid"],
}
_OTHER_FLAG_TERMS: dict[str, list[str]] = {
    "structured_abstract": ["structured abstract"],
    "graphical_abstract":  ["graphical abstract"],
    "double_blind_review": ["double-blind", "double blind", "anonymi"],
    "preprint_policy":     ["preprint", "biorxiv", "medrxiv", "arxiv"],
}


def _extract_declarations(text: str) -> dict:
    """Detect required declaration statements + a few policy flags from text."""
    low = text.lower()
    required = [name for name, terms in _DECLARATION_TERMS.items()
               if any(t in low for t in terms)]
    flags = {name: any(t in low for t in terms)
             for name, terms in _OTHER_FLAG_TERMS.items()}
    out: dict = {}
    if required:
        out["required_declarations"] = required
    for k, v in flags.items():
        if v:
            out[k] = True
    return out


def _extract_sections(text: str) -> list[str]:
    common = ["Abstract", "Introduction", "Methods", "Materials and Methods",
              "Results", "Discussion", "Conclusion", "Acknowledgements",
              "Conflict of Interest", "Data Availability", "Author Contributions",
              "References", "Supplementary"]
    found = []
    for s in common:
        if re.search(rf"\b{re.escape(s)}\b", text, re.IGNORECASE):
            found.append(s)
    return found


def _parse_text_to_spec(text: str) -> dict:
    """Generic extraction from any visible text."""
    word_limit = _extract_word_limit(text)
    abs_limit  = _extract_abstract_limit(text)
    ref_limit  = _extract_ref_limit(text)
    fig_limit  = _extract_figure_limit(text)
    dpi        = _extract_figure_dpi(text)
    ref_style  = _extract_ref_style(text)
    sections   = _extract_sections(text)
    declarations = _extract_declarations(text)

    article_spec: dict = {}
    if word_limit:
        article_spec["max_words_main_text"] = word_limit
    if abs_limit:
        article_spec["max_words_abstract"] = abs_limit
    if fig_limit:
        article_spec["max_figures"] = fig_limit
    if ref_limit:
        article_spec["max_references"] = ref_limit
    if sections:
        article_spec["required_sections"] = sections

    return {
        "article_types":   {"Article": article_spec} if article_spec else {},
        "reference_style": ref_style,
        "figure_format":   [f"TIFF ({dpi} dpi min)"] if dpi else [],
        "figure_dpi":      dpi,
        "submission_guidelines": declarations,
    }


# ── Browser helpers ────────────────────────────────────────────────────────────

async def _dismiss_cookies(page: Page):
    """Try common cookie consent dismiss patterns."""
    for selector in [
        "button[id*='accept']", "button[class*='accept']",
        "button[data-testid*='accept']", "#onetrust-accept-btn-handler",
        ".cookie-consent-accept", "[aria-label*='Accept']",
        "button:has-text('Accept')", "button:has-text('Accept all')",
        "button:has-text('I agree')", "button:has-text('Allow all')",
    ]:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible():
                await btn.click()
                await page.wait_for_timeout(800)
                return
        except Exception:
            pass


async def _get_visible_text(page: Page) -> str:
    """Extract all visible text from the current page."""
    return await page.evaluate("""() => {
        const blocks = document.querySelectorAll(
            'article, main, .content, .article-body, ' +
            '[class*="author"], [class*="guideline"], [class*="instruction"], ' +
            '[class*="submission"], .tab-content, #tab-content, ' +
            'section, .section'
        );
        if (blocks.length > 0) {
            return Array.from(blocks).map(el => el.innerText).join('\\n');
        }
        return document.body.innerText;
    }""")


async def _find_guidelines_link(page: Page) -> Optional[str]:
    """Find the 'Instructions for Authors' / 'Author Guidelines' link."""
    keywords = [
        "instructions for authors", "author guidelines", "guide for authors",
        "author instructions", "submission guidelines", "for authors",
        "how to submit", "preparing your manuscript",
    ]
    links = await page.query_selector_all("a")
    candidates: list[tuple[int, str]] = []
    for link in links:
        try:
            text  = (await link.inner_text()).strip().lower()
            href  = await link.get_attribute("href") or ""
            score = 0
            for i, kw in enumerate(keywords):
                if kw in text:
                    score = len(keywords) - i
                    break
            if score:
                candidates.append((score, href))
        except Exception:
            pass
    candidates.sort(reverse=True)
    return candidates[0][1] if candidates else None


async def _safe_navigate(page: Page, url: str, timeout: int = 30000) -> bool:
    """Navigate to URL, return True if successful."""
    try:
        await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        await _dismiss_cookies(page)
        return True
    except Exception:
        return False


# ── Publisher-specific parsers ─────────────────────────────────────────────────

async def parse_elsevier(page: Page, url: str) -> dict:
    """
    Elsevier guide-for-authors pages have structured sidebar sections.
    URL pattern: .../guide-for-authors or elsevier.com/journals/.../guide-for-authors
    """
    # Try to expand all collapsed sections
    try:
        expanders = await page.query_selector_all("[class*='expandable'], [aria-expanded='false']")
        for el in expanders[:20]:
            try:
                await el.click()
                await page.wait_for_timeout(200)
            except Exception:
                pass
    except Exception:
        pass

    text = await _get_visible_text(page)
    result = _parse_text_to_spec(text)

    # Elsevier-specific: Highlights requirement
    if re.search(r"highlight", text, re.IGNORECASE):
        result["highlights"] = "3–5 bullet points, ≤ 85 characters each"

    # Elsevier-specific: Graphical abstract
    if re.search(r"graphical\s+abstract", text, re.IGNORECASE):
        result["graphical_abstract"] = "Required (531 px wide)"

    result["source_url"]  = url
    result["parser_used"] = "elsevier"
    return result


async def parse_springer(page: Page, url: str) -> dict:
    """Springer / Nature for-authors pages."""
    # Click "Submission guidelines" or "Manuscript preparation" tabs if present
    for tab_text in ["Submission guidelines", "Manuscript preparation", "Article types"]:
        try:
            tab = page.locator(f"text='{tab_text}'").first
            if await tab.is_visible():
                await tab.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass

    text = await _get_visible_text(page)
    result = _parse_text_to_spec(text)

    # Nature-specific: Reporting Summary requirement
    if re.search(r"reporting\s+summary|life\s+sciences\s+checklist", text, re.IGNORECASE):
        result["reporting_summary"] = "Required (Nature checklist)"

    result["source_url"]  = url
    result["parser_used"] = "springer_nature"
    return result


async def parse_wiley(page: Page, url: str) -> dict:
    """Wiley Online Library journal pages."""
    # Navigate to "For Authors" tab
    try:
        for_authors = page.locator("a:has-text('For Authors')").first
        if await for_authors.is_visible():
            await for_authors.click()
            await page.wait_for_timeout(1500)
    except Exception:
        pass

    text = await _get_visible_text(page)
    result = _parse_text_to_spec(text)
    result["source_url"]  = url
    result["parser_used"] = "wiley"
    return result


async def parse_oup(page: Page, url: str) -> dict:
    """Oxford University Press academic.oup.com pages."""
    text = await _get_visible_text(page)
    result = _parse_text_to_spec(text)
    result["source_url"]  = url
    result["parser_used"] = "oup"
    return result


async def parse_tandf(page: Page, url: str) -> dict:
    """Taylor & Francis tandfonline.com author submission pages."""
    text = await _get_visible_text(page)
    result = _parse_text_to_spec(text)
    result["source_url"]  = url
    result["parser_used"] = "taylor_francis"
    return result


async def parse_frontiers(page: Page, url: str) -> dict:
    """
    Frontiers pages are well-structured: word limits per article type in tables.
    """
    # Click through article type tabs
    article_types: dict = {}
    try:
        tabs = await page.query_selector_all(".article-type-tab, [data-type], .tab")
        for tab in tabs[:10]:
            try:
                tab_name = await tab.inner_text()
                await tab.click()
                await page.wait_for_timeout(800)
                section_text = await _get_visible_text(page)
                spec = _parse_text_to_spec(section_text).get("article_types", {}).get("Article", {})
                if spec:
                    article_types[tab_name.strip()] = spec
            except Exception:
                pass
    except Exception:
        pass

    text = await _get_visible_text(page)
    base = _parse_text_to_spec(text)
    if article_types:
        base["article_types"] = article_types
    base["open_access_option"] = True
    base["source_url"]  = url
    base["parser_used"] = "frontiers"
    return base


async def parse_plos(page: Page, url: str) -> dict:
    """PLOS journals have structured submission guidelines."""
    text = await _get_visible_text(page)
    result = _parse_text_to_spec(text)
    result["open_access_option"] = True
    result["source_url"]  = url
    result["parser_used"] = "plos"
    return result


async def parse_generic(page: Page, url: str) -> dict:
    """Generic fallback: extract visible text and run regex."""
    text = await _get_visible_text(page)
    result = _parse_text_to_spec(text)
    result["source_url"]  = url
    result["parser_used"] = "generic"
    return result


# ── URL finders ────────────────────────────────────────────────────────────────

def _normalize_issn(data: dict) -> str:
    """Return a hyphen-stripped ISSN string; schema 2.0 stores issn as a list."""
    issn = data.get("issn", "")
    if isinstance(issn, list):
        issn = issn[0] if issn else ""
    return str(issn).replace("-", "")


def _guess_guidelines_url(data: dict) -> Optional[str]:
    """
    Guess the Instructions for Authors URL from journal metadata.
    Returns None if we can't construct a good candidate.
    """
    issn      = _normalize_issn(data)
    publisher = data.get("publisher", "").lower()
    name      = data.get("display_name", "").lower()
    sub_url   = data.get("submission_url", "")

    # Elsevier
    if "elsevier" in publisher or "cell press" in publisher:
        slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
        return f"https://www.elsevier.com/journals/{slug}/{data.get('issn','')}/guide-for-authors"

    # Nature Portfolio
    if "nature portfolio" in publisher or "nature publishing" in publisher:
        slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
        return f"https://www.nature.com/{slug}/for-authors"

    # Springer (non-Nature)
    if "springer" in publisher and "nature" not in publisher:
        if issn:
            return f"https://link.springer.com/journal/{issn}/submission-guidelines"

    # Wiley
    if "wiley" in publisher or "blackwell" in publisher:
        if issn:
            return f"https://onlinelibrary.wiley.com/journal/{issn}"

    # Oxford
    if "oxford" in publisher or "oup" in publisher:
        slug = re.sub(r"[^a-z0-9]+", "", name)
        return f"https://academic.oup.com/{slug}/pages/General_Instructions"

    # Taylor & Francis
    if "taylor" in publisher or "informa" in publisher:
        if issn:
            return f"https://www.tandfonline.com/action/authorSubmission?journalCode={issn}&page=instructions"

    # Frontiers
    if "frontiers" in publisher:
        slug = re.sub(r"^frontiers\s+in\s+", "", name)
        slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
        return f"https://www.frontiersin.org/journals/{slug}/for-authors"

    # PLOS
    if "plos" in publisher or "public library" in publisher:
        slug = re.sub(r"[^a-z0-9]+", "", name.replace("plos ", "plos"))
        return f"https://journals.{slug}.org/s/submission-guidelines"

    return None


def _get_parser(url: str, publisher: str):
    """Select the right parser function based on URL and publisher."""
    url_lower = publisher.lower() + " " + url.lower()
    if "elsevier.com" in url_lower or "cell press" in url_lower:
        return parse_elsevier
    if "nature.com" in url_lower or "springer" in url_lower:
        return parse_springer
    if "wiley" in url_lower or "onlinelibrary" in url_lower:
        return parse_wiley
    if "oup.com" in url_lower or "oxford" in url_lower:
        return parse_oup
    if "tandfonline" in url_lower or "taylor" in url_lower:
        return parse_tandf
    if "frontiers" in url_lower:
        return parse_frontiers
    if "plos" in url_lower:
        return parse_plos
    return parse_generic


# ── Main scraping loop ─────────────────────────────────────────────────────────

async def scrape_one(
    page: Page,
    json_path: Path,
    delay: float = 2.0,
    dry_run: bool = False,
) -> dict:
    """Scrape guidelines for one journal. Returns result dict."""
    data      = json.loads(json_path.read_text(encoding="utf-8"))
    title     = data.get("display_name") or data.get("title") or json_path.stem
    publisher = data.get("publisher", "")

    result = {"file": json_path.name, "title": title, "status": "skipped",
               "parser": "", "fields_found": 0}

    # Skip if already has article_types with word limits (dict or list schema).
    art_types = data.get("article_types") or {}
    has_data = False
    if isinstance(art_types, dict):
        has_data = any(
            isinstance(v, dict) and (
                v.get("max_words_main_text") or v.get("max_words_abstract"))
            for v in art_types.values()
        )
    elif isinstance(art_types, list) and art_types:
        has_data = False  # cloud list form — no structured limits yet
    if has_data:
        result["status"] = "already_complete"
        return result

    # Prefer cloud-pulled URL, then legacy source_url, then heuristic guess.
    guidelines_url = (
        data.get("guidelines_url")
        or data.get("source_url")
        or _guess_guidelines_url(data)
    )
    if not guidelines_url:
        result["status"] = "no_url"
        return result

    # Navigate
    ok = await _safe_navigate(page, guidelines_url)
    if not ok:
        # Try finding link from journal homepage
        homepage = data.get("submission_url", "")
        if homepage:
            ok = await _safe_navigate(page, homepage)
            if ok:
                guidelines_url = await _find_guidelines_link(page) or ""
                if guidelines_url:
                    if not guidelines_url.startswith("http"):
                        from urllib.parse import urljoin
                        guidelines_url = urljoin(homepage, guidelines_url)
                    ok = await _safe_navigate(page, guidelines_url)

    if not ok:
        result["status"] = "navigation_failed"
        return result

    # Parse
    parser_fn = _get_parser(guidelines_url, publisher)
    try:
        scraped = await parser_fn(page, guidelines_url)
    except Exception as e:
        result["status"] = f"parse_error: {e}"
        return result

    await asyncio.sleep(delay)

    # Count useful fields found
    fields = 0
    for art_spec in scraped.get("article_types", {}).values():
        fields += sum(1 for v in art_spec.values() if v)
    if scraped.get("reference_style"):
        fields += 1
    if scraped.get("figure_format"):
        fields += 1
    fields += len(scraped.get("submission_guidelines", {}))

    if fields == 0:
        result["status"] = "no_data_extracted"
        return result

    result["status"]      = "success"
    result["parser"]      = scraped.get("parser_used", "")
    result["fields_found"] = fields

    if not dry_run:
        # Merge scraped data into existing JSON (non-destructive: never
        # overwrite existing non-empty curated values).
        for key in ["article_types", "reference_style", "figure_format",
                    "figure_dpi", "data_availability", "source_url",
                    "highlights", "graphical_abstract", "reporting_summary",
                    "open_access_option", "submission_guidelines"]:
            if scraped.get(key):
                existing = data.get(key)
                if not existing or existing == {} or existing == []:
                    data[key] = scraped[key]

        # Provenance + verification status (matches scrape_guidelines_local.py).
        from datetime import datetime, timezone
        data.setdefault("_provenance", {})
        data["_provenance"]["guidelines"] = {
            "source_url": scraped.get("source_url", guidelines_url),
            "scraped_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "method": "playwright",
            "parser": scraped.get("parser_used", ""),
            "verification_status": "scraped_unverified",
        }

        json_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    return result


async def run_scraper(
    journal_dir: Path,
    limit: int = 0,
    publisher_filter: str = "",
    delay: float = 2.0,
    headless: bool = True,
    dry_run: bool = False,
    verbose: bool = True,
) -> dict:
    files = [f for f in sorted(journal_dir.glob("*.json"))
             if not f.name.startswith("_")]

    # Filter by publisher if requested
    if publisher_filter:
        pf = publisher_filter.lower()
        filtered = []
        for f in files:
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                if pf in d.get("publisher", "").lower():
                    filtered.append(f)
            except Exception:
                pass
        files = filtered

    if limit:
        files = files[:limit]

    summary = {
        "total": len(files), "success": 0, "skipped": 0,
        "no_url": 0, "failed": 0, "dry_run": dry_run,
        "by_parser": {},
    }

    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(headless=headless)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )
        page = await ctx.new_page()

        for i, path in enumerate(files):
            if verbose:
                print(f"  [{i+1}/{len(files)}] {path.stem[:50]}", end=" ... ", flush=True)
            try:
                r = await scrape_one(page, path, delay=delay, dry_run=dry_run)
            except Exception as e:
                r = {"status": f"exception: {e}", "parser": "", "fields_found": 0,
                     "title": path.stem}

            status = r["status"]
            if status == "success":
                summary["success"] += 1
                p = r.get("parser", "generic")
                summary["by_parser"][p] = summary["by_parser"].get(p, 0) + 1
                if verbose:
                    print(f"✓ ({r['fields_found']} fields, parser={p})")
            elif status in ("skipped", "already_complete"):
                summary["skipped"] += 1
                if verbose:
                    print("skip")
            elif status == "no_url":
                summary["no_url"] += 1
                if verbose:
                    print("no URL")
            else:
                summary["failed"] += 1
                if verbose:
                    print(f"✗ {status}")

        await browser.close()

    return summary


def main():
    parser = argparse.ArgumentParser(description="Playwright-based journal guidelines scraper")
    parser.add_argument("--limit",      type=int,   default=0,     help="Max journals to process")
    parser.add_argument("--publisher",  type=str,   default="",    help="Filter by publisher substring")
    parser.add_argument("--delay",      type=float, default=2.0,   help="Seconds between requests")
    parser.add_argument("--no-headless",action="store_true",        help="Show browser window")
    parser.add_argument("--dry-run",    action="store_true",        help="Don't write files")
    parser.add_argument("--journal-dir",default=str(JOURNAL_DIR),  help="Journal JSON directory")
    args = parser.parse_args()

    jdir = Path(args.journal_dir)
    if not jdir.exists():
        print(f"ERROR: {jdir} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Playwright scraper starting — {jdir}")
    if args.dry_run:
        print("  DRY RUN — no files will be modified")
    print()

    summary = asyncio.run(run_scraper(
        jdir,
        limit=args.limit,
        publisher_filter=args.publisher,
        delay=args.delay,
        headless=not args.no_headless,
        dry_run=args.dry_run,
    ))

    print()
    print("=" * 55)
    print("  Results")
    print("=" * 55)
    print(f"  Total processed  : {summary['total']:,}")
    print(f"  Successfully scraped: {summary['success']:,}")
    print(f"  Already complete : {summary['skipped']:,}")
    print(f"  No URL found     : {summary['no_url']:,}")
    print(f"  Failed           : {summary['failed']:,}")
    if summary["by_parser"]:
        print()
        print("  By parser:")
        for p, n in sorted(summary["by_parser"].items(), key=lambda x: -x[1]):
            print(f"    {p:<25} {n:>5}")
    print("=" * 55)


if __name__ == "__main__":
    main()
