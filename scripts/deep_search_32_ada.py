#!/usr/bin/env python3
"""
Deep ADA extraction for 32 antibodies whose PubMed abstracts discuss
immunogenicity but don't include a specific ADA percentage.

Strategy per antibody:
  1. Try PMC full-text XML via efetch for the best PMID → scan for ADA %.
  2. Try DailyMed / FDA label search for the INN → look for Sec 6.2.
  3. Fallback: broaden PubMed search to pharmacokinetics / safety.

Output: data/ADA_reliable_package/verification/deep_search_32_report.json
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FWD_REPORT = REPO / "data" / "ADA_reliable_package" / "verification" / "forward_search_report.json"
OUT_DIR = REPO / "data" / "ADA_reliable_package" / "verification"

EMAIL = "ada-audit@insynbio.com"
DELAY = 0.4

ADA_NUMERIC = re.compile(
    r"(?:ADA|anti[- ]?drug\s+antibod|immunogenic|neutralizing\s+antibod|"
    r"treatment[- ]emergent\s+anti|binding\s+antibod|HAHA|HACA|HAMA)"
    r"[^.]{0,200}?(\d+\.?\d*)\s*%",
    re.I,
)
BROAD_ADA_PCT = re.compile(
    r"(\d+\.?\d*)\s*%\s*[^.]{0,60}?"
    r"(?:ADA|anti[- ]?drug|immunogenic|neutraliz)",
    re.I,
)
SECTION_62 = re.compile(r"(?:6\.2\s+Immunogenicity|Immunogenicity)", re.I)


def _pmc_fulltext(pmid: str) -> str | None:
    """Try to get PMC full text via efetch. Returns text or None."""
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
        + urllib.parse.urlencode({
            "db": "pmc", "id": pmid,
            "rettype": "xml", "retmode": "xml",
            "email": EMAIL,
        })
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AntibodyEngineerSuite/deep"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            xml_bytes = resp.read()
        root = ET.fromstring(xml_bytes)
        texts = []
        for elem in root.iter():
            if elem.text:
                texts.append(elem.text)
            if elem.tail:
                texts.append(elem.tail)
        full = " ".join(texts)
        if len(full) > 500:
            return full
    except Exception:
        pass
    return None


def _pubmed_to_pmc(pmid: str) -> str | None:
    """Convert PMID to PMCID via elink."""
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?"
        + urllib.parse.urlencode({
            "dbfrom": "pubmed", "db": "pmc",
            "id": pmid, "retmode": "json",
            "email": EMAIL,
        })
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AntibodyEngineerSuite/deep"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
        for ls in data.get("linksets", []):
            for ldb in ls.get("linksetdbs", []):
                if ldb.get("dbto") == "pmc":
                    ids = ldb.get("links", [])
                    if ids:
                        return str(ids[0])
    except Exception:
        pass
    return None


def _dailymed_search(inn: str) -> str | None:
    """Search DailyMed for the antibody name and return first SPL XML URL."""
    url = (
        "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?"
        + urllib.parse.urlencode({"drug_name": inn, "page": "1", "pagesize": "1"})
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AntibodyEngineerSuite/deep"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
        results = data.get("data", [])
        if results:
            setid = results[0].get("setid")
            if setid:
                return f"https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}.xml"
    except Exception:
        pass
    return None


def _fetch_dailymed_xml(spl_url: str) -> str | None:
    """Fetch DailyMed SPL XML and extract text."""
    try:
        req = urllib.request.Request(spl_url, headers={"User-Agent": "AntibodyEngineerSuite/deep"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            xml_bytes = resp.read()
        root = ET.fromstring(xml_bytes)
        texts = []
        for elem in root.iter():
            if elem.text:
                texts.append(elem.text)
            if elem.tail:
                texts.append(elem.tail)
        return " ".join(texts)
    except Exception:
        return None


def _extract_ada_from_text(text: str, name: str) -> list[dict]:
    """Extract ADA-associated percentages from text."""
    hits = []
    for m in ADA_NUMERIC.finditer(text):
        start = max(0, m.start() - 100)
        end = min(len(text), m.end() + 100)
        context = text[start:end].replace("\n", " ").strip()
        hits.append({"pct": m.group(1), "context": context[:250]})
    for m in BROAD_ADA_PCT.finditer(text):
        start = max(0, m.start() - 100)
        end = min(len(text), m.end() + 100)
        context = text[start:end].replace("\n", " ").strip()
        pct = m.group(1)
        if not any(h["pct"] == pct for h in hits):
            hits.append({"pct": pct, "context": context[:250]})
    return hits


def process_antibody(name: str, pmid: str) -> dict:
    result: dict = {
        "antibody_name": name,
        "best_pmid": pmid,
        "pmc_fulltext_found": False,
        "dailymed_found": False,
        "ada_extractions": [],
        "verdict": "no_data",
    }

    # Path 1: PMC full text
    if pmid:
        pmcid = _pubmed_to_pmc(pmid)
        time.sleep(DELAY)
        if pmcid:
            fulltext = _pmc_fulltext(pmcid)
            time.sleep(DELAY)
            if fulltext:
                result["pmc_fulltext_found"] = True
                result["pmcid"] = pmcid
                hits = _extract_ada_from_text(fulltext, name)
                if hits:
                    result["ada_extractions"].extend(hits)
                    result["extraction_source"] = "pmc_fulltext"

    # Path 2: DailyMed / FDA label
    spl_url = _dailymed_search(name)
    time.sleep(DELAY)
    if spl_url:
        result["dailymed_found"] = True
        result["dailymed_url"] = spl_url
        label_text = _fetch_dailymed_xml(spl_url)
        time.sleep(DELAY)
        if label_text:
            has_62 = bool(SECTION_62.search(label_text))
            result["label_has_immunogenicity_section"] = has_62
            if has_62:
                sec_start = SECTION_62.search(label_text).start()
                window = label_text[sec_start:sec_start + 3000]
                hits = _extract_ada_from_text(window, name)
                if hits:
                    for h in hits:
                        h["source"] = "fda_label_sec6.2"
                    result["ada_extractions"].extend(hits)
                    if not result.get("extraction_source"):
                        result["extraction_source"] = "fda_label"

    if result["ada_extractions"]:
        result["verdict"] = "ada_value_extracted"
        unique_pcts = sorted({h["pct"] for h in result["ada_extractions"]})
        result["extracted_ada_percentages"] = unique_pcts
    elif result["pmc_fulltext_found"] or result["dailymed_found"]:
        result["verdict"] = "source_found_no_ada_pct"

    return result


def main() -> None:
    fwd = json.loads(FWD_REPORT.read_text(encoding="utf-8"))
    targets = fwd.get("immunogenicity_discussed", [])
    print(f"Deep search for {len(targets)} antibodies ...\n")

    results: list[dict] = []
    for i, t in enumerate(targets):
        name = t["antibody_name"]
        pmid = t["pmid"]
        print(f"  [{i+1}/{len(targets)}] {name} (PMID {pmid}) ...")
        r = process_antibody(name, pmid)
        results.append(r)
        print(f"    -> {r['verdict']}: {r.get('extracted_ada_percentages', [])}")

    verdicts: dict[str, int] = {}
    for r in results:
        v = r["verdict"]
        verdicts[v] = verdicts.get(v, 0) + 1

    extracted = [r for r in results if r["verdict"] == "ada_value_extracted"]

    print(f"\n{'='*70}")
    print("VERDICT SUMMARY")
    print(f"{'='*70}")
    for v, c in sorted(verdicts.items(), key=lambda x: -x[1]):
        print(f"  {v:35s} {c}")
    print(f"\n  ADA value extracted: {len(extracted)}")

    if extracted:
        print(f"\nEXTRACTED ADA VALUES:")
        for r in extracted:
            src = r.get("extraction_source", "?")
            print(f"  {r['antibody_name']:25s} pcts={r['extracted_ada_percentages']} source={src}")

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "description": "Deep ADA extraction for 32 immunogenicity-discussed antibodies via PMC full-text and DailyMed/FDA labels.",
        "total_searched": len(targets),
        "verdict_counts": verdicts,
        "extracted_count": len(extracted),
        "extracted": [
            {
                "antibody_name": r["antibody_name"],
                "pmid": r["best_pmid"],
                "extracted_ada_percentages": r.get("extracted_ada_percentages", []),
                "extraction_source": r.get("extraction_source", ""),
                "ada_extractions": r["ada_extractions"],
            }
            for r in extracted
        ],
        "all_results": results,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "deep_search_32_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
