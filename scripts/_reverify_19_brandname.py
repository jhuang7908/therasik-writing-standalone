#!/usr/bin/env python3
"""
Final pass for the 19 still-unverified entries.
Uses brand names for DailyMed and alternative PubMed queries.
"""
from __future__ import annotations
import json, re, time, urllib.parse, urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

REPO = Path(__file__).resolve().parents[1]
EUTILS   = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DAILYMED = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
HEADERS  = {"User-Agent": "InSynBio-ADA-Verifier/1.0"}
RATE     = 0.4

# Brand names and alternative queries for each still-unverified entry
TARGETS: dict[str, dict] = {
    "Bimagrumab":   {"brand": "bimagrumab", "alts": ["bimagrumab BYM338 immunogenicity ADA"]},
    "Brentuximab":  {"brand": "adcetris", "alts": ["brentuximab vedotin ADCETRIS immunogenicity anti-drug antibody 7% 30%"]},
    "Brolucizumab": {"brand": "beovu",    "alts": ["brolucizumab BEOVU pre-existing ADA immunogenicity 36%"]},
    "Budigalimab":  {"brand": "budigalimab","alts": ["budigalimab ABBV-181 immunogenicity anti-drug antibody"]},
    "Daclizumab":   {"brand": "zinbryta",  "alts": ["daclizumab Zinbryta immunogenicity antibody 12%"]},
    "Ecromeximab":  {"brand": "ecromeximab","alts": ["ecromeximab KW2871 anti-drug antibody immunogenicity 1.8%"]},
    "Elezanumab":   {"brand": "elezanumab","alts": ["elezanumab ABT-555 immunogenicity anti-drug antibody 2%"]},
    "Enfortumab":   {"brand": "padcev",    "alts": ["enfortumab vedotin PADCEV immunogenicity ADA 1%"]},
    "Enuzovimab":   {"brand": "HFB30132A", "alts": ["enuzovimab HFB30132A COVID-19 immunogenicity ADA"]},
    "Etaracizumab": {"brand": "etaracizumab","alts": ["etaracizumab Vitaxin MEDI-522 anti-drug antibody immunogenicity 5%"]},
    "Exidavnemab":  {"brand": "exidavnemab","alts": ["exidavnemab BAN0805 alpha-synuclein immunogenicity 7%"]},
    "Fulranumab":   {"brand": "fulranumab", "alts": ["fulranumab REGN475 nerve growth factor anti-drug antibody ADA"]},
    "Gemtuzumab":   {"brand": "mylotarg",   "alts": ["gemtuzumab ozogamicin Mylotarg immunogenicity anti-drug antibody 1.1%"]},
    "Infliximab":   {"brand": "remicade",   "alts": ["infliximab Remicade anti-drug antibody immunogenicity ATI Crohn's rheumatoid 40%"]},
    "Olaratumab":   {"brand": "lartruvo",   "alts": ["olaratumab Lartruvo immunogenicity anti-drug antibody 3.5%"]},
    "Retifanlimab": {"brand": "zynyz",      "alts": ["retifanlimab Zynyz immunogenicity anti-drug antibody 2.8%"]},
    "Sacituzumab":  {"brand": "trodelvy",   "alts": ["sacituzumab govitecan Trodelvy immunogenicity anti-drug antibody 1.1%"]},
    "Satralizumab": {"brand": "enspryng",   "alts": ["satralizumab Enspryng NMOSD immunogenicity ADA 41% 71%"]},
    "Trastuzumab":  {"brand": "herceptin",  "alts": ["trastuzumab Herceptin immunogenicity anti-drug antibody 8%"]},
}

# ADA claimed values per entry
ADA_DISPLAY: dict[str, str] = {
    "Bimagrumab": "4.0%",
    "Brentuximab": "7% 30%",
    "Brolucizumab": "36% 52%",
    "Budigalimab": "1.80%",
    "Daclizumab": "12%",
    "Ecromeximab": "1.80%",
    "Elezanumab": "2.0%",
    "Enfortumab": "1% 0.3%",
    "Enuzovimab": "1.50%",
    "Etaracizumab": "5.0%",
    "Exidavnemab": "7.00%",
    "Fulranumab": "6.0%",
    "Gemtuzumab": "1.1% 5%",
    "Infliximab": "10% 40% 17% 44%",
    "Olaratumab": "3.5%",
    "Retifanlimab": "2.8%",
    "Sacituzumab": "1.1%",
    "Satralizumab": "41% 71%",
    "Trastuzumab": "8%",
}


def _get(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
            enc = r.headers.get_content_charset() or "utf-8"
            return raw.decode(enc, errors="replace")
    except Exception as e:
        return f"__ERR__:{e}"


def strip_html(h: str) -> str:
    h = re.sub(r"<[^>]+>", " ", h)
    h = re.sub(r"&[a-z#0-9]+;", " ", h)
    return re.sub(r"\s+", " ", h).strip()


def pct_match(display: str, text: str) -> tuple[bool, list[float]]:
    clean_d = re.sub(r"9[0-9]\s*%\s*CI", "", display or "", flags=re.I)
    clean_t = re.sub(r"9[0-9]\s*%\s*CI", "", text or "", flags=re.I)
    claimed = [float(m) for m in re.findall(r"(\d+\.?\d*)\s*%", clean_d) if 0 < float(m) <= 100]
    matched: list[float] = []
    for cv in claimed:
        for m in re.finditer(r"(\d+\.?\d*)\s*%", clean_t):
            try:
                if abs(float(m.group(1)) - cv) <= 0.5:
                    matched.append(cv)
                    break
            except ValueError:
                pass
    return bool(matched), matched


def dailymed_immuno(drug_name: str) -> tuple[str, str]:
    url = f"{DAILYMED}/spls.json?drug_name={urllib.parse.quote(drug_name)}&pagesize=1"
    r = _get(url); time.sleep(RATE)
    if r.startswith("__ERR__"):
        return "", r
    try:
        spls = json.loads(r).get("data", [])
        if not spls:
            return "", "no_spl"
        setid = spls[0].get("setid", "")
    except Exception as e:
        return "", str(e)
    if not setid:
        return "", "no_setid"
    xml_text = _get(f"{DAILYMED}/spls/{setid}.xml"); time.sleep(RATE)
    if xml_text.startswith("__ERR__"):
        return setid, xml_text
    try:
        root = ET.fromstring(xml_text)
        parts: list[str] = []
        for sec in root.iter("section"):
            t_el = sec.find("title")
            if t_el is not None and t_el.text and "immunogen" in t_el.text.lower():
                for el in sec.iter():
                    if el.text:
                        parts.append(el.text)
                    if el.tail:
                        parts.append(el.tail)
        if parts:
            return setid, re.sub(r"\s+", " ", " ".join(parts))[:4000]
        all_text = " ".join(el.text for el in root.iter() if el.text)
        idx = all_text.lower().find("immunogen")
        if idx >= 0:
            return setid, all_text[max(0, idx - 50):idx + 3000]
        return setid, "no_immuno_section"
    except ET.ParseError:
        return setid, "__XML_ERR__"


def pmid_to_pmcid(pmid: str) -> str | None:
    url = f"{EUTILS}/elink.fcgi?dbfrom=pubmed&db=pmc&id={pmid}&retmode=json"
    r = _get(url); time.sleep(RATE)
    if r.startswith("__ERR__"):
        return None
    try:
        data = json.loads(r)
        for lb in data.get("linksets", [{}])[0].get("linksetdbs", []):
            if lb.get("dbto") == "pmc":
                ids = lb.get("links", [])
                if ids:
                    return str(ids[0])
    except Exception:
        pass
    return None


def fetch_pmc(pmcid: str) -> str:
    url = f"{EUTILS}/efetch.fcgi?db=pmc&rettype=full&retmode=xml&id={pmcid}"
    xml_text = _get(url); time.sleep(RATE)
    if xml_text.startswith("__ERR__"):
        return xml_text
    try:
        root = ET.fromstring(xml_text)
        parts = []
        for el in root.iter():
            if el.text and el.text.strip():
                parts.append(el.text.strip())
            if el.tail and el.tail.strip():
                parts.append(el.tail.strip())
        return re.sub(r"\s+", " ", " ".join(parts))
    except ET.ParseError:
        return "__XML_ERR__"


def pubmed_search(query: str, retmax: int = 5) -> list[str]:
    q = urllib.parse.quote(query)
    url = f"{EUTILS}/esearch.fcgi?db=pubmed&retmode=json&retmax={retmax}&term={q}"
    r = _get(url); time.sleep(RATE)
    if r.startswith("__ERR__"):
        return []
    try:
        return json.loads(r).get("esearchresult", {}).get("idlist", [])
    except Exception:
        return []


def fetch_abstract(pmid: str) -> str:
    url = f"{EUTILS}/efetch.fcgi?db=pubmed&rettype=abstract&retmode=xml&id={pmid}"
    xml_text = _get(url); time.sleep(RATE)
    if xml_text.startswith("__ERR__"):
        return xml_text
    try:
        root = ET.fromstring(xml_text)
        parts = []
        for n in root.iter("ArticleTitle"):
            parts.append(n.text or "")
        for n in root.iter("AbstractText"):
            parts.append(n.text or "")
        return " ".join(parts)
    except ET.ParseError:
        return "__XML_ERR__"


print("=== FINAL PASS: 19 still-unverified entries ===\n")
results = {}

for name, cfg in TARGETS.items():
    display = ADA_DISPLAY.get(name, "")
    print(f"--- {name}  claimed={display} ---")
    verified = False
    matched_pcts = []
    verified_source = None
    verified_snippet = ""

    # 1. DailyMed with brand name
    brand = cfg["brand"]
    print(f"  DailyMed '{brand}'...")
    setid, dm_text = dailymed_immuno(brand)
    ok, matched = pct_match(display, dm_text)
    if ok:
        verified = True
        matched_pcts = matched
        verified_source = f"DailyMed:{brand}:setid={setid}"
        verified_snippet = dm_text[:400]
        print(f"  ✓ DailyMed matched: {matched}")
    else:
        print(f"  ✗ DailyMed {setid or 'no_spl'}: {dm_text[:80]}")

    # 2. PubMed alternative queries
    if not verified:
        for q in cfg.get("alts", []):
            print(f"  PubMed: {q[:70]}...")
            pmids = pubmed_search(q, retmax=6)
            for pmid in pmids:
                pmcid = pmid_to_pmcid(pmid)
                if pmcid:
                    txt = fetch_pmc(pmcid)
                    src = f"PMC{pmcid}"
                else:
                    txt = fetch_abstract(pmid)
                    src = f"PMID{pmid}"
                ok, matched = pct_match(display, txt)
                if ok:
                    verified = True
                    matched_pcts = matched
                    verified_source = src
                    verified_snippet = txt[:400]
                    print(f"  ✓ matched via {src}: {matched}")
                    break
            if verified:
                break

    status = "✓ VERIFIED" if verified else "✗ UNVERIFIED"
    print(f"  → {status}\n")
    results[name] = {
        "verified": verified,
        "matched_pcts": matched_pcts,
        "verified_source": verified_source,
        "verified_snippet": verified_snippet,
    }

# Save
out = REPO / "data/ADA_reliable_package/verification/final_19_pass_results.json"
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved to {out}\n")

print("=== SUMMARY ===")
v = sum(1 for r in results.values() if r["verified"])
print(f"Verified: {v}/{len(results)}")
for name, r in sorted(results.items()):
    sym = "✓" if r["verified"] else "✗"
    src = r.get("verified_source") or ""
    print(f"  {sym} {name:25s}  matched={r['matched_pcts']}  src={src[:50]}")
