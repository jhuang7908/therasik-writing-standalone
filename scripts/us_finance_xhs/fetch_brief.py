#!/usr/bin/env python3

"""Fetch US finance headlines + market snapshot for XHS brief (free RSS/Yahoo)."""

from __future__ import annotations



import json

import re

import xml.etree.ElementTree as ET

from datetime import datetime, timezone

from pathlib import Path

from typing import Any

from urllib.error import URLError

from urllib.request import Request, urlopen



_PKG = Path(__file__).resolve().parent

_USER_AGENT = "InSynBio-FinanceXHS/1.1 (+https://insynbio.com)"



_YAHOO_SYMBOLS = {

    "^GSPC": "S&P 500",

    "^DJI": "道琼斯",

    "^IXIC": "纳斯达克",

    "^TNX": "10年期美债收益率",

    "GC=F": "黄金期货",

    "CL=F": "WTI原油",

}



_YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols}"

_YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"

# FRED keyless CSV endpoint (no API key needed). Frequency per series.
_FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"

# Mortgage rate series:
#  - OBMMIC30YF: Optimal Blue 30Y Fixed Conforming, DAILY (nightly, prior-day locks; weekdays only)
#  - MORTGAGE30US: Freddie Mac PMMS 30Y, WEEKLY (published Thursdays)
_FRED_MORTGAGE_SERIES = {
    "obmmi_30y": {
        "series": "OBMMIC30YF",
        "label": "30年固定房贷（Optimal Blue 日频）",
        "freq": "daily",
        "source": "FRED · Optimal Blue OBMMI (OBMMIC30YF)",
    },
    "freddie_30y": {
        "series": "MORTGAGE30US",
        "label": "30年固定房贷（房地美 PMMS 周值）",
        "freq": "weekly_thu",
        "source": "FRED · Freddie Mac PMMS (MORTGAGE30US)",
    },
}

_YAHOO_NEWS_RSS = (

    "https://feeds.finance.yahoo.com/rss/2.0/headline?"

    "s=^GSPC,^DJI,^TNX,GC=F&region=US&lang=en-US"

)

_YAHOO_HOUSING_RSS = (

    "https://feeds.finance.yahoo.com/rss/2.0/headline?"

    "s=MORTGAGE,RATE,HOOD,^TNX&region=US&lang=en-US"

)



# Higher = more relevant for 北美华人圈 + dai款/房产

_HEADLINE_SCORE_KEYWORDS: list[tuple[str, int]] = [

    (r"mortgage|housing|home price|real estate|rent|refinanc", 14),

    (r"iran|israel|hezbollah|geopolit|middle east|war", 13),

    (r"oil price|crude|wti|\$150 oil|inflation worry", 12),

    (r"selloff|sell-off|rout|plunge|sink|tumble|rebound", 11),

    (r"semiconductor|chip stock|ai trade|tech sector", 11),

    (r"fed|rate cut|rate hike|treasury|yield|bond|payroll|jobs", 10),

    (r"tariff|trade|china|immigration|inflation|cpi", 8),

    (r"nasdaq|s&p|dow|stock market today|gold", 7),

    (r"commercial|sba|small business|cre", 9),

]

_HEADLINE_SCORE_PENALTIES: list[tuple[str, int]] = [

    (r"robinhood stocks|best .* stocks under|bull case for", -18),

    (r"credit rating upgrade.*bull|deliveries surge|why .* stock", -12),

    (r"can .* save .* stock|fading blockbusters", -10),

]





def _http_get(url: str, *, timeout: int = 25) -> bytes:

    req = Request(

        url,

        headers={

            "User-Agent": _USER_AGENT,

            "Accept": "application/json,text/plain,*/*",

        },

    )

    with urlopen(req, timeout=timeout) as resp:

        return resp.read()





def _fetch_chart_quote(symbol: str, label: str) -> dict[str, Any] | None:

    try:

        raw = _http_get(_YAHOO_CHART_URL.format(symbol=symbol.replace("^", "%5E")))

        data = json.loads(raw.decode("utf-8", errors="replace"))

        meta = (data.get("chart") or {}).get("result") or []

        if not meta:

            return None

        m = meta[0].get("meta") or {}

        price = m.get("regularMarketPrice") or m.get("previousClose")

        if price is None:

            return None

        prev = m.get("chartPreviousClose") or m.get("previousClose")

        chg_pct = None

        if prev and prev != 0:

            chg_pct = round((float(price) - float(prev)) / float(prev) * 100, 2)

        return {

            "symbol": symbol,

            "label": label,

            "price": price,

            "change_pct": chg_pct,

            "currency": m.get("currency") or "USD",

            "market_state": m.get("marketState") or "",

            "source": "Yahoo Finance (chart)",

        }

    except (URLError, json.JSONDecodeError, KeyError, TypeError, ValueError):

        return None





def _fetch_fred_latest(series: str) -> dict[str, Any] | None:
    """Return latest non-empty observation {date, value} from FRED keyless CSV.

    No fabrication: returns None on any failure so callers can omit the number.
    """
    try:
        raw = _http_get(_FRED_CSV_URL.format(series=series), timeout=25)
    except (URLError, ValueError, OSError):
        return None
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    rows = text.splitlines()
    if len(rows) < 2:
        return None
    # Header is "observation_date,<SERIES>" (older: "DATE,<SERIES>"); data rows
    # may use "." for missing values. Walk from the end for the latest real value.
    last: dict[str, Any] | None = None
    prev: dict[str, Any] | None = None
    for line in rows[1:]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        date_s = parts[0].strip()
        val_s = parts[1].strip()
        if not date_s or val_s in ("", "."):
            continue
        try:
            val = round(float(val_s), 3)
        except ValueError:
            continue
        prev = last
        last = {"date": date_s, "value": val}
    if last is None:
        return None
    if prev is not None and prev.get("value") is not None:
        last["prev_value"] = prev["value"]
        last["change_bp"] = round((last["value"] - prev["value"]) * 100, 1)
        last["prev_date"] = prev["date"]
    return last


def fetch_mortgage_rates() -> dict[str, Any]:
    """Fetch daily (OBMMI) + weekly (Freddie Mac) 30Y mortgage rates from FRED.

    Returns a dict keyed by rate id; missing series are simply absent (never
    fabricated). Each entry carries value, date, source, label, freq.
    """
    out: dict[str, Any] = {}
    for key, spec in _FRED_MORTGAGE_SERIES.items():
        obs = _fetch_fred_latest(spec["series"])
        if not obs:
            continue
        out[key] = {
            "series": spec["series"],
            "label": spec["label"],
            "freq": spec["freq"],
            "source": spec["source"],
            "value": obs["value"],
            "date": obs["date"],
            "value_pct": obs["value"],
            "prev_value": obs.get("prev_value"),
            "prev_date": obs.get("prev_date"),
            "change_bp": obs.get("change_bp"),
        }
    return out


def _parse_rss_items(xml_bytes: bytes, *, limit: int = 12) -> list[dict[str, str]]:

    root = ET.fromstring(xml_bytes)

    items: list[dict[str, str]] = []

    for item in root.findall(".//item")[:limit]:

        title = (item.findtext("title") or "").strip()

        link = (item.findtext("link") or "").strip()

        pub = (item.findtext("pubDate") or "").strip()

        desc = re.sub(r"<[^>]+>", "", item.findtext("description") or "").strip()

        if title:

            items.append({"title": title, "link": link, "pubDate": pub, "summary": desc[:400]})

    return items





def _score_headline(item: dict[str, str]) -> int:

    blob = f"{item.get('title', '')} {item.get('summary', '')}".lower()

    score = 0

    for pat, pts in _HEADLINE_SCORE_KEYWORDS:

        if re.search(pat, blob, re.IGNORECASE):

            score += pts

    for pat, pts in _HEADLINE_SCORE_PENALTIES:

        if re.search(pat, blob, re.IGNORECASE):

            score += pts

    return score





def _dedupe_headlines(items: list[dict[str, str]]) -> list[dict[str, str]]:

    seen: set[str] = set()

    out: list[dict[str, str]] = []

    for h in items:

        key = re.sub(r"\W+", "", (h.get("title") or "").lower())[:80]

        if not key or key in seen:

            continue

        seen.add(key)

        out.append(h)

    return out





def rank_headlines(headlines: list[dict[str, str]]) -> list[dict[str, str]]:

    enriched = []

    for h in headlines:

        row = dict(h)

        row["relevance_score"] = _score_headline(h)

        enriched.append(row)

    enriched.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    return enriched





def fetch_yahoo_quotes() -> list[dict[str, Any]]:

    symbols = ",".join(_YAHOO_SYMBOLS)

    out: list[dict[str, Any]] = []

    try:

        raw = _http_get(_YAHOO_QUOTE_URL.format(symbols=symbols))

        data = json.loads(raw.decode("utf-8", errors="replace"))

        for q in data.get("quoteResponse", {}).get("result") or []:

            sym = q.get("symbol") or ""

            label = _YAHOO_SYMBOLS.get(sym, sym)

            price = q.get("regularMarketPrice")

            chg_pct = q.get("regularMarketChangePercent")

            if price is None:

                continue

            out.append(

                {

                    "symbol": sym,

                    "label": label,

                    "price": price,

                    "change_pct": round(chg_pct, 2) if chg_pct is not None else None,

                    "currency": q.get("currency") or "USD",

                    "market_state": q.get("marketState") or "",

                    "source": "Yahoo Finance",

                }

            )

    except (URLError, json.JSONDecodeError, KeyError):

        out = []



    if out:

        return out



    for sym, label in _YAHOO_SYMBOLS.items():

        row = _fetch_chart_quote(sym, label)

        if row:

            out.append(row)

    return out





def quotes_lookup(quotes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:

    """Map symbol → quote row; add value_pct for ^TNX."""

    out: dict[str, dict[str, Any]] = {}

    for q in quotes:

        sym = q.get("symbol") or ""

        row = dict(q)

        if sym == "^TNX" and row.get("price") is not None:

            row["value_pct"] = round(float(row["price"]), 3)

        out[sym] = row

    return out





def fetch_headlines(*, limit: int = 14) -> list[dict[str, str]]:

    merged: list[dict[str, str]] = []

    for url in (_YAHOO_NEWS_RSS, _YAHOO_HOUSING_RSS):

        try:

            raw = _http_get(url)

            merged.extend(_parse_rss_items(raw, limit=limit))

        except (URLError, ET.ParseError):

            continue

    return rank_headlines(_dedupe_headlines(merged))[:limit]





def pick_layout_variant(*, run_index: int | None = None) -> dict[str, str]:

    variants = json.loads((_PKG / "layout_variants.json").read_text(encoding="utf-8"))

    if not variants:

        return {"id": "sticker_grid", "label": "贴纸九宫格", "card1_hint": "", "card2_hint": ""}

    idx = run_index if run_index is not None else datetime.now(timezone.utc).toordinal()

    return variants[idx % len(variants)]





def build_brief_markdown(

    *,

    loan_topic: dict[str, str],

    quotes: list[dict[str, Any]] | None = None,

    headlines: list[dict[str, str]] | None = None,

    layout_variant: dict[str, str] | None = None,

    edition_theme: str = "dual",

    archive_headlines: list[dict[str, str]] | None = None,

    mortgage: dict[str, Any] | None = None,

) -> str:

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    local_date = datetime.now().strftime("%m/%d/%Y")

    is_thursday = datetime.now().weekday() == 3

    quotes = quotes if quotes is not None else fetch_yahoo_quotes()

    headlines = headlines if headlines is not None else fetch_headlines()

    mortgage = mortgage if mortgage is not None else fetch_mortgage_rates()

    if archive_headlines:

        headlines = rank_headlines(_dedupe_headlines(headlines + archive_headlines))

    layout_variant = layout_variant or pick_layout_variant()



    lines = [

        f"# 北美华人圈 · 财经与 dai款 新闻简报",

        f"*生成时间：{now}*",

        "",

        "## 市场快照（来源：Yahoo Finance）",

        "",

    ]

    if quotes:

        for q in quotes:

            chg = q.get("change_pct")

            chg_s = f"{chg:+.2f}%" if chg is not None else "n/a"

            lines.append(

                f"- **{q['label']}** ({q['symbol']}): {q['price']} {q['currency']} "

                f"({chg_s}) [{q['source']}]"

            )

    else:

        lines.append("- 行情抓取失败，请勿编造具体点位。")



    # 房贷与利率：日频 OBMMI + 周四房地美官方周值（数据仅来自 FRED，缺失即不写）

    tnx = next((q for q in quotes if q.get("symbol") == "^TNX"), None)

    lines += ["", "## 房贷与利率（来源：FRED，数值唯一可信来源）", ""]

    if tnx and tnx.get("price") is not None:

        lines.append(

            f"- **10年期美债收益率**（房贷先行指标）：{round(float(tnx['price']), 3)}%"

        )

    obmmi = mortgage.get("obmmi_30y")

    freddie = mortgage.get("freddie_30y")

    if obmmi:

        chg = obmmi.get("change_bp")

        chg_s = f"，较上一交易日 {chg:+.1f}bp" if chg is not None else ""

        lines.append(

            f"- **30年固定房贷·日频**（Optimal Blue OBMMI）：{obmmi['value']}%"

            f"（数据日 {obmmi['date']}{chg_s}）"

        )

    if freddie:

        chg = freddie.get("change_bp")

        chg_s = f"，较上周 {chg:+.1f}bp" if chg is not None else ""

        thu_tag = "（本周四官方更新）" if is_thursday else "（最近一期周值）"

        lines.append(

            f"- **30年固定房贷·官方周值**（房地美 PMMS）：{freddie['value']}%"

            f"（数据日 {freddie['date']}{chg_s}）{thu_tag}"

        )

    if not obmmi and not freddie:

        lines.append("- 房贷数据抓取失败，禁止编造任何房贷利率数字，仅可定性描述方向。")

    lines += [

        "",

        "**房贷走势分析口径（给内容生成器）：** 仅依据上方 10年期美债与房贷数字，"

        "说明今日数据对房贷利率的方向性影响（上行/下行/持平压力）；"

        "若周四有房地美新值，须点出本周官方房贷利率；无具体数字时只可定性，禁止编造数值。",

    ]



    lines += [

        "",

        "## 近一月要闻池（北美华人相关，已排序；卡1 可任选其一讲故事）",

        "",

    ]

    if headlines:

        for i, h in enumerate(headlines[:20], 1):

            score = h.get("relevance_score", 0)

            seen = h.get("first_seen") or h.get("pubDate") or ""

            lines.append(f"{i}. **{h['title']}**（相关度 {score}）")

            if seen:

                lines.append(f"   - 收录: {seen}")

            if h.get("summary"):

                lines.append(f"   - {h['summary'][:280]}")

            if h.get("link"):

                lines.append(f"   - 链接: {h['link']}")

        top = headlines[0]

        lines += [

            "",

            f"**卡1 故事首选：** {top.get('title', '')}",

            "（用讲故事口吻：这事咋发生的、跟北美华人钱包有啥关系、一句幽默评论；可选用近一月内其他条目）",

        ]

    else:

        lines.append("- 新闻 RSS 抓取失败，卡1 仅写市场快照，勿编造头条。")



    cat = loan_topic.get("category") or "residential"

    cat_label = "住宅房dai" if cat == "residential" else "商业房dai"

    lines += [

        "",

        "## 本期 dai款 知识专题（轮换）",

        "",

        f"- **主题：** {loan_topic.get('title', '')}",

        f"- **类别：** {cat_label}",

        f"- **要点：** {loan_topic.get('focus', '')}",

        "",

        "## 本期配图版式（形式微变，风格不变）",

        "",

        f"- **版式 ID：** {layout_variant.get('id', '')}（{layout_variant.get('label', '')}）",

        f"- **卡1 构图：** {layout_variant.get('card1_hint', '')}",

        f"- **卡2 构图：** {layout_variant.get('card2_hint', '')}",

        "",

        "## 写作要求（给内容生成器）",

        "",

        "1. 简体中文；幽默生活化；**去 AI 味**；面向北美华人圈。",

        "2. **cards 恰好 2 张**：卡1=cover 财经故事/新闻；卡2=content 本期 dai款 知识。",

        f"3. **卡1**：从「近一月要闻池」选一条讲故事+评论（优先「卡1 故事首选」）；数字仅用简报。",

        f"4. **卡2**：本期知识「{loan_topic.get('title', '')}」（{cat_label}），通俗科普，不是借贷广告。",

        "5. 全文禁止「贷款」「房贷」「商业贷款」；用 dai款、房dai、商业房dai。",

        "6. bullets 用阿拉伯数字 1/2/3 编号。",

        "7. 禁止编造未出现在简报中的 Fed 决议细节或价格。",

        f"8. 配图页脚日期可写「截至{local_date}」。",

        "9. **房贷走势**：用「房贷与利率」段的真实数字，点评今日数据对房dai利率的方向影响；"

        "周四若有房地美新值要提及；无数字只可定性，绝不编造利率。",

        "10. **股市**：可顺带一句点评三大股指今日表现，数字只用「市场快照」里的，不得自造点位/涨跌幅。",

        "11. **数字纪律（硬性）**：正文出现的任何百分比、点位、利率，必须能在本简报中找到对应数字；"

        "找不到来源的具体数值一律不得出现（会被数字校验闸门拦截、不予发送）。",

    ]

    return "\n".join(lines) + "\n"





def pick_edition_theme(*, run_index: int | None = None) -> str:

    """Legacy hook — dual-card mode always uses cover+content."""

    return "dual"

