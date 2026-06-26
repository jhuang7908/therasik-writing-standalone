"""Multi-source community event fetcher with detail-page deep-dive capability.

Supports 30+ sources defined in config/nyc_community_event_sources.json.
Handles HTML list pages, RSS/Atom feeds, detail page recursion, 30-day
rolling window, deduplication, and per-source timeout control.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from nyc_community_events.models import CommunityEvent

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "nyc_community_event_sources.json"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}

PARKS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

PARKS_BASE = "https://www.nycgovparks.org"

_EVENT_PATH = re.compile(
    r'href="(/events/(20\d{2})/(\d{2})/(\d{2})/([^"?#]+))"[^>]*>([^<]+)</a>',
    re.I,
)
_LOCATION_SNIP = re.compile(r'class="[^"]*location[^"]*"[^>]*>([^<]{3,120})', re.I)
_TIME_SNIP = re.compile(r'class="[^"]*time[^"]*"[^>]*>([^<]{3,40})', re.I)


# ─── Borough inference ────────────────────────────────────────────────────────

BOROUGH_HINTS = (
    ("Queens", ("queens", "flushing", "bowne", "kissena", "corona", "elmhurst",
                "forest hills", "bayside", "fresh meadows", "jackson heights",
                "woodside", "rego park", "jamaica")),
    ("Brooklyn", ("brooklyn", "sunset park", "prospect", "bensonhurst",
                  "bay ridge", "dyker", "flatbush", "8th ave")),
    ("Manhattan", ("manhattan", "chinatown", "central park", "battery",
                   "lower east side", "canal st", "east broadway")),
    ("Bronx", ("bronx", "pelham", "van cortlandt")),
    ("Staten Island", ("staten", "snug harbor")),
)


def infer_borough(text: str) -> str:
    blob = text.lower()
    for boro, kws in BOROUGH_HINTS:
        if any(k in blob for k in kws):
            return boro
    return ""


# ─── Deduplication ────────────────────────────────────────────────────────────

def _event_fingerprint(ev: CommunityEvent) -> str:
    key = f"{ev.title.lower().strip()}|{ev.start_date}|{ev.url}"
    return hashlib.md5(key.encode()).hexdigest()


def deduplicate(events: list[CommunityEvent]) -> list[CommunityEvent]:
    seen: set[str] = set()
    out: list[CommunityEvent] = []
    for ev in events:
        fp = _event_fingerprint(ev)
        if fp in seen:
            continue
        seen.add(fp)
        out.append(ev)
    return out


# ─── 30-day window filter ─────────────────────────────────────────────────────

def within_horizon(ev: CommunityEvent, *, today: date, days: int) -> bool:
    try:
        start = datetime.strptime(ev.start_date, "%Y-%m-%d").date()
    except ValueError:
        return False
    end = today + timedelta(days=days)
    return today <= start <= end


def within_retention(
    ev: CommunityEvent,
    *,
    today: date,
    retention_days: int = 30,
    future_horizon_days: int | None = None,
) -> bool:
    try:
        start = datetime.strptime(ev.start_date, "%Y-%m-%d").date()
    except ValueError:
        return False
    cutoff = today - timedelta(days=retention_days)
    future = int(future_horizon_days if future_horizon_days is not None else retention_days)
    future_limit = today + timedelta(days=future)
    return cutoff <= start <= future_limit


def _is_waf_challenge(resp: "requests.Response") -> bool:
    """Detect AWS WAF or Cloudflare bot-challenge pages."""
    if resp.status_code not in (200, 202, 204):
        return False
    if len(resp.text) < 5000 and any(
        marker in resp.text for marker in (
            "awsWafCoo", "AWSManagedRules", "__CFDUID", "cf-chl-",
            "challenge-platform", "jschl_vc", "window.awsWaf",
        )
    ):
        return True
    return False


# ─── NYC Open Data Parks fallback ─────────────────────────────────────────────

# Primary: NYC Parks Public Events – Upcoming 14 Days (w3wp-dpdi)
# Fallback: NYC Parks Events Listing (fudw-fgrp, may contain recent records)
PARKS_OD_UPCOMING_ENDPOINT = (
    "https://data.cityofnewyork.us/resource/w3wp-dpdi.json"
    "?%24limit=200"
)
PARKS_OD_ENDPOINT = (
    "https://data.cityofnewyork.us/resource/fudw-fgrp.json"
    "?%24limit=500&%24order=date+DESC"
    "&%24select=event_id,event_name,date,end_date,borough,location"
)


def _fetch_parks_open_data(
    session: "requests.Session",
    today: date,
    app_token: str | None = None,
) -> list[CommunityEvent]:
    """Fetch Parks events from NYC Open Data (WAF bypass).

    Primary: w3wp-dpdi (upcoming 14 days; needs NYC_OPEN_DATA_TOKEN).
    Fallback: fudw-fgrp with date filter (field is ``title``, not event_name).
    """
    headers: dict[str, str] = {
        "Accept": "application/json",
        "User-Agent": PARKS_HEADERS.get("User-Agent", DEFAULT_HEADERS["User-Agent"]),
    }
    if app_token:
        headers["X-App-Token"] = app_token

    window_start = (today - timedelta(days=7)).isoformat()
    window_end = (today + timedelta(days=60)).isoformat()
    where_clause = f"date >= '{window_start}T00:00:00' AND date <= '{window_end}T23:59:59'"

    rows: list[dict] = []
    source_id = "nyc_parks_opendata_fallback"
    for endpoint, params in (
        ("https://data.cityofnewyork.us/resource/w3wp-dpdi.json", {"$limit": "400"}),
        (
            "https://data.cityofnewyork.us/resource/fudw-fgrp.json",
            {"$limit": "500", "$order": "date DESC", "$where": where_clause},
        ),
    ):
        try:
            resp = session.get(endpoint, headers=headers, params=params, timeout=25)
            if resp.status_code == 200:
                batch = resp.json()
                if isinstance(batch, list) and batch:
                    rows = batch
                    break
        except Exception:
            continue
    if not rows:
        return []

    events: list[CommunityEvent] = []
    seen: set[str] = set()
    for row in rows:
        name = str(
            row.get("title") or row.get("event_name") or row.get("name") or row.get("eventname") or ""
        ).strip()
        if not name or len(name) < 4:
            continue
        dt_raw = str(row.get("date") or row.get("date_and_time") or row.get("start_date") or "")
        ev_date = dt_raw[:10] if len(dt_raw) >= 10 else today.isoformat()
        if not (window_start <= ev_date <= window_end):
            continue

        borough = str(row.get("borough") or "")
        location = str(row.get("location") or row.get("location_description") or "")
        event_id = str(row.get("event_id") or "")

        key = f"{ev_date}|{name.lower()}"
        if key in seen:
            continue
        seen.add(key)

        if event_id and len(ev_date) >= 10:
            event_url = f"{PARKS_BASE}/events/{ev_date.replace('-', '/')}/{event_id}"
        else:
            slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            event_url = f"{PARKS_BASE}/events/{ev_date.replace('-', '/')}/{slug}"

        events.append(CommunityEvent(
            title=name,
            start_date=ev_date,
            source=source_id,
            url=event_url,
            location=f"{location}, {borough}".strip(", "),
            borough=borough,
            category="recreation",
            is_free=True,
            description=location or name,
        ))

    return events


# ─── HTTP with retry ──────────────────────────────────────────────────────────

def _fetch_with_retry(
    url: str,
    *,
    session: requests.Session,
    max_retries: int = 0,
    timeout: int = 12,
) -> requests.Response | None:
    for attempt in range(max_retries + 1):
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException:
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            else:
                return None
    return None


# ─── NYC Parks parser (existing, enhanced) ────────────────────────────────────

_PARKS_URL_CATEGORY = {
    "festivals": "entertainment",
    "concerts": "entertainment",
    "arts-and-crafts": "entertainment",
    "history": "entertainment",
    "free": "entertainment",
    "fitness": "recreation",
    "sports": "recreation",
    "nature": "recreation",
    "family": "recreation",
    "seniors": "recreation",
}


def _parks_category_from_url(url: str) -> str:
    """Infer event category from the Parks listing URL path."""
    for keyword, cat in _PARKS_URL_CATEGORY.items():
        if keyword in url:
            return cat
    return "entertainment"


def _parse_parks_list_html(html: str, *, source_url: str) -> list[CommunityEvent]:
    seen: set[str] = set()
    out: list[CommunityEvent] = []
    default_category = _parks_category_from_url(source_url)
    src_id = "nyc_parks_festivals"

    for m in _EVENT_PATH.finditer(html):
        path, y, mo, d, slug, title = m.groups()
        clean_title = re.sub(r"\s+", " ", title).strip()
        # Skip CANCELED events — not useful to surface
        if clean_title.upper().startswith("CANCELED") or clean_title.upper().startswith("CANCELLED"):
            continue
        key = path.lower()
        if key in seen:
            continue
        seen.add(key)
        start = f"{y}-{mo}-{d}"
        chunk = html[m.start():m.start() + 900]
        loc_m = _LOCATION_SNIP.search(chunk)
        time_m = _TIME_SNIP.search(chunk)
        location = re.sub(r"\s+", " ", loc_m.group(1)).strip() if loc_m else ""
        start_time = re.sub(r"\s+", " ", time_m.group(1)).strip() if time_m else ""
        borough = infer_borough(f"{location} {slug} {title}")
        # Infer finer category from slug keywords
        slug_lower = slug.lower()
        category = default_category
        if any(kw in slug_lower for kw in ("concert", "music", "festival", "art", "craft", "histor", "culture")):
            category = "entertainment"
        elif any(kw in slug_lower for kw in ("fitness", "sport", "run", "swim", "yoga", "nature", "family", "kid", "senior")):
            category = "recreation"

        out.append(
            CommunityEvent(
                title=clean_title,
                start_date=start,
                source=src_id,
                url=urljoin(PARKS_BASE, path),
                start_time=start_time,
                location=location,
                borough=borough,
                is_free=True,
                category=category,
                description=slug.replace("-", " "),
            )
        )
    return out


def _parse_parks_detail(html: str, event: CommunityEvent) -> CommunityEvent:
    """Extract richer info from a Parks event detail page."""
    desc_m = re.search(
        r'class="[^"]*event[-_]?desc[^"]*"[^>]*>(.*?)</(?:div|section)',
        html, re.I | re.S,
    )
    if desc_m:
        raw = re.sub(r"<[^>]+>", " ", desc_m.group(1))
        event.description = re.sub(r"\s+", " ", raw).strip()[:500]

    reg_m = re.search(r'href="([^"]*(?:register|signup|rsvp)[^"]*)"', html, re.I)
    if reg_m:
        event.url = urljoin(PARKS_BASE, reg_m.group(1))

    cost_m = re.search(r'(?:cost|fee|price)[:\s]*\$?([\d,.]+|free)', html, re.I)
    if cost_m:
        val = cost_m.group(1).lower()
        event.cost = "Free" if val == "free" else f"${val}"
        event.is_free = val == "free"

    return event


# ─── Generic NYC.gov page parser ─────────────────────────────────────────────

def _parse_nyc_gov_page(html: str, *, source_id: str, base_url: str) -> list[CommunityEvent]:
    """Extract links and descriptions from NYC.gov-style service pages."""
    out: list[CommunityEvent] = []
    link_pattern = re.compile(
        r'<a[^>]+href="([^"]+)"[^>]*>([^<]{5,200})</a>',
        re.I,
    )
    today_str = date.today().isoformat()
    for m in link_pattern.finditer(html):
        href, text = m.group(1), m.group(2)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 8 or text.lower() in ("read more", "learn more", "click here", "back to top"):
            continue
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        if parsed.netloc and "nyc.gov" not in parsed.netloc and "nycgovparks" not in parsed.netloc:
            continue
        out.append(
            CommunityEvent(
                title=text,
                start_date="",
                source=source_id,
                url=full_url,
                borough="",
                is_free=None,
                category="general",
            )
        )
    return out[:50]


# ─── Community org parser ─────────────────────────────────────────────────────

def _parse_community_org_page(html: str, *, source_id: str, base_url: str) -> list[CommunityEvent]:
    """Parse event listings from community organization websites."""
    out: list[CommunityEvent] = []
    today_str = date.today().isoformat()

    date_patterns = [
        re.compile(r'(\w+ \d{1,2},?\s*20\d{2})', re.I),
        re.compile(r'(\d{1,2}/\d{1,2}/20\d{2})', re.I),
        re.compile(r'(20\d{2}-\d{2}-\d{2})', re.I),
    ]

    blocks = re.split(r'<(?:article|li|div)[^>]*class="[^"]*(?:event|post|item)[^"]*"', html, flags=re.I)

    for block in blocks[1:]:
        title_m = re.search(r'<(?:h[2-4]|a)[^>]*>([^<]{5,200})</(?:h[2-4]|a)>', block, re.I)
        if not title_m:
            continue
        title = re.sub(r"\s+", " ", title_m.group(1)).strip()

        link_m = re.search(r'href="([^"]+)"', block, re.I)
        url = urljoin(base_url, link_m.group(1)) if link_m else base_url

        event_date = ""
        for dp in date_patterns:
            dm = dp.search(block)
            if dm:
                try:
                    for fmt in ("%B %d, %Y", "%B %d %Y", "%m/%d/%Y", "%Y-%m-%d"):
                        try:
                            parsed_dt = datetime.strptime(dm.group(1).replace(",", "").strip(), fmt)
                            event_date = parsed_dt.strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
                break

        loc_m = re.search(r'(?:location|venue|address)[:\s]*([^<]{5,100})', block, re.I)
        location = re.sub(r"\s+", " ", loc_m.group(1)).strip() if loc_m else ""

        out.append(
            CommunityEvent(
                title=title,
                start_date=event_date,
                source=source_id,
                url=url,
                location=location,
                borough=infer_borough(f"{title} {location}"),
                is_free=None,
                category="community",
            )
        )

    return out[:30]


# ─── Library event parser ─────────────────────────────────────────────────────

def _parse_library_page(html: str, *, source_id: str, base_url: str) -> list[CommunityEvent]:
    """Parse events from NYPL, Queens Library, Brooklyn Public Library."""
    out: list[CommunityEvent] = []
    today_str = date.today().isoformat()

    blocks = re.split(
        r'<(?:article|div|li)[^>]*class="[^"]*(?:event|program|listing|result)[^"]*"',
        html, flags=re.I,
    )

    for block in blocks[1:]:
        title_m = re.search(r'<(?:h[2-4]|a|span)[^>]*>([^<]{5,200})</(?:h[2-4]|a|span)>', block, re.I)
        if not title_m:
            continue
        title = re.sub(r"\s+", " ", title_m.group(1)).strip()

        link_m = re.search(r'href="([^"]+)"', block, re.I)
        url = urljoin(base_url, link_m.group(1)) if link_m else base_url

        date_m = re.search(r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2})', block, re.I)
        if date_m:
            try:
                yr = date.today().year
                parsed_dt = datetime.strptime(f"{date_m.group(1)} {yr}", "%B %d %Y")
                event_date = parsed_dt.strftime("%Y-%m-%d")
            except ValueError:
                event_date = ""
        else:
            event_date = ""

        loc_m = re.search(r'(?:branch|location|library)[:\s]*([^<]{5,80})', block, re.I)
        location = re.sub(r"\s+", " ", loc_m.group(1)).strip() if loc_m else ""

        borough = ""
        if "queens" in source_id:
            borough = "Queens"
        elif "bpl" in source_id or "brooklyn" in source_id:
            borough = "Brooklyn"
        elif "nypl" in source_id:
            borough = infer_borough(f"{title} {location}") or "Manhattan"

        out.append(
            CommunityEvent(
                title=title,
                start_date=event_date,
                source=source_id,
                url=url,
                location=location,
                borough=borough,
                is_free=True,
                category="education",
            )
        )

    return out[:40]


# ─── RSS / Atom feed parser ────────────────────────────────────────────────────

_RSS_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
}

_DATE_FMTS = (
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S %Z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d",
)


def _rss_date(raw: str) -> str:
    """Parse RSS/Atom date string → YYYY-MM-DD. Falls back to empty."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            pass
    try:
        return parsedate_to_datetime(raw).strftime("%Y-%m-%d")
    except Exception:
        pass
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _rss_datetime_iso(raw: str) -> str:
    """Parse RSS/Atom date → ISO-8601 with offset when possible."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw).isoformat(timespec="seconds")
    except Exception:
        pass
    m = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return m.group(1)
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def _parse_rss_feed(
    text: str,
    *,
    source_id: str,
    base_url: str,
    source_borough: str = "",
    source_category: str = "community",
) -> list[CommunityEvent]:
    """Parse RSS 2.0 or Atom 1.0 feeds into CommunityEvent list."""
    out: list[CommunityEvent] = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return out

    # Strip default namespace for easier find
    tag = root.tag
    is_atom = "Atom" in tag or "atom" in tag or tag == "{http://www.w3.org/2005/Atom}feed"

    if is_atom:
        items = root.findall("{http://www.w3.org/2005/Atom}entry")
    else:
        items = root.findall(".//item")

    today_str = date.today().isoformat()
    for item in items:
        if is_atom:
            title_el = item.find("{http://www.w3.org/2005/Atom}title")
            link_el = item.find("{http://www.w3.org/2005/Atom}link")
            # Must use `is not None` — childless XML elements are falsy in Python
            _d_upd = item.find("{http://www.w3.org/2005/Atom}updated")
            _d_pub = item.find("{http://www.w3.org/2005/Atom}published")
            date_el = _d_upd if _d_upd is not None else _d_pub
            _desc_s = item.find("{http://www.w3.org/2005/Atom}summary")
            _desc_c = item.find("{http://www.w3.org/2005/Atom}content")
            desc_el = _desc_s if _desc_s is not None else _desc_c
            title = (title_el.text or "").strip() if title_el is not None else ""
            url = (link_el.get("href") or link_el.text or "").strip() if link_el is not None else base_url
            raw_date = (date_el.text or "") if date_el is not None else ""
        else:
            title_el = item.find("title")
            link_el = item.find("link")
            date_el = item.find("pubDate")
            desc_el = item.find("description")
            title = (title_el.text or "").strip() if title_el is not None else ""
            url = (link_el.text or "").strip() if link_el is not None else base_url
            raw_date = (date_el.text or "") if date_el is not None else ""

        if not title or len(title) < 4:
            continue

        pub_iso = _rss_datetime_iso(raw_date) if raw_date else ""
        pub_day = pub_iso[:10] if pub_iso else ""
        url_event = ""
        um = re.search(r"/events/(20\d{2})/(\d{2})/(\d{2})/", url or "")
        if um:
            url_event = f"{um.group(1)}-{um.group(2)}-{um.group(3)}"
        event_date = url_event
        description = ""
        if desc_el is not None and desc_el.text:
            description = re.sub(r"<[^>]+>", " ", desc_el.text)
            description = re.sub(r"\s+", " ", description).strip()[:300]

        if not url or not url.startswith("http"):
            url = urljoin(base_url, url) if url else base_url

        out.append(
            CommunityEvent(
                title=title,
                start_date=event_date,
                source=source_id,
                url=url,
                description=description,
                location="",
                borough=source_borough or infer_borough(title),
                is_free=True,
                category=source_category,
                published_at=pub_iso or pub_day,
            )
        )

    return out[:60]


# ─── Continuing-education / course-listing parser ────────────────────────────

def _parse_education_page(html: str, *, source_id: str, base_url: str) -> list[CommunityEvent]:
    """Parse CUNY CE, NYC Immigrants, library ESL landing pages.

    These pages describe programs rather than event calendars.
    Extracts program/course names from headings and links that contain
    education-relevant keywords, avoiding navigation/footer junk.
    """
    out: list[CommunityEvent] = []
    today = date.today()
    days_ahead = 7 - today.weekday()  # days to next Monday
    enroll_date = (today + timedelta(days=days_ahead)).isoformat()

    # Key education keywords — require at least one to accept an item
    edu_re = re.compile(
        r'esl|english\s+as\s+a\s+second|language\s+class|adult\s+ed|continuing\s+ed|'
        r'ged|tasc|literacy|citizenship\s+(class|prep|test)|workforce|job\s+train|'
        r'vocational|certificate\s+(program|course)|digital\s+(skill|literacy)|'
        r'computer\s+class|free\s+(class|course|program)|enroll|register\s+(now|for)|'
        r'免费|课程|英语|继续教育|成人|职业培训|入籍|数字',
        re.I,
    )

    # Hard exclusions — skip any link/heading containing these
    junk_re = re.compile(
        r'^(?:home|menu|skip\s+to|search|contact\s+us|about\s+us|login|sign\s*in|'
        r'register|privacy|terms|accessibility|feedback|sitemap|next|previous|'
        r'back|read\s+more|learn\s+more|view\s+all|see\s+all|click\s+here|'
        r'(?:nyc|city)\s+services?|your\s+government|emergency\s+alerts?|'
        r'website\s+feedback|text.?size|font\s+size)',
        re.I,
    )

    # Only match h2/h3/h4 heading tags for reliable extraction (not bare <a> or <strong>)
    heading_pattern = re.compile(
        r'<(h[2-4])[^>]*>(.*?)</\1>',
        re.I | re.S,
    )
    link_pattern = re.compile(r'href="([^"#][^"]*)"', re.I)
    # Also extract anchor links with edu-keyword text (for program list pages)
    anchor_pattern = re.compile(
        r'<a\s[^>]*href="([^"#][^"]*)"[^>]*>([^<]{12,160})</a>',
        re.I,
    )

    seen: set[str] = set()

    def _clean(raw: str) -> str:
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', re.sub(r'&\w+;', ' ', raw))).strip()

    def _add(title: str, url: str) -> bool:
        title = _clean(title)
        if len(title) < 10 or len(title) > 160:
            return False
        if junk_re.match(title):
            return False
        if not edu_re.search(title):
            return False
        # Skip mailto/tel/javascript links
        if re.match(r'(?:mailto|tel|javascript):', url, re.I):
            return False
        # Skip root-level CE department pages (they are generic listing pages)
        if re.match(r'^https?://[^/]+/ce/?$', url, re.I):
            return False
        # Skip if url == base_url (no specific page found)
        if url.rstrip('/') == base_url.rstrip('/'):
            return False
        key = re.sub(r'\W+', '', title.lower())[:60]
        if key in seen:
            return False
        seen.add(key)
        out.append(
            CommunityEvent(
                title=title,
                start_date=enroll_date,
                source=source_id,
                url=url,
                description=f"Education program on {urlparse(base_url).netloc} — click to enroll or learn more.",
                location="New York City",
                borough="",
                is_free=True,
                category="education",
            )
        )
        return True

    # Pass 1: headings with nearby links
    for m in heading_pattern.finditer(html):
        title_raw = m.group(2)
        title = _clean(title_raw)
        # Find the nearest href after this heading (within 400 chars)
        search_window = html[m.start(): min(len(html), m.end() + 400)]
        href_m = link_pattern.search(search_window)
        url = urljoin(base_url, href_m.group(1)) if href_m else base_url
        _add(title, url)
        if len(out) >= 15:
            break

    # Pass 2: anchor links with edu keywords (fills gaps on program-list pages)
    if len(out) < 8:
        for m in anchor_pattern.finditer(html):
            url_raw, title_raw = m.group(1), m.group(2)
            url = urljoin(base_url, url_raw)
            if re.match(r'(?:mailto|tel|javascript):', url, re.I):
                continue
            _add(title_raw, url)
            if len(out) >= 15:
                break

    return out


# ─── MTA Service Status XML parser ───────────────────────────────────────────

def _parse_mta_xml(html: str, *, source_id: str, base_url: str) -> list[CommunityEvent]:
    """Parse MTA service status XML (serviceStatus.txt) for delays and planned work.

    Only extracts lines that are NOT in GOOD SERVICE — delays, planned work, service change.
    Generates one CommunityEvent per affected line with a useful description.
    """
    out: list[CommunityEvent] = []
    today_str = date.today().isoformat()
    # Try to parse as XML
    try:
        root = ET.fromstring(html if html.strip().startswith("<") else f"<root>{html}</root>")
    except ET.ParseError:
        return []

    status_skip = {"GOOD SERVICE", "PLANNED WORK NOTICE", ""}
    status_zh = {
        "DELAYS": "服务延误",
        "SERVICE CHANGE": "线路变更",
        "SUSPENDED": "暂停运营",
        "PLANNED WORK": "计划施工",
        "SPECIAL NOTICE": "特别通知",
        "NO SCHEDULED SERVICE": "暂停运营",
    }

    sections = {"subway": "地铁", "bus": "公交", "BT": "巴士终点站", "LIRR": "长岛铁路", "MetroNorth": "捷运北线"}
    for section_tag, section_name in sections.items():
        section = root.find(section_tag)
        if section is None:
            continue
        for line in section.findall("line"):
            name_el = line.find("name")
            status_el = line.find("status")
            if name_el is None or status_el is None:
                continue
            name = (name_el.text or "").strip()
            status = (status_el.text or "").strip().upper()
            if not name or status in status_skip:
                continue
            # Extract planned work or delay message
            msg = ""
            for tag in ("planned_work", "delays", "incidents", "MessageLong"):
                el = line.find(tag)
                if el is not None:
                    txt = el.get("Text", "") or (el.text or "")
                    txt = re.sub(r"<[^>]+>", " ", txt)
                    txt = re.sub(r"\s+", " ", txt).strip()
                    if len(txt) > 10:
                        msg = txt[:200]
                        break

            status_label = status_zh.get(status, status.title())
            title = f"【{section_name} {name}】{status_label}"
            desc = msg or f"{section_name} {name} 线路当前状态：{status_label}，请注意出行安排。"
            out.append(CommunityEvent(
                title=title,
                start_date=today_str,
                source=source_id,
                url="https://new.mta.info/alerts",
                location="NYC",
                borough="Citywide",
                category="transit",
                is_free=None,
                description=desc,
            ))
    return out[:20]


# ─── Source router ────────────────────────────────────────────────────────────

PARSER_MAP = {
    "parsers.nyc_parks": "_parse_parks_list",
    "parsers.nyc_parks_facilities": "_parse_nyc_gov",
    "parsers.queens_library": "_parse_library",
    "parsers.nypl": "_parse_library",
    "parsers.bpl": "_parse_library",
    "parsers.rss": "_parse_rss",
    "parsers.nyc_gov_generic": "_parse_nyc_gov",
    "parsers.nyc_health": "_parse_nyc_gov",
    "parsers.nyc_council": "_parse_nyc_gov",
    "parsers.mta": "_parse_nyc_gov",
    "_parse_mta_xml": "_parse_mta_xml",
    "parsers.community_org": "_parse_community_org",
    "parsers.legal_services": "_parse_nyc_gov",
    "parsers.education": "_parse_education",
    "parsers.museum_events": "_parse_community_org",
    "parsers.access_nyc": "_parse_nyc_gov",
}


def _get_parser(parse_module: str):
    parser_key = PARSER_MAP.get(parse_module, "_parse_nyc_gov")
    return {
        "_parse_parks_list": _parse_parks_list_html,
        "_parse_nyc_gov": _parse_nyc_gov_page,
        "_parse_community_org": _parse_community_org_page,
        "_parse_library": _parse_library_page,
        "_parse_rss": _parse_rss_feed,
        "_parse_education": _parse_education_page,
        "_parse_mta_xml": _parse_mta_xml,
    }[parser_key]


# ─── Multi-source fetch orchestrator ─────────────────────────────────────────

def fetch_all_sources(
    config: dict[str, Any] | None = None,
    *,
    deep_dive: bool = True,
    max_detail_pages: int = 5,
    session: requests.Session | None = None,
    source_ids: set[str] | frozenset[str] | None = None,
) -> tuple[list[CommunityEvent], list[dict[str, Any]]]:
    """Fetch events from all configured sources.

    Args:
        config: Parsed config dict. Loads from CONFIG_PATH if None.
        deep_dive: If True, follow links into detail pages for richer data.
        max_detail_pages: Max detail pages to fetch per source.
        session: Optional shared session.

    Returns:
        (all_events, fetch_logs)
    """
    if config is None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    sess = session or requests.Session()
    sess.headers.update(DEFAULT_HEADERS)

    sources = config.get("sources", [])
    if source_ids is not None:
        allow = set(source_ids)
        sources = [s for s in sources if s.get("id") in allow]
    all_events: list[CommunityEvent] = []
    logs: list[dict[str, Any]] = []
    today = date.today()
    retention = int(config.get("retention_days", 30))
    future_horizon = int(config.get("future_horizon_days") or config.get("horizon_days") or retention)
    nyc_open_data_token: str | None = os.environ.get("NYC_OPEN_DATA_TOKEN") or None
    parks_waf_blocked = False   # once blocked, use Open Data fallback for remaining Parks URLs

    parks_in_run = source_ids is None or any(
        str(s.get("id", "")).startswith("nyc_parks") for s in sources
    )
    if parks_in_run:
        od_prefetch = _fetch_parks_open_data(sess, today=today, app_token=nyc_open_data_token)
        if od_prefetch:
            all_events.extend(od_prefetch)
            logs.append({
                "source": "nyc_parks_opendata_fallback",
                "url": "prefetch",
                "ok": True,
                "count": len(od_prefetch),
            })

    for src in sources:
        src_id = src.get("id", "unknown")
        parse_module = src.get("parse_module", "parsers.nyc_gov_generic")
        urls = src.get("urls", [])
        src_events: list[CommunityEvent] = []
        # Per-source timeout: library/slow sources can specify longer timeout
        src_timeout = int(src.get("timeout_seconds", 12))
        src_borough = src.get("borough_scope", "")
        if src_borough.lower() in ("all", "citywide", ""):
            src_borough = ""
        src_category = src.get("category", "community")
        is_rss = parse_module == "parsers.rss"
        is_parks = parse_module == "parsers.nyc_parks"

        # For Parks sources, use PARKS_HEADERS to reduce WAF challenge rate
        if is_parks and not parks_waf_blocked:
            parks_sess = requests.Session()
            parks_sess.headers.update(PARKS_HEADERS)
        else:
            parks_sess = sess

        for url in urls:
            # If Parks WAF already blocked, skip further HTML attempts
            if is_parks and parks_waf_blocked:
                logs.append({"source": src_id, "url": url, "ok": False, "error": "waf_blocked_using_opendata"})
                continue

            fetch_sess = parks_sess if is_parks else sess
            resp = _fetch_with_retry(url, session=fetch_sess, timeout=src_timeout)
            if resp is None:
                logs.append({"source": src_id, "url": url, "ok": False, "error": "timeout_or_http_error"})
                continue

            # Detect WAF challenge page (bot-blocking)
            if is_parks and _is_waf_challenge(resp):
                logs.append({"source": src_id, "url": url, "ok": False, "error": "waf_challenge_detected"})
                parks_waf_blocked = True
                continue

            try:
                if is_rss:
                    batch = _parse_rss_feed(
                        resp.text,
                        source_id=src_id,
                        base_url=url,
                        source_borough=src_borough,
                        source_category=src_category,
                    )
                elif is_parks:
                    batch = _parse_parks_list_html(resp.text, source_url=url)
                elif parse_module in ("parsers.queens_library", "parsers.nypl", "parsers.bpl"):
                    batch = _parse_library_page(resp.text, source_id=src_id, base_url=url)
                elif parse_module in ("parsers.community_org", "parsers.museum_events"):
                    batch = _parse_community_org_page(resp.text, source_id=src_id, base_url=url)
                elif parse_module == "parsers.education":
                    batch = _parse_education_page(resp.text, source_id=src_id, base_url=url)
                elif parse_module == "_parse_mta_xml":
                    batch = _parse_mta_xml(resp.text, source_id=src_id, base_url=url)
                else:
                    batch = _parse_nyc_gov_page(resp.text, source_id=src_id, base_url=url)

                src_events.extend(batch)
                logs.append({"source": src_id, "url": url, "ok": True, "count": len(batch)})
            except Exception as exc:
                logs.append({"source": src_id, "url": url, "ok": False, "error": str(exc)[:300]})

            time.sleep(1.5 if is_parks else 0.4)

        # If Parks HTML was fully blocked by WAF, fall back to NYC Open Data JSON API
        if is_parks and parks_waf_blocked and not src_events:
            od_events = _fetch_parks_open_data(sess, today=today, app_token=nyc_open_data_token)
            src_events.extend(od_events)
            parks_waf_blocked = False  # reset; already used fallback
            logs.append({"source": "nyc_parks_opendata_fallback", "url": PARKS_OD_ENDPOINT, "ok": True, "count": len(od_events)})

        if deep_dive and src_events and is_parks:
            detail_count = 0
            for ev in src_events[:max_detail_pages]:
                if not ev.url or detail_count >= max_detail_pages:
                    break
                detail_resp = _fetch_with_retry(ev.url, session=parks_sess, timeout=10)
                if detail_resp and not _is_waf_challenge(detail_resp):
                    _parse_parks_detail(detail_resp.text, ev)
                    detail_count += 1
                time.sleep(0.5)

        valid = [
            ev for ev in src_events
            if within_retention(ev, today=today, retention_days=retention, future_horizon_days=future_horizon)
        ]
        all_events.extend(valid)

    all_events = deduplicate(all_events)
    return all_events, logs


# ─── Legacy API (backward-compatible) ─────────────────────────────────────────

def fetch_parks_events(
    list_urls: list[str],
    *,
    session: requests.Session | None = None,
) -> tuple[list[CommunityEvent], list[dict[str, Any]]]:
    """Legacy function: fetch only NYC Parks events from given URLs."""
    sess = session or requests.Session()
    sess.headers.update(DEFAULT_HEADERS)
    all_events: list[CommunityEvent] = []
    logs: list[dict[str, Any]] = []
    for url in list_urls:
        try:
            resp = sess.get(url, timeout=45)
            resp.raise_for_status()
            batch = _parse_parks_list_html(resp.text, source_url=url)
            all_events.extend(batch)
            logs.append({"url": url, "ok": True, "count": len(batch)})
        except Exception as exc:
            logs.append({"url": url, "ok": False, "error": str(exc)[:300]})
    dedup: dict[str, CommunityEvent] = {}
    for ev in all_events:
        dedup[ev.url] = ev
    return list(dedup.values()), logs


def load_curated_seed(path: Path) -> list[CommunityEvent]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    out: list[CommunityEvent] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        if not title or title.startswith("（示例）"):
            continue
        out.append(CommunityEvent.from_dict(row))
    return out
