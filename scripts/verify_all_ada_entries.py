#!/usr/bin/env python3
"""
Full re-verification of every ADA entry in the verifiable classified database.

For each entry:
  1. If PMID available → fetch PubMed abstract via NCBI efetch
  2. If PMC URL available → fetch PMC abstract/full text
  3. If other URL available → fetch page text
  4. Check whether the claimed ADA % value appears in the fetched text

Output: verification/full_reverification_report.json  +  .csv
"""
from __future__ import annotations

import csv
import json
import re
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

REPO = Path(__file__).resolve().parents[1]
IDX_PATH = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_index.json"
OUT_DIR = REPO / "data/ADA_reliable_package/verification"

# NCBI E-utils base
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EFETCH_ABSTRACT = EUTILS + "/efetch.fcgi?db=pubmed&rettype=abstract&retmode=xml&id={pmid}"
EFETCH_PMC_XML = EUTILS + "/efetch.fcgi?db=pmc&rettype=full&retmode=xml&id={pmcid}"
ELINK_PMID2PMC = EUTILS + "/elink.fcgi?dbfrom=pubmed&db=pmc&id={pmid}&retmode=json"

HEADERS = {"User-Agent": "InSynBio-ADA-Verifier/1.0 (contact@insynbio.com)"}

RATE_DELAY = 0.4   # seconds between NCBI calls
URL_TIMEOUT = 12   # seconds


# ─── helpers ─────────────────────────────────────────────────────────────────

def _get(url: str, timeout: int = URL_TIMEOUT) -> str:
    """HTTP GET, returns text or '' on error."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            enc = r.headers.get_content_charset() or "utf-8"
            return raw.decode(enc, errors="replace")
    except Exception as e:
        return f"__FETCH_ERROR__:{e}"


def _strip_html(html: str) -> str:
    """Very rough HTML → plain text."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_pubmed_abstract(pmid: str) -> str:
    """Return abstract text for a PubMed ID."""
    url = EFETCH_ABSTRACT.format(pmid=pmid.strip())
    xml_text = _get(url)
    time.sleep(RATE_DELAY)
    if xml_text.startswith("__FETCH_ERROR__"):
        return xml_text
    try:
        root = ET.fromstring(xml_text)
        parts = []
        for node in root.iter("AbstractText"):
            parts.append(node.text or "")
        # Also grab MeSH / article title for context
        for node in root.iter("ArticleTitle"):
            parts.insert(0, node.text or "")
        return " ".join(parts).strip()
    except ET.ParseError:
        return "__XML_PARSE_ERROR__"


def pmid_to_pmcid(pmid: str) -> str | None:
    """Convert PMID → PMCID via elink."""
    url = ELINK_PMID2PMC.format(pmid=pmid.strip())
    resp = _get(url)
    time.sleep(RATE_DELAY)
    if resp.startswith("__FETCH_ERROR__"):
        return None
    try:
        data = json.loads(resp)
        links = data.get("linksets", [{}])[0].get("linksetdbs", [])
        for lb in links:
            if lb.get("dbto") == "pmc":
                ids = lb.get("links", [])
                if ids:
                    return str(ids[0])
    except Exception:
        pass
    return None


def fetch_pmc_text(pmcid: str) -> str:
    """Fetch PMC full-text XML, extract <abstract> + <body> text."""
    url = EFETCH_PMC_XML.format(pmcid=pmcid)
    xml_text = _get(url)
    time.sleep(RATE_DELAY)
    if xml_text.startswith("__FETCH_ERROR__"):
        return xml_text
    try:
        root = ET.fromstring(xml_text)
        parts = []
        for tag in ("abstract", "body", "sec", "p", "title"):
            for node in root.iter(tag):
                if node.text:
                    parts.append(node.text)
                for child in node:
                    if child.tail:
                        parts.append(child.tail)
        text = " ".join(parts)
        return re.sub(r"\s+", " ", text).strip()
    except ET.ParseError:
        return "__XML_PARSE_ERROR__"


def fetch_url_text(url: str) -> str:
    """Fetch generic URL (HTML/XML/text), return plain text."""
    raw = _get(url)
    if raw.startswith("__FETCH_ERROR__"):
        return raw
    if "<html" in raw.lower() or "<!doctype" in raw.lower():
        return _strip_html(raw)
    return raw[:8000]


# ─── ADA value matching ───────────────────────────────────────────────────────

def extract_claimed_pcts(display: str) -> list[float]:
    """Extract numeric ADA percentage values from ada_value_display string."""
    if not display:
        return []
    # Remove 95% CI patterns to avoid false positives
    s = re.sub(r"9[0-9]\s*%\s*CI", "", display, flags=re.I)
    s = re.sub(r"9[0-9]\s*%\s*confidence", "", s, flags=re.I)
    nums = re.findall(r"(\d+\.?\d*)\s*%", s)
    pcts = []
    for n in nums:
        v = float(n)
        if 0 < v <= 100:
            pcts.append(v)
    return pcts


def pct_found_in_text(pct: float, text: str, tol: float = 0.5) -> bool:
    """Check if a percentage value (±tol) appears in text."""
    # Remove 95% CI context from text too
    clean = re.sub(r"9[0-9]\s*%\s*CI", "", text, flags=re.I)
    clean = re.sub(r"9[0-9]\s*%\s*confidence", "", clean, flags=re.I)
    # Look for the number near a % sign
    pattern = rf"(\d+\.?\d*)\s*%"
    for m in re.finditer(pattern, clean):
        try:
            v = float(m.group(1))
            if abs(v - pct) <= tol:
                return True
        except ValueError:
            pass
    return False


def check_ada_in_text(display: str, text: str) -> dict:
    """Check each claimed ADA % against fetched text."""
    pcts = extract_claimed_pcts(display)
    if not pcts:
        return {"claimed_pcts": [], "matched": [], "unmatched": [], "verdict": "no_numeric_value"}
    matched = [p for p in pcts if pct_found_in_text(p, text)]
    unmatched = [p for p in pcts if not pct_found_in_text(p, text)]
    if not text or text.startswith("__"):
        verdict = "fetch_failed"
    elif len(matched) == len(pcts):
        verdict = "all_matched"
    elif matched:
        verdict = "partial_match"
    else:
        verdict = "not_found"
    return {"claimed_pcts": pcts, "matched": matched, "unmatched": unmatched, "verdict": verdict}


# ─── main ─────────────────────────────────────────────────────────────────────

def verify_entry(row: dict) -> dict:
    name = row["antibody_name"]
    display = row.get("ada_value_display") or ""
    pmids = row.get("pmids_extracted") or []
    urls = row.get("citation_urls") or []
    tier = row.get("class_evidence_tier")

    result = {
        "antibody_name": name,
        "tier": tier,
        "ada_value_display": display,
        "claimed_pcts": extract_claimed_pcts(display),
        "source_tried": None,
        "source_type": None,
        "text_snippet": "",
        "check": {},
        "verdict": "pending",
        "notes": [],
    }

    text = ""

    # Strategy: try PMID first (most reliable), then PMC URL, then other URLs
    if pmids:
        pmid = str(pmids[0]).strip()
        result["source_tried"] = f"pmid:{pmid}"
        result["source_type"] = "pubmed_abstract"
        print(f"  [{name}] fetching PMID {pmid} abstract...")
        text = fetch_pubmed_abstract(pmid)
        if text.startswith("__") or len(text) < 50:
            # Try PMC full text
            print(f"  [{name}] abstract short/failed, trying PMC full text...")
            pmcid = pmid_to_pmcid(pmid)
            if pmcid:
                pmc_text = fetch_pmc_text(pmcid)
                if not pmc_text.startswith("__") and len(pmc_text) > 200:
                    text = pmc_text
                    result["source_tried"] = f"pmcid:{pmcid}"
                    result["source_type"] = "pmc_fulltext"
                    result["notes"].append(f"PMC fallback via PMCID {pmcid}")

    elif urls:
        # Prefer PMC/PubMed/FDA URLs
        preferred = None
        for u in urls:
            ul = u.lower()
            if "pmc.ncbi.nlm.nih.gov" in ul or "pubmed.ncbi" in ul:
                preferred = u
                break
            if "accessdata.fda.gov" in ul:
                preferred = u
                break
        if preferred is None:
            preferred = urls[0]
        result["source_tried"] = preferred
        # Try to extract PMCID from PMC URL
        pmc_match = re.search(r"pmc\.ncbi\.nlm\.nih\.gov/articles/PMC(\d+)", preferred, re.I)
        if pmc_match:
            pmcid = pmc_match.group(1)
            result["source_type"] = "pmc_fulltext"
            print(f"  [{name}] fetching PMC {pmcid} full text...")
            text = fetch_pmc_text(pmcid)
        else:
            result["source_type"] = "url_html"
            print(f"  [{name}] fetching URL: {preferred[:70]}...")
            text = fetch_url_text(preferred)
    else:
        result["verdict"] = "no_source"
        result["notes"].append("No PMID and no URL found")
        return result

    if text.startswith("__FETCH_ERROR__"):
        result["verdict"] = "fetch_failed"
        result["notes"].append(text)
        result["text_snippet"] = ""
        return result

    # Truncate snippet for report
    result["text_snippet"] = text[:500]
    result["check"] = check_ada_in_text(display, text)
    result["verdict"] = result["check"]["verdict"]
    return result


def main() -> None:
    idx_blob = json.loads(IDX_PATH.read_text(encoding="utf-8"))
    entries = idx_blob.get("index", [])
    print(f"Verifying {len(entries)} entries...\n")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    for i, row in enumerate(sorted(entries, key=lambda x: x["antibody_name"]), 1):
        print(f"[{i:03d}/{len(entries)}] {row['antibody_name']}")
        res = verify_entry(row)
        results.append(res)
        # Progress checkpoint every 20 entries
        if i % 20 == 0:
            _write_outputs(results, OUT_DIR, partial=True)
            print(f"  → checkpoint saved ({i} done)\n")

    _write_outputs(results, OUT_DIR, partial=False)

    # Print summary
    verdicts: dict[str, int] = {}
    for r in results:
        k = r["verdict"]
        verdicts[k] = verdicts.get(k, 0) + 1

    print("\n=== VERIFICATION SUMMARY ===")
    for k, v in sorted(verdicts.items(), key=lambda x: -x[1]):
        print(f"  {k:30s}: {v}")
    print(f"Total: {len(results)}")
    print(f"Wrote {OUT_DIR}/full_reverification_report.*")


def _write_outputs(results: list[dict], out_dir: Path, partial: bool = False) -> None:
    suffix = "_partial" if partial else ""
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "summary": {},
        "results": results,
    }
    for r in results:
        k = r["verdict"]
        report["summary"][k] = report["summary"].get(k, 0) + 1

    json_path = out_dir / f"full_reverification_report{suffix}.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_path = out_dir / f"full_reverification_report{suffix}.csv"
    fields = [
        "antibody_name", "tier", "ada_value_display",
        "claimed_pcts", "verdict",
        "matched", "unmatched",
        "source_tried", "source_type",
        "notes", "text_snippet",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in results:
            row = dict(r)
            row["claimed_pcts"] = str(r.get("claimed_pcts", []))
            row["matched"] = str(r.get("check", {}).get("matched", []))
            row["unmatched"] = str(r.get("check", {}).get("unmatched", []))
            row["notes"] = "; ".join(r.get("notes", []))
            row["text_snippet"] = (r.get("text_snippet") or "")[:300]
            w.writerow(row)


if __name__ == "__main__":
    main()
