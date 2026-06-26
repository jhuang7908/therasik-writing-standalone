#!/usr/bin/env python3
"""Fetch compact US market snapshot for NYC Chinese Life Hub header."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]

# Symbols shown in hub header (compact strip)
HUB_MARKET_SYMBOLS: dict[str, str] = {
    "^GSPC": "标普",
    "^IXIC": "纳指",
    "^TNX": "10Y",
    "GC=F": "黄金",
}


HUB_MORTGAGE_SERIES = "OBMMIC30YF"
HUB_MORTGAGE_LABEL = "30Y房贷"


def _fetch_fred_obmmi(*, timeout: int = 60) -> dict[str, Any] | None:
    """Latest OBMMI 30Y fixed conforming rate from FRED CSV (daily)."""
    from urllib.error import URLError
    from urllib.request import Request, urlopen

    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={HUB_MORTGAGE_SERIES}"
    try:
        req = Request(url, headers={"User-Agent": "InSynBio-Hub/1.0", "Accept": "text/csv,*/*"})
        raw = urlopen(req, timeout=timeout).read().decode("utf-8", errors="replace").strip()
    except (URLError, OSError, TimeoutError, ValueError):
        return None
    rows = raw.splitlines()
    if len(rows) < 2:
        return None
    last: dict[str, Any] | None = None
    prev: dict[str, Any] | None = None
    for line in rows[1:]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        date_s, val_s = parts[0].strip(), parts[1].strip()
        if not date_s or val_s in ("", "."):
            continue
        try:
            val = round(float(val_s), 3)
        except ValueError:
            continue
        prev, last = last, {"date": date_s, "value": val}
    if last is None:
        return None
    if prev is not None:
        last["change_bp"] = round((last["value"] - prev["value"]) * 100, 1)
    return last


def fetch_hub_market_snapshot() -> dict[str, Any]:
    """Return {as_of, tz, quotes:[...], mortgage:{...}?}."""
    tz = ZoneInfo("America/New_York")
    as_of = datetime.now(tz).strftime("%Y-%m-%d %H:%M ET")
    quotes: list[dict[str, Any]] = []
    mortgage: dict[str, Any] | None = None

    try:
        from us_finance_xhs.fetch_brief import fetch_mortgage_rates, fetch_yahoo_quotes  # noqa: WPS433

        raw = fetch_yahoo_quotes()
        by_sym = {q.get("symbol"): q for q in raw if q.get("symbol")}
        for sym, label in HUB_MARKET_SYMBOLS.items():
            q = by_sym.get(sym) or {}
            quotes.append(
                {
                    "kind": "index",
                    "symbol": sym,
                    "label": label,
                    "change_pct": q.get("change_pct"),
                    "price": q.get("price"),
                }
            )

        rates = fetch_mortgage_rates()
        obmmi = rates.get("obmmi_30y")
        if not obmmi:
            obmmi_raw = _fetch_fred_obmmi()
            if obmmi_raw:
                obmmi = {
                    "series": HUB_MORTGAGE_SERIES,
                    "value": obmmi_raw["value"],
                    "date": obmmi_raw["date"],
                    "change_bp": obmmi_raw.get("change_bp"),
                }
        if obmmi and obmmi.get("value") is not None:
            mortgage = {
                "kind": "mortgage",
                "series": obmmi.get("series") or "OBMMIC30YF",
                "label": "30Y房贷",
                "value_pct": obmmi.get("value"),
                "date": obmmi.get("date") or "",
                "change_bp": obmmi.get("change_bp"),
                "source": "FRED·OBMMI",
            }
            quotes.append(
                {
                    "kind": "mortgage",
                    "symbol": "OBMMIC30YF",
                    "label": "30Y房贷",
                    "value_pct": obmmi.get("value"),
                    "change_bp": obmmi.get("change_bp"),
                    "date": obmmi.get("date"),
                }
            )
    except Exception:
        for sym, label in HUB_MARKET_SYMBOLS.items():
            quotes.append(
                {"kind": "index", "symbol": sym, "label": label, "change_pct": None, "price": None}
            )

    out: dict[str, Any] = {"as_of": as_of, "tz": "America/New_York", "quotes": quotes}
    if mortgage:
        out["mortgage"] = mortgage
    return out


def write_hub_market_json(out_path: Path, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    snap = snapshot or fetch_hub_market_snapshot()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snap, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return snap


def fetch_hub_weather_snapshot(*, timeout: int = 15) -> dict[str, Any]:
    """NYC current weather from Open-Meteo (server-side, embedded in hub HTML)."""
    from urllib.error import URLError
    from urllib.parse import urlencode
    from urllib.request import Request, urlopen

    tz = ZoneInfo("America/New_York")
    as_of = datetime.now(tz).strftime("%Y-%m-%d %H:%M ET")
    params = urlencode(
        {
            "latitude": 40.7143,
            "longitude": -74.006,
            "current_weather": "true",
            "timezone": "America/New_York",
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    try:
        req = Request(url, headers={"User-Agent": "InSynBio-Hub/1.0", "Accept": "application/json"})
        raw = urlopen(req, timeout=timeout).read().decode("utf-8")
        data = json.loads(raw)
        cw = data.get("current_weather") or {}
        temp = cw.get("temperature")
        if temp is None:
            raise ValueError("no temperature")
        return {
            "as_of": as_of,
            "tz": "America/New_York",
            "city": "纽约",
            "temp_c": round(float(temp), 1),
            "code": int(cw.get("weathercode") or 0),
        }
    except (URLError, OSError, TimeoutError, ValueError, json.JSONDecodeError, TypeError):
        return {"as_of": as_of, "tz": "America/New_York", "city": "纽约", "temp_c": None, "code": 0}


def write_hub_weather_json(out_path: Path, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    snap = snapshot or fetch_hub_weather_snapshot()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snap, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return snap


if __name__ == "__main__":
    p = ROOT / "insynbio-web-source" / "hub_market_snapshot.json"
    snap = write_hub_market_json(p)
    print(json.dumps(snap, ensure_ascii=False, indent=2))
