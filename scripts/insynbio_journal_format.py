"""
InSynBio Journal Format CLI — thin wrapper around three public APIs.

We do NOT self-build journal format logic. We delegate to:
  1. CrossRef REST API   → journal metadata (ISSN, publisher, subjects, article types)
  2. Zotero CSL Library  → 9,000+ citation style files, download on demand
  3. Sherpa RoMEO v2 API → open-access & embargo policy for any journal

Feeds into ARS journal-submission-prep change_style.ps1 and Pandoc.

Usage:
    python scripts/insynbio_journal_format.py lookup "Journal of Clinical Investigation"
    python scripts/insynbio_journal_format.py lookup --issn 0021-9738
    python scripts/insynbio_journal_format.py get-csl "Nature Medicine" --out styles/nature-medicine.csl
    python scripts/insynbio_journal_format.py oa-policy "PLOS ONE"
    python scripts/insynbio_journal_format.py full-spec "Cell" --out specs/cell_live.json

Sources (all free, no API key required for basic use):
  CrossRef:  https://api.crossref.org/journals/{issn}
  Zotero:    https://www.zotero.org/styles/{slug} (CSL file download)
             https://api.zotero.org/styles (search)
  Sherpa:    https://v2.sherpa.ac.uk/api/publication?issn={issn}&api-key=...
             (Sherpa: free API key at https://v2.sherpa.ac.uk/api/registration)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    sys.exit("ERROR: 'requests' not installed. Run: pip install requests")

import os

CROSSREF_BASE  = "https://api.crossref.org"
ZOTERO_STYLES  = "https://www.zotero.org/styles"
ZOTERO_API     = "https://api.zotero.org/styles"
SHERPA_BASE    = "https://v2.sherpa.ac.uk/api/publication"
OPENALEX_BASE  = "https://api.openalex.org"

CROSSREF_EMAIL = os.environ.get("CROSSREF_EMAIL", "research@insynbio.com")
SHERPA_API_KEY = os.environ.get("SHERPA_API_KEY", "")
# NOTE 2026-07: Sherpa RoMEO suspended new key registration until end of July 2026.
# DOAJ is the primary OA policy source until then (no key required, 21,000+ journals).


# ── helpers ─────────────────────────────────────────────────────────────────

def _get(url: str, params: dict | None = None, retries: int = 3, timeout: int = 15) -> Any:
    for attempt in range(retries):
        resp = requests.get(url, params=params or {}, timeout=timeout)
        if resp.status_code == 429:
            time.sleep(4 * (attempt + 1))
            continue
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        ct = resp.headers.get("Content-Type", "")
        if "json" in ct:
            return resp.json()
        return resp.text
    raise RuntimeError(f"API failed after {retries} retries: {url}")


def _normalize_issn(raw: str) -> str:
    digits = re.sub(r"[^0-9X]", "", raw.upper())
    if len(digits) == 8:
        return f"{digits[:4]}-{digits[4:]}"
    return raw


def _journal_slug(name: str) -> str:
    """Convert journal name to Zotero-style slug (lowercase, hyphens)."""
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


# ── CrossRef ─────────────────────────────────────────────────────────────────

def crossref_lookup_by_issn(issn: str) -> dict | None:
    """Fetch journal metadata from CrossRef by ISSN."""
    issn = _normalize_issn(issn)
    data = _get(f"{CROSSREF_BASE}/journals/{issn}",
                params={"mailto": CROSSREF_EMAIL})
    if data is None:
        return None
    return data.get("message", data)


def crossref_search_by_name(name: str, rows: int = 5) -> list[dict]:
    """Search CrossRef journals by name, return list of candidate records."""
    data = _get(f"{CROSSREF_BASE}/journals",
                params={"query": name, "rows": rows, "mailto": CROSSREF_EMAIL})
    if not data:
        return []
    return data.get("message", {}).get("items", [])


def _crossref_record_to_summary(rec: dict) -> dict:
    issns = rec.get("ISSN", [])
    return {
        "title": rec.get("title", ""),
        "publisher": rec.get("publisher", ""),
        "issn": issns,
        "issn_print": next((i["value"] for i in rec.get("issn-type", []) if i["type"] == "pissn"), issns[0] if issns else ""),
        "issn_electronic": next((i["value"] for i in rec.get("issn-type", []) if i["type"] == "eissn"), ""),
        "subjects": rec.get("subjects", []),
        "flags": rec.get("flags", {}),
        "counts": rec.get("counts", {}),
        "coverage": rec.get("coverage", {}),
        "crossref_url": f"https://api.crossref.org/journals/{issns[0]}" if issns else "",
    }


# ── Zotero CSL ───────────────────────────────────────────────────────────────

def zotero_get_csl(journal_name: str, out_path: Path | None = None) -> str | None:
    """
    Download a CSL style file from Zotero for a journal.
    Tries slug-based URL first, then Zotero API search.
    Returns CSL text or None if not found.
    """
    slug = _journal_slug(journal_name)
    # Try direct slug URL
    url = f"{ZOTERO_STYLES}/{slug}"
    def _is_csl(text: str) -> bool:
        t = text.strip()
        return t.startswith("<?xml") or t.startswith("<style")

    resp = requests.get(url, timeout=15, allow_redirects=True)
    if resp.status_code == 200 and _is_csl(resp.text):
        csl_text = resp.text
        _write_csl(csl_text, out_path)
        return csl_text

    # Try common slug variants
    for variant in [slug.replace("-", ""), slug.replace("the-", ""), slug + "-journal"]:
        url2 = f"{ZOTERO_STYLES}/{variant}"
        resp2 = requests.get(url2, timeout=10, allow_redirects=True)
        if resp2.status_code == 200 and _is_csl(resp2.text):
            _write_csl(resp2.text, out_path)
            return resp2.text

    # Zotero API search (returns JSON list of styles)
    try:
        api_resp = requests.get(ZOTERO_API, params={"q": journal_name}, timeout=10)
        if api_resp.ok:
            styles = api_resp.json() if "json" in api_resp.headers.get("Content-Type","") else []
            if isinstance(styles, list) and styles:
                best = styles[0]
                csl_url = best.get("href") or f"{ZOTERO_STYLES}/{best.get('name','')}"
                r3 = requests.get(csl_url, timeout=10)
                if r3.ok and _is_csl(r3.text):
                    _write_csl(r3.text, out_path)
                    return r3.text
    except Exception:
        pass

    return None


def _write_csl(csl_text: str, out_path: Path | None) -> None:
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(csl_text, encoding="utf-8")
        print(f"[JournalFormat] CSL → {out_path}")


def zotero_pandoc_cmd(csl_path: Path, bib_path: Path, input_md: Path, output: Path) -> str:
    """Return the pandoc command to format using the downloaded CSL."""
    return (
        f"pandoc {input_md} "
        f"--bibliography {bib_path} "
        f"--csl {csl_path} "
        f"--output {output}"
    )


# ── OpenAlex /sources — OA policy (no key, polite pool) ─────────────────────

def openalex_oa_lookup(issn: str) -> dict | None:
    """
    Look up OA status and APC from OpenAlex /sources endpoint.
    No key required (polite pool via mailto). Covers all ~250k tracked journals.
    Returns is_oa, is_in_doaj, apc_usd, license, and key stats.
    """
    issn = _normalize_issn(issn)
    data = _get(f"{OPENALEX_BASE}/sources",
                params={"filter": f"issn:{issn}", "mailto": CROSSREF_EMAIL})
    if not data:
        return None
    results = data.get("results", [])
    if not results:
        return None
    src = results[0]
    apc_prices = src.get("apc_prices") or []
    apc_usd = src.get("apc_usd")
    return {
        "source": "OpenAlex",
        "title": src.get("display_name", ""),
        "issn": issn,
        "publisher": src.get("host_organization_name", ""),
        "is_oa": src.get("is_oa", False),
        "is_in_doaj": src.get("is_in_doaj", False),
        "is_in_doaj_since_year": src.get("is_in_doaj_since_year"),
        "oa_flip_year": src.get("oa_flip_year"),
        "apc_usd": apc_usd,
        "apc_prices": apc_prices,
        "works_count": src.get("works_count"),
        "oa_works_count": src.get("oa_works_count"),
        "h_index": src.get("summary_stats", {}).get("h_index"),
        "is_core": src.get("is_core"),
        "openalex_id": src.get("id"),
        "openalex_url": f"https://openalex.org/sources?filter=issn:{issn}",
    }


# ── Sherpa RoMEO ─────────────────────────────────────────────────────────────

def sherpa_oa_policy(issn: str) -> dict | None:
    """
    Fetch OA policy from Sherpa RoMEO v2.
    Free API key required (register at https://v2.sherpa.ac.uk/api/registration).
    Without key: returns limited info from the public endpoint.
    """
    issn = _normalize_issn(issn)
    params: dict[str, Any] = {"issn": issn, "format": "Json"}
    if SHERPA_API_KEY:
        params["api-key"] = SHERPA_API_KEY
    data = _get(SHERPA_BASE, params=params)
    if not data or not isinstance(data, dict):
        return None
    items = data.get("items", [])
    if not items:
        return None
    pub = items[0]
    # Extract key fields
    policies = pub.get("publisher_policy", [])
    summary: list[dict] = []
    for pol in policies:
        for path in pol.get("permitted_oa", []):
            summary.append({
                "location": path.get("location", {}).get("location", []),
                "article_version": path.get("article_version", []),
                "conditions": path.get("conditions", []),
                "embargo_months": path.get("embargo", {}).get("amount", 0),
                "license": [l.get("license", "") for l in path.get("license", [])],
            })
    return {
        "title": pub.get("title", [{}])[0].get("title", ""),
        "issn": issn,
        "publisher": pub.get("publishers", [{}])[0].get("publisher", {}).get("name", [{}])[0].get("name", ""),
        "system_metadata": {"uri": pub.get("system_metadata", {}).get("uri", "")},
        "oa_policies": summary,
        "sherpa_uri": pub.get("system_metadata", {}).get("uri", ""),
    }


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_lookup(args: argparse.Namespace) -> None:
    """Look up journal by name or ISSN via CrossRef."""
    if args.issn:
        print(f"[JournalFormat] CrossRef lookup by ISSN: {args.issn}")
        rec = crossref_lookup_by_issn(args.issn)
        if not rec:
            print(f"[JournalFormat] Not found in CrossRef: {args.issn}")
            return
        results = [_crossref_record_to_summary(rec)]
    else:
        print(f"[JournalFormat] CrossRef search: '{args.journal}'")
        recs = crossref_search_by_name(args.journal, rows=args.top)
        if not recs:
            print(f"[JournalFormat] No results for '{args.journal}'")
            return
        results = [_crossref_record_to_summary(r) for r in recs]

    _output(results, args.out)
    if not args.out:
        for r in results:
            print(f"\n  {r['title']} | {r['publisher']}")
            print(f"  ISSN print: {r['issn_print']} | electronic: {r['issn_electronic']}")
            print(f"  Subjects: {', '.join(r['subjects']) or '(none)'}")
            print(f"  CrossRef: {r['crossref_url']}")


def cmd_get_csl(args: argparse.Namespace) -> None:
    """Download CSL style file from Zotero for a journal."""
    out = Path(args.out) if args.out else None
    print(f"[JournalFormat] Zotero CSL search: '{args.journal}'")
    csl = zotero_get_csl(args.journal, out)
    if csl:
        # Extract title from CSL
        title_match = re.search(r'<title>([^<]+)</title>', csl)
        title = title_match.group(1) if title_match else "(unknown)"
        print(f"[JournalFormat] Found CSL: {title}")
        if not args.out:
            print(f"\nTo use with pandoc:")
            slug = _journal_slug(args.journal)
            print(f"  pandoc manuscript.md --bibliography refs.bib --csl {slug}.csl --output manuscript.docx")
        if args.out:
            print(f"\nNext step (ARS integration):")
            print(f"  Copy to submission package: cp {args.out} paper/<project>/")
            print(f"  Or use ARS change_style.ps1 -CslUrl https://www.zotero.org/styles/{_journal_slug(args.journal)}")
    else:
        print(f"[JournalFormat] CSL not found in Zotero for '{args.journal}'")
        print(f"  Try: https://www.zotero.org/styles?q={args.journal.replace(' ', '+')}")
        print(f"  Or:  change_style.ps1 -CslUrl <paste URL from Zotero>")


def cmd_oa_policy(args: argparse.Namespace) -> None:
    """
    Fetch OA/embargo policy.
    Priority: DOAJ (no key, 21k journals) → Sherpa RoMEO (key required).
    NOTE 2026-07: Sherpa suspended new key registration until end of July 2026.
    """
    issn = args.issn
    if not issn:
        print(f"[JournalFormat] Resolving ISSN for '{args.journal}' via CrossRef...")
        recs = crossref_search_by_name(args.journal, rows=1)
        if not recs:
            print(f"[JournalFormat] Could not resolve ISSN for '{args.journal}'")
            return
        issns = recs[0].get("ISSN", [])
        if not issns:
            print(f"[JournalFormat] No ISSN in CrossRef record")
            return
        issn = issns[0]
        print(f"[JournalFormat] Resolved ISSN: {issn}")

    # 1. Try DOAJ first (no key, fully OA journals)
    print(f"[JournalFormat] OpenAlex OA lookup: ISSN {issn}")
    doaj = openalex_oa_lookup(issn)
    if doaj:
        _output(doaj, args.out)
        if not args.out:
            oa_rec = doaj
            print(f"\n  Journal: {oa_rec['title']} | Publisher: {oa_rec['publisher']}")
            print(f"  is_oa: {oa_rec['is_oa']} | in_DOAJ: {oa_rec['is_in_doaj']}")
            apc = oa_rec.get('apc_usd')
            print(f"  APC: {'$' + str(apc) if apc else 'not listed'}")
            print(f"  Works: {oa_rec.get('works_count', '?')} | OA: {oa_rec.get('oa_works_count', '?')} | h-index: {oa_rec.get('h_index', '?')}")
            print(f"  OpenAlex: {oa_rec.get('openalex_url', '')}")
        return

    # 2. DOAJ miss → try Sherpa RoMEO (subscription/hybrid journals)
    if not SHERPA_API_KEY:
        print(f"[JournalFormat] Not in DOAJ (may be subscription/hybrid journal)")
        print(f"  Sherpa RoMEO key not set. Registration suspended until end of July 2026.")
        print(f"  Register at: https://v2.sherpa.ac.uk/api/registration (check after July 2026)")
        print(f"  Manual check: https://v2.sherpa.ac.uk/cgi/search/publication?issn={_normalize_issn(issn)}")
        return

    print(f"[JournalFormat] Sherpa RoMEO: ISSN {issn}")
    policy = sherpa_oa_policy(issn)
    if not policy:
        print(f"[JournalFormat] Not found in Sherpa RoMEO either.")
        print(f"  Check: https://v2.sherpa.ac.uk/cgi/search/publication?issn={_normalize_issn(issn)}")
        return
    _output(policy, args.out)
    if not args.out:
        print(f"\n  Journal: {policy['title']} | Publisher: {policy['publisher']}")
        if policy['oa_policies']:
            for pol in policy['oa_policies'][:3]:
                print(f"  OA path: versions={pol['article_version']} | "
                      f"embargo={pol['embargo_months']}mo | license={pol['license']}")
        if policy['sherpa_uri']:
            print(f"  Sherpa: {policy['sherpa_uri']}")


def cmd_full_spec(args: argparse.Namespace) -> None:
    """Combine CrossRef + Zotero CSL + Sherpa into one spec JSON."""
    print(f"[JournalFormat] Building full spec for '{args.journal}'...")

    # 1. CrossRef
    recs = crossref_search_by_name(args.journal, rows=1)
    crossref_data = _crossref_record_to_summary(recs[0]) if recs else {}
    issn = crossref_data.get("issn_print") or crossref_data.get("issn", [""])[0]

    # 2. Zotero CSL (check availability)
    slug = _journal_slug(args.journal)
    csl_url = f"{ZOTERO_STYLES}/{slug}"
    csl_resp = requests.get(csl_url, timeout=10, allow_redirects=True)
    _t = csl_resp.text.strip()
    csl_available = csl_resp.status_code == 200 and (_t.startswith("<?xml") or _t.startswith("<style"))
    if csl_available and args.out:
        csl_out = Path(args.out).with_suffix(".csl")
        _write_csl(csl_resp.text, csl_out)

    # 3. OA policy: OpenAlex /sources (no key) → Sherpa fallback (key required)
    oa_data = openalex_oa_lookup(issn) if issn else {}
    sherpa_data: dict = {}
    if not oa_data and issn and SHERPA_API_KEY:
        sherpa_data = sherpa_oa_policy(issn) or {}
        time.sleep(0.5)

    oa_section: dict
    if oa_data:
        oa_section = oa_data
    elif sherpa_data:
        oa_section = sherpa_data
    else:
        oa_section = {
            "note": (
                "Journal not found in OpenAlex sources. "
                "Sherpa RoMEO: registration suspended until end of July 2026. "
                f"Manual: https://v2.sherpa.ac.uk/cgi/search/publication?issn={issn}"
            )
        }

    spec = {
        "_source": "insynbio_journal_format.py — CrossRef + Zotero CSL + DOAJ + Sherpa RoMEO",
        "_generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "journal": args.journal,
        "crossref": crossref_data,
        "zotero_csl": {
            "available": csl_available,
            "url": csl_url if csl_available else None,
            "pandoc_cmd": f"--csl {slug}.csl" if csl_available else "not available — download manually from https://www.zotero.org/styles",
            "ars_change_style": f".\\change_style.ps1 -CslUrl {csl_url}" if csl_available else None,
        },
        "oa_policy": oa_section,
    }
    _output(spec, args.out)
    if not args.out:
        print(json.dumps(spec, indent=2, ensure_ascii=False))
    else:
        print(f"\n[JournalFormat] Full spec → {args.out}")
        print(f"  CrossRef: {crossref_data.get('title', '?')} | {crossref_data.get('publisher', '?')}")
        print(f"  Zotero CSL: {'✓ available' if csl_available else '✗ not found'} → {csl_url}")
        oa_src = "OpenAlex ✓" if oa_data else ("Sherpa ✓" if sherpa_data else "✗ not resolved (Sherpa key suspended until July 2026)")
        print(f"  OA policy: {oa_src}")


def _output(data: Any, out_path: str | None) -> None:
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[JournalFormat] → {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="insynbio_journal_format",
        description=(
            "Journal format lookup via CrossRef + Zotero CSL + Sherpa RoMEO. "
            "Covers 30,000+ journals without self-building any format logic."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # lookup
    p_l = sub.add_parser("lookup", help="CrossRef journal metadata (name or ISSN)")
    p_l.add_argument("journal", nargs="?", default=None, help="Journal name")
    p_l.add_argument("--issn", default=None, help="ISSN (overrides name search)")
    p_l.add_argument("--top", type=int, default=3)
    p_l.add_argument("--out", default=None)

    # get-csl
    p_c = sub.add_parser("get-csl", help="Download CSL style from Zotero (9,000+ journals)")
    p_c.add_argument("journal", help="Journal name")
    p_c.add_argument("--out", default=None, help="Save CSL to file (e.g. styles/nature.csl)")

    # oa-policy
    p_o = sub.add_parser("oa-policy", help="Sherpa RoMEO open-access & embargo policy")
    p_o.add_argument("journal", nargs="?", default=None, help="Journal name")
    p_o.add_argument("--issn", default=None, help="ISSN (faster than name)")
    p_o.add_argument("--out", default=None)

    # full-spec
    p_f = sub.add_parser("full-spec", help="CrossRef + Zotero CSL + Sherpa in one JSON")
    p_f.add_argument("journal", help="Journal name")
    p_f.add_argument("--out", default=None, help="Save JSON + CSL (e.g. specs/nature.json)")

    args = parser.parse_args()
    dispatch = {
        "lookup": cmd_lookup,
        "get-csl": cmd_get_csl,
        "oa-policy": cmd_oa_policy,
        "full-spec": cmd_full_spec,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
