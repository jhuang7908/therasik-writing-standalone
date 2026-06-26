from __future__ import annotations

import re
from typing import Iterable

from nyc_community_events.models import CommunityEvent

# ── Category keyword rules (English; Chinese titles matched separately) ──────

_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    # 老人关怀 — Senior services (checked first for specificity)
    ("senior", (
        "senior", "elder", "aging", "dfta", "scrie", "drie", "home care", "case management",
        "senior center", "lunch program", "meals on wheels", "老人", "长者", "老年", "老年人",
        "敬老", "乐龄", "银龄",
    )),
    # 宠物领养 — Pet adoption
    ("pet", (
        "adopt", "adoption", "rescue", "foster pet", "animal care center",
        "kitten", "puppy", "animal shelter", "nycacc",
        "领养", "收养", "猫", "狗", "宠物", "动物收容",
    )),
    # 福利类 — Medicaid / SNAP / food / unemployment
    ("healthcare", (
        "medicaid", "white card", "essential plan", "申请白卡", "白卡",
        "health insurance", "health coverage", "chip",
    )),
    ("food_benefit", (
        "snap", "food stamp", "food bank", "food pantry", "free food", "emergency food",
        "粮食券", "粮食银行", "食物银行", "免费食物", "食品援助",
    )),
    ("employment_benefit", (
        "unemployment", "unemployment insurance", "jobless benefit", "job loss",
        "失业金", "失业保险", "申请失业",
    )),
    # 交通出行
    ("transit", (
        "subway", "mta", "bus route", "service change", "planned work", "detour",
        "lirr", "metro north", "train delay", "地铁", "公交", "路线变更", "改线", "延误", "施工",
        "小巴", "华人小巴", "线路公告",
    )),
    # 义工志愿
    ("volunteer", (
        "volunteer", "volunteering", "community service", "nyc service",
        "义工", "志愿者", "义务服务",
    )),
    # 就业招聘
    ("employment", (
        "job fair", "career fair", "hiring", "recruitment", "job training", "workforce",
        "招聘", "求职", "职业博览会", "就业",
    )),
    # 活动休闲 — before education (continuing-education swim was misclassified)
    ("recreation", (
        "pool", "swim", "fitness", "zumba", "kids in motion", "playground",
        "family day", "story time", "nycgovparks.org/events",
        "泳池", "健身", "亲子", "公园",
    )),
    ("enrollment", ("registration", "register", "enroll", "signup", "sign-up", "open house", "招生", "报名", "注册", "入学")),
    ("parade_festival", ("parade", "festival", "celebration", "gala", "游行", "节庆", "嘉年华", "庙会", "龙舟")),
    ("education", ("class", "workshop", "lecture", "seminar", "citizenship", "esl", "english as a second", "language", "school", "library", "adult education", "continuing education", "ged", "tasc", "literacy", "digital skills", "cuny", "vocational", "certificate program", "学习", "讲座", "中文", "语言", "图书馆", "继续教育", "成人教育", "职业培训", "入籍")),
    ("welfare", ("benefit", "tax", "medicaid", "snap", "wic", "housing", "immigrant", "resource fair", "福利", "报税", "医保", "粮食券", "住房")),
    ("safety", ("nypd", "police", "safety", "scam", "fraud", "anti-hate", "警", "安全", "防诈骗")),
    ("culture", ("concert", "exhibition", "gallery", "performance", "music", "art show", "展览", "音乐会", "演出")),
    ("civic", ("council", "councilmember", "town hall", "community board", "议员", "市政", "社区委员会")),
    ("charity", ("fundraiser", "charity", "bake sale", "义卖", "公益")),
    ("food_promo", ("tasting", "grand opening", "discount", "promotion", "探店", "促销", "开幕")),
]

_ROUTINE_PATTERNS = (
    r"\bkids in motion\b",
    r"\bshape up nyc\b",
    r"\bline dance fitness\b",
    r"\bzumba\b",
)

_MAJOR_BOOST: list[tuple[int, tuple[str, ...]]] = [
    (40, ("parade", "festival", "dragon boat", "lunar new year", "游行", "节庆", "龙舟", "春节")),
    (38, ("medicaid", "white card", "snap enrollment", "申请白卡", "粮食券申请",
          "unemployment insurance", "失业金申请", "失业保险")),
    (35, ("registration", "enroll", "signup", "open house", "deadline", "招生", "报名", "截止",
          "free esl", "free english", "free class", "free course", "免费课程", "免费英语",
          "adopt a dog", "adopt a cat", "pet adoption", "领养猫", "领养狗")),
    (32, ("senior benefit", "home care", "senior center", "dfta", "scrie", "meals on wheels",
          "老人福利", "长者服务", "老人中心", "上门护理",
          "food bank", "food pantry", "free food", "粮食银行", "免费食物",
          "volunteer opportunity", "nyc service", "义工招募")),
    (30, ("concert", "gala", "fundraiser", "citizenship", "tax prep", "音乐会", "义卖", "报税",
          "ged", "tasc", "adult literacy", "continuing education", "cuny", "certificate",
          "job training", "digital skills", "继续教育", "职业培训", "入籍准备",
          "subway delay", "service change", "planned work", "地铁延误", "路线变更")),
    (25, ("nypd", "council", "town hall", "lecture", "exhibition", "议员", "讲座", "展览")),
    (20, ("free", "family day", "workshop", "免费", "亲子", "senior", "volunteer", "老人", "义工")),
]

_BOROUGH_KEYWORDS = {
    "Queens": ("queens", "flushing", "elmhurst", "bayside", "forest hills", "corona", "jackson heights", "法拉盛"),
    "Brooklyn": ("brooklyn", "sunset park", "bensonhurst", "bay ridge"),
    "Manhattan": ("manhattan", "chinatown", "华埠", "lower east side"),
    "Bronx": ("bronx",),
    "Staten Island": ("staten island",),
}


def _text_blob(ev: CommunityEvent) -> str:
    parts = [ev.title, ev.description, ev.location, ev.url]
    return " ".join(p for p in parts if p).lower()


def _kw_hit(blob: str, kw: str) -> bool:
    k = kw.lower()
    if k in ("nypd", "police", "警"):
        return bool(re.search(r"\bnypd\b|\bpolice department\b|\bcommunity affairs\b|警察局", blob, re.I))
    if len(k) <= 4 and k.isascii():
        return bool(re.search(rf"\b{re.escape(k)}\b", blob, re.I))
    return k in blob


def infer_category(ev: CommunityEvent) -> str:
    blob = _text_blob(ev)
    for cat, kws in _CATEGORY_RULES:
        if any(_kw_hit(blob, kw) for kw in kws):
            return cat
    return ev.category or "general"


def is_routine(ev: CommunityEvent) -> bool:
    blob = _text_blob(ev)
    return any(re.search(pat, blob, re.I) for pat in _ROUTINE_PATTERNS)


def score_event(ev: CommunityEvent, *, boroughs_preferred: Iterable[str] | None = None) -> CommunityEvent:
    blob = _text_blob(ev)
    reasons: list[str] = []
    score = 0

    ev.category = infer_category(ev)
    ev.routine = is_routine(ev)

    if ev.routine:
        score += 5
        reasons.append("routine_recreation")

    for pts, kws in _MAJOR_BOOST:
        if any(_kw_hit(blob, kw) for kw in kws):
            score += pts
            reasons.append(f"keyword+{pts}")

    if ev.is_free is True or "free" in blob or "免费" in blob:
        score += 10
        reasons.append("free")

    if ev.borough:
        if boroughs_preferred and ev.borough in boroughs_preferred:
            score += 15
            reasons.append(f"borough_{ev.borough}")
    else:
        for boro, kws in _BOROUGH_KEYWORDS.items():
            if any(kw in blob for kw in kws):
                ev.borough = boro
                if boroughs_preferred and boro in boroughs_preferred:
                    score += 15
                    reasons.append(f"borough_{boro}")
                break

    for kw in ("must see", "featured", "annual"):
        if kw in blob:
            score += 20
            reasons.append(kw.replace(" ", "_"))

    if ev.category in ("enrollment", "parade_festival", "welfare", "safety", "civic", "charity",
                        "senior", "pet", "healthcare", "food_benefit", "employment_benefit",
                        "transit", "volunteer"):
        score += 15
        reasons.append(f"category_{ev.category}")

    if any(kw in blob for kw in ("中文", "chinese", "mandarin", "cantonese", "华人", "粤语")):
        score += 20
        reasons.append("chinese_language")

    if any(kw in blob for kw in ("deadline", "截止", "last day", "expires", "最后")):
        score += 25
        reasons.append("deadline_approaching")

    if ev.url and len(ev.url) > 20:
        score += 5
        reasons.append("has_precise_link")

    official_domains = ("nyc.gov", "nycgovparks.org", "queenslibrary.org", "nypl.org",
                        "bklynlibrary.org", "cuny.edu", "qcc.cuny.edu", "laguardia.edu",
                        "bmcc.cuny.edu", "kingsborough.edu", "hostos.cuny.edu", "mta.info")
    if any(d in ev.url for d in official_domains):
        score += 10
        reasons.append("official_source")

    ev.score = score
    ev.score_reasons = reasons
    return ev


def filter_major_events(
    events: list[CommunityEvent],
    *,
    threshold: int = 50,
    exclude_routine: bool = True,
    max_items: int = 12,
) -> list[CommunityEvent]:
    return _filter_scored(events, min_score=threshold, exclude_routine=exclude_routine, max_items=max_items)


def filter_notable_events(
    events: list[CommunityEvent],
    *,
    major: list[CommunityEvent],
    min_score: int = 35,
    max_score: int = 49,
    exclude_routine: bool = True,
    max_items: int = 8,
) -> list[CommunityEvent]:
    major_urls = {e.url for e in major}
    pool = [e for e in events if e.url not in major_urls]
    return _filter_scored(
        pool,
        min_score=min_score,
        max_score=max_score,
        exclude_routine=exclude_routine,
        max_items=max_items,
    )


def _filter_scored(
    events: list[CommunityEvent],
    *,
    min_score: int,
    max_score: int | None = None,
    exclude_routine: bool = True,
    max_items: int,
) -> list[CommunityEvent]:
    ranked = sorted(events, key=lambda e: (e.start_date, -e.score, e.title))
    out: list[CommunityEvent] = []
    for ev in ranked:
        if ev.score < min_score:
            continue
        if max_score is not None and ev.score > max_score:
            continue
        if exclude_routine and ev.routine and ev.score < min_score + 25:
            continue
        out.append(ev)
        if len(out) >= max_items:
            break
    return out
