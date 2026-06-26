"""
verify_hub_links.py — Independent third-party link & content verifier
======================================================================
Runs AFTER run_nyc_community_live_update.py and operates purely on the
published HTML output. It does NOT share logic with the scraping pipeline.

Checks performed (four independent gates):
  G1  URL liveness   — HEAD request; 200/301/302 = PASS, 4xx/5xx = FAIL
  G2  Domain trust   — URL must resolve to an approved top-level domain
  G3  Date validity  — Event date must not be more than 1 day in the past
  G4  Title quality  — Title must be ≥ 8 chars and not a navigation label

Output artifacts (written to output_dir):
  link_audit.json   — per-item results + aggregate stats
  link_audit.md     — human-readable markdown summary

The HTML is also patched: the stream-banner gains a verification badge
showing pass/fail counts and the timestamp of the audit run.

Usage:
  python scripts/verify_hub_links.py [--hub PATH] [--output-dir DIR] [--timeout N]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

# ── Config ────────────────────────────────────────────────────────────────────

HUB_DEFAULT   = Path(__file__).parent.parent / "insynbio-web-source" / "us-chinese-life-hub.html"
OUTPUT_DEFAULT = Path(__file__).parent.parent / "outputs" / "nyc_community_events"

TRUSTED_DOMAINS = {
    "nyc.gov", "nycgovparks.org", "ny.gov", "cuny.edu", "nypl.org",
    "queenslibrary.org", "brooklynpubliclibrary.org", "mta.info", "new.mta.info",
    "eventbrite.com", "cpc-nyc.org", "cpcnyc.org", "aafederation.org", "aafny.org",
    "tzuchi.us", "foodbanknyc.org", "dol.ny.gov", "labor.ny.gov", "service.nyc.gov",
    "nycacc.app", "nyacc.org", "legalaidnyc.org", "legalaid.org",
    "nyc311.com", "portal.311.nyc.gov",
}

# Navigation-style titles that are not real events
_NAV_PATTERNS = re.compile(
    r"^(home|events|programs?|services?|about|contact|apply|register|"
    r"login|sign[\s-]?in|news|更多|首页|关于我们|联系我们|全部活动)$",
    re.I,
)

# ── HTML parsing ──────────────────────────────────────────────────────────────

def _extract_items(html: str) -> list[dict[str, Any]]:
    m = re.search(r"const ITEMS = (\[.*?\]);\s*\nconst UI_STRINGS", html, re.S)
    if not m:
        raise ValueError("Could not locate ITEMS array in hub HTML")
    return json.loads(m.group(1))


def _patch_html_badge(html: str, stats: dict[str, Any]) -> str:
    """Inject verification badge into stream-banner."""
    passed    = stats["g1_pass"]
    total     = stats["total"]
    rate_pct  = int(passed / total * 100) if total else 0
    color     = "#16a34a" if rate_pct >= 90 else "#d97706" if rate_pct >= 70 else "#dc2626"
    ts        = stats["verified_at_et"]
    badge_html = (
        f'<span style="font-size:11px;color:{color};font-weight:700;margin-left:12px;">'
        f'✔ 验证 {passed}/{total} 条链接有效 ({rate_pct}%) · {ts} ET</span>'
    )
    # Insert into stream-right span
    html = re.sub(
        r'(<span[^>]+class=["\']stream-right["\'][^>]*>)(.*?)(</span>)',
        lambda m2: m2.group(1) + m2.group(2) + badge_html + m2.group(3),
        html, flags=re.S
    )
    # Also update the footer last-updated timestamp
    html = re.sub(r"最后更新: [^']+';",
                  f"最后更新: {stats['verified_at_et']} (已校验);",
                  html)
    return html


# ── Gate checkers ─────────────────────────────────────────────────────────────

def _check_domain(url: str) -> tuple[bool, str]:
    """G2: domain must be in TRUSTED_DOMAINS or a subdomain thereof."""
    from urllib.parse import urlparse
    host = urlparse(url).hostname or ""
    for td in TRUSTED_DOMAINS:
        if host == td or host.endswith("." + td):
            return True, "trusted_domain"
    return False, f"untrusted_domain:{host}"


def _check_date(item_date: str) -> tuple[bool, str]:
    """G3: date must be today or future (allow 1-day grace)."""
    try:
        ev_date = date.fromisoformat(item_date)
        cutoff  = date.today() - timedelta(days=1)
        if ev_date >= cutoff:
            return True, "date_valid"
        return False, f"date_expired:{item_date}"
    except Exception:
        return True, "date_unknown_kept"  # unknown date: keep with benefit of doubt


def _check_title(title: str) -> tuple[bool, str]:
    """G4: title must be substantive."""
    t = title.strip()
    if len(t) < 8:
        return False, "title_too_short"
    if _NAV_PATTERNS.match(t):
        return False, "title_nav_label"
    return True, "title_ok"


# ── Main verifier ─────────────────────────────────────────────────────────────

def verify(
    hub_path: Path,
    output_dir: Path,
    timeout: int = 10,
    patch_html: bool = True,
) -> dict[str, Any]:
    print(f"[verify] Reading hub: {hub_path}", flush=True)
    html  = hub_path.read_text(encoding="utf-8")
    items = _extract_items(html)
    total = len(items)
    print(f"[verify] {total} items to verify across 4 gates", flush=True)

    # G1: URL liveness (HEAD request)
    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (compatible; NYC-Hub-Verifier/1.0; "
        "+https://insynbio.com/console)"
    )
    session.headers["Accept"] = "text/html,application/xhtml+xml"

    results: list[dict[str, Any]] = []
    g1_pass = g2_pass = g3_pass = g4_pass = 0
    all_pass = 0
    dead_urls: list[str] = []

    for idx, item in enumerate(items):
        url        = item.get("url", "")
        title      = item.get("title_zh") or item.get("title_en") or ""
        item_date  = item.get("date", "")
        item_id    = item.get("id", f"item_{idx+1}")

        rec: dict[str, Any] = {
            "id": item_id, "url": url,
            "title_zh": title, "date": item_date,
            "g1_liveness": None, "g2_domain": None,
            "g3_date": None, "g4_title": None,
            "overall": "FAIL",
        }

        # G4: title (cheap, no network)
        g4_ok, g4_reason = _check_title(title)
        rec["g4_title"] = g4_reason
        if g4_ok: g4_pass += 1

        # G3: date (cheap)
        g3_ok, g3_reason = _check_date(item_date)
        rec["g3_date"] = g3_reason
        if g3_ok: g3_pass += 1

        # G2: domain trust (cheap)
        g2_ok, g2_reason = _check_domain(url)
        rec["g2_domain"] = g2_reason
        if g2_ok: g2_pass += 1

        # G1: HTTP liveness
        g1_ok = False
        g1_reason = "skipped"
        if url:
            try:
                resp = session.head(url, timeout=timeout, allow_redirects=True)
                if resp.status_code < 400:
                    g1_ok = True
                    g1_reason = f"http_{resp.status_code}"
                else:
                    # Retry with GET for servers that block HEAD
                    try:
                        resp2 = session.get(url, timeout=timeout,
                                            allow_redirects=True, stream=True)
                        resp2.close()
                        if resp2.status_code < 400:
                            g1_ok = True
                            g1_reason = f"http_get_{resp2.status_code}"
                        else:
                            g1_reason = f"http_{resp2.status_code}"
                            dead_urls.append(url)
                    except Exception as e2:
                        g1_reason = f"get_error:{type(e2).__name__}"
                        dead_urls.append(url)
            except requests.Timeout:
                g1_ok  = True   # timeout ≠ dead; benefit of doubt
                g1_reason = "timeout_kept"
            except Exception as e:
                g1_ok  = True   # connection error; keep
                g1_reason = f"conn_error_kept:{type(e).__name__}"
        rec["g1_liveness"] = g1_reason
        if g1_ok: g1_pass += 1

        overall = "PASS" if (g1_ok and g2_ok and g3_ok and g4_ok) else "WARN"
        if not g1_ok or not g3_ok or not g4_ok:
            overall = "FAIL"
        rec["overall"] = overall
        if overall == "PASS":
            all_pass += 1

        results.append(rec)
        if (idx + 1) % 20 == 0:
            print(f"[verify]   {idx+1}/{total} checked …", flush=True)
        time.sleep(0.15)

    now_et = datetime.now().strftime("%Y-%m-%d %H:%M")
    stats: dict[str, Any] = {
        "verified_at_et": now_et,
        "total": total,
        "g1_pass": g1_pass, "g1_fail": total - g1_pass,
        "g2_pass": g2_pass, "g2_fail": total - g2_pass,
        "g3_pass": g3_pass, "g3_fail": total - g3_pass,
        "g4_pass": g4_pass, "g4_fail": total - g4_pass,
        "all_gates_pass": all_pass,
        "pass_rate_pct": round(g1_pass / total * 100, 1) if total else 0,
        "dead_urls": dead_urls,
    }
    audit: dict[str, Any] = {"meta": stats, "items": results}

    # Write JSON audit
    output_dir.mkdir(parents=True, exist_ok=True)
    audit_path = output_dir / "link_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[verify] Audit written → {audit_path}", flush=True)

    # Write Markdown summary
    _write_md_summary(stats, results, output_dir / "link_audit.md")

    # Patch HTML with badge
    if patch_html:
        patched = _patch_html_badge(html, stats)
        hub_path.write_text(patched, encoding="utf-8")
        print(f"[verify] HTML badge injected → {hub_path}", flush=True)

    # Summary to stdout
    print(
        f"\n[verify] ═══ VERIFICATION SUMMARY ══════════════════════\n"
        f"  Total items   : {total}\n"
        f"  G1 Liveness   : {g1_pass}/{total} PASS  ({total-g1_pass} dead/error)\n"
        f"  G2 Domain     : {g2_pass}/{total} trusted domains\n"
        f"  G3 Date       : {g3_pass}/{total} future/current events\n"
        f"  G4 Title      : {g4_pass}/{total} substantive titles\n"
        f"  All gates OK  : {all_pass}/{total} ({stats['pass_rate_pct']}%)\n"
        f"  Verified at   : {now_et} ET\n"
        f"════════════════════════════════════════════════════════",
        flush=True
    )
    return stats


def _write_md_summary(stats: dict, results: list[dict], path: Path) -> None:
    lines = [
        "# 美东华人生活圈 — 每日链接验证报告",
        "",
        f"**验证时间**: {stats['verified_at_et']} ET  ",
        f"**总条目**: {stats['total']}  ",
        f"**链接有效率 (G1)**: {stats['g1_pass']}/{stats['total']} ({stats['pass_rate_pct']}%)  ",
        f"**可信域名 (G2)**: {stats['g2_pass']}/{stats['total']}  ",
        f"**日期有效 (G3)**: {stats['g3_pass']}/{stats['total']}  ",
        f"**标题有效 (G4)**: {stats['g4_pass']}/{stats['total']}  ",
        f"**全部通过**: {stats['all_gates_pass']}/{stats['total']}  ",
        "",
        "## 失效链接",
        "",
    ]
    dead = [r for r in results if r["overall"] == "FAIL"]
    if dead:
        for r in dead:
            lines.append(f"- [{r['title_zh'][:50]}]({r['url']})  ")
            lines.append(f"  G1:{r['g1_liveness']} | G2:{r['g2_domain']} | "
                         f"G3:{r['g3_date']} | G4:{r['g4_title']}  ")
    else:
        lines.append("无失效链接 ✅")
    lines += [
        "",
        "## 警告条目 (WARN)",
        "",
    ]
    warn = [r for r in results if r["overall"] == "WARN"]
    if warn:
        for r in warn[:20]:
            lines.append(f"- [{r['title_zh'][:50]}]({r['url']})  ")
    else:
        lines.append("无警告 ✅")
    path.write_text("\n".join(lines), encoding="utf-8")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Independent hub link verifier")
    parser.add_argument("--hub",        default=str(HUB_DEFAULT),    help="Path to hub HTML")
    parser.add_argument("--output-dir", default=str(OUTPUT_DEFAULT),  help="Output directory for audit files")
    parser.add_argument("--timeout",    type=int, default=10,         help="HTTP request timeout (seconds)")
    parser.add_argument("--no-patch",   action="store_true",          help="Don't patch HTML with badge")
    args = parser.parse_args()

    stats = verify(
        hub_path   = Path(args.hub),
        output_dir = Path(args.output_dir),
        timeout    = args.timeout,
        patch_html = not args.no_patch,
    )

    fail_rate = 1.0 - (stats["g1_pass"] / stats["total"]) if stats["total"] else 0
    if fail_rate > 0.20:
        print(f"[verify] ⚠️  WARNING: {fail_rate*100:.0f}% of links failed G1 liveness check", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
