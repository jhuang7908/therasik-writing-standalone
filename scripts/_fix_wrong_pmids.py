#!/usr/bin/env python3
"""
For the 7 entries with confirmed-wrong PMIDs, search PubMed for the correct
immunogenicity paper and verify if the claimed ADA % appears in the abstract.
"""
from __future__ import annotations
import json, re, time, urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
HEADERS = {"User-Agent": "InSynBio-ADA-Verifier/1.0"}
RATE = 0.4
REPO = Path(__file__).resolve().parents[1]

WRONG_PMID_ENTRIES = {
    "Abciximab":   {"claimed_ada": "3.1%",   "search": "abciximab immunogenicity anti-drug antibody incidence"},
    "Belantamab":  {"claimed_ada": "17%",    "search": "belantamab mafodotin ADA anti-drug antibody immunogenicity"},
    "Cadonilimab": {"claimed_ada": "5.2%",   "search": "cadonilimab AK104 anti-drug antibody immunogenicity"},
    "Golimumab":   {"claimed_ada": "4.1-4.6%","search": "golimumab immunogenicity anti-drug antibody incidence"},
    "Lecanemab":   {"claimed_ada": "3.4%",   "search": "lecanemab immunogenicity anti-drug antibody ADA incidence"},
    "Naxitamab":   {"claimed_ada": "8%",     "search": "naxitamab anti-drug antibody immunogenicity incidence"},
    "Nirsevimab":  {"claimed_ada": "5% 3.3%","search": "nirsevimab anti-drug antibody ADA immunogenicity incidence"},
}


def _get(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as r:
            raw = r.read()
            enc = r.headers.get_content_charset() or "utf-8"
            return raw.decode(enc, errors="replace")
    except Exception as e:
        return f"__ERROR__:{e}"


def esearch(query: str, retmax: int = 5) -> list[str]:
    q = urllib.parse.quote(query)
    url = f"{EUTILS}/esearch.fcgi?db=pubmed&retmode=json&retmax={retmax}&term={q}"
    resp = _get(url)
    time.sleep(RATE)
    if resp.startswith("__ERROR__"):
        return []
    try:
        return json.loads(resp).get("esearchresult", {}).get("idlist", [])
    except Exception:
        return []


def efetch_abstract(pmids: list[str]) -> dict[str, str]:
    """Fetch abstracts for a list of PMIDs. Returns {pmid: abstract_text}."""
    if not pmids:
        return {}
    ids = ",".join(pmids)
    url = f"{EUTILS}/efetch.fcgi?db=pubmed&rettype=abstract&retmode=xml&id={ids}"
    xml_text = _get(url)
    time.sleep(RATE)
    result = {}
    try:
        root = ET.fromstring(xml_text)
        for article in root.findall(".//PubmedArticle"):
            pmid_node = article.find(".//PMID")
            if pmid_node is None:
                continue
            pmid = pmid_node.text or ""
            title_node = article.find(".//ArticleTitle")
            title = title_node.text or "" if title_node is not None else ""
            parts = [title]
            for ab in article.findall(".//AbstractText"):
                parts.append(ab.text or "")
            result[pmid] = " ".join(parts)
    except ET.ParseError:
        pass
    return result


def pct_in_text(pct_str: str, text: str) -> bool:
    nums = re.findall(r"(\d+\.?\d*)\s*%", pct_str)
    clean = re.sub(r"9[0-9]\s*%\s*CI", "", text, flags=re.I)
    for n in nums:
        v = float(n)
        for m in re.finditer(r"(\d+\.?\d*)\s*%", clean):
            try:
                if abs(float(m.group(1)) - v) <= 0.5:
                    return True
            except ValueError:
                pass
    return False


import urllib.parse

print("=== Searching for correct PMIDs for 7 wrong-PMID entries ===\n")

results = {}

for name, info in WRONG_PMID_ENTRIES.items():
    print(f"--- {name} (claimed ADA: {info['claimed_ada']}) ---")
    pmids = esearch(info["search"], retmax=8)
    print(f"  esearch returned {len(pmids)} PMIDs: {pmids}")
    
    if not pmids:
        results[name] = {"status": "no_results", "new_pmid": None, "title": None, "abstract_snippet": None}
        print("  No results found.\n")
        continue
    
    abstracts = efetch_abstract(pmids)
    
    found = False
    for pmid, text in abstracts.items():
        snippet = text[:150]
        has_pct = pct_in_text(info["claimed_ada"], text)
        marker = "✓ ADA% FOUND" if has_pct else "  (no match)"
        print(f"  PMID {pmid}: {snippet[:100]}...")
        print(f"    {marker}")
        if has_pct and not found:
            results[name] = {
                "status": "found_correct_pmid",
                "new_pmid": pmid,
                "claimed_ada": info["claimed_ada"],
                "title": text[:200],
                "abstract_snippet": text[:400],
            }
            found = True
    
    if not found:
        # Take the most relevant paper even without % match
        first_pmid = pmids[0]
        first_text = abstracts.get(first_pmid, "")
        results[name] = {
            "status": "no_pct_match_best_candidate",
            "new_pmid": first_pmid,
            "claimed_ada": info["claimed_ada"],
            "title": first_text[:200],
            "abstract_snippet": first_text[:400],
        }
        print(f"  No % match found. Best candidate: PMID {first_pmid}")
    print()

# Save results
out = REPO / "data/ADA_reliable_package/verification/wrong_pmid_fix_results.json"
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved to {out}")

print("\n=== SUMMARY ===")
for name, res in results.items():
    status = res["status"]
    pmid = res.get("new_pmid")
    print(f"  {name:20s}: {status}  new_pmid={pmid}")
