"""SSOT: NYC Chinese Life Hub — 12 livelihood channels (deals are a separate section)."""
from __future__ import annotations

import re
from datetime import date
from typing import Any

HUB_MODULES: list[dict[str, Any]] = [
    {
        "id": "family",
        "zh": "亲子·公园",
        "zht": "親子·公園",
        "en": "Family & Parks",
        "desc_zh": "儿童故事会、亲子活动、游乐场、Baby & Toddler 等公园家庭项目。",
        "desc_zht": "兒童故事會、親子活動、遊樂場、Baby & Toddler 等公園家庭項目。",
        "desc_en": "Story time, family days, playgrounds and kid-focused park programs.",
        "color": "#0d9488",
    },
    {
        "id": "fitness",
        "zh": "健身·户外",
        "zht": "健身·戶外",
        "en": "Fitness & Outdoors",
        "desc_zh": "游泳、Zumba、瑜伽、球类、徒步与自然探索等免费健身活动。",
        "desc_zht": "游泳、Zumba、瑜伽、球類、徒步與自然探索等免費健身活動。",
        "desc_en": "Swimming, zumba, sports, hiking and outdoor fitness programs.",
        "color": "#0891b2",
    },
    {
        "id": "culture",
        "zh": "文化·节庆",
        "zht": "文化·節慶",
        "en": "Culture & Festivals",
        "desc_zh": "音乐会、节庆、电影、艺术展览、宠物领养与社区庆典。",
        "desc_zht": "音樂會、節慶、電影、藝術展覽、寵物領養與社區慶典。",
        "desc_en": "Concerts, festivals, film, arts and community celebrations.",
        "color": "#7c3aed",
    },
    {
        "id": "education",
        "zh": "语言·教育",
        "zht": "語言·教育",
        "en": "Language & Education",
        "desc_zh": "免费 ESL、GED、公民入籍、图书馆课程与成人 literacy 项目。",
        "desc_zht": "免費 ESL、GED、公民入籍、圖書館課程與成人 literacy 項目。",
        "desc_en": "Free ESL, GED, citizenship, library classes and adult literacy.",
        "color": "#6366f1",
    },
    {
        "id": "employment",
        "zh": "就业·培训",
        "zht": "就業·培訓",
        "en": "Jobs & Training",
        "desc_zh": "Workforce1 职业培训、华人社区招聘会、技能提升与就业辅导。",
        "desc_zht": "Workforce1 職業培訓、華人社區招聘會、技能提升與就業輔導。",
        "desc_en": "Workforce training, job fairs and career development programs.",
        "color": "#2563eb",
    },
    {
        "id": "benefits",
        "zh": "福利·政务",
        "zht": "福利·政務",
        "en": "Benefits & Services",
        "desc_zh": "白卡、粮食券、长者服务、IDNYC、移民法律援助与住房资讯。",
        "desc_zht": "白卡、糧食券、長者服務、IDNYC、移民法律援助與住房資訊。",
        "desc_en": "Medicaid, SNAP, senior services, IDNYC, immigration and housing aid.",
        "color": "#16a34a",
    },
    {
        "id": "transit",
        "zh": "交通·出行",
        "zht": "交通·出行",
        "en": "Transit & Travel",
        "desc_zh": "地铁巴士改线、道路施工、Fair Fares 与出行通知。",
        "desc_zht": "地鐵巴士改線、道路施工、Fair Fares 與出行通知。",
        "desc_en": "MTA alerts, road work, reduced fare programs and travel notices.",
        "color": "#ca8a04",
    },
    {
        "id": "charity",
        "zh": "公益·义工",
        "zht": "公益·義工",
        "en": "Volunteer",
        "desc_zh": "官方义工招募、食物银行志愿、华人机构社区服务项目。",
        "desc_zht": "官方義工招募、食物銀行志願、華人機構社區服務項目。",
        "desc_en": "Official volunteer roles and Chinese org community service.",
        "color": "#c026d3",
    },
    {
        "id": "safety",
        "zh": "安全·突发",
        "zht": "安全·突發",
        "en": "Safety & Alerts",
        "desc_zh": "游行集会、封街通知、治安预警与紧急求助。",
        "desc_zht": "遊行集會、封街通知、治安預警與緊急求助。",
        "desc_en": "Protests, street closures, safety alerts and emergency help.",
        "color": "#dc2626",
    },
    {
        "id": "recreation",
        "zh": "休闲·运动",
        "zht": "休閒·運動",
        "en": "Recreation & Sports",
        "desc_zh": "滑冰、网球、高尔夫、游泳班、击剑与社区运动课程。",
        "desc_zht": "滑冰、網球、高爾夫、游泳班、擊劍與社區運動課程。",
        "desc_en": "Skating, tennis, golf, swim lessons, fencing and community sports.",
        "color": "#0284c7",
    },
    {
        "id": "housing",
        "zh": "住房·安居",
        "zht": "住房·安居",
        "en": "Housing & Living",
        "desc_zh": "平价房抽签、租客权利、水电费减免与社区指南。",
        "desc_zht": "平價房抽籤、租客權利、水電費減免與社區指南。",
        "desc_en": "Affordable housing lotteries, tenant rights and utility assistance.",
        "color": "#10b981",
    },
    {
        "id": "health",
        "zh": "医疗·健康",
        "zht": "醫療·健康",
        "en": "Health & Medical",
        "desc_zh": "免费筛查、疫苗接种、心理健康与红蓝卡资讯。",
        "desc_zht": "免費篩查、疫苗接種、心理健康與紅藍卡資訊。",
        "desc_en": "Free screenings, vaccines, mental health and Medicare info.",
        "color": "#ef4444",
    },
]

DEAL_MODULE_ZH = "促销·折扣"
DEAL_URL_MARKERS = ("slickdeals.net", "slickdeals.com", "bensbargains.com", "techbargains.com")
DEAL_MODULE_NAMES = frozenset({DEAL_MODULE_ZH, "消费促销", "折扣·羊毛"})

MODULE_ZH_SET = {m["zh"] for m in HUB_MODULES}

MODULE_BY_CATEGORY: dict[str, str] = {
    "benefits": "福利·政务",
    "welfare": "福利·政务",
    "healthcare": "医疗·健康",
    "housing": "住房·安居",
    "immigration": "福利·政务",
    "food_benefit": "福利·政务",
    "employment_benefit": "福利·政务",
    "senior": "福利·政务",
    "elder": "福利·政务",
    "aging": "福利·政务",
    "education": "语言·教育",
    "enrollment": "语言·教育",
    "employment": "就业·培训",
    "recreation": "休闲·运动",
    "sports": "休闲·运动",
    "fitness": "健身·户外",
    "nature": "健身·户外",
    "pet": "文化·节庆",
    "animal": "文化·节庆",
    "entertainment": "文化·节庆",
    "culture": "文化·节庆",
    "history": "文化·节庆",
    "arts": "文化·节庆",
    "parade_festival": "文化·节庆",
    "general": "文化·节庆",
    "food_promo": DEAL_MODULE_ZH,
    "safety": "安全·突发",
    "legal": "福利·政务",
    "government": "福利·政务",
    "civic": "交通·出行",
    "transportation": "交通·出行",
    "transit": "交通·出行",
    "community": "公益·义工",
    "charity": "公益·义工",
    "volunteer": "公益·义工",
}

LEGACY_MODULE_MAP: dict[str, str] = {
    "福利申请": "福利·政务",
    "老人关怀": "福利·政务",
    "福利·政务": "福利·政务",
    "语言教育": "语言·教育",
    "语言·就业": "语言·教育",
    "就业·培训": "就业·培训",
    "交通出行": "交通·出行",
    "市政议员": "交通·出行",
    "社区政务": "交通·出行",
    "社区安全": "安全·突发",
    "活动休闲": "文化·节庆",
    "公园亲子": "亲子·公园",
    "亲子·活动": "亲子·公园",
    "文化展览": "文化·节庆",
    "宠物领养": "文化·节庆",
    "消费促销": DEAL_MODULE_ZH,
    "折扣·羊毛": DEAL_MODULE_ZH,
    "促销·折扣": DEAL_MODULE_ZH,
    "交通·安全": "交通·出行",
    "公益志愿": "公益·义工",
    "公益义工": "公益·义工",
}

CHARITY_SOURCE_IDS = frozenset({
    "nyc_volunteer_service",
})

WELFARE_SOURCE_IDS = frozenset({
    "nyc_hra", "access_nyc", "nyc_moia", "idnyc", "nyc_medicaid_snap",
    "nyc_food_access", "nys_unemployment", "nyc_dfta", "nyc_dfta_senior",
    "nyc_chinese_minibus",
})

TRANSIT_SOURCE_IDS = frozenset({"mta_service_alerts", "mta_service", "nyc_chinese_minibus"})

HOUSING_SOURCE_IDS = frozenset({"nyc_hpd"})

HEALTH_SOURCE_IDS = frozenset({
    "nyc_health_hospitals", "nyc_health_dept", "charles_b_wang_health", "nyc_medicaid_snap",
})

SAFETY_SOURCE_IDS = frozenset({"nypd_community", "nyc_emergency_mgmt"})

EMPLOYMENT_SOURCE_IDS = frozenset({"nyc_workforce1"})

EDUCATION_SOURCE_IDS = frozenset({
    "cuny_continuing_ed", "nyc_adult_literacy", "nyc_libraries_esl",
    "qpl_flushing", "qpl_elmhurst", "nypl_chatham_square", "nypl_flushing",
    "bpl_sunset_park", "bpl_rss", "nyc_immigrant_services_edu",
})

PARKS_SLUG_RULES: list[tuple[tuple[str, ...], str]] = [
    (("kids-in-motion", "story-time", "storytime", "family", "children", "toddler", "baby", "playground"), "亲子·公园"),
    (("zumba", "fitness", "yoga", "swim", "sports", "basketball", "tennis", "hiking", "nature-walk", "boot-camp"), "健身·户外"),
    (("concert", "festival", "film", "movies-under", "movies under", "parade", "music", "dance", "exhibition", "arts-and"), "文化·节庆"),
    (("volunteer", "cleanup", "stewardship", "restoration-friday", "green-nyc"), "公益·义工"),
    (("senior", "older-adult"), "福利·政务"),
]

PARKS_PATH_MODULE: list[tuple[str, str]] = [
    ("/events/family", "亲子·公园"),
    ("/events/fitness", "健身·户外"),
    ("/events/sports", "休闲·运动"),
    ("/events/nature", "健身·户外"),
    ("/events/festivals", "文化·节庆"),
    ("/events/concerts", "文化·节庆"),
    ("/events/film", "文化·节庆"),
    ("/events/arts-and-crafts", "文化·节庆"),
    ("/events/history", "文化·节庆"),
    ("/events/volunteer", "公益·义工"),
    ("/events/seniors", "福利·政务"),
]

_JUNK_TITLES = frozenset({
    "资源", "服务", "services", "resources", "nyc 资源", "市长办公室",
    "按项目查看", "找到我们", "view by program", "find us", "benefits",
    "about nyc.gov content", "关于 nyc.gov 内容", "无障碍资源",
    "accessibility resources", "how to apply", "如何申请", "如何续期",
    "how to renew", "make appointment", "预约", "update your card", "更新您的卡",
    "may 2026", "2026年5月", "calendar of current and past events",
    "当前和过去活动日历", "contact us online via our webform",
    "通过我们的网页表单在线联系我们", "subscribe to our freight mobility newsletter",
    "订阅我们的货运流动通讯", "office of the mayor", "nyc resources",
    "priority1 – services for veterans and spouses", "access training", "访问培训",
    "translate this page", "site map", "sitemap", "directions",
})

_JUNK_TITLE_PATTERNS = (
    r"^truck\s",
    r"truck\s+(smart|map|driver|route)",
    r"freight\s",
    r"货运",
    r"卡车",
    r"traditional chinese\s*\|",
    r"^faq for truck",
    r"^nyc traffic rules",
    r"^express lane permit",
    r"^parking and making deliveries",
    r"eventdata\.title",
    r"marker\.name",
    r"^\+\s*'",
    r"^' \+ ",
)


def module_balance_targets(max_items: int) -> dict[str, dict[str, int]]:
    """Per-module min/max for balanced hub selection."""
    n = len(HUB_MODULES)
    target = max(10, max_items // n)
    return {
        m["zh"]: {"min": max(6, target - 3), "max": target + 5}
        for m in HUB_MODULES
    }


def _blob_parts(item: dict[str, Any]) -> str:
    parts = [
        item.get("title_zh", ""),
        item.get("title_en", ""),
        item.get("summary_zh", ""),
        item.get("url", ""),
        item.get("module", ""),
    ]
    return " ".join(str(p) for p in parts).lower()


def _module_from_parks_slug(url: str, blob: str) -> str | None:
    if "nycgovparks.org" not in url:
        return None
    slug = url.split("/events/")[-1].lower() if "/events/" in url else url
    combined = f"{slug} {blob}"
    for keys, mod in PARKS_SLUG_RULES:
        if any(k in combined for k in keys):
            return mod
    for path, mod in PARKS_PATH_MODULE:
        if path in url:
            return mod
    if "/events/" in url and re.search(r"/events/20\d{2}/", url):
        return "文化·节庆"
    return None


def _module_from_blob(blob: str, url: str, category: str = "", source_id: str = "") -> str | None:
    parks_hit = _module_from_parks_slug(url, blob)
    if parks_hit:
        return parks_hit

    if "eventbrite.com" in url:
        if any(k in blob for k in ("job fair", "workforce", "hiring", "career", "招聘")):
            return "就业·培训"
        if any(k in blob for k in ("esl", "mandarin meetup", "literacy", "citizenship", "education")):
            return "语言·教育"
        return "文化·节庆"
    if any(k in blob for k in ("immigrant", "immigration", "idnyc", "snap", "medicaid")):
        return "福利·政务"
    if source_id in EDUCATION_SOURCE_IDS:
        return "语言·教育"
    if source_id in EMPLOYMENT_SOURCE_IDS:
        return "就业·培训"
    if source_id in TRANSIT_SOURCE_IDS or any(k in blob for k in (
        "mta.info", "subway", "bus detour", "service change", "地铁", "巴士改线", "fair fares",
    )):
        return "交通·出行"
    if source_id in SAFETY_SOURCE_IDS or any(k in blob for k in (
        "nypd", "fraud", "scam", "town hall", "council member", "防诈骗", "protest", "rally", "游行", "封街",
        "notify nyc", "emergency management", "severe weather",
    )):
        return "安全·突发"
    if source_id in HOUSING_SOURCE_IDS or any(k in blob for k in (
        "housingconnect", "affordable housing", "tenant rights", "rent freeze", "租客", "抽签", "housing lottery", "hpd.nyc",
    )):
        return "住房·安居"
    if source_id in HEALTH_SOURCE_IDS or category == "healthcare" or any(k in blob for k in (
        "vaccine", "vaccination", "health fair", "mental health", "nyc care", "筛查", "疫苗", "health hospital",
    )):
        return "医疗·健康"
    if any(k in blob for k in ("skating", "tennis", "golf", "fencing", "swim lesson", "滑冰", "网球", "高尔夫", "击剑", "游泳班")):
        return "休闲·运动"
    if source_id in WELFARE_SOURCE_IDS or any(k in blob for k in (
        "snap", "medicaid", "hra/help", "immigrant legal", "moia", "idnyc", "senior center",
    )):
        return "福利·政务"
    if category == "employment" or any(k in blob for k in (
        "job fair", "job & resource", "workforce", "workforce1", "career fair", "hiring", "招聘",
    )):
        return "就业·培训"
    if category in ("education", "enrollment") or any(k in blob for k in (
        "esl", " ged", "literacy", "citizenship", "continuing education", "library.org/programs",
        "cuny.edu/ce", "mandarin meetup", "tea ceremony",
    )):
        return "语言·教育"
    if source_id in CHARITY_SOURCE_IDS or any(k in blob for k in (
        "volunteer workday", "volunteers", "义工", "/opportunities/volunteer",
    )) and "volunteer" in blob:
        return "公益·义工"
    if any(k in blob for k in (
        "kids in motion", "story time", "playground", "family day", "baby", "toddler",
        "children", "kids", "亲子", "儿童",
    )):
        return "亲子·公园"
    if any(k in blob for k in (
        "tai chi", "zumba", "swim", "yoga", "fitness", "hiking", "basketball", "tennis", "boot camp",
    )):
        return "健身·户外"
    if category in ("entertainment", "culture", "arts", "parade_festival", "history", "pet", "animal"):
        return "文化·节庆"
    if any(k in blob for k in (
        "concert", "festival", "film", "movies under", "parade", "art", "museum", "comedy",
        "juneteenth", "food tour", "stand-up", "cultural exchange", "宠物", "adopt",
    )):
        return "文化·节庆"
    if category in ("volunteer", "charity") and "volunteer" in blob:
        return "公益·义工"
    if category == "community" and "volunteer" in blob:
        return "公益·义工"
    return None


def infer_module_from_event(ev: Any, src: dict[str, Any] | None = None) -> str:
    """Map a CommunityEvent (+ optional source config) to hub module zh name."""
    blob = f"{getattr(ev, 'title', '')} {getattr(ev, 'description', '') or ''} {getattr(ev, 'url', '') or ''}"
    if src:
        blob += f" {(src.get('name_zh') or '')} {(src.get('name_en') or '')}"
    url = (getattr(ev, "url", "") or "").lower()
    category = getattr(ev, "category", "") or (src or {}).get("category", "")
    source_id = getattr(ev, "source", "") or ""

    hit = _module_from_blob(blob.lower(), url, category, source_id)
    if hit:
        return hit
    if "html/dot/" in url or "/motorist/truck" in url:
        return "交通·出行"
    return MODULE_BY_CATEGORY.get(category, MODULE_BY_CATEGORY.get((src or {}).get("category", ""), "文化·节庆"))


def is_deal_item(item: dict[str, Any]) -> bool:
    """Commercial promo / affiliate deal — not a livelihood community item."""
    if item.get("content_kind") == "deal":
        return True
    module = (item.get("module") or "").strip()
    if module in DEAL_MODULE_NAMES:
        return True
    url = (item.get("url") or "").lower()
    if any(m in url for m in DEAL_URL_MARKERS):
        return True
    blob = _blob_parts(item)
    if "slickdeals" in blob or "bensbargains" in blob or "techbargains" in blob:
        return True
    title = (item.get("title_zh") or item.get("title_en") or "").strip()
    if title.startswith("🔥") and any(k in blob for k in ("$", "deal", "折扣", "coupon", "free shipping")):
        return True
    return False


def normalize_deal_item(item: dict[str, Any]) -> dict[str, Any]:
    out = dict(item)
    out["module"] = DEAL_MODULE_ZH
    out["content_kind"] = "deal"
    out["date_kind"] = "deal"
    out["score"] = min(int(out.get("score") or 0), 30)
    return out


def split_livelihood_and_deals(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    livelihood: list[dict[str, Any]] = []
    deals: list[dict[str, Any]] = []
    seen_deal_urls: set[str] = set()
    for item in items:
        if is_deal_item(item):
            u = (item.get("url") or "").strip().rstrip("/")
            if u and u in seen_deal_urls:
                continue
            if u:
                seen_deal_urls.add(u)
            deals.append(normalize_deal_item(item))
        else:
            livelihood.append(item)
    return livelihood, deals


_STALE_LEGACY_BUCKETS = frozenset({"亲子·活动", "语言·就业", "福利·政务", "公益义工"})


def infer_hub_module(item: dict[str, Any]) -> str:
    """Content-aware module for an existing hub card."""
    blob = _blob_parts(item)
    url = (item.get("url") or "").lower()

    hit = _module_from_blob(blob, url)
    if hit:
        return hit

    legacy = item.get("module") or ""
    if legacy in LEGACY_MODULE_MAP and legacy not in _STALE_LEGACY_BUCKETS:
        return LEGACY_MODULE_MAP[legacy]
    if legacy in MODULE_ZH_SET and legacy not in _STALE_LEGACY_BUCKETS:
        return legacy
    return "文化·节庆"


def is_hub_junk(item: dict[str, Any]) -> bool:
    title = (item.get("title_zh") or item.get("title_en") or "").strip()
    t_lower = title.lower()
    url = (item.get("url") or "").lower()

    if not title or len(title) < 4:
        return True
    if t_lower in _JUNK_TITLES or title in _JUNK_TITLES:
        return True
    for pat in _JUNK_TITLE_PATTERNS:
        if re.search(pat, t_lower, re.I):
            return True
    if "/events/archive/" in url and not re.search(r"/events/[^/]+-[^/]+", url):
        return True
    if url.endswith("/events") or url.endswith("/events/"):
        return True
    if "contact-us" in url and title in ("资源", "Resources"):
        return True
    if re.match(r"^https?://[^/]+/main/(services|about)", url):
        return True
    if "/html/dot/" in url and ".pdf" in url and "truck" in url:
        return True
    if "eventdata" in url or "marker.link" in url or "google_translate" in url:
        return True
    if "sitemap" in url or url.rstrip("/").endswith("/sitemap"):
        return True
    if title in ("社区与经济赋权", "Community & Economic Empowerment") and "/cpc-front" in url:
        return True
    return False


def normalize_hub_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for item in items:
        if is_deal_item(item):
            continue
        if is_hub_junk(item):
            continue
        url = (item.get("url") or "").strip().rstrip("/")
        if url in seen_urls:
            continue
        seen_urls.add(url)
        item = dict(item)
        item["module"] = infer_hub_module(item)
        item = enrich_hub_item_dates(item)
        out.append(item)
    return out


_SERVICE_URL_MARKERS = (
    "/main/", "/help/", "/services/", "/benefits", "/programs/",
    "/contact", "/about", "/apply-for", "/get-assistance",
)

_EVENT_URL_MARKERS = (
    "/events/20", "eventbrite.com/e/", "eventbrite.com/d/",
)


def is_dated_event_url(url: str) -> bool:
    u = (url or "").lower()
    if re.search(r"/events/20\d{2}/\d{2}/\d{2}/", u):
        return True
    return any(m in u for m in _EVENT_URL_MARKERS)


def is_service_info_url(url: str) -> bool:
    u = (url or "").lower()
    if is_dated_event_url(u):
        return False
    return any(m in u for m in _SERVICE_URL_MARKERS)


def event_date_from_url(url: str) -> str:
    m = re.search(r"/events/(20\d{2})/(\d{2})/(\d{2})/", url or "")
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


def enrich_hub_item_dates(item: dict[str, Any], *, published_at: str | None = None) -> dict[str, Any]:
    """Split event schedule vs source publish time on a hub card."""
    item = dict(item)
    pub = (published_at if published_at is not None else item.get("published_at") or "")[:10]
    item["published_at"] = pub

    url = item.get("url") or ""
    url_date = event_date_from_url(url)
    raw_event = (item.get("event_date") or item.get("date") or "").strip()[:10]

    if url_date:
        event_date = url_date
        item["event_date_source"] = "url"
    elif is_service_info_url(url):
        event_date = ""
        item["event_date_source"] = "none"
    elif raw_event and raw_event != pub:
        event_date = raw_event
        item["event_date_source"] = "listing"
    elif raw_event and is_dated_event_url(url):
        event_date = raw_event
        item["event_date_source"] = "listing"
    elif raw_event and not is_service_info_url(url):
        event_date = raw_event
        item["event_date_source"] = "listing"
    else:
        event_date = ""
        item["event_date_source"] = "none"

    item["event_date"] = event_date
    item["date"] = event_date
    if item.get("event_time") is None:
        item["event_time"] = ""
    item["date_kind"] = "event" if event_date else "service"
    return item


def _anchor_to_hub_item(anchor: dict[str, Any], idx: int) -> dict[str, Any]:
    """Convert a curated channel anchor into a hub card (ongoing service / official page)."""
    module = anchor["module"]
    title_zh = anchor["title_zh"]
    url = anchor["url"]
    summary_zh = anchor.get("summary_zh") or f"官方民生信息页，详情以官网为准。（来源：{anchor.get('source_zh', '官方')}）"
    guide_zh = (
        "1. 点击“直达官方页面”打开原始页面；<br>"
        "2. 页面为英文时，可在浏览器右键选择“翻译成中文”（Chrome）或使用地址栏翻译按鈕；<br>"
        "3. 查找 Apply / Enroll / Contact / Sign up 等入口；<br>"
        "4. 以官网最新信息为准。"
    )
    item = {
        "id": f"anchor_{idx:03d}",
        "module": module,
        "city": "纽约",
        "borough": anchor.get("borough", "Citywide"),
        "area_zh": anchor.get("area_zh", "纽约全市"),
        "area_zht": anchor.get("area_zht", "紐約全市"),
        "area_en": anchor.get("area_en", "NYC Citywide"),
        "event_date": "",
        "event_time": "",
        "published_at": "",
        "source_published_at": "",
        "date": "",
        "date_kind": "service",
        "score": int(anchor.get("score", 35)),
        "relevance": 3,
        "title_zh": title_zh,
        "title_zht": anchor.get("title_zht") or title_zh,
        "title_en": anchor.get("title_en") or title_zh,
        "summary_zh": summary_zh,
        "summary_zht": anchor.get("summary_zht") or summary_zh,
        "summary_en": anchor.get("summary_en") or summary_zh,
        "url": url,
        "guide_zh": guide_zh,
        "guide_zht": guide_zh,
        "guide_en": guide_zh,
        "location_kind": "citywide",
        "location_tag_zh": "全市",
        "location_tag_zht": "全市",
        "location_tag_en": "Citywide",
        "content_kind": "anchor",
    }
    return enrich_hub_item_dates(item)


def ensure_module_coverage(
    items: list[dict[str, Any]],
    anchors: list[dict[str, Any]],
    *,
    min_per_module: int = 4,
    max_total: int | None = None,
) -> list[dict[str, Any]]:
    """Backfill empty 12-channel modules with curated official anchors."""
    from collections import Counter

    out = list(items)
    seen_urls = {(i.get("url") or "").strip().rstrip("/") for i in out}
    counts = Counter(i.get("module") for i in out)
    by_mod: dict[str, list[dict[str, Any]]] = {}
    for a in anchors:
        by_mod.setdefault(a["module"], []).append(a)

    idx = len(out) + 1
    for mod in [m["zh"] for m in HUB_MODULES]:
        need = max(0, min_per_module - counts.get(mod, 0))
        if need <= 0:
            continue
        for anchor in by_mod.get(mod, [])[:need]:
            url = (anchor.get("url") or "").strip().rstrip("/")
            if not url or url in seen_urls:
                continue
            out.append(_anchor_to_hub_item(anchor, idx))
            seen_urls.add(url)
            counts[mod] = counts.get(mod, 0) + 1
            idx += 1
            if max_total and len(out) >= max_total:
                return out
    return out
