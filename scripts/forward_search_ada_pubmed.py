#!/usr/bin/env python3
"""
Forward PubMed search for 62 AI-batch antibodies.

For each antibody:
  1. esearch: "antibody_name" AND (immunogenicity OR anti-drug antibod* OR ADA)
  2. efetch top-N abstracts
  3. Scan abstract for ADA keywords + percentage values
  4. Report: which antibodies have real findable ADA literature

Output: data/ADA_reliable_package/verification/forward_search_report.json
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
EXCLUDED_JSON = REPO / "data" / "ADA_reliable_package" / "verifiable_classified" / "verifiable_ada_excluded.json"
CLINICAL_INDEX = REPO / "data" / "ADA_reliable_package" / "clinical_db" / "clinical_ada_db_index.json"
OUT_DIR = REPO / "data" / "ADA_reliable_package" / "verification"

EMAIL = "ada-audit@insynbio.com"
DELAY = 0.35
TOP_N = 5

ADA_KW = re.compile(
    r"(anti[- ]?drug\s+antibod|immunogenicit|ADA[,.\s;:\)]|"
    r"neutralizing\s+antibod|binding\s+antibod|treatment[- ]emergent\s+anti|"
    r"anti[- ]?therapeutic\s+antibod|HAHA|HACA|HAMA)",
    re.I,
)
PCT_RE = re.compile(r"(\d+\.?\d*)\s*%")
ADA_NUMERIC_CONTEXT = re.compile(
    r"(?:ADA|anti[- ]?drug|immunogenic|neutralizing)[^.]{0,120}?(\d+\.?\d*)\s*%",
    re.I,
)


def esearch(query: str) -> list[str]:
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
        + urllib.parse.urlencode({
            "db": "pubmed", "term": query,
            "retmax": str(TOP_N), "retmode": "json",
            "sort": "relevance", "email": EMAIL,
        })
    )
    req = urllib.request.Request(url, headers={"User-Agent": "AntibodyEngineerSuite/forward-search"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    return data.get("esearchresult", {}).get("idlist", [])


def efetch_batch(pmids: list[str]) -> dict[str, dict]:
    """Fetch titles + abstracts for a batch of PMIDs. Returns {pmid: {title, abstract}}."""
    if not pmids:
        return {}
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
        + urllib.parse.urlencode({
            "db": "pubmed", "id": ",".join(pmids),
            "rettype": "xml", "retmode": "xml", "email": EMAIL,
        })
    )
    req = urllib.request.Request(url, headers={"User-Agent": "AntibodyEngineerSuite/forward-search"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        xml_bytes = resp.read()
    root = ET.fromstring(xml_bytes)
    out: dict[str, dict] = {}
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        if pmid_el is None:
            continue
        pmid = pmid_el.text.strip()
        title_el = article.find(".//ArticleTitle")
        title = "".join(title_el.itertext()) if title_el is not None else ""
        abs_parts: list[str] = []
        for at in article.findall(".//AbstractText"):
            label = at.get("Label", "")
            text = "".join(at.itertext())
            abs_parts.append(f"{label}: {text}" if label else text)
        out[pmid] = {"title": title, "abstract": " ".join(abs_parts)}
    return out


def analyze_abstract(name: str, pmid: str, title: str, abstract: str) -> dict:
    full_text = title + " " + abstract
    has_name = name.lower() in full_text.lower()
    has_ada_kw = bool(ADA_KW.search(full_text))
    all_pcts = sorted({m.group(1) for m in PCT_RE.finditer(abstract)})
    ada_pcts = sorted({m.group(1) for m in ADA_NUMERIC_CONTEXT.finditer(full_text)})
    return {
        "pmid": pmid,
        "title": title[:200],
        "abstract_length": len(abstract),
        "antibody_in_text": has_name,
        "ada_keywords_found": has_ada_kw,
        "ada_associated_percentages": ada_pcts,
        "all_percentages": all_pcts[:15],
    }


def main() -> None:
    vx = json.loads(EXCLUDED_JSON.read_text(encoding="utf-8"))
    ci = json.loads(CLINICAL_INDEX.read_text(encoding="utf-8"))
    ci_map = {r["antibody_name"]: r for r in ci["index"]}

    ai_names = sorted(
        e["antibody_name"]
        for e in vx["excluded"]
        if "ai_batch" in e.get("reason", "")
    )

    print(f"Forward PubMed search for {len(ai_names)} antibodies ...\n")

    search_results: dict[str, list[str]] = {}
    for i, name in enumerate(ai_names):
        query = f'"{name}"[Title/Abstract] AND (immunogenicity OR "anti-drug antibod*" OR ADA)'
        try:
            pmids = esearch(query)
        except Exception as e:
            print(f"  [{i+1}/{len(ai_names)}] {name}: search error - {e}")
            pmids = []
        search_results[name] = pmids
        hit_label = f"{len(pmids)} hits" if pmids else "0 hits"
        print(f"  [{i+1}/{len(ai_names)}] {name}: {hit_label}")
        time.sleep(DELAY)

    all_pmids = sorted({p for ps in search_results.values() for p in ps})
    print(f"\nFetching {len(all_pmids)} unique abstracts in batches ...")
    abstract_map: dict[str, dict] = {}
    batch_size = 50
    for start in range(0, len(all_pmids), batch_size):
        batch = all_pmids[start:start + batch_size]
        try:
            fetched = efetch_batch(batch)
            abstract_map.update(fetched)
        except Exception as e:
            print(f"  Batch {start}-{start+len(batch)}: fetch error - {e}")
        time.sleep(DELAY * 2)
    print(f"  Fetched {len(abstract_map)} abstracts.\n")

    entries: list[dict] = []
    for name in ai_names:
        row = ci_map.get(name, {})
        claimed_ada = row.get("ada_value_display") or ""
        pmids = search_results.get(name, [])

        entry: dict = {
            "antibody_name": name,
            "claimed_ada_value_ai": claimed_ada,
            "pubmed_query_hits": len(pmids),
            "pmids_found": pmids,
            "abstracts_analyzed": [],
            "best_verdict": "no_hits",
        }

        best_score = 0
        best_ada_pcts: list[str] = []
        best_pmid = ""
        best_title = ""

        for pmid in pmids:
            info = abstract_map.get(pmid)
            if not info:
                continue
            analysis = analyze_abstract(name, pmid, info["title"], info["abstract"])
            entry["abstracts_analyzed"].append(analysis)

            score = 0
            if analysis["antibody_in_text"]:
                score += 1
            if analysis["ada_keywords_found"]:
                score += 2
            if analysis["ada_associated_percentages"]:
                score += 4
            if score > best_score:
                best_score = score
                best_ada_pcts = analysis["ada_associated_percentages"]
                best_pmid = pmid
                best_title = analysis["title"]

        if best_score >= 6:
            entry["best_verdict"] = "ada_value_found"
        elif best_score >= 3:
            entry["best_verdict"] = "immunogenicity_discussed"
        elif best_score >= 1:
            entry["best_verdict"] = "antibody_mentioned_only"
        elif pmids:
            entry["best_verdict"] = "hits_but_irrelevant"

        entry["best_pmid"] = best_pmid
        entry["best_title"] = best_title
        entry["real_ada_percentages_in_abstract"] = best_ada_pcts
        entries.append(entry)

    verdicts: dict[str, int] = {}
    for e in entries:
        v = e["best_verdict"]
        verdicts[v] = verdicts.get(v, 0) + 1

    ada_found = [e for e in entries if e["best_verdict"] == "ada_value_found"]
    immuno_discussed = [e for e in entries if e["best_verdict"] == "immunogenicity_discussed"]
    rehabilitable = ada_found + immuno_discussed

    print("=" * 70)
    print("VERDICT SUMMARY")
    print("=" * 70)
    for v, c in sorted(verdicts.items(), key=lambda x: -x[1]):
        print(f"  {v:35s} {c}")
    print(f"\n  Rehabilitable (ada_value_found + immunogenicity_discussed): {len(rehabilitable)}")
    print()

    if ada_found:
        print("ADA VALUE FOUND IN ABSTRACT:")
        for e in ada_found:
            print(f"  {e['antibody_name']:25s} PMID {e['best_pmid']:12s} ADA pcts: {e['real_ada_percentages_in_abstract']}")
    if immuno_discussed:
        print("\nIMMUNOGENICITY DISCUSSED (no specific % extracted):")
        for e in immuno_discussed:
            print(f"  {e['antibody_name']:25s} PMID {e['best_pmid']:12s} title: {e['best_title'][:80]}")

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "description": "Forward PubMed search for 62 AI-batch antibodies: real literature with ADA/immunogenicity data.",
        "total_searched": len(ai_names),
        "verdict_counts": verdicts,
        "rehabilitable_count": len(rehabilitable),
        "ada_value_found": [
            {
                "antibody_name": e["antibody_name"],
                "pmid": e["best_pmid"],
                "real_ada_percentages": e["real_ada_percentages_in_abstract"],
                "claimed_ada_ai": e["claimed_ada_value_ai"],
                "title": e["best_title"],
            }
            for e in ada_found
        ],
        "immunogenicity_discussed": [
            {
                "antibody_name": e["antibody_name"],
                "pmid": e["best_pmid"],
                "title": e["best_title"],
            }
            for e in immuno_discussed
        ],
        "entries": entries,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "forward_search_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
