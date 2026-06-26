#!/usr/bin/env python3
"""Fetch live NYC Chinese-community sources and update the temporary hub page.

This script is intentionally conservative for the first rollout:
- only uses sources listed in config/nyc_community_event_sources.json
- keeps a 30-day rolling information window by default
- updates insynbio-web-source/us-chinese-life-hub.html in-place
- writes an audit JSON artifact under outputs/nyc_community_events/live_update/
- optionally translates English titles/summaries to Chinese via OpenAI
"""
from __future__ import annotations

import argparse
import html as _html_module
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from nyc_community_events.fetch_sources import fetch_all_sources  # noqa: E402
from nyc_community_events.models import CommunityEvent  # noqa: E402
from nyc_community_events.scoring import score_event  # noqa: E402
from hub_modules_ssot import (  # noqa: E402
    HUB_MODULES,
    enrich_hub_item_dates,
    event_date_from_url,
    infer_module_from_event,
    is_dated_event_url,
    is_deal_item,
    is_hub_junk,
    is_service_info_url,
    module_balance_targets,
    normalize_hub_items,
    split_livelihood_and_deals,
    ensure_module_coverage,
)
from fetch_hub_deals import fetch_deal_items  # noqa: E402
from hub_market_snapshot import fetch_hub_market_snapshot, fetch_hub_weather_snapshot, write_hub_market_json  # noqa: E402

# ─── OpenAI translation layer ─────────────────────────────────────────────────

def _load_openai_key() -> str | None:
    """Load OPENAI_API_KEY from env or .env file in content_generation_tools."""
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:
        return key
    env_file = ROOT / "content_generation_tools" / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val and not val.startswith("${{"):
                    return val
    return None


def translate_items_to_chinese(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Translate English titles and summaries to Chinese using OpenAI gpt-4o-mini.

    Only translates items that appear to be English (not already Chinese).
    Falls back gracefully if no API key or rate-limited.
    """
    api_key = _load_openai_key()
    if not api_key:
        print("[translate] OPENAI_API_KEY not found — skipping translation", flush=True)
        return items

    try:
        import openai  # type: ignore
    except ImportError:
        print("[translate] openai package not installed — skipping translation", flush=True)
        return items

    client = openai.OpenAI(api_key=api_key)

    def _looks_english(text: str) -> bool:
        """Return True if text is predominantly ASCII/English."""
        if not text:
            return False
        cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        return cjk < len(text) * 0.15

    # Collect unique English texts needing translation
    to_translate: list[tuple[str, str]] = []  # (field_key, text)
    seen: dict[str, str] = {}  # text → translation cache

    for item in items:
        for field in ("title_zh", "summary_zh"):
            val = item.get(field, "")
            if _looks_english(val) and val not in seen:
                seen[val] = ""  # placeholder
                to_translate.append((field, val))

    if not to_translate:
        return items

    # Batch translate (max 80 texts per call for token budget)
    unique_texts = list({t for _, t in to_translate})
    batch_size = 60
    for i in range(0, len(unique_texts), batch_size):
        batch = unique_texts[i:i + batch_size]
        numbered = "\n".join(f"{j+1}. {t}" for j, t in enumerate(batch))
        prompt = (
            "你是一位专业的纽约华人社区信息编辑。请将以下英文事件标题和摘要译成简体中文，"
            "保留地名/机构名的英文+中文对照（如 Queens 皇后区），保持简洁专业。\n"
            "每行对应一条，输出相同编号，只输出译文，不要解释。\n\n" + numbered
        )
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.2,
            )
            lines = resp.choices[0].message.content.strip().splitlines()
            for j, line in enumerate(lines):
                line = re.sub(r"^\d+\.\s*", "", line.strip())
                if line and j < len(batch):
                    seen[batch[j]] = line
        except Exception as exc:
            print(f"[translate] OpenAI batch {i//batch_size+1} error: {exc}", flush=True)

    # Apply translations
    for item in items:
        for zh_field, zht_field in (("title_zh", "title_zht"), ("summary_zh", "summary_zht")):
            val = item.get(zh_field, "")
            if _looks_english(val) and seen.get(val):
                item[zh_field] = seen[val]
                item[zht_field] = seen[val]  # Simplified → Traditional: keep same for now

    print(f"[translate] Translated {sum(1 for v in seen.values() if v)} / {len(unique_texts)} texts", flush=True)
    return items

CONFIG_PATH = ROOT / "config" / "nyc_community_event_sources.json"
HUB_ANCHORS_PATH = ROOT / "data" / "community_events" / "hub_channel_anchors.json"
HUB_PATH = ROOT / "insynbio-web-source" / "us-chinese-life-hub.html"
OUT_DIR = ROOT / "outputs" / "nyc_community_events" / "live_update"
HUB_SEARCH_WEB_PATH = ROOT / "insynbio-web-source" / "hub_search_index.json"
HISTORY_DIR = OUT_DIR / "history"
HISTORY_INDEX = OUT_DIR / "run_history.jsonl"

# Evening incremental run: transit / safety / civic alerts only
INCREMENTAL_SOURCE_IDS = frozenset({
    "mta_service_alerts",
    "mta_service",
    "nyc_chinese_minibus",
    "nypd_community",
    "nyc_emergency_mgmt",
    "nyc_311_services",
})

AREA_BY_BOROUGH = {
    "Citywide": ("纽约全市", "紐約全市", "NYC Citywide"),
    "Queens": ("皇后区 Queens", "皇后區 Queens", "Queens"),
    "Brooklyn": ("布鲁克林 Brooklyn", "布魯克林 Brooklyn", "Brooklyn"),
    "Manhattan": ("曼哈顿 Manhattan", "曼哈頓 Manhattan", "Manhattan"),
    "Bronx": ("布朗士 Bronx", "布朗士 Bronx", "Bronx"),
    "Staten Island": ("史泰登岛 Staten Island", "史泰登島 Staten Island", "Staten Island"),
    "": ("纽约全市", "紐約全市", "NYC Citywide"),
}


def _load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _load_channel_anchors() -> list[dict[str, Any]]:
    if not HUB_ANCHORS_PATH.is_file():
        return []
    try:
        data = json.loads(HUB_ANCHORS_PATH.read_text(encoding="utf-8"))
        return [a for a in (data.get("anchors") or []) if isinstance(a, dict) and a.get("url")]
    except Exception as exc:
        print(f"[anchors] load failed: {exc}", flush=True)
        return []


def _source_lookup(cfg: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {src["id"]: src for src in cfg.get("sources", []) if isinstance(src, dict) and src.get("id")}


def _clean_text(text: str, *, limit: int = 220) -> str:
    # Decode HTML entities (&amp; → &, &#038; → &, &nbsp; → space, etc.)
    text = _html_module.unescape(text or "")
    # Strip any remaining HTML tags (just in case)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


_NAV_EXACT = frozenset({
    "home", "about", "contact", "menu", "search", "back", "next", "previous",
    "prev", "more", "less", "expand", "collapse", "see all", "view all",
    "show more", "load more", "newsletter", "subscribe", "follow us",
    "privacy policy", "terms of use", "accessibility", "sitemap", "faq",
    "help", "help center", "login", "log in", "register", "sign in",
    "upcoming events", "past events", "all events", "events calendar",
    "calendar", "categories", "tags", "archive",
    # NYC Parks facilities page section headers / nav links
    "brooklyn", "manhattan", "queens", "bronx", "staten island",
    "nyc parks", "new york city parks", "nyc department of parks",
    # Generic service links (not events)
    "learn to swim", "lap swim hours", "aquatics", "recreation centers",
    "outdoor pools",
    # Parks website global nav items
    "contact us", "for business", "jobs at parks", "facilities",
    "programs", "get involved", "about parks", "volunteer",
    "news & events", "parks news", "press releases", "jobs",
    "permits", "permits & reservations", "rules & regulations",
    "accessibility", "languages", "translate", "español",
    # SBS / Workforce1 nav items
    "businesses", "neighborhoods", "careers at sbs", "additional resources",
    "explore job openings", "preparing for your job search",
    "support for justice-involved individuals", "support for people with disabilities",
    "careers", "career discovery nyc",
    # Access NYC & 311 nav labels
    "city services", "get legal help", "language needs",
    "united states", "know your rights",
    # Contact / call-to-action buttons
    "click to register", "click here to register",
    "announcing municipal immigrant",
    # Generic program listing labels
    "continuing education",
    # Language-selector items (not events)
    "español", "kreyòl ayisyen", "русский", "polski", "italiano",
    "français", "arabic", "한국어", "বাংলা", "עברית",
    # Emergency management generic pages
    "be ready", "recovery",
    # IDNYC / Small biz nav
    "m/wbe certification", "find licenses & permits your business needs",
    "restaurant hiring, onboarding, and training playbook",
    "business owner's bill of rights", "hiring assistance for businesses",
    "customized training grant program", "nyc online directory of certified businesses",
    "support nyc small businesses",
    # nyc.gov global footer nav
    "text-size", "text size", "your government", "contact nyc government",
    "emergency alerts", "digital accessibility resources",
    "website accessibility statement", "am i eligible?",
    "the mayor's office for economic opportunity",
    "learn more at nyc.gov/opportunity",
    "community partners",
    # Duplicate / partial-match nav items
    "benefits",
})

_NAV_CONTAINS = (
    "click here", "sign up for email", "sign up for newsletter",
    "past featured", "featured content", "recurring events",
    "email updates", "mailing list", "back to top", "skip to",
    "types of high school", "transfer school", "waitlist",
    "young adult borough", "feedback", "survey",
    "learn more about free", "find out more about",
    "registration/", "programs/aquatics", "programs/swimming",
)

_NAV_PATTERNS = (
    r"^(click|tap)\s+here",
    r"^sign\s+up\s+for\b",
    r"^(read|learn|find out)\s+more$",
    r"^(see|view|show|load)\s+(all|more)$",
    r"^\w+\s*\|\s*\w+\s*\|\s*\w+",       # breadcrumbs: A | B | C
    r"^(home|about|contact|menu|search|back|next|prev|previous)\s*$",
    r"^\d+$",                              # pure numbers
    r"^https?://",                         # bare URL
    r"^(page|item|result)\s+\d+",
)


# ─── Chinese community relevance gate ────────────────────────────────────────
#
# DESIGN PRINCIPLE: Two types of relevant content
#   TYPE A — "华人社区专属" (Chinese community specific)
#            Content explicitly for or about Chinese/Asian community.
#   TYPE B — "融入主流社会" (Mainstream integration)
#            Services, events, civic activities that help newcomers/immigrants
#            participate in American civic life — even without Chinese keywords.
#            Examples: town halls, library programs, free legal aid, job training,
#            school enrollment, public health, parks & arts events.

# TYPE A: Keywords that directly indicate Chinese/Asian community relevance
_CHINESE_DIRECT = (
    "chinese", "mandarin", "cantonese", "china", "taiwan", "hong kong",
    "asian", "asian american", "immigrants", "immigration", "new american",
    "中文", "华人", "中国", "台湾", "粤语", "普通话", "移民", "华裔",
    "flushing", "法拉盛", "chinatown", "唐人街", "sunset park", "日落公园",
    "elmhurst", "bayside", "corona", "jackson heights",
    "cpc", "aafny", "oca-ny", "oca ny", "committee of 100",
    "charles b wang", "wang community",
)

# TYPE B: Services & civic activities for mainstream integration
# These help Chinese newcomers navigate American institutions directly.
_MAINSTREAM_INTEGRATION = (
    # Government benefits & welfare — immigrants heavily rely on these
    "benefit", "snap", "medicaid", "food stamp", "wic", "housing",
    "health insurance", "health care", "free clinic", "free meal",
    "affordable", "subsidy", "assistance",
    # White card / essential health benefits (白卡, 粮食券, 失业金)
    "white card", "essential plan", "unemployment insurance", "jobless",
    "food bank", "food pantry", "emergency food",
    # Legal & civic rights
    "citizenship", "naturalization", "green card", "visa",
    "legal aid", "legal service", "free legal", "tenant right",
    "voter registration", "election", "town hall", "public hearing",
    "council", "councilmember", "community board", "civic",
    # Education & language integration
    "esl", "english as a second", "english class", "english language",
    "language class", "literacy", "adult education",
    "school enrollment", "school registration", "kindergarten",
    "public school", "after school", "tutoring",
    "library", "reading", "story time", "workshop", "seminar",
    # Senior services — large Chinese senior population
    "senior center", "senior benefit", "aging", "dfta", "scrie", "drie",
    "home care", "case management", "meals on wheels",
    # Pet adoption — community integration activity
    "pet adoption", "adopt a dog", "adopt a cat", "animal care center",
    # Volunteer opportunities — builds community ties
    "volunteer", "volunteering", "nyc service", "community service",
    # Transit alerts — daily life need
    "subway", "service change", "planned work", "bus detour", "mta",
    # Employment & economic integration
    "job training", "employment", "workforce", "career", "resume",
    "small business", "entrepreneur", "business license",
    "tax", "tax prep", "free tax", "vita", "financial",
    # Health & safety
    "vaccination", "vaccine", "health screening", "free health",
    "mental health", "police", "safety", "scam", "fraud", "hate crime",
    "emergency", "preparedness",
    # Arts, parks & civic life — building sense of belonging
    "parks", "free event", "family", "children", "senior",
    "concert", "festival", "parade", "exhibition", "performance",
    "art", "culture", "music", "film", "movie",
    "community event", "open house",
    # Chinese-language equivalents
    "福利", "医保", "食物券", "住房", "入学", "就业",
    "讲座", "展览", "音乐会", "节日", "游行", "社区", "报税",
    "入籍", "绿卡", "法律", "图书馆",
)

# Sources that are always Chinese community relevant
_ALWAYS_RELEVANT_SOURCES = {
    # Chinese community orgs
    "qpl_flushing", "qpl_elmhurst", "nypl_chatham_square", "nypl_flushing",
    "bpl_sunset_park", "bpl_rss", "cpc_chinese_planning", "aafny",
    "charles_b_wang_health", "eventbrite_chinese_nyc", "eventbrite_flushing",
    "tzu_chi_ny", "flushing_chamber",
    # Education: directly serves immigrant/Chinese newcomer needs
    "cuny_continuing_ed", "nyc_adult_literacy", "nyc_libraries_esl",
    "nyc_immigrant_services_edu", "nyc_workforce1",
    # Immigrant affairs: every item from MOIA is inherently relevant for newcomers
    "nyc_moia",
    # Identity card (IDNYC) and legal aid: high immigrant relevance
    "idnyc", "legal_aid_society",
    # Senior services: directly serves older Chinese immigrants
    "nyc_dfta_senior", "nyc_dfta",
    # Pet adoption: community integration activity, high interest
    "nyc_acc_adoption",
    # Government benefits: Medicaid (白卡), SNAP (粮食券), food access
    "nyc_medicaid_snap", "nyc_food_access",
    # Unemployment insurance: critical for job-seekers
    "nys_unemployment",
    # Volunteer: social integration via service
    "nyc_volunteer_service",
    # Transit alerts: essential for daily commuters
    "mta_service_alerts", "nyc_chinese_minibus",
}

# Sources where content needs keyword check to qualify
_NEEDS_RELEVANCE_CHECK = {
    "nyc_doe_family", "nyc_council", "nyc_community_boards",
    "access_nyc", "nyc_hra", "nyc_health_hospitals",
    "nypd_community", "nyc_gov_legal_aid",
}


def _chinese_relevance_score(ev: CommunityEvent, src: dict[str, Any] | None) -> int:
    """Return relevance score 0-3.

    3 = Type A: Directly Chinese/Asian community specific.
    2 = Type B: Mainstream integration services useful to Chinese newcomers.
    1 = Borderline (generic page with weak connection).
    0 = Irrelevant.
    """
    src_id = ev.source or ""

    # Always-relevant sources (华人专属来源) → score 3
    if src_id in _ALWAYS_RELEVANT_SOURCES:
        return 3

    blob = " ".join([
        ev.title or "", ev.description or "", ev.location or "",
        ev.url or "",
        (src or {}).get("name_en", ""), (src or {}).get("name_zh", ""),
    ]).lower()

    # Type A: Direct Chinese/Asian keyword → score 3
    if any(kw in blob for kw in _CHINESE_DIRECT):
        return 3

    # Parks events: free, public, citywide → Type B integration (score 2)
    if "nycgovparks.org" in (ev.url or "") and "/events/" in (ev.url or ""):
        return 2

    # Type B: Mainstream integration services → score 2
    if any(kw in blob for kw in _MAINSTREAM_INTEGRATION):
        return 2

    # Queens/Brooklyn + any civic content → score 2 (Chinese-dense neighborhoods)
    if ev.borough in ("Queens", "Brooklyn") or any(
        place in blob for place in ("queens", "brooklyn", "flushing", "sunset park", "elmhurst", "chinatown")
    ):
        return 2

    # Borderline: generic government page, no clear immigrant utility
    return 1


def _is_nav_junk(title: str) -> bool:
    """Return True if the title looks like a navigation link or UI boilerplate."""
    t = title.strip().lower()
    if not t or len(t) < 4:
        return True
    if t in _NAV_EXACT:
        return True
    for fragment in _NAV_CONTAINS:
        if fragment in t:
            return True
    for pat in _NAV_PATTERNS:
        if re.search(pat, t, re.I):
            return True
    return False


def _is_valid_url(url: str) -> bool:
    """Return False for anchors, root homepages, and generic listing/category pages.

    Strict generic-path filtering applies only to .gov domains.
    Trusted community org URLs are only blocked if they are a bare root homepage.
    """
    if not url or len(url) < 15:
        return False
    if re.match(r'^(?:mailto|tel|javascript):', url, re.I):
        return False
    # Fragment-only anchors on category pages
    if re.search(r'#[A-Za-z]$', url) or re.search(r'#(facilities|programs|opportunities|about|contact)_', url):
        return False
    # Root domain only (no path info)
    if re.match(r'^https?://[^/]+/?$', url):
        return False

    parsed = urlparse(url)
    path = parsed.path.rstrip('/')
    domain = parsed.netloc.lower()

    # Trusted non-gov community org domains: only block bare root (no real path)
    _COMMUNITY_TRUSTED_DOMAINS = (
        "cpc-nyc.org", "cpcnyc.org",
        "aafederation.org", "aafny.org",
        "tzuchi.us", "tzu-chi.us",
        "charlesbwangcc.org", "flushingchamber.com",
        "legalaidnyc.org", "legal-aid.org",
        "advancingjustice-aajc.org", "advancingjustice.org",
        "aabany.org", "oca.org", "committee100.org",
    )
    if any(t in domain for t in _COMMUNITY_TRUSTED_DOMAINS):
        # Allow any path that has at least one real path segment
        return bool(path)

    # .gov / large-portal domains: strict generic-path filter
    _gov_path_re = re.compile(
        r'^/(?:ce(?:/(?:index\.html?|home/?|index\.php))?|'
        r'about|services?|calendar|resources?|'
        r'adult-?learning|continuing-?ed(?:ucation)?(?:/index\.html?)?|'
        r'workforce|esl|learn|help|contact|news|'
        r'jobs?|permits?|businesses?|neighborhoods?|careers?|'
        r'index(?:\.html?|\.php)?|home(?:\.html?)?|main(?:\.html?)?)/?$',
        re.I,
    )
    # For .gov / major portals: also block /events and /programs generic roots
    _gov_events_re = re.compile(r'^/(?:events?|programs?|classes?|courses?)/?$', re.I)

    if ".gov" in domain or "portal.311" in domain:
        if _gov_path_re.match(path) or _gov_events_re.match(path):
            return False
        # NYC.gov root-level index pages (e.g. /site/immigrants/index.page, /site/hra/index.page)
        # Allow deeper sub-section index pages (≥5 path segments) like /site/immigrants/learn-english/index.page
        if re.search(r'/index\.page$', url, re.I):
            path_segments = [p for p in parsed.path.split('/') if p]
            if len(path_segments) <= 4:  # shallow root → block
                return False
            # else: deeper sub-section index pages are allowed (specific program pages)
        # SBS nav-only pages (not events or services)
        if re.search(r'nyc\.gov/site/sbs/(?:businesses|neighborhoods|about)(?:/|$)', url, re.I):
            return False
    else:
        # Non-gov, non-community: moderate filter (block truly generic top-level paths)
        _moderate_path_re = re.compile(
            r'^/(?:about|contact|help|index(?:\.html?)?|home(?:\.html?)?|main(?:\.html?)?)/?$',
            re.I,
        )
        if _moderate_path_re.match(path):
            return False

    # Eventbrite help/support pages (not events)
    if re.search(r'eventbrite\.com/help/', url, re.I):
        return False

    # Library homepage with no event slug
    if re.search(r'(?:queenslibrary|bklynlibrary|nypl)\.org(/learn|/help)?/?$', url, re.I):
        return False

    # Parks list pages that are just category roots (not a specific event)
    if re.search(r'nycgovparks\.org/events$', url, re.I):
        return False

    return True


def _normalize_title(title: str) -> str:
    """Normalize a title for fuzzy dedup comparison."""
    t = title.lower().strip()
    # Remove CANCELED: prefix
    t = re.sub(r'^(canceled|cancelled|postponed)\s*:?\s*', '', t)
    # Remove punctuation except spaces
    t = re.sub(r'[^\w\s]', ' ', t)
    # Collapse whitespace
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def _fuzzy_dedup(events: list[CommunityEvent]) -> list[CommunityEvent]:
    """Cross-source fuzzy deduplication: same date + similar title → keep best one.

    Also caps recurring multi-day events (same normalized title, multiple dates) at
    MAX_RECURRING_OCCURRENCES to prevent a single exhibition/series flooding the feed.
    """
    MAX_RECURRING_OCCURRENCES = 3  # e.g. "Exhibition: Think Global" cap at 3 dates

    # Group by date
    by_date: dict[str, list[CommunityEvent]] = {}
    for ev in events:
        by_date.setdefault(ev.start_date or "9999", []).append(ev)

    seen_keys: set[str] = set()
    result: list[CommunityEvent] = []
    # Track how many times each title-stem (date-independent) has appeared
    title_occurrence: dict[str, int] = {}

    # Prefer Parks/official over Eventbrite/generic
    SOURCE_QUALITY = {
        "nyc_parks_festivals": 10, "nyc_parks_opendata_fallback": 8,
        "eventbrite_chinese_nyc": 6, "eventbrite_flushing": 5,
        "qpl_flushing": 9, "nypl_chatham_square": 9,
    }

    for dt, group in sorted(by_date.items()):
        # Sort by source quality (best first)
        group.sort(key=lambda e: SOURCE_QUALITY.get(e.source, 3), reverse=True)
        for ev in group:
            norm = _normalize_title(ev.title)
            # Key: first 6 significant words + date (same-day dedup)
            words = norm.split()[:6]
            key = f"{dt}|{' '.join(words)}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            # Also check recurring-title cap (date-independent, first 5 words)
            title_stem = " ".join(words[:5])
            if title_occurrence.get(title_stem, 0) >= MAX_RECURRING_OCCURRENCES:
                continue
            title_occurrence[title_stem] = title_occurrence.get(title_stem, 0) + 1
            result.append(ev)

    return result


def _is_first_stage_allowed(ev: CommunityEvent, src: dict[str, Any] | None) -> bool:
    """First rollout source gate: official or formal public-interest institutions only."""
    if not ev.url:
        return False
    source_text = " ".join(
        str(x or "")
        for x in (
            ev.source,
            ev.url,
            (src or {}).get("name_en"),
            (src or {}).get("name_zh"),
            (src or {}).get("notes"),
        )
    ).lower()
    allowed_markers = (
        # NYC government official domains
        "nyc.gov",
        "nycgovparks.org",
        "queenslibrary.org",
        "nypl.org",
        "bklynlibrary.org",
        "cuny.edu",
        "qcc.cuny.edu",
        "laguardia.edu",
        "bmcc.cuny.edu",
        "kingsborough.edu",
        "hostos.cuny.edu",
        "mta.info",
        "nychealthandhospitals.org",
        "access.nyc.gov",
        "council.nyc.gov",
        "nycourts.gov",
        # Legal/aid orgs
        "legalaidnyc.org",
        "legal-aid.org",
        # Verified Chinese/Asian community orgs (non-profit, registered)
        "cpcnyc.org",
        "cpc-nyc.org",       # CPC Chinese-American Planning Council (actual domain)
        "aafny.org",
        "aafederation.org",  # AAFNY federation actual domain
        "tzuchi.us",
        "tzu-chi.us",
        "oca.org",
        "committee100.org",
        # Pet adoption (NYC official)
        "nycacc.app",
        "nyacc.org",
        # Food Bank
        "foodbanknyc.org",
        # MTA transit
        "mta.info",
        "new.mta.info",
        # NYS Dept of Labor (unemployment)
        "dol.ny.gov",
        "labor.ny.gov",
        # NYC Volunteer
        "service.nyc.gov",
        "aabany.org",
        "advancingjustice",
        "charlesbwangcc.org",
        "flushingchamber.com",
        # Eventbrite: only Chinese community search pages are allowed
        # (enforced by source_id check rather than domain alone)
        "eventbrite.com",
        # General qualifiers
        "nonprofit",
        "foundation",
        "community health",
        "public library",
        "public school",
        "official",
        "registered",
    )
    blocked_markers = ("facebook.com", "instagram.com", "tiktok.com", "wechat", "weixin")
    # Eventbrite: only allow items from Chinese-specific Eventbrite sources
    if "eventbrite.com" in (ev.url or "").lower():
        return ev.source in {"eventbrite_chinese_nyc", "eventbrite_flushing"}
    return any(m in source_text for m in allowed_markers) and not any(m in source_text for m in blocked_markers)


def _infer_enclave_area(ev: CommunityEvent) -> tuple[str, str, str] | None:
    """Map event text/location to Chinese enclave label when detectable."""
    blob = " ".join([ev.location, ev.title, ev.description, ev.url]).lower()
    rules: list[tuple[tuple[str, ...], tuple[str, str, str]]] = [
        (("flushing", "11354", "11355", "bowne", "kissena", "college point", "法拉盛"), ("法拉盛 Flushing", "法拉盛 Flushing", "Flushing")),
        (("chinatown", "canal st", "mott st", "bayard", "10013", "唐人街"), ("唐人街 Chinatown", "唐人街 Chinatown", "Chinatown")),
        (("sunset park", "8th ave", "八大道", "11220", "11232", "bay ridge"), ("八大道 Sunset Park", "八大道 Sunset Park", "Sunset Park")),
        (("elmhurst", "11373", "jackson heights", "11372", "艾姆赫斯特", "corona"), ("艾姆赫斯特 Elmhurst", "艾姆赫斯特 Elmhurst", "Elmhurst")),
    ]
    for keys, labels in rules:
        if any(k in blob for k in keys):
            return labels
    return None


def _hub_location_meta(
    ev: CommunityEvent,
    *,
    enclave: tuple[str, str, str] | None,
    area_zh: str,
    area_zht: str,
    area_en: str,
) -> dict[str, str]:
    """Canonical location tag for every hub card: citywide, enclave, or borough."""
    if ev.borough == "Citywide" or area_zh.startswith("纽约全市"):
        return {
            "location_kind": "citywide",
            "location_tag_zh": "全市",
            "location_tag_zht": "全市",
            "location_tag_en": "Citywide",
        }
    if enclave:
        return {
            "location_kind": "enclave",
            "location_tag_zh": area_zh,
            "location_tag_zht": area_zht,
            "location_tag_en": area_en,
        }
    return {
        "location_kind": "borough",
        "location_tag_zh": area_zh,
        "location_tag_zht": area_zht,
        "location_tag_en": area_en,
    }


def _to_hub_item(ev: CommunityEvent, idx: int, src: dict[str, Any] | None) -> dict[str, Any]:
    module = infer_module_from_event(ev, src)
    enclave = _infer_enclave_area(ev)
    area_zh, area_zht, area_en = enclave or AREA_BY_BOROUGH.get(ev.borough, AREA_BY_BOROUGH[""])
    summary = _clean_text(ev.description or f"来自{(src or {}).get('name_zh') or ev.source}的官方/正式机构页面，具体时间、地点、报名要求以官网为准。")
    title = _clean_text(ev.title, limit=120)
    source_name = (src or {}).get("name_zh") or (src or {}).get("name_en") or ev.source
    guide_zh = (
        "1. 点击“直达官方页面”打开原始页面；<br>"
        "2. 页面为英文时，可在浏览器右键选择“翻译成中文”（Chrome）或使用地址栏翻译按鈕；<br>"
        "3. 查找 Registration / RSVP / Apply / Enroll / Contact 等报名入口；<br>"
        "4. 以官网显示的最新时间、地点、费用和要求为准，本平台仅提供中文导读。"
    )
    guide_zht = (
        "1. 點擊“直達官方頁面”打開原始頁面；<br>"
        "2. 頁面為英文時，可在瀏覽器右鍵選擇“翻譯成中文”（Chrome）或使用地址欄翻譯按鈕；<br>"
        "3. 查找 Registration / RSVP / Apply / Enroll / Contact 等報名入口；<br>"
        "4. 以官網顯示的最新時間、地點、費用和要求為準，本平台僅提供中文導讀。"
    )
    guide_en = (
        "1. Open the official page directly;<br>"
        "2. Use Chrome's built-in Translate if the page is in English;<br>"
        "3. Look for Registration / RSVP / Apply / Enroll / Contact entry points;<br>"
        "4. Always follow the latest official details on the source website."
    )
    publish_raw = (ev.published_at or "").strip()
    publish_date = publish_raw[:10] if publish_raw else ""
    url = ev.url or ""
    event_date = event_date_from_url(url) if is_dated_event_url(url) else (
        ev.start_date if ev.start_date and not is_service_info_url(url) else ""
    )
    if not event_date and ev.start_date and is_dated_event_url(url):
        event_date = ev.start_date

    item = {
        "id": f"live_{idx:03d}",
        "module": module,
        "city": "纽约",
        "borough": ev.borough or "Citywide",
        "area_zh": area_zh,
        "area_zht": area_zht,
        "area_en": area_en,
        **_hub_location_meta(ev, enclave=enclave, area_zh=area_zh, area_zht=area_zht, area_en=area_en),
        "location": _clean_text(ev.location or "", limit=160),
        "event_date": event_date,
        "event_time": (ev.start_time or "").strip(),
        "published_at": publish_date,
        "source_published_at": publish_raw if publish_raw and "T" in publish_raw else "",
        "date": event_date,
        "date_kind": "event" if event_date else "service",
        "score": int(ev.score or 0),
        "relevance": _chinese_relevance_score(ev, src),
        "title_zh": title,
        "title_zht": title,
        "title_en": title,
        "summary_zh": f"{summary}（来源类型：{source_name}）",
        "summary_zht": f"{summary}（來源類型：{source_name}）",
        "summary_en": summary,
        "url": ev.url,
        "guide_zh": guide_zh,
        "guide_zht": guide_zht,
        "guide_en": guide_en,
    }
    return enrich_hub_item_dates(item, published_at=publish_date or None)


def _drop_dead_urls(events: list[CommunityEvent], *, max_check: int = 80, timeout: int = 8) -> list[CommunityEvent]:
    """HEAD-check a sample of event URLs and remove any that return 4xx/5xx or timeout.

    Only checks URLs that look suspiciously generic (short path, common-junk suffixes).
    Skips NYC Open Data synthetic URLs and always-trusted NYC.gov links to save time.
    """
    import time as _time
    import requests as _requests

    # Domains we unconditionally trust (skip checking to save time)
    trusted_domains = (
        "nyc.gov", "nycgovparks.org", "queenslibrary.org", "nypl.org",
        "bklynlibrary.org", "cuny.edu", "qcc.cuny.edu", "laguardia.edu",
        "bmcc.cuny.edu", "kingsborough.edu", "mta.info",
    )

    def _should_check(ev: CommunityEvent) -> bool:
        url = ev.url or ""
        if not url.startswith("http"):
            return False
        parsed = urlparse(url)
        if any(d in parsed.netloc for d in trusted_domains):
            return False
        # Only check URLs with a non-trivial path (not just / or /index)
        path = parsed.path.strip('/')
        if len(path) < 5:
            return False
        return True

    to_check = [ev for ev in events if _should_check(ev)]
    # Cap total checks to avoid slowing down the pipeline
    to_check = to_check[:max_check]

    dead_urls: set[str] = set()
    if to_check:
        sess = _requests.Session()
        sess.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"
        )
        checked = 0
        for ev in to_check:
            url = ev.url
            try:
                resp = sess.head(url, timeout=timeout, allow_redirects=True)
                if resp.status_code in (404, 410, 403, 500, 503):
                    dead_urls.add(url)
                    print(f"[url_check] DEAD {resp.status_code}  {url[:80]}", flush=True)
                checked += 1
            except Exception:
                # Timeout or connection error — keep the event (benefit of doubt)
                pass
            _time.sleep(0.2)
        print(f"[url_check] Checked {checked}, removed {len(dead_urls)} dead URLs", flush=True)

    return [ev for ev in events if ev.url not in dead_urls]


def _load_existing_deal_items() -> list[dict[str, Any]]:
    if not HUB_PATH.is_file():
        return []
    html = HUB_PATH.read_text(encoding="utf-8")
    m = re.search(r"const DEAL_ITEMS = (\[.*?\]);", html, re.S)
    if not m:
        return []
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return []


def _load_existing_hub_items() -> list[dict[str, Any]]:
    if not HUB_PATH.is_file():
        return []
    html = HUB_PATH.read_text(encoding="utf-8")
    m = re.search(r"const ITEMS = (\[.*?\]);", html, re.S)
    if not m:
        return []
    return json.loads(m.group(1))


def _load_hub_auto_update(html: str) -> dict[str, str]:
    m = re.search(r"const HUB_AUTO_UPDATE = (\{.*?\});", html, re.S)
    if not m:
        return {"last_full": "", "last_incremental": "", "tz": "America/New_York"}
    return json.loads(m.group(1))


def _merge_incremental_hub_items(
    existing: list[dict[str, Any]],
    fresh: list[dict[str, Any]],
    *,
    max_total: int,
) -> list[dict[str, Any]]:
    """Deprecated wrapper — use merge_hub_items_preserving_index."""
    merged, _ = merge_hub_items_preserving_index(existing, fresh, max_total=max_total)
    return merged


def _norm_hub_url(url: str) -> str:
    return (url or "").strip().rstrip("/")


def _parse_item_index_dt(raw: str | None, fallback_date: str = "") -> datetime | None:
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("America/New_York")
    if raw:
        s = str(raw).strip()
        if "T" in s:
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(tz)
            except ValueError:
                pass
        if len(s) >= 10:
            try:
                return datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=tz)
            except ValueError:
                pass
    if fallback_date and len(fallback_date) >= 10:
        try:
            return datetime.strptime(fallback_date[:10], "%Y-%m-%d").replace(tzinfo=tz)
        except ValueError:
            pass
    return None


def _item_importance(item: dict[str, Any]) -> tuple[int, int]:
    return (int(item.get("relevance") or 0), int(item.get("score") or 0))


def _is_hub_item_new_24h(item: dict[str, Any], *, cut24: datetime, tz: Any) -> bool:
    """True if first seen by scan or official publish time is within rolling 24h (ET)."""
    fi = _parse_item_index_dt(item.get("first_indexed_at"), None)
    if fi and fi.astimezone(tz) >= cut24:
        return True
    pub_raw = (item.get("source_published_at") or item.get("published_at") or "").strip()
    if not pub_raw:
        return False
    pub_dt = _parse_item_index_dt(
        pub_raw if "T" in str(pub_raw) else None,
        str(pub_raw)[:10] if len(str(pub_raw)) >= 10 else None,
    )
    return bool(pub_dt and pub_dt.astimezone(tz) >= cut24)


def _is_hub_item_recent_3d(item: dict[str, Any], *, cut3: datetime, tz: Any, today: date) -> bool:
    """Recent for 3-day featured row: indexed/published in 72h OR event within next 3 days."""
    if is_deal_item(item):
        return False
    fi = _parse_item_index_dt(item.get("first_indexed_at"), None)
    if fi and fi.astimezone(tz) >= cut3:
        return True
    for key in ("source_published_at", "published_at"):
        raw = (item.get(key) or "").strip()
        if not raw:
            continue
        pub_dt = _parse_item_index_dt(raw if "T" in raw else None, raw[:10] if len(raw) >= 10 else None)
        if pub_dt and pub_dt.astimezone(tz) >= cut3:
            return True
    ed = str(item.get("event_date") or item.get("date") or "")[:10]
    if ed:
        try:
            diff = (date.fromisoformat(ed) - today).days
            if 0 <= diff <= 3:
                return True
        except ValueError:
            pass
    return False


def _recent_3d_rank(item: dict[str, Any], *, today: date) -> tuple[int, int, int]:
    ed = str(item.get("event_date") or item.get("date") or "")[:10]
    event_boost = 0
    if ed:
        try:
            diff = (date.fromisoformat(ed) - today).days
            if 0 <= diff <= 3:
                event_boost = 1000 - diff * 100
        except ValueError:
            pass
    fi = _parse_item_index_dt(item.get("first_indexed_at"), None)
    fi_ms = int(fi.timestamp() * 1000) if fi else 0
    return (event_boost, fi_ms, _item_importance(item))


def compute_hub_index_stats(items: list[dict[str, Any]], *, run_dt: datetime | None = None) -> dict[str, Any]:
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("America/New_York")
    now = run_dt or datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    else:
        now = now.astimezone(tz)
    cut24 = now - timedelta(hours=24)
    cut3 = now - timedelta(days=3)
    today = now.date()
    events_7d = 0
    new_24h_items: list[dict[str, Any]] = []
    recent_3d_items: list[dict[str, Any]] = []
    for item in items:
        if is_deal_item(item):
            continue
        if _is_hub_item_new_24h(item, cut24=cut24, tz=tz):
            new_24h_items.append(item)
        if _is_hub_item_recent_3d(item, cut3=cut3, tz=tz, today=today):
            recent_3d_items.append(item)
        if item.get("date_kind") != "event":
            continue
        ed = str(item.get("event_date") or "")[:10]
        if not ed:
            continue
        try:
            diff = (date.fromisoformat(ed) - now.date()).days
        except ValueError:
            continue
        if 0 <= diff <= 7:
            events_7d += 1
    featured = sorted(new_24h_items, key=_item_importance, reverse=True)[:6]
    recent3d = sorted(
        recent_3d_items,
        key=lambda x: _recent_3d_rank(x, today=today),
        reverse=True,
    )[:6]
    return {
        "computed_at": now.strftime("%Y-%m-%d %H:%M ET"),
        "tz": "America/New_York",
        "new_24h": len(new_24h_items),
        "featured_24h_ids": [x.get("id") for x in featured if x.get("id")],
        "recent_3d": len(recent_3d_items),
        "featured_recent3d_ids": [x.get("id") for x in recent3d if x.get("id")],
        "events_7d": events_7d,
        "total": len(items),
        "scan_schedule_et": "07:30 ET daily",
    }


def _hub_item_urls(items: list[dict[str, Any]]) -> set[str]:
    return {_norm_hub_url(i.get("url") or "") for i in items if _norm_hub_url(i.get("url") or "")}


def _load_previous_run_artifact(output_dir: Path) -> dict[str, Any] | None:
    """Load the most recent saved run for delta comparison (before overwriting daily file)."""
    if HISTORY_INDEX.is_file():
        lines = [ln.strip() for ln in HISTORY_INDEX.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if lines:
            try:
                rec = json.loads(lines[-1])
                hist_path = Path(rec.get("artifact_path", ""))
                if hist_path.is_file():
                    return json.loads(hist_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError, TypeError):
                pass
    daily = output_dir / f"live_update_{date.today().strftime('%Y%m%d')}.json"
    if daily.is_file():
        try:
            return json.loads(daily.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    for path in sorted(output_dir.glob("live_update_*.json"), reverse=True):
        if path.name in ("latest_delta.json",):
            continue
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _compute_run_delta(
    previous: dict[str, Any] | None,
    current_items: list[dict[str, Any]],
    index_stats: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    if not previous:
        return {"has_previous": False, "generated_at": generated_at}
    prev_items = previous.get("items") or []
    prev_urls = _hub_item_urls(prev_items)
    curr_urls = _hub_item_urls(current_items)
    new_urls = sorted(curr_urls - prev_urls)
    removed_urls = sorted(prev_urls - curr_urls)
    prev_stats = previous.get("index_stats") or {}
    new_samples: list[dict[str, str]] = []
    by_url = {_norm_hub_url(i.get("url") or ""): i for i in current_items}
    for u in new_urls[:15]:
        it = by_url.get(u) or {}
        new_samples.append({
            "url": u,
            "title_zh": str(it.get("title_zh") or "")[:120],
            "module": str(it.get("module") or ""),
        })
    return {
        "has_previous": True,
        "previous_generated_at": previous.get("generated_at"),
        "generated_at": generated_at,
        "urls_new": len(new_urls),
        "urls_removed": len(removed_urls),
        "urls_unchanged": len(curr_urls & prev_urls),
        "hub_total_prev": len(prev_items),
        "hub_total_now": len(current_items),
        "new_24h_prev": prev_stats.get("new_24h"),
        "new_24h_now": index_stats.get("new_24h"),
        "events_7d_prev": prev_stats.get("events_7d"),
        "events_7d_now": index_stats.get("events_7d"),
        "featured_24h_ids_now": index_stats.get("featured_24h_ids") or [],
        "new_urls_sample": new_samples,
        "removed_urls_sample": removed_urls[:10],
    }


def _persist_run_history(
    output_dir: Path,
    artifact: dict[str, Any],
    index_stats: dict[str, Any],
    delta: dict[str, Any],
) -> Path:
    """Append JSONL index + timestamped history snapshot."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    hist_path = HISTORY_DIR / f"run_{ts}.json"
    slim = {
        k: artifact[k]
        for k in (
            "ok", "update_mode", "generated_at", "sources_configured", "sources_ok",
            "events_fetched", "items_written_to_hub", "source_breakdown",
        )
        if k in artifact
    }
    slim["index_stats"] = index_stats
    slim["delta_vs_previous"] = delta
    slim["item_url_count"] = len(artifact.get("items") or [])
    hist_path.write_text(json.dumps({**artifact, "index_stats": index_stats, "delta_vs_previous": delta},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    index_row = {**slim, "artifact_path": str(hist_path), "run_id": ts}
    with HISTORY_INDEX.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(index_row, ensure_ascii=False) + "\n")
    delta_path = output_dir / "latest_delta.json"
    delta_path.write_text(json.dumps(delta, ensure_ascii=False, indent=2), encoding="utf-8")
    return hist_path


def _format_index_timestamp(raw: str | None) -> str:
    if not raw:
        return ""
    s = str(raw).strip()
    if "T" in s:
        return s[:19].replace("T", " ")
    return s[:10]


def build_hub_search_index(items: list[dict[str, Any]], *, generated_at: str) -> dict[str, Any]:
    """Structured retrieval library: discovery, publish, event, content, location."""
    records: list[dict[str, Any]] = []
    for it in items:
        title = str(it.get("title_zh") or "")
        summary = str(it.get("summary_zh") or "")
        loc_tag = str(it.get("location_tag_zh") or it.get("area_zh") or "")
        fi = _format_index_timestamp(it.get("first_indexed_at"))
        sp_raw = (it.get("source_published_at") or it.get("published_at") or "")
        sp = _format_index_timestamp(str(sp_raw).strip() or None)
        ed = str(it.get("event_date") or "")[:10]
        venue = str(it.get("location") or "")[:160]
        parts = [
            it.get("id"), it.get("module"), title, it.get("title_en"), summary,
            loc_tag, it.get("area_zh"), it.get("borough"), venue, fi, sp, ed, it.get("url"),
        ]
        records.append({
            "id": it.get("id"),
            "module": it.get("module"),
            "title_zh": title,
            "summary_zh": summary[:320],
            "location_tag_zh": loc_tag,
            "location_kind": it.get("location_kind") or "",
            "area_zh": it.get("area_zh") or "",
            "borough": it.get("borough") or "",
            "location": venue,
            "event_date": ed,
            "event_time": str(it.get("event_time") or "").strip(),
            "published_at": str(it.get("published_at") or "")[:10],
            "source_published_at": sp,
            "first_indexed_at": fi,
            "last_seen_at": _format_index_timestamp(it.get("last_seen_at")),
            "date_kind": it.get("date_kind") or "",
            "url": it.get("url") or "",
            "search_text": " ".join(str(x) for x in parts if x).lower(),
        })
    return {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "count": len(records),
        "fields": [
            "first_indexed_at", "source_published_at", "published_at",
            "event_date", "title_zh", "summary_zh", "location_tag_zh", "location", "url",
        ],
        "records": records,
    }


def write_hub_search_index(
    items: list[dict[str, Any]],
    *,
    generated_at: str,
    output_dir: Path,
    web_path: Path | None = None,
) -> Path:
    payload = build_hub_search_index(items, generated_at=generated_at)
    target_web = web_path or HUB_SEARCH_WEB_PATH
    paths = [output_dir / "hub_search_index.json", target_web]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[search_index] Wrote {payload['count']} records → {target_web.name}", flush=True)
    return paths[0]


def merge_hub_items_preserving_index(
    existing: list[dict[str, Any]],
    fresh: list[dict[str, Any]],
    *,
    max_total: int,
    run_dt: datetime | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Merge by URL; preserve first_indexed_at; stamp new URLs at scan time for 24h window."""
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("America/New_York")
    now = run_dt or datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    else:
        now = now.astimezone(tz)
    run_iso = now.isoformat(timespec="seconds")

    by_url: dict[str, dict[str, Any]] = {}
    for item in existing:
        if is_deal_item(item):
            continue
        u = _norm_hub_url(item.get("url") or "")
        if u:
            by_url[u] = dict(item)

    for item in fresh:
        u = _norm_hub_url(item.get("url") or "")
        if not u:
            continue
        old = by_url.get(u)
        merged_item = dict(item)
        if old:
            prev_fi = (old.get("first_indexed_at") or "").strip()
            if not prev_fi:
                for key in ("source_published_at", "published_at", "last_seen_at"):
                    v = (old.get(key) or "").strip()
                    if v:
                        prev_fi = v if "T" in v else f"{v[:10]}T12:00:00"
                        break
                if not prev_fi:
                    ed = str(old.get("event_date") or old.get("date") or "")[:10]
                    if ed:
                        prev_fi = f"{ed}T12:00:00"
            merged_item["first_indexed_at"] = prev_fi
            merged_item["published_at"] = (old.get("published_at") or merged_item.get("published_at") or "")[:10]
            merged_item["source_published_at"] = old.get("source_published_at") or merged_item.get("source_published_at") or ""
        else:
            merged_item["first_indexed_at"] = run_iso
            merged_item["published_at"] = (merged_item.get("published_at") or "")[:10]
            merged_item["source_published_at"] = merged_item.get("source_published_at") or ""
        merged_item["last_seen_at"] = run_iso
        by_url[u] = merged_item

    merged = normalize_hub_items(list(by_url.values()))
    merged, _dropped = split_livelihood_and_deals(merged)
    for idx, it in enumerate(merged, 1):
        it["id"] = f"live_{idx:03d}"
    merged = merged[:max_total]
    stats = compute_hub_index_stats(merged, run_dt=now)
    return merged, stats


def _replace_js_items(
    html: str,
    items: list[dict[str, Any]],
    generated_at: str,
    *,
    update_mode: str = "full",
    index_stats: dict[str, Any] | None = None,
    deal_items: list[dict[str, Any]] | None = None,
) -> str:
    payload = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    deals_payload = json.dumps(deal_items or [], ensure_ascii=False, separators=(",", ":"))
    if re.search(r"const DEAL_ITEMS = \[", html):
        html = re.sub(
            r"const DEAL_ITEMS = \[.*?\];\s*\n",
            f"const DEAL_ITEMS = {deals_payload};\n",
            html,
            count=1,
            flags=re.S,
        )
    else:
        html = re.sub(
            r"(const ITEMS = \[.*?\];)\s*(const HUB_AUTO_UPDATE)",
            rf"\1\nconst DEAL_ITEMS = {deals_payload};\n\2",
            html,
            count=1,
            flags=re.S,
        )
    html = re.sub(
        r"const ITEMS = \[.*?\];\s*(?:const DEAL_ITEMS = \[.*?\];\s*)?const HUB_AUTO_UPDATE",
        f"const ITEMS = {payload};\nconst DEAL_ITEMS = {deals_payload};\nconst HUB_AUTO_UPDATE",
        html,
        count=1,
        flags=re.S,
    )
    mods = json.dumps(HUB_MODULES, ensure_ascii=False, separators=(",", ":"))
    html = re.sub(r"const MODULES = \[.*?\];", f"const MODULES = {mods};", html, count=1, flags=re.S)
    n_ch = len(HUB_MODULES)
    for old in ("11", "8", "5", "4"):
        html = html.replace(f"{old}大民生频道", f"{n_ch}大民生频道")
        html = html.replace(f"{old}大民生頻道", f"{n_ch}大民生頻道")
    html = html.replace("8 Public Channels", f"{n_ch} Public Channels")
    html = html.replace("11 Public Channels", f"{n_ch} Public Channels")
    html = html.replace("5 Public Channels", f"{n_ch} Public Channels")
    html = html.replace("4 Public Channels", f"{n_ch} Public Channels")
    html = re.sub(
        r"📂 \d+大民生频道 · 按类别浏览",
        f"📂 {n_ch}大民生频道 · 按类别浏览",
        html,
    )
    html = re.sub(
        r'"channels_title": "1️⃣ \d+大民生频道"',
        f'"channels_title": "1️⃣ {n_ch}大民生频道"',
        html,
    )
    html = re.sub(
        r'"channels_title": "1️⃣ \d+大民生頻道"',
        f'"channels_title": "1️⃣ {n_ch}大民生頻道"',
        html,
    )
    html = re.sub(
        r'"channels_title": "1️⃣ \d+ Public Channels"',
        f'"channels_title": "1️⃣ {n_ch} Public Channels"',
        html,
    )
    today = date.today().isoformat()
    html = re.sub(r"const today = new Date\('20\d{2}-\d{2}-\d{2}'\);", f"const today = new Date('{today}');", html)
    html = re.sub(r"const todayStr = '20\d{2}-\d{2}-\d{2}';", f"const todayStr = '{today}';", html)
    stamp = f"{generated_at} ET"
    auto = _load_hub_auto_update(html)
    if update_mode == "incremental":
        auto["last_incremental"] = stamp
    else:
        auto["last_full"] = stamp
    auto.setdefault("tz", "America/New_York")
    auto_json = json.dumps(auto, ensure_ascii=False, separators=(",", ":"))
    if re.search(r"const HUB_AUTO_UPDATE = \{", html):
        html = re.sub(r"const HUB_AUTO_UPDATE = \{.*?\};", f"const HUB_AUTO_UPDATE = {auto_json};", html, count=1, flags=re.S)
    else:
        html = html.replace(
            "const UI_STRINGS = {",
            f"const HUB_AUTO_UPDATE = {auto_json};\n\nconst UI_STRINGS = {{",
            1,
        )

    try:
        market = fetch_hub_market_snapshot()
        write_hub_market_json(ROOT / "insynbio-web-source" / "hub_market_snapshot.json", market)
    except Exception as exc:
        print(f"[market] snapshot fetch failed: {exc}", flush=True)
        market = {"as_of": stamp, "tz": "America/New_York", "quotes": []}
    market_json = json.dumps(market, ensure_ascii=False, separators=(",", ":"))
    if re.search(r"const HUB_MARKET_SNAPSHOT = \{", html):
        html = re.sub(
            r"const HUB_MARKET_SNAPSHOT = \{.*?\};",
            f"const HUB_MARKET_SNAPSHOT = {market_json};",
            html,
            count=1,
            flags=re.S,
        )
    else:
        html = html.replace(
            f"const HUB_AUTO_UPDATE = {auto_json};",
            f"const HUB_AUTO_UPDATE = {auto_json};\nconst HUB_MARKET_SNAPSHOT = {market_json};",
            1,
        )

    try:
        weather = fetch_hub_weather_snapshot()
        weather_path = ROOT / "insynbio-web-source" / "hub_weather_snapshot.json"
        weather_path.parent.mkdir(parents=True, exist_ok=True)
        weather_path.write_text(json.dumps(weather, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    except Exception as exc:
        print(f"[weather] snapshot fetch failed: {exc}", flush=True)
        weather = {"as_of": stamp, "tz": "America/New_York", "city": "纽约", "temp_c": None, "code": 0}
    weather_json = json.dumps(weather, ensure_ascii=False, separators=(",", ":"))
    if re.search(r"const HUB_WEATHER_SNAPSHOT = \{", html):
        html = re.sub(
            r"const HUB_WEATHER_SNAPSHOT = \{.*?\};",
            f"const HUB_WEATHER_SNAPSHOT = {weather_json};",
            html,
            count=1,
            flags=re.S,
        )
    else:
        html = html.replace(
            f"const HUB_MARKET_SNAPSHOT = {market_json};",
            f"const HUB_MARKET_SNAPSHOT = {market_json};\nconst HUB_WEATHER_SNAPSHOT = {weather_json};",
            1,
        )
    if weather.get("temp_c") is not None:
        temp_f = round(float(weather["temp_c"]) * 9 / 5 + 32)
        html = re.sub(
            r'(<span class="dash-wx-temp" id="weather-temp">)[^<]*(</span>)',
            rf"\g<1>{temp_f}°F\2",
            html,
            count=1,
        )

    stats = index_stats or compute_hub_index_stats(items)
    stats_json = json.dumps(stats, ensure_ascii=False, separators=(",", ":"))
    if re.search(r"const HUB_INDEX_STATS = \{", html):
        html = re.sub(
            r"const HUB_INDEX_STATS = \{.*?\};",
            f"const HUB_INDEX_STATS = {stats_json};",
            html,
            count=1,
            flags=re.S,
        )
    else:
        html = html.replace(
            f"const HUB_MARKET_SNAPSHOT = {market_json};",
            f"const HUB_MARKET_SNAPSHOT = {market_json};\nconst HUB_INDEX_STATS = {stats_json};",
            1,
        )
    html = re.sub(
        r"<!-- hub-build: [^>]+ -->",
        f"<!-- hub-build: {stamp.replace(' ', 'T')} -->",
        html,
        count=1,
    )
    return html


def run_update(
    *,
    max_items: int,
    deep_dive_pages: int,
    output_dir: Path,
    translate: bool = False,
    update_mode: str = "full",
    hub_dir: Path | None = None,
) -> dict[str, Any]:
    hub_root = hub_dir or (ROOT / "insynbio-web-source")
    hub_path = hub_root / "us-chinese-life-hub.html"
    hub_search_web_path = hub_root / "hub_search_index.json"
    global HUB_PATH, HUB_SEARCH_WEB_PATH
    HUB_PATH = hub_path
    HUB_SEARCH_WEB_PATH = hub_search_web_path
    cfg = _load_config()
    source_filter = INCREMENTAL_SOURCE_IDS if update_mode == "incremental" else None
    fetch_max_pages = 3 if update_mode == "incremental" else deep_dive_pages
    events, logs = fetch_all_sources(
        cfg,
        deep_dive=True,
        max_detail_pages=fetch_max_pages,
        source_ids=source_filter,
    )
    src_by_id = _source_lookup(cfg)
    boroughs = cfg.get("boroughs_preferred") or ["Queens", "Brooklyn", "Manhattan"]
    today_iso = date.today().isoformat()
    # Sources that produce mostly nav/page links rather than dated events.
    # Items from these sources get stricter quality gates (title length, no empty description).
    # NOTE: nyc_hra, idnyc, nyc_moia, nyc_workforce1 are NOT listed — they produce
    # genuinely useful immigrant services / employment content for Chinese newcomers.
    GENERIC_SCRAPER_SOURCES_SET = {
        "nyc_doe_family", "nyc_council", "nyc_community_boards",
        "nyc_311_services",
        "nyc_immigrant_services_edu", "nyc_adult_literacy",
        "nyc_small_business", "nyc_emergency_mgmt",
        "nyc_dfta",   # mostly senior-center nav links, less immigrant-relevant
    }

    def _is_low_quality(ev: CommunityEvent) -> bool:
        """True for generic-scraper items that are clearly page navigation labels."""
        if not ev.title or not ev.url:
            return True
        if not _is_valid_url(ev.url):
            return True
        # Apply HTML entity decoding before nav-junk check (raw titles may have &ntilde; etc.)
        decoded_title = _html_module.unescape(ev.title)
        if _is_nav_junk(decoded_title):
            return True
        # Generic gov scraper items with no real date and no description are page labels
        if (ev.source in GENERIC_SCRAPER_SOURCES_SET
                and ev.start_date == today_iso
                and not (ev.description or "").strip()):
            return True
        # Very short titles from generic scrapers are almost always nav links
        if ev.source in GENERIC_SCRAPER_SOURCES_SET and len(ev.title.strip()) < 8:
            return True
        # Extra nav patterns specific to SBS / Access NYC / 311
        if re.match(r'^(?:businesses?|neighborhoods?|careers?|additional\s+resources?|'
                    r'support\s+for|preparing\s+for|priority\s*\d|united\s+states?)$',
                    ev.title.strip(), re.I):
            return True
        # Phone numbers as titles (e.g. "Call NYC's Hotline at 1-800-...")
        if re.match(r'^call\s+\w', ev.title, re.I) and re.search(r'\d{3}[-.\s]\d{3}', ev.title):
            return True
        # Hotline / Contact page links
        if re.match(r'^(?:call|contact|hotline|phone)\b', ev.title, re.I) and 'hotline' in ev.title.lower():
            return True
        # Language-selector titles (not events)
        if re.match(r'^(?:español|kreyòl|русский|polski|italiano|français|한국어|বাংলা|עברית)$',
                    ev.title.strip(), re.I):
            return True
        # Business licensing / certification nav from SBS
        if ev.source == "nyc_small_business" and re.search(r'certification|licenses?\s+&?\s+permits?|playbook|bill\s+of\s+rights|directory\s+of\s+certified', ev.title, re.I):
            return True
        url_l = (ev.url or "").lower()
        if "/html/dot/" in url_l and re.search(r"truck|freight|motorist", url_l):
            return True
        if "nyc_chinese_minibus" in (ev.source or "") and "/html/dot/" in url_l:
            return True
        return False

    scored = [
        score_event(ev, boroughs_preferred=boroughs)
        for ev in events
        if not _is_low_quality(ev)
    ]

    # ── Chinese relevance gate: drop score-0/1 items that aren't relevant ──────
    MIN_RELEVANCE = 2  # must be immigrant-relevant or higher
    relevance_filtered = [
        ev for ev in scored
        if _chinese_relevance_score(ev, src_by_id.get(ev.source)) >= MIN_RELEVANCE
    ]

    # ── Cross-source fuzzy dedup (same date + near-identical title → keep best) ─
    deduped = _fuzzy_dedup(relevance_filtered)

    # ── URL liveness check: HEAD-verify a sample of URLs to drop 404/dead links ──
    deduped = _drop_dead_urls(deduped, max_check=80, timeout=8)

    first_stage = [
        ev for ev in deduped
        if _is_first_stage_allowed(ev, src_by_id.get(ev.source))
    ]
    # ── Selection: Parks first (primary, reliable, dated), then Chinese-specific ──
    PARKS_SOURCES = {
        "nyc_parks_festivals", "nyc_parks_opendata_fallback", "nyc_parks_rec_shapeup",
    }
    CHINESE_SOURCES = {
        "qpl_flushing", "qpl_elmhurst", "nypl_chatham_square", "nypl_flushing",
        "bpl_sunset_park", "bpl_rss", "cpc_chinese_planning", "aafny",
        "charles_b_wang_health", "eventbrite_chinese_nyc", "eventbrite_flushing",
        "eventbrite_family_nyc", "eventbrite_summer_camp_nyc",
        "nyc_doe_summer",
        "tzu_chi_ny", "flushing_chamber",
        # Education sources (immigrant integration tier 1)
        "cuny_continuing_ed", "nyc_adult_literacy", "nyc_libraries_esl",
        "nyc_immigrant_services_edu", "nyc_workforce1",
        # New welfare/life sources
        "nyc_dfta_senior", "nyc_acc_adoption", "mta_service_alerts",
        "nys_unemployment", "nyc_volunteer_service",
        "nyc_medicaid_snap", "nyc_food_access", "nyc_chinese_minibus",
    }
    PARKS_SCORE_BONUS = 45
    FAMILY_SCORE_BONUS = 40
    CHINESE_SCORE_BONUS = 25

    def _is_family_lifestyle(ev: CommunityEvent) -> bool:
        if ev.source in PARKS_SOURCES:
            return True
        blob = f"{ev.title} {(ev.description or '')} {ev.url or ''}".lower()
        if ev.category in ("recreation", "fitness", "nature", "sports", "pet", "entertainment", "culture"):
            return True
        return any(k in blob for k in (
            "family", "kids", "children", "story time", "playground", "baby", "toddler",
            "亲子", "儿童", "nycgovparks.org/events", "eventbrite_family",
        ))

    def _sort_key(ev: CommunityEvent) -> tuple:
        src_bonus = (PARKS_SCORE_BONUS if ev.source in PARKS_SOURCES
                     else CHINESE_SCORE_BONUS if ev.source in CHINESE_SOURCES
                     else 0)
        blob = f"{ev.title} {(ev.description or '')}".lower()
        family_bonus = FAMILY_SCORE_BONUS if any(
            k in blob for k in ("family", "kids", "children", "story time", "playground", "亲子", "儿童")
        ) else 0
        lang_bonus = 25 if any(kw in blob for kw in ("chinese", "mandarin", "cantonese", "中文", "华人", "粤语")) else 0
        date_bonus = 10 if ev.start_date > date.today().isoformat() else 0
        return (ev.score + src_bonus + family_bonus + lang_bonus + date_bonus, ev.start_date)

    first_stage.sort(key=_sort_key, reverse=True)

    if update_mode == "incremental":
        inc_pick = min(35, max_items)
        selected = first_stage[:inc_pick]
        src_counts = {ev.source: 1 for ev in selected}
    else:
        quotas = module_balance_targets(max_items)
        module_order = [m["zh"] for m in HUB_MODULES]
        src_cap_parks = min(18, max(12, max_items // 7))
        src_cap_chinese = max(10, max_items // 12)
        src_cap = max(8, max_items // 14)

        def _event_module(ev: CommunityEvent) -> str:
            return infer_module_from_event(ev, src_by_id.get(ev.source))

        src_counts: dict[str, int] = {}
        selected: list[CommunityEvent] = []
        selected_ids: set[int] = set()
        module_counts: dict[str, int] = {m: 0 for m in module_order}

        def _try_add(ev: CommunityEvent) -> bool:
            if len(selected) >= max_items or id(ev) in selected_ids:
                return False
            mod = _event_module(ev)
            mod_max = quotas.get(mod, {}).get("max", max_items)
            if module_counts.get(mod, 0) >= mod_max:
                return False
            n = src_counts.get(ev.source, 0)
            cap = (src_cap_parks if ev.source in PARKS_SOURCES
                   else src_cap_chinese if ev.source in CHINESE_SOURCES
                   else src_cap)
            if n >= cap:
                return False
            src_counts[ev.source] = n + 1
            selected_ids.add(id(ev))
            selected.append(ev)
            module_counts[mod] = module_counts.get(mod, 0) + 1
            return True

        def _fill_module(mod: str, minimum: int) -> None:
            for ev in first_stage:
                if module_counts.get(mod, 0) >= minimum or len(selected) >= max_items:
                    break
                if id(ev) in selected_ids or _event_module(ev) != mod:
                    continue
                _try_add(ev)

        for mod in module_order:
            _fill_module(mod, quotas[mod]["min"])

        while len(selected) < max_items:
            added = False
            for mod in module_order:
                if len(selected) >= max_items:
                    break
                if module_counts.get(mod, 0) >= quotas[mod]["max"]:
                    continue
                for ev in first_stage:
                    if id(ev) in selected_ids or _event_module(ev) != mod:
                        continue
                    if _try_add(ev):
                        added = True
                        break
            if not added:
                break

        for ev in first_stage:
            if len(selected) >= max_items:
                break
            if id(ev) not in selected_ids:
                _try_add(ev)

    items = [_to_hub_item(ev, idx + 1, src_by_id.get(ev.source)) for idx, ev in enumerate(selected)]
    items = normalize_hub_items(items)
    from zoneinfo import ZoneInfo

    run_dt = datetime.now(ZoneInfo("America/New_York"))
    existing = _load_existing_hub_items()
    items, index_stats = merge_hub_items_preserving_index(
        existing, items, max_total=max_items, run_dt=run_dt,
    )
    anchors = _load_channel_anchors()
    if anchors:
        before = len(items)
        items = ensure_module_coverage(items, anchors, min_per_module=4, max_total=max_items + 36)
        items = normalize_hub_items(items)
        for idx, it in enumerate(items, 1):
            it["id"] = f"live_{idx:03d}"
        index_stats = compute_hub_index_stats(items, run_dt=run_dt)
        added = len(items) - before
        if added:
            print(f"[anchors] backfilled {added} official channel anchors", flush=True)
    index_stats["sources_scanned"] = len(cfg.get("sources", []))

    if translate and items:
        print(f"[update] Running translation for {len(items)} items…", flush=True)
        items = translate_items_to_chinese(items)

    existing_deals = _load_existing_deal_items()
    _, legacy_deals = split_livelihood_and_deals(_load_existing_hub_items())
    try:
        fresh_deals = fetch_deal_items(max_items=12)
        print(f"[deals] fetched {len(fresh_deals)} promo cards", flush=True)
    except Exception as exc:
        print(f"[deals] fetch failed: {exc}", flush=True)
        fresh_deals = []
    deal_pool = fresh_deals or existing_deals or legacy_deals
    deal_items: list[dict[str, Any]] = []
    seen_deal: set[str] = set()
    for d in deal_pool:
        u = _norm_hub_url(d.get("url") or "")
        if not u or u in seen_deal:
            continue
        seen_deal.add(u)
        deal_items.append(d)
        if len(deal_items) >= 12:
            break
    for idx, d in enumerate(deal_items, 1):
        d["id"] = f"deal_{idx:03d}"

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not hub_path.is_file():
        raise FileNotFoundError(
            f"Hub HTML not found at {hub_path}. "
            "In CI, ensure insynbio-website is checked out to insynbio-web-source/ "
            "(remove empty gitlink submodule dir before checkout)."
        )
    html = hub_path.read_text(encoding="utf-8")
    hub_path.write_text(
        _replace_js_items(
            html, items, generated_at,
            update_mode=update_mode, index_stats=index_stats, deal_items=deal_items,
        ),
        encoding="utf-8",
    )
    search_index_path = write_hub_search_index(
        items,
        generated_at=generated_at,
        output_dir=output_dir,
        web_path=hub_search_web_path,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    previous_artifact = _load_previous_run_artifact(output_dir)
    delta = _compute_run_delta(previous_artifact, items, index_stats, generated_at=generated_at)
    artifact = {
        "ok": True,
        "update_mode": update_mode,
        "generated_at": generated_at,
        "sources_configured": len(cfg.get("sources", [])),
        "sources_fetched": len(source_filter) if source_filter else len(cfg.get("sources", [])),
        "fetch_log_count": len(logs),
        "sources_ok": sum(1 for x in logs if x.get("ok")),
        "events_fetched": len(events),
        "after_quality_filter": len(scored),
        "after_relevance_filter": len(relevance_filtered),
        "after_fuzzy_dedup": len(deduped),
        "events_first_stage_allowed": len(first_stage),
        "items_written_to_hub": len(items),
        "index_stats": index_stats,
        "delta_vs_previous": delta,
        "source_breakdown": dict(sorted(
            {ev.source: src_counts.get(ev.source, 0) for ev in selected}.items(),
            key=lambda x: -x[1]
        )) if selected else {},
        "fetch_logs": logs,
        "items": items,
    }
    out_path = output_dir / f"live_update_{date.today().strftime('%Y%m%d')}.json"
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    hist_path = _persist_run_history(output_dir, artifact, index_stats, delta)
    artifact["artifact_path"] = str(out_path)
    artifact["history_path"] = str(hist_path)
    artifact["search_index_path"] = str(search_index_path)
    if delta.get("has_previous"):
        print(
            f"[delta] vs {delta.get('previous_generated_at')}: "
            f"+{delta.get('urls_new', 0)} new URLs, -{delta.get('urls_removed', 0)} removed, "
            f"24h {delta.get('new_24h_prev')}→{delta.get('new_24h_now')}, "
            f"7d events {delta.get('events_7d_prev')}→{delta.get('events_7d_now')}",
            flush=True,
        )
    else:
        print("[delta] No previous run — baseline recorded", flush=True)
    return artifact


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch NYC sources and update Chinese life hub with optional translation")
    ap.add_argument("--max-items", type=int, default=120, help="Maximum cards to write to the website")
    ap.add_argument("--deep-dive-pages", type=int, default=8, help="Detail pages to follow per supported source")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--translate", action="store_true", help="Translate English titles/summaries to Chinese via OpenAI")
    ap.add_argument(
        "--mode",
        choices=("full", "incremental"),
        default="full",
        help="full=52 sources balanced refresh; incremental=transit/safety merge into existing hub",
    )
    ap.add_argument(
        "--hub-dir",
        type=Path,
        default=None,
        help="Directory containing us-chinese-life-hub.html (default: insynbio-web-source/)",
    )
    args = ap.parse_args()
    result = run_update(
        max_items=args.max_items,
        deep_dive_pages=args.deep_dive_pages,
        output_dir=args.out_dir,
        translate=args.translate,
        update_mode=args.mode,
        hub_dir=args.hub_dir,
    )
    omit = {"items", "fetch_logs"}
    print(json.dumps({k: v for k, v in result.items() if k not in omit}, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
