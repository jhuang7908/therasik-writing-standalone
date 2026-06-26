"""
Step 1 — Fetch the full MEDLINE-indexed journal list from NLM.

Source: NLM Catalog API (E-utilities)
Output: scripts/journal_db/medline_journals_raw.json  (~5,600 entries)

Usage:
    python scripts/journal_db/fetch_medline_journals.py
    python scripts/journal_db/fetch_medline_journals.py --out custom_path.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
import urllib.request
import urllib.parse
import urllib.error

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
SEARCH_TERM = "currentlyindexed[All]"
BATCH = 200          # conservative batch size
# NCBI_API_KEY from env → 10 req/sec; without → 3 req/sec (use 1 req/sec to be safe)
API_KEY = os.environ.get("NCBI_API_KEY", "")
DELAY = 0.12 if API_KEY else 1.0   # safe delays
MAX_RETRIES = 5

HERE = Path(__file__).parent
DEFAULT_OUT = HERE / "medline_journals_raw.json"


def _first_nonempty(d: dict, *keys) -> str:
    """Return the first non-empty string value from dict d for any of keys."""
    for k in keys:
        v = d.get(k)
        if v and isinstance(v, str):
            return v
    return ""


def _api_suffix() -> str:
    return f"&api_key={API_KEY}" if API_KEY else ""


def _get(url: str, timeout: int = 30) -> bytes:
    """GET with exponential backoff on 429 / 5xx."""
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt * 2
                print(f"\n  [retry {attempt+1}] HTTP {e.code} — waiting {wait}s …")
                time.sleep(wait)
            else:
                raise
        except urllib.error.URLError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                raise
    raise RuntimeError("Max retries exceeded")


def esearch_count(term: str) -> int:
    url = (f"{EUTILS}/esearch.fcgi?db=nlmcatalog"
           f"&term={urllib.parse.quote(term)}&retmode=json&retmax=0{_api_suffix()}")
    data = json.loads(_get(url))
    return int(data["esearchresult"]["count"])


def esearch_ids(term: str, retstart: int, retmax: int) -> list[str]:
    url = (f"{EUTILS}/esearch.fcgi?db=nlmcatalog"
           f"&term={urllib.parse.quote(term)}"
           f"&retmode=json&retmax={retmax}&retstart={retstart}{_api_suffix()}")
    data = json.loads(_get(url))
    return data["esearchresult"]["idlist"]


def esummary_batch(ids: list[str]) -> dict:
    uid_str = ",".join(ids)
    url = (f"{EUTILS}/esummary.fcgi?db=nlmcatalog"
           f"&id={uid_str}&retmode=json{_api_suffix()}")
    data = json.loads(_get(url, timeout=60))
    return data.get("result", {})


def main(out_path: Path):
    print(f"[1/3] Counting MEDLINE journals …")
    total = esearch_count(SEARCH_TERM)
    print(f"      Found {total} journals")

    all_ids: list[str] = []
    start = 0
    while start < total:
        batch_ids = esearch_ids(SEARCH_TERM, start, BATCH)
        all_ids.extend(batch_ids)
        print(f"      IDs fetched: {len(all_ids)}/{total}", end="\r")
        start += BATCH
        time.sleep(DELAY)
    print(f"\n[2/3] Fetching summaries for {len(all_ids)} journals …")

    journals = []
    debug_printed = False
    for i in range(0, len(all_ids), 100):
        chunk = all_ids[i:i+100]
        result = esummary_batch(chunk)

        # Print raw keys of first real record for field-name discovery
        if not debug_printed:
            for probe_uid in chunk:
                probe = result.get(probe_uid, {})
                if probe and probe_uid != "uids":
                    print(f"\n  [DEBUG] API keys for uid={probe_uid}: {list(probe.keys())}")
                    print(f"  [DEBUG] Full record sample: {json.dumps(probe, ensure_ascii=False)[:500]}")
                    debug_printed = True
                    break

        for uid in chunk:
            rec = result.get(uid, {})
            if not rec or uid == "uids":
                continue
            # NLM Catalog esummary JSON structure (verified 2026-06-25):
            # titlemainlist → [{title, sorttitle, aiid}, ...]
            # medlineta     → string abbreviation
            # issnlist      → [{issn, issntype, validyn}, ...]
            # publicationinfolist → [{publisher, place, imprint, ...}, ...]
            # country       → string
            # language      → string (not a list)
            title_list = rec.get("titlemainlist") or []
            title = title_list[0].get("title", "").rstrip(".") if title_list else ""
            abbr  = rec.get("medlineta", "") or rec.get("isoabbreviation", "")
            issns = [e["issn"] for e in rec.get("issnlist", [])
                     if isinstance(e, dict) and e.get("issn")]
            pub_list = rec.get("publicationinfolist") or []
            publisher = pub_list[0].get("publisher", "").rstrip(",").strip() if pub_list else ""
            country  = rec.get("country", "")
            lang_raw = rec.get("language", "")
            language = [lang_raw] if isinstance(lang_raw, str) and lang_raw else lang_raw if isinstance(lang_raw, list) else []
            journals.append({
                "nlm_id":    uid,
                "title":     title,
                "abbr":      abbr,
                "issn":      issns,
                "publisher": publisher,
                "country":   country,
                "language":  language,
            })
        print(f"      Summaries: {min(i+100, len(all_ids))}/{len(all_ids)}", end="\r")
        time.sleep(DELAY)

    # Quick sanity: show first record to verify field mapping
    if journals:
        sample = journals[0]
        print(f"\n  Sample record: title='{sample['title']}' abbr='{sample['abbr']}' publisher='{sample['publisher']}'")
    else:
        print("\n  WARNING: 0 journal records extracted — check API field names above")
    print(f"\n[3/3] Writing {len(journals)} records → {out_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(journals, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Done. {len(journals)} MEDLINE journals saved.")
    return len(journals)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    n = main(Path(args.out))
    sys.exit(0 if n > 0 else 1)
