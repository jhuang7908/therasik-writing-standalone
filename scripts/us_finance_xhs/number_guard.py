#!/usr/bin/env python3
"""Deterministic finance number gate: every rate/point/percent in the copy must
trace back to the fetched data snapshot (FRED + Yahoo). No fabrication ("不能瞎报").

Design (anti-hallucination):
- The ONLY source of numeric truth is the API snapshot (quotes + mortgage rates).
- This module extracts data-like numbers from the generated copy and checks each
  against the snapshot within tolerance. Numbers with no source are violations.
- This is a code-level gate that runs *in addition to* the third-party AI
  consistency review (content_ssot_guard, which already receives the brief).
"""
from __future__ import annotations

import re
from typing import Any

# Numbers we treat as structural (NOT data claims) and never audit.
# e.g. 30年 / 10年期 / 2026年 / 3条 / 2张 / 5个 / 第1 / 25个基点
_WHITELIST_SUFFIX = "年月日周期条卡字个名位章节点钟分秒倍折成档岁"
_BP_SUFFIX = ("基点", "bp", "BP", "個基點", "个基点")

# Percentage: 6.81% / +1.2% / -0.5% / 4.542% — must not match "542%" inside "4.542%"
_PCT_RE = re.compile(r"(?<![\d.])([+\-±]?\d+(?:\.\d+)?)\s*[%％]")
# Index point: 5,432.10 / 43210.55 / 4321.0 (>=4 integer digits w/ decimal, or comma group)
_POINT_RE = re.compile(r"([+\-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{4,}\.\d+)")


def _round_variants(v: float) -> set[float]:
    return {round(v, 3), round(v, 2), round(v, 1), round(abs(v), 2), round(abs(v), 1)}


def build_facts_snapshot(
    quotes: list[dict[str, Any]] | None,
    mortgage: dict[str, Any] | None,
) -> dict[str, Any]:
    """Collect every trusted numeric value (and rounded variants) from the snapshot.

    Returns {"values": set[float], "labels": list[str], "raw": {...}} where
    `values` is the allow-list the copy is checked against.
    """
    values: set[float] = set()
    labels: list[str] = []

    for q in quotes or []:
        price = q.get("price")
        chg = q.get("change_pct")
        label = q.get("label") or q.get("symbol") or ""
        if price is not None:
            try:
                values |= _round_variants(float(price))
            except (TypeError, ValueError):
                pass
        if chg is not None:
            try:
                values |= _round_variants(float(chg))
            except (TypeError, ValueError):
                pass
        if q.get("symbol") == "^TNX" and price is not None:
            labels.append(f"10Y美债 {round(float(price), 3)}%")
        elif price is not None:
            labels.append(f"{label} {price} ({chg})")

    for key, m in (mortgage or {}).items():
        for fld in ("value", "value_pct", "prev_value"):
            val = m.get(fld)
            if val is not None:
                try:
                    values |= _round_variants(float(val))
                except (TypeError, ValueError):
                    pass
        bp = m.get("change_bp")
        if bp is not None:
            try:
                values |= _round_variants(float(bp))
            except (TypeError, ValueError):
                pass
        if m.get("value") is not None:
            labels.append(f"{m.get('label', key)} {m['value']}% ({m.get('date', '')})")

    return {"values": values, "labels": labels, "raw": {"quotes": quotes, "mortgage": mortgage}}


def _is_whitelisted(text: str, start: int, end: int) -> bool:
    """True if the number at [start:end] is a structural token (tenor/year/count)."""
    after = text[end : end + 3]
    if after and after[0] in _WHITELIST_SUFFIX:
        return True
    for suf in _BP_SUFFIX:
        if text[end : end + len(suf)] == suf:
            return True
    # 4-digit calendar year (1900-2099)
    token = text[start:end].lstrip("+-±")
    if token.isdigit() and len(token) == 4 and 1900 <= int(token) <= 2099:
        return True
    return False


def _match(value: float, allowed: set[float], *, rel: float = 0.005, abs_tol: float = 0.1) -> bool:
    av = abs(value)
    for f in allowed:
        tol = max(abs_tol, abs(f) * rel)
        if abs(av - abs(f)) <= tol:
            return True
    return False


def extract_data_numbers(text: str) -> list[dict[str, Any]]:
    """Find percentages and index-point values that look like data claims."""
    found: list[dict[str, Any]] = []
    for m in _PCT_RE.finditer(text):
        if _is_whitelisted(text, m.start(), m.end()):
            continue
        try:
            val = float(m.group(1).replace("±", ""))
        except ValueError:
            continue
        found.append({"raw": m.group(0), "value": val, "kind": "percent", "pos": m.start()})
    for m in _POINT_RE.finditer(text):
        # skip if this point is actually part of a percentage already captured
        tail = text[m.end() : m.end() + 1]
        if tail in ("%", "％"):
            continue
        if _is_whitelisted(text, m.start(), m.end()):
            continue
        try:
            val = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        found.append({"raw": m.group(0), "value": val, "kind": "point", "pos": m.start()})
    return found


def collect_copy_text(xhs: dict[str, Any]) -> str:
    """Concatenate all human-visible copy fields that may contain numbers."""
    parts: list[str] = [
        str(xhs.get("title") or ""),
        str(xhs.get("cover_hook") or ""),
        str(xhs.get("body") or ""),
        str(xhs.get("voice_script") or ""),
    ]
    for card in xhs.get("cards") or []:
        parts.append(str(card.get("title") or ""))
        parts.append(str(card.get("body") or ""))
        for b in card.get("bullets") or []:
            parts.append(str(b))
        for h in card.get("hot_takes") or []:
            parts.append(str(h))
    return "\n".join(p for p in parts if p)


def audit_finance_numbers(
    xhs: dict[str, Any],
    facts: dict[str, Any],
) -> dict[str, Any]:
    """Hard gate: any data-like number not traceable to the snapshot is a violation."""
    allowed: set[float] = facts.get("values") or set()
    text = collect_copy_text(xhs)
    numbers = extract_data_numbers(text)
    violations: list[dict[str, Any]] = []
    for n in numbers:
        if not _match(n["value"], allowed):
            ctx = text[max(0, n["pos"] - 18) : n["pos"] + 18].replace("\n", " ")
            violations.append(
                {
                    "raw": n["raw"],
                    "value": n["value"],
                    "kind": n["kind"],
                    "context": f"…{ctx}…",
                    "issue": "数值无法在数据快照中找到来源（疑似编造）",
                    "severity": "high",
                }
            )
    return {
        "status": "FAIL" if violations else "PASS",
        "checked": len(numbers),
        "violations": violations,
        "allowed_count": len(allowed),
        "labels": facts.get("labels") or [],
    }
