"""Offline publication checks for current US Life Hub recommendations.

Discovery timestamps are not event dates. This gate deliberately works on copies:
archival hub records remain available for explicitly historical uses elsewhere.
"""
from __future__ import annotations

import calendar
import html
import re
from datetime import date, datetime
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit
from zoneinfo import ZoneInfo

_MONTHS = '|'.join(calendar.month_name[1:] + calendar.month_abbr[1:])
_GENERIC = re.compile(
    rf'^(?:查看活动|查看詳情|查看详情|了解更多|活动日历|更多|view\s+(?:event|details)|'
    rf'learn\s+more|read\s+more|events?|calendar|(?:\d{{4}}年)?\d{{1,2}}月|'
    rf'(?:{_MONTHS})\s+\d{{4}}|\d{{4}}\s+(?:{_MONTHS})|\d{{4}}[-/]\d{{1,2}})$', re.I,
)
_EVENT_WORDS = re.compile(
    r'parade|festival|gala|concert|conference|convention|workshop|tournament|'
    r'游行|巡游|節慶|节庆|晚会|晚會|音乐会|音樂會|年会|年會|会议|會議|研讨会|研討會', re.I,
)
_YEAR = re.compile(r'(?<!\d)((?:19|20)\d{2})(?!\d)')
_URL_DATE = re.compile(r'/(20\d{2})/(\d{1,2})/(\d{1,2})(?:/|$)')
_ARCHIVE = re.compile(r'^(?:历史|歷史|往期|历年|歷年)|^(?:archive|historical)\b|(?:历史回顾|歷史回顧)', re.I)


def current_date(as_of: date | datetime | None = None) -> date:
    if as_of is None:
        return datetime.now(ZoneInfo('America/New_York')).date()
    if isinstance(as_of, datetime):
        if as_of.tzinfo is not None:
            return as_of.astimezone(ZoneInfo('America/New_York')).date()
        return as_of.date()
    return as_of


def _date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value or '')[:10])
    except ValueError:
        return None


def _text(value: Any) -> str:
    return re.sub(r'\s+', ' ', html.unescape(str(value or ''))).strip()


def generic_title(value: Any) -> bool:
    title = _text(value).strip(' →←↗»›:：|/-–—')
    return not title or bool(_GENERIC.fullmatch(title))


def descriptive_title(event: dict[str, Any]) -> str:
    """Use structured title fields, then an event-specific URL slug; never invent."""
    for key in ('title_zh', 'title_en', 'title', 'name'):
        candidate = _text(event.get(key))
        if candidate and not generic_title(candidate):
            return candidate
    path = unquote(urlsplit(str(event.get('url') or '')).path).rstrip('/')
    slug = path.rsplit('/', 1)[-1]
    slug = re.sub(r'\.(?:html?|php)$', '', slug, flags=re.I)
    candidate = re.sub(r'[-_]+', ' ', slug).strip()
    # A generic directory/ID must not become a fabricated event name.
    if _EVENT_WORDS.search(candidate) and len(candidate.split()) >= 2 and not generic_title(candidate):
        return candidate[0].upper() + candidate[1:]
    return ''


def _wrong_flushing_source(event: dict[str, Any]) -> bool:
    text = ' '.join(_text(event.get(k)) for k in ('title_zh', 'title_en', 'title', 'summary_zh'))
    authority = r'(?:NYPL|New\s+York\s+Public\s+Library|纽约公共图书馆|紐約公共圖書館)'
    direct = authority + r'\s*(?:[-（(·:：]|的)?\s*(?:法拉盛|Flushing)'
    reverse = r'(?:法拉盛(?:公共)?(?:图书馆|分馆)|Flushing\s+(?:Library|branch))\s*(?:[（(]|属于|隶属于)\s*' + authority
    if re.search(direct, text, re.I) or re.search(reverse, text, re.I):
        return True
    url = urlsplit(str(event.get('url') or ''))
    host = (url.hostname or '').lower()
    if host == 'nypl.org' or host.endswith('.nypl.org'):
        if '/locations/flushing' in unquote(url.path).lower():
            return True
        return any('flushing' in value.lower() for value in parse_qs(url.query).get('location', []))
    return False


def _event_directory(url: str) -> bool:
    """Known browsing/service entry points are not individual dated events."""
    parsed = urlsplit(url)
    path = unquote(parsed.path).rstrip('/').lower()
    host = (parsed.hostname or '').lower().removeprefix('www.')
    if path in {'', '/events', '/event', '/calendar'}:
        return True
    if host == 'eventbrite.com' and path.startswith('/d/'):
        return True
    return host == 'nycgovparks.org' and path == '/events/volunteer'


def prepare_current_event(event: dict[str, Any], *, as_of: date | datetime | None = None) -> dict[str, Any] | None:
    """Return a publishable current/evergreen copy, or None for unsafe entries.

    Missing/malformed dates on explicitly dated events fail closed. A year in an
    event title or event URL is event evidence even when upstream calls it a
    service; policy years and old publication dates alone do not expire services.
    """
    today = current_date(as_of)
    title = descriptive_title(event)
    if not title or _wrong_flushing_source(event):
        return None
    if str(event.get('date_kind') or '').lower() in {'archive', 'historical'} or event.get('is_archive') is True:
        return None
    if _ARCHIVE.search(title):
        return None

    url_path = unquote(urlsplit(str(event.get('url') or '')).path)
    identity = ' '.join((title, _text(event.get('title_en')), url_path))
    event_like = bool(_EVENT_WORDS.search(identity) or re.search(r'/events?/', url_path, re.I))
    years = [int(y) for y in _YEAR.findall(identity)] if event_like else []
    if years and max(years) < today.year:
        return None

    # Do not silently prefer one field when upstream aliases disagree.
    for keys in (('event_date', 'start_date'), ('event_end_date', 'end_date')):
        values = [_date(event[k]) for k in keys if event.get(k)]
        if None in values or len(set(values)) > 1:
            return None
    raw_start = event.get('event_date') or event.get('start_date') or ''
    raw_end = event.get('event_end_date') or event.get('end_date') or ''
    start, end = _date(raw_start), _date(raw_end)
    if raw_start and start is None or raw_end and end is None:
        return None
    url_match = _URL_DATE.search(url_path) if event_like else None
    if url_match:
        try:
            url_date = date(*map(int, url_match.groups()))
        except ValueError:
            return None
        if start is not None and start != url_date:
            return None  # contradictory source dates need review
        start = url_date
    source_start = event.get('source_event_date')
    if source_start and (_date(source_start) is None or _date(source_start) != start):
        return None  # ingestion must not erase a contradictory listing date
    if end is not None and start is not None and end < start:
        return None
    if start is not None and years and any(y < start.year or y > (end or start).year for y in years):
        return None  # title/URL year disagrees with the supplied event schedule
    if (end or start) is not None and (end or start) < today:
        return None
    if start is None and end is None and (
        str(event.get('date_kind') or '').lower() == 'event'
        or years
        or (event_like and not _event_directory(str(event.get('url') or '')))
    ):
        return None  # discovery/service labels cannot establish an event schedule

    result = dict(event)
    result['title_zh'] = title
    if title != _text(event.get('title_zh')):
        result['title_quality_source'] = 'structured_title_or_event_url'
    if start is not None:
        result['event_date'] = start.isoformat()
    return result
