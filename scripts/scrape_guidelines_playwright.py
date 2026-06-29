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
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

SKILL_DIR   = Path(__file__).resolve().parents[1]
JOURNAL_DIR = SKILL_DIR / "assets" / "journal_requirements"
CROSSREF_JOURNALS = "https://api.crossref.org/journals/{issn}"
CROSSREF_UA = "therasik-journal-scraper/1.1 (mailto:research@therasik.io)"

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
    text = await page.evaluate("""() => {
        const blocks = document.querySelectorAll(
            'article, main, .content, .article-body, ' +
            '[class*="author"], [class*="guideline"], [class*="instruction"], ' +
            '[class*="submission"], .tab-content, #tab-content, ' +
            'section, .section, [data-test="submission-guidelines"]'
        );
        const joined = blocks.length > 0
            ? Array.from(blocks).map(el => el.innerText).join('\\n')
            : '';
        const body = document.body ? document.body.innerText : '';
        return joined.length > 400 ? joined : body;
    }""")
    return text or ""


async def _find_guidelines_link(page: Page) -> Optional[str]:
    """Find the 'Instructions for Authors' / 'Author Guidelines' link."""
    keywords = [
        "submission-guidelines", "instructions for authors", "author guidelines",
        "guide for authors", "author instructions", "submission guidelines",
        "for authors", "how to submit", "preparing your manuscript",
    ]
    links = await page.query_selector_all("a")
    candidates: list[tuple[int, str]] = []
    for link in links:
        try:
            text  = (await link.inner_text()).strip().lower()
            href  = (await link.get_attribute("href") or "").lower()
            score = 0
            for i, kw in enumerate(keywords):
                if kw in text or kw in href:
                    score = len(keywords) - i + (2 if "submission-guidelines" in href else 0)
                    break
            if score:
                candidates.append((score, await link.get_attribute("href") or ""))
        except Exception:
            pass
    candidates.sort(reverse=True)
    return candidates[0][1] if candidates else None


def _crossref_homepage(issn: str) -> str:
    if not issn:
        return ""
    url = CROSSREF_JOURNALS.format(issn=urllib.parse.quote(issn))
    req = urllib.request.Request(url, headers={"User-Agent": CROSSREF_UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            msg = json.loads(resp.read()).get("message", {})
            homepage = (msg.get("URL") or "").strip()
            if homepage:
                return homepage
    except Exception:
        pass
    return _openalex_homepage(issn)


def _openalex_homepage(issn: str) -> str:
    clean = issn.replace("-", "").strip()
    display = issn if "-" in issn else clean
    for candidate in (display, clean):
        url = f"https://api.openalex.org/sources/issn:{candidate}"
        req = urllib.request.Request(url, headers={"User-Agent": CROSSREF_UA})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                homepage = (json.loads(resp.read()).get("homepage_url") or "").strip()
                if homepage:
                    return homepage.replace("://www.springer.com/", "://link.springer.com/")
        except Exception:
            continue
    return ""


async def _safe_navigate(page: Page, url: str, timeout: int = 45000) -> bool:
    """Navigate to URL, return True if successful."""
    try:
        await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        await _dismiss_cookies(page)
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
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
    for tab_text in [
        "Submission guidelines", "Instructions for Authors",
        "Manuscript preparation", "Article types", "For authors",
    ]:
        try:
            tab = page.locator(f"a:has-text('{tab_text}'), button:has-text('{tab_text}')").first
            if await tab.is_visible():
                await tab.click()
                await page.wait_for_timeout(1200)
        except Exception:
            pass

    if "submission-guidelines" not in page.url.lower():
        try:
            link = page.locator("a[href*='submission-guidelines']").first
            if await link.is_visible():
                await link.click()
                await page.wait_for_timeout(1500)
        except Exception:
            pass

    text = await _get_visible_text(page)
    result = _parse_text_to_spec(text)

    if re.search(r"reporting\s+summary|life\s+sciences\s+checklist", text, re.IGNORECASE):
        result["reporting_summary"] = "Required (Nature checklist)"

    result["source_url"]  = page.url
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


# ── Journal metadata helpers ───────────────────────────────────────────────────

_PUBLISHER_PRIORITY = (
    "elsevier", "springer", "nature", "wiley", "plos", "frontiers",
    "oxford", "oup", "taylor", "cell press",
)


def _resolve_issn(data: dict) -> str:
    for key in ("issn_online", "issn_print", "issn"):
        val = data.get(key)
        if isinstance(val, list):
            val = val[0] if val else ""
        if isinstance(val, str) and val.strip():
            return val.replace("-", "").strip()
    return ""


def _resolve_issn_display(data: dict) -> str:
    raw = data.get("issn_print") or data.get("issn_online") or data.get("issn")
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    return raw.strip() if isinstance(raw, str) else ""


def _journal_name(data: dict) -> str:
    return (data.get("display_name") or data.get("title") or "").strip()


def _has_complete_article_types(data: dict) -> bool:
    art_types = data.get("article_types") or {}
    if not art_types:
        return False
    return any(
        v.get("max_words_main_text") or v.get("max_words_abstract")
        for v in art_types.values()
        if isinstance(v, dict)
    )


def _materialize_from_requirements(data: dict) -> tuple[dict, int]:
    req = data.get("requirements") or {}
    if not req:
        return {}, 0

    article_spec: dict = {}
    word_limits = req.get("word_limits") or {}
    if isinstance(word_limits, dict):
        general = word_limits.get("general")
        if general:
            article_spec["max_words_main_text"] = general
        elif word_limits:
            first = next(iter(word_limits.values()))
            if isinstance(first, int):
                article_spec["max_words_main_text"] = first

    if req.get("abstract_limit"):
        article_spec["max_words_abstract"] = req["abstract_limit"]
    if req.get("reference_limit"):
        article_spec["max_references"] = req["reference_limit"]
    if req.get("required_sections"):
        article_spec["required_sections"] = req["required_sections"]

    scraped: dict = {}
    if article_spec:
        scraped["article_types"] = {"Article": article_spec}
    if req.get("citation_style"):
        scraped["reference_style"] = req["citation_style"]
    if req.get("figure_resolution_dpi"):
        scraped["figure_dpi"] = req["figure_resolution_dpi"]
        scraped["figure_format"] = [f"TIFF ({req['figure_resolution_dpi']} dpi min)"]
    elif req.get("figure_format"):
        scraped["figure_format"] = req["figure_format"]
    if req.get("source_url") and not data.get("source_url"):
        scraped["source_url"] = req["source_url"]

    fields = 0
    for art_spec in scraped.get("article_types", {}).values():
        fields += sum(1 for v in art_spec.values() if v)
    for key in ("reference_style", "figure_format", "figure_dpi"):
        if scraped.get(key):
            fields += 1
    return scraped, fields


def _scrape_priority(data: dict) -> int:
    score = 0
    if data.get("source_url"):
        score += 120
    if data.get("homepage"):
        score += 60
    if data.get("requirements"):
        score += 50
    if _resolve_issn(data):
        score += 30
    pub = (data.get("publisher") or "").lower()
    for i, needle in enumerate(_PUBLISHER_PRIORITY):
        if needle in pub:
            score += 40 - i
            break
    if _journal_name(data):
        score += 10
    return score


def _select_scrape_queue(
    files: list[Path],
    limit: int,
    publisher_filter: str = "",
) -> list[Path]:
    candidates: list[tuple[int, Path]] = []
    pf = publisher_filter.lower().strip()

    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if _has_complete_article_types(data):
            continue
        if pf and pf not in (data.get("publisher") or "").lower():
            continue
        if _scrape_priority(data) <= 0 and not _guess_guidelines_url(data):
            continue
        candidates.append((_scrape_priority(data), path))

    candidates.sort(key=lambda x: (-x[0], x[1].name))
    selected = [p for _, p in candidates]
    return selected[:limit] if limit else selected


# ── URL finders ────────────────────────────────────────────────────────────────

def _guess_guidelines_url(data: dict) -> Optional[str]:
    """
    Guess the Instructions for Authors URL from journal metadata.
    Returns None if we can't construct a good candidate.
    """
    issn      = _resolve_issn(data)
    issn_disp = _resolve_issn_display(data)
    publisher = (data.get("publisher") or "").lower()
    name      = _journal_name(data).lower()
    homepage  = (data.get("homepage") or "").strip()

    if homepage and any(k in homepage.lower() for k in (
        "guide-for-authors", "for-authors", "author-guidelines",
        "submission-guidelines", "instructions-for-authors",
    )):
        return homepage

    if "elsevier" in publisher or "cell press" in publisher:
        slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
        if slug and issn_disp:
            return f"https://www.elsevier.com/journals/{slug}/{issn_disp}/guide-for-authors"
        if slug:
            return f"https://www.elsevier.com/journals/{slug}/guide-for-authors"

    if "nature portfolio" in publisher or "nature publishing" in publisher or (
        name.startswith("nature ") or name == "nature"
    ):
        slug = re.sub(r"^nature\s+", "", name)
        slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-") or "nature"
        return f"https://www.nature.com/{slug}/for-authors"

    if "springer" in publisher and "nature" not in publisher:
        # Springer journal pages use internal numeric IDs, not ISSN — resolve via homepage.
        homepage = (data.get("homepage") or _crossref_homepage(_resolve_issn_display(data) or _resolve_issn(data))).strip()
        if homepage:
            return homepage

    if "wiley" in publisher or "blackwell" in publisher or "wolters kluwer" in publisher:
        if issn:
            return f"https://onlinelibrary.wiley.com/journal/{issn}"

    if "oxford" in publisher or "oup" in publisher:
        slug = re.sub(r"[^a-z0-9]+", "", name)
        if slug:
            return f"https://academic.oup.com/{slug}/pages/General_Instructions"

    if "taylor" in publisher or "informa" in publisher:
        if issn:
            return f"https://www.tandfonline.com/action/authorSubmission?journalCode={issn}&page=instructions"

    if "frontiers" in publisher:
        slug = re.sub(r"^frontiers\s+in\s+", "", name)
        slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
        if slug:
            return f"https://www.frontiersin.org/journals/{slug}/for-authors"

    if "plos" in publisher or "public library" in publisher:
        slug = re.sub(r"[^a-z0-9]+", "", name.replace("plos ", "plos"))
        if slug:
            return f"https://journals.plos.org/{slug}/s/submission-guidelines"

    return None


def _resolve_guidelines_url(data: dict) -> Optional[str]:
    issn = _resolve_issn_display(data) or _resolve_issn(data)
    for candidate in (
        data.get("source_url"),
        (data.get("requirements") or {}).get("source_url"),
        data.get("homepage"),
        _crossref_homepage(issn) if issn else "",
        _guess_guidelines_url(data),
    ):
        if isinstance(candidate, str) and candidate.startswith("http"):
            return candidate
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
    title     = _journal_name(data) or json_path.stem
    publisher = data.get("publisher", "")

    result = {"file": json_path.name, "title": title, "status": "skipped",
               "parser": "", "fields_found": 0}

    if _has_complete_article_types(data):
        result["status"] = "already_complete"
        return result

    promoted, promoted_fields = _materialize_from_requirements(data)
    if promoted_fields > 0 and not dry_run:
        for key, val in promoted.items():
            existing = data.get(key)
            if not existing or existing == {} or existing == []:
                data[key] = val
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        result["status"] = "success"
        result["parser"] = "requirements_promote"
        result["fields_found"] = promoted_fields
        return result

    # Get guidelines URL
    guidelines_url = _resolve_guidelines_url(data)
    if not guidelines_url:
        result["status"] = "no_url"
        return result

    # Navigate
    ok = await _safe_navigate(page, guidelines_url)
    if not ok:
        # Try finding link from journal homepage
        homepage = (data.get("homepage") or data.get("submission_url") or "").strip()
        if homepage.startswith("http"):
            ok = await _safe_navigate(page, homepage)
            if ok:
                found = await _find_guidelines_link(page) or ""
                if found:
                    from urllib.parse import urljoin
                    guidelines_url = found if found.startswith("http") else urljoin(homepage, found)
                    ok = await _safe_navigate(page, guidelines_url)

    if not ok:
        result["status"] = "navigation_failed"
        return result

    if "submission-guidelines" not in page.url.lower() and "guide-for-authors" not in page.url.lower():
        found = await _find_guidelines_link(page)
        if found:
            from urllib.parse import urljoin
            next_url = found if found.startswith("http") else urljoin(page.url, found)
            if await _safe_navigate(page, next_url):
                guidelines_url = next_url

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

    if fields == 0:
        # Persist resolved guidelines URL even when regex extraction fails.
        if not dry_run and guidelines_url:
            data["source_url"] = page.url if ok else guidelines_url
            data["guidelines_scrape_status"] = "partial_no_fields"
            data["guidelines_scraped_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        result["status"] = "no_data_extracted"
        return result

    result["status"]      = "success"
    result["parser"]      = scraped.get("parser_used", "")
    result["fields_found"] = fields

    if not dry_run:
        # Merge scraped data into existing JSON
        for key in ["article_types", "reference_style", "figure_format",
                    "figure_dpi", "data_availability", "source_url",
                    "highlights", "graphical_abstract", "reporting_summary",
                    "open_access_option"]:
            if scraped.get(key):
                # Don't overwrite existing non-empty values
                existing = data.get(key)
                if not existing or existing == {} or existing == []:
                    data[key] = scraped[key]

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
    all_files = [f for f in sorted(journal_dir.glob("*.json")) if f.name != "_index.json"]
    files = _select_scrape_queue(all_files, limit, publisher_filter)
    if verbose:
        print(f"  Queue selected: {len(files)} / {len(all_files)} journals needing guidelines")

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
