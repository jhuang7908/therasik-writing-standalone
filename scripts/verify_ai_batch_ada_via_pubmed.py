#!/usr/bin/env python3
"""
Reverse-verify ADA values for 62 AI-batch-generated entries.

For each entry with a PubMed ID:
  1. Fetch title + abstract via NCBI E-utilities (efetch).
  2. Search abstract for ADA/immunogenicity keywords.
  3. Search abstract for the claimed ADA numeric value.
  4. Classify: confirmed / plausible / unconfirmed / no_abstract.

Output: data/ADA_reliable_package/verification/ai_batch_verification_report.json
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
CLINICAL_INDEX = REPO / "data" / "ADA_reliable_package" / "clinical_db" / "clinical_ada_db_index.json"
CLINICAL_DATA = REPO / "data" / "ADA_reliable_package" / "clinical_db" / "clinical_ada_db_data.json"
EXCLUDED_JSON = REPO / "data" / "ADA_reliable_package" / "verifiable_classified" / "verifiable_ada_excluded.json"
OUT_DIR = REPO / "data" / "ADA_reliable_package" / "verification"

ADA_KEYWORDS = re.compile(
    r"(anti[- ]?drug\s+antibod|immunogenicit|ADA[\s,.]|anti[- ]?therapeutic|"
    r"neutralizing\s+antibod|binding\s+antibod|treatment[- ]emergent\s+anti)",
    re.I,
)

PERCENTAGE_RE = re.compile(r"(\d+\.?\d*)\s*%")


def _normalize_pct(s: str) -> set[str]:
    """Extract all percentage numbers from a string for matching."""
    return {m.group(1) for m in PERCENTAGE_RE.finditer(s)}


def fetch_pubmed_abstract(pmid: str, email: str = "ada-audit@insynbio.com") -> dict:
    """Fetch title + abstract from PubMed efetch XML."""
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
        + urllib.parse.urlencode({
            "db": "pubmed",
            "id": pmid,
            "rettype": "xml",
            "retmode": "xml",
            "email": email,
        })
    )
    req = urllib.request.Request(url, headers={"User-Agent": "AntibodyEngineerSuite/ADA-verifier"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        xml_bytes = resp.read()
    root = ET.fromstring(xml_bytes)
    article = root.find(".//PubmedArticle")
    if article is None:
        return {"pmid": pmid, "title": "", "abstract": "", "error": "no_article_found"}
    title_el = article.find(".//ArticleTitle")
    title = "".join(title_el.itertext()) if title_el is not None else ""
    abs_texts = []
    for at in article.findall(".//AbstractText"):
        label = at.get("Label", "")
        text = "".join(at.itertext())
        if label:
            abs_texts.append(f"{label}: {text}")
        else:
            abs_texts.append(text)
    abstract = " ".join(abs_texts)
    return {"pmid": pmid, "title": title, "abstract": abstract}


def verify_entry(name: str, ada_value: str, pmid: str) -> dict:
    """Verify one antibody's ADA value against its PubMed abstract."""
    result = {
        "antibody_name": name,
        "claimed_ada_value": ada_value,
        "pmid": pmid,
    }
    try:
        pub = fetch_pubmed_abstract(pmid)
    except Exception as e:
        result["verdict"] = "fetch_error"
        result["error"] = str(e)
        return result

    result["title"] = pub.get("title", "")
    abstract = pub.get("abstract", "")
    result["abstract_length"] = len(abstract)

    if not abstract:
        result["verdict"] = "no_abstract"
        result["note"] = "PubMed entry has no abstract; cannot verify from abstract alone."
        return result

    name_lower = name.lower()
    name_in_text = name_lower in (pub["title"] + " " + abstract).lower()
    result["antibody_in_text"] = name_in_text

    ada_kw_match = bool(ADA_KEYWORDS.search(abstract))
    result["ada_keywords_in_abstract"] = ada_kw_match

    claimed_pcts = _normalize_pct(ada_value)
    abstract_pcts = _normalize_pct(abstract)
    title_pcts = _normalize_pct(pub.get("title", ""))
    all_pcts = abstract_pcts | title_pcts
    matched_pcts = claimed_pcts & all_pcts
    result["claimed_percentages"] = sorted(claimed_pcts)
    result["abstract_percentages"] = sorted(abstract_pcts)
    result["matched_percentages"] = sorted(matched_pcts)

    if matched_pcts and ada_kw_match:
        result["verdict"] = "confirmed"
        result["note"] = "ADA keyword + matching percentage found in abstract."
    elif matched_pcts and name_in_text:
        result["verdict"] = "plausible"
        result["note"] = "Matching percentage found, antibody named, but no explicit ADA keyword."
    elif ada_kw_match and not matched_pcts:
        result["verdict"] = "value_mismatch"
        result["note"] = "Abstract discusses immunogenicity but claimed percentage not found."
    elif not ada_kw_match and not matched_pcts:
        result["verdict"] = "unconfirmed"
        result["note"] = "Neither ADA keywords nor matching percentage in abstract."
    else:
        result["verdict"] = "partial"
        result["note"] = "Percentage matched but no ADA context."

    return result


def main() -> None:
    idx_blob = json.loads(CLINICAL_INDEX.read_text(encoding="utf-8"))
    vx_blob = json.loads(EXCLUDED_JSON.read_text(encoding="utf-8"))

    ci_map = {r["antibody_name"]: r for r in idx_blob["index"]}
    ai_names = [
        e["antibody_name"]
        for e in vx_blob["excluded"]
        if "ai_batch" in e.get("reason", "")
    ]

    results: list[dict] = []
    skipped: list[dict] = []

    for name in sorted(ai_names):
        row = ci_map[name]
        ada = row.get("ada_value_display") or ""
        pmids = row.get("pmids_extracted") or []

        if not pmids:
            skipped.append({"antibody_name": name, "ada_value": ada, "reason": "no_pmid"})
            continue

        pmid = pmids[0]
        print(f"  Verifying {name} (PMID {pmid}, claimed ADA: {ada}) ...")
        r = verify_entry(name, ada, pmid)
        results.append(r)
        time.sleep(0.4)

    verdicts: dict[str, int] = {}
    for r in results:
        v = r["verdict"]
        verdicts[v] = verdicts.get(v, 0) + 1

    confirmed = [r for r in results if r["verdict"] == "confirmed"]
    plausible = [r for r in results if r["verdict"] == "plausible"]
    rehabilitable = confirmed + plausible

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "description": "Reverse verification of 62 AI-batch ADA entries via PubMed abstract check.",
        "total_ai_batch": len(ai_names),
        "verified_via_pubmed": len(results),
        "skipped_no_pmid": len(skipped),
        "verdict_counts": verdicts,
        "rehabilitable_count": len(rehabilitable),
        "rehabilitable_names": [r["antibody_name"] for r in rehabilitable],
        "results": results,
        "skipped": skipped,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "ai_batch_verification_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nVerdict summary: {verdicts}")
    print(f"Rehabilitable (confirmed + plausible): {len(rehabilitable)}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
