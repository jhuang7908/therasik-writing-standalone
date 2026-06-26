#!/usr/bin/env python3
"""
Row-by-row ADA verification against local evidence excerpt + optional URL fetch
for high-ADA rows (>= HIGH_ADA_PCT threshold).

Outputs:
  data/immunogenicity_knowledge_base/reports/ada_master_row_verification.csv
"""
from __future__ import annotations

import csv
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MASTER = REPO / "data/immunogenicity_knowledge_base/master/ada_master_136_curated.csv"
OUT_CSV = REPO / "data/immunogenicity_knowledge_base/reports/ada_master_row_verification.csv"

HIGH_ADA_PCT = 25.0  # fetch primary URL for re-check (includes 25–30% band)
URL_TIMEOUT = 14
UA = "InSynBio-ADA-Verifier/1.1 (research; +https://insynbio.com)"


def _strip_html(html: str) -> str:
    t = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    t = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t


def _fetch(url: str) -> tuple[bytes, str, str]:
    if not url or not url.startswith("http"):
        return b"", "no_url", ""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=URL_TIMEOUT) as r:
            raw = r.read()
            ct = r.headers.get("Content-Type") or ""
            return raw, "ok", ct
    except Exception as e:
        return b"", f"fetch_error:{e.__class__.__name__}", ""


def _urls_for_row(row: dict) -> list[str]:
    """Prefer HTTP URLs; master often puts prose in ada_source_url_primary."""
    out: list[str] = []
    for key in ("ada_source_url_primary", "citation_urls"):
        v = (row.get(key) or "").strip()
        if v.startswith("http"):
            out.append(v.split()[0].rstrip(",;"))
    seen = set()
    return [u for u in out if u not in seen and not seen.add(u)]


def _body_to_text(raw: bytes, content_type: str | None) -> str:
    enc = "utf-8"
    if content_type and "charset=" in content_type.lower():
        try:
            enc = content_type.lower().split("charset=")[-1].split(";")[0].strip()
        except Exception:
            enc = "utf-8"
    try:
        return raw.decode(enc, errors="replace")
    except Exception:
        return raw.decode("utf-8", errors="replace")


def _primary(row: dict) -> float | None:
    s = (row.get("ada_first_pct") or "").strip()
    if not s or s.upper() == "NR":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _pcts_in_text(t: str) -> list[float]:
    if not t:
        return []
    t = re.sub(r"9[0-9]\s*%\s*CI", "", t, flags=re.I)
    out: list[float] = []
    for m in re.finditer(r"(\d+\.?\d*)\s*%", t):
        try:
            v = float(m.group(1))
            if 0 <= v <= 100:
                out.append(v)
        except ValueError:
            pass
    return out


def _excerpt_matches_primary(primary: float | None, excerpt: str) -> tuple[bool, str]:
    if primary is None:
        return True, "no_numeric_primary"
    ex = excerpt or ""
    for v in _pcts_in_text(ex):
        if abs(v - primary) <= 0.51:
            return True, f"excerpt_pct≈{v}"
    if primary == 0 and re.search(r"0\s*%|not detected|were not detected", ex, re.I):
        return True, "excerpt_zero_or_not_detected"
    nums = _pcts_in_text(ex)[:6]
    return False, f"excerpt_pcts={nums}"


def _display_in_excerpt(display: str, excerpt: str) -> bool:
    d = (display or "").strip()
    return bool(d and d in (excerpt or ""))


def _raw_supports_primary(raw: bytes, primary: float) -> tuple[bool, str]:
    """Search raw bytes (helps PDFs with embedded ASCII)."""
    if not raw:
        return False, "empty_raw"
    if primary == int(primary):
        needle = f"{int(primary)}%".encode("ascii")
        if needle in raw:
            return True, f"bytes:{needle.decode()}"
    needle2 = f"{primary:.1f}%".encode("ascii")
    if needle2 in raw:
        return True, f"bytes:{needle2.decode()}"
    needle3 = f"{primary:.2f}%".encode("ascii")
    if needle3 in raw:
        return True, f"bytes:{needle3.decode()}"
    return False, "not_in_raw"


def _url_supports_primary(html_text: str, primary: float) -> tuple[bool, str]:
    """Heuristic: primary value appears as N% or obvious fraction in page text."""
    t = html_text
    if not t or len(t) < 80:
        return False, "empty_or_short_text"
    # Integer and one-decimal forms
    candidates = [primary]
    if primary == int(primary):
        candidates.append(float(int(primary)))
    pats = []
    for c in candidates:
        if c == int(c):
            pats.append(rf"\b{int(c)}\s*%")
        pats.append(rf"\b{re.escape(str(round(c, 2)).rstrip('0').rstrip('.'))}\s*%")
    for pat in pats:
        if re.search(pat, t):
            return True, f"regex:{pat[:30]}"
    # e.g. 87% (691/792) — allow n/n close to rate
    if primary >= 1:
        if re.search(rf"\b{int(round(primary))}\b", t) and "%" in t[max(0, t.find(str(int(round(primary))) ) - 20) : t.find(str(int(round(primary)))) + 40]:
            # weak: just check number appears near a percent somewhere in doc
            pass
    # Stronger: any percentage within tolerance of primary in page
    for v in _pcts_in_text(t):
        if abs(v - primary) <= 1.0:
            return True, f"page_pct≈{v}"
    return False, "primary_not_found_in_page_text"


def main() -> int:
    rows = list(csv.DictReader(MASTER.open(encoding="utf-8")))
    out_rows: list[dict] = []

    for row in rows:
        name = row["antibody_name"]
        primary = _primary(row)
        excerpt = row.get("ada_evidence_chain_excerpt") or ""
        display = (row.get("ada_value_display") or "").strip()
        tier = row.get("evidence_tier") or ""
        url_list = _urls_for_row(row)
        url_report = "; ".join(url_list[:2])[:220]

        ok_ex, ex_note = _excerpt_matches_primary(primary, excerpt)
        strict_disp = _display_in_excerpt(display, excerpt)
        high = primary is not None and primary >= HIGH_ADA_PCT

        url_ok = ""
        url_note = ""
        if high and primary is not None:
            if not url_list:
                url_ok = "SKIP"
                url_note = "no_http_url_in_primary_or_citation"
            else:
                best_why = ""
                for u in url_list:
                    raw, st, ct = _fetch(u)
                    if st != "ok":
                        best_why = f"{u[:40]}…:{st}"
                        continue
                    br_ok, br_why = _raw_supports_primary(raw, primary)
                    if br_ok:
                        url_ok = "Y"
                        url_note = f"{br_why} @ {u[:60]}"
                        break
                    plain = _strip_html(_body_to_text(raw, ct))
                    u_ok, u_why = _url_supports_primary(plain, primary)
                    if u_ok:
                        url_ok = "Y"
                        url_note = f"{u_why} @ {u[:60]}"
                        break
                    best_why = f"{u[:40]}…:{u_why}"
                if not url_ok:
                    url_ok = "N"
                    url_note = (best_why or "all_urls_failed")[:200]

        risk = "LOW"
        if primary is not None and primary >= 30:
            risk = "HIGH"
        elif primary is not None and primary >= 25:
            risk = "ELEVATED"

        local_status = "OK" if ok_ex and strict_disp else ("WARN" if ok_ex else "FAIL")

        out_rows.append(
            {
                "antibody_name": name,
                "ada_first_pct": row.get("ada_first_pct", ""),
                "ada_value_display": display[:120],
                "evidence_tier": tier,
                "risk_band": risk,
                "local_status": local_status,
                "strict_display_in_excerpt": "Y" if strict_disp else "N",
                "excerpt_numeric_aligned": "Y" if ok_ex else "N",
                "excerpt_check_note": ex_note[:300],
                "primary_url_fetched": "Y" if high and url_ok in ("Y", "N", "SKIP") else "",
                "url_text_supports_primary": url_ok if high else "",
                "url_check_note": url_note,
                "urls_tried": url_report,
            }
        )

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    if out_rows:
        with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)

    # Console summary
    fail_ex = sum(1 for r in out_rows if r["excerpt_numeric_aligned"] == "N")
    ok_local = sum(1 for r in out_rows if r["local_status"] == "OK")
    warn_local = sum(1 for r in out_rows if r["local_status"] == "WARN")
    fail_local = sum(1 for r in out_rows if r["local_status"] == "FAIL")

    def _summ_url(band: str) -> None:
        sub = [r for r in out_rows if r["risk_band"] == band]
        if not sub:
            return
        y = sum(1 for r in sub if r["url_text_supports_primary"] == "Y")
        n = sum(1 for r in sub if r["url_text_supports_primary"] == "N")
        sk = sum(1 for r in sub if r["url_text_supports_primary"] == "SKIP")
        print(f"{band} (fetch threshold >={HIGH_ADA_PCT}%): n={len(sub)} URL Y/N/SKIP = {y}/{n}/{sk}")

    high_rows = [r for r in out_rows if r["risk_band"] == "HIGH"]

    print(f"Wrote {OUT_CSV}")
    print(f"Total rows: {len(out_rows)}")
    print(f"Local: OK={ok_local} WARN={warn_local} FAIL={fail_local} (FAIL = excerpt % not matching ada_first_pct)")
    print(f"Excerpt numeric mismatch: {fail_ex}")
    _summ_url("ELEVATED")
    _summ_url("HIGH")
    print("--- HIGH ADA (>=30%), descending ---")
    for r in sorted(high_rows, key=lambda x: -float(x["ada_first_pct"] or 0)):
        pct = r["ada_first_pct"]
        print(
            f"  {pct:>6}% {r['antibody_name']:22} local={r['local_status']:4} excerpt#={r['excerpt_numeric_aligned']} "
            f"strictDisp={r['strict_display_in_excerpt']} url={r['url_text_supports_primary']:4} {r['url_check_note'][:55]}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
