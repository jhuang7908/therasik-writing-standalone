#!/usr/bin/env python3
"""
Phase 2 verification:
 1. For wrong-PMID entries: check all their citation_urls for ADA values
 2. For FDA/EMA PDF entries: try DailyMed API text version to extract immunogenicity data
"""
from __future__ import annotations
import json, re, time, urllib.request, urllib.parse
from pathlib import Path
from xml.etree import ElementTree as ET

REPO = Path(__file__).resolve().parents[1]
IDX_PATH = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_index.json"
HEADERS = {"User-Agent": "InSynBio-ADA-Verifier/1.0"}
RATE = 0.35
OUT = REPO / "data/ADA_reliable_package/verification"

# DailyMed SPLS search API
DAILYMED_SEARCH = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name={name}&pagesize=1"
DAILYMED_SPL = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}.xml"

WRONG_PMID_NAMES = [
    "Abciximab", "Belantamab", "Cadonilimab", "Golimumab",
    "Lecanemab", "Naxitamab", "Nirsevimab",
]
PDF_NAMES = [
    "Adalimumab", "Benralizumab", "Bevacizumab", "Brentuximab", "Burosumab",
    "Enfortumab", "Erenumab", "Galcanezumab", "Infliximab", "Olaratumab",
    "Ranibizumab", "Risankizumab", "Sarilumab", "Satralizumab",
]


def _get(url: str, timeout: int = 15) -> str:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            enc = r.headers.get_content_charset() or "utf-8"
            return raw.decode(enc, errors="replace")
    except Exception as e:
        return f"__ERROR__:{e}"


def strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def pct_in_text(claimed_display: str, text: str) -> tuple[bool, list[float]]:
    """Return (any_found, list_of_matched_pcts)."""
    clean_text = re.sub(r"9[0-9]\s*%\s*CI", "", text, flags=re.I)
    clean_text = re.sub(r"9[0-9]\s*%\s*confidence", "", clean_text, flags=re.I)
    claimed = re.findall(r"(\d+\.?\d*)\s*%", re.sub(r"9[0-9]\s*%\s*CI", "", claimed_display or "", flags=re.I))
    matched = []
    for cn in claimed:
        cv = float(cn)
        if cv <= 0:
            continue
        for m in re.finditer(r"(\d+\.?\d*)\s*%", clean_text):
            try:
                if abs(float(m.group(1)) - cv) <= 0.5:
                    matched.append(cv)
                    break
            except ValueError:
                pass
    return bool(matched), matched


def dailymed_immunogenicity_text(drug_name: str) -> tuple[str, str]:
    """Search DailyMed and return (setid, immunogenicity_section_text)."""
    search_url = DAILYMED_SEARCH.format(name=urllib.parse.quote(drug_name))
    resp = _get(search_url)
    time.sleep(RATE)
    if resp.startswith("__ERROR__"):
        return "", f"search failed: {resp}"
    try:
        data = json.loads(resp)
        spls = data.get("data", [])
        if not spls:
            return "", "no SPL found"
        setid = spls[0].get("setid", "")
    except Exception as e:
        return "", f"json parse error: {e}"

    if not setid:
        return "", "no setid"

    spl_url = DAILYMED_SPL.format(setid=setid)
    xml_text = _get(spl_url)
    time.sleep(RATE)
    if xml_text.startswith("__ERROR__"):
        return setid, f"spl fetch failed: {xml_text}"

    # Extract immunogenicity sections from SPL XML
    try:
        root = ET.fromstring(xml_text)
        ns = {"spl": "urn:hl7-org:v3"}
        immuno_parts = []
        for section in root.iter("section"):
            title_el = section.find("title")
            if title_el is not None and title_el.text and "immunogen" in title_el.text.lower():
                # Collect all text in this section
                texts = []
                for el in section.iter():
                    if el.text:
                        texts.append(el.text)
                    if el.tail:
                        texts.append(el.tail)
                immuno_parts.append(" ".join(texts))
        if immuno_parts:
            return setid, " ".join(immuno_parts)[:3000]
        # Fallback: search all text for immunogenicity context
        all_text = " ".join(t for t in (el.text for el in root.iter() if el.text) if t)
        # Find window around "immunogen"
        idx = all_text.lower().find("immunogen")
        if idx >= 0:
            return setid, all_text[max(0, idx - 100):idx + 2000]
        return setid, "no immunogenicity section found"
    except ET.ParseError as e:
        return setid, f"xml parse error: {e}"


# Load index
idx_blob = json.loads(IDX_PATH.read_text(encoding="utf-8"))
name_to_row = {r["antibody_name"]: r for r in idx_blob["index"]}

results = {}

print("=== PHASE 2: WRONG PMID entries — check all citation URLs ===\n")
for name in WRONG_PMID_NAMES:
    row = name_to_row.get(name)
    if not row:
        print(f"{name}: not in index\n")
        continue
    display = row.get("ada_value_display", "")
    urls = row.get("citation_urls") or []
    print(f"{name}  claimed={display}  urls={len(urls)}")
    entry_result = {"ada_value_display": display, "urls_checked": [], "dailymed": None}
    found = False
    for url in urls:
        if url.startswith("http"):
            print(f"  fetching: {url[:70]}")
            text = _get(url)
            time.sleep(RATE)
            if text.startswith("__ERROR__"):
                status = "fetch_error"
                matched = []
            elif "%PDF" in text[:10]:
                status = "pdf_binary"
                matched = []
            else:
                plain = strip_html(text) if "<html" in text.lower() else text
                ok, matched = pct_in_text(display, plain[:8000])
                status = "matched" if ok else "not_found"
                if ok:
                    found = True
            entry_result["urls_checked"].append({"url": url[:80], "status": status, "matched": matched})
            print(f"    → {status}  matched={matched}")
    # Also try DailyMed
    print(f"  trying DailyMed for {name}...")
    setid, dm_text = dailymed_immunogenicity_text(name)
    ok, matched = pct_in_text(display, dm_text)
    entry_result["dailymed"] = {
        "setid": setid,
        "status": "matched" if ok else ("no_immuno_section" if "no immunogen" in dm_text else "not_found"),
        "matched": matched,
        "text_snippet": dm_text[:400],
    }
    if ok:
        found = True
    print(f"  DailyMed → {entry_result['dailymed']['status']}  matched={matched}")
    entry_result["overall"] = "verified" if found else "unverified"
    results[name] = entry_result
    print()

print("\n=== PHASE 2b: FDA/EMA PDF entries — DailyMed text verification ===\n")
for name in PDF_NAMES:
    row = name_to_row.get(name)
    if not row:
        continue
    display = row.get("ada_value_display", "")
    print(f"{name}  claimed={display}")
    setid, dm_text = dailymed_immunogenicity_text(name)
    ok, matched = pct_in_text(display, dm_text)
    status = "matched" if ok else ("no_immuno_section" if "no immunogen" in dm_text else "not_found")
    results[name] = {
        "ada_value_display": display,
        "dailymed_setid": setid,
        "dailymed_status": status,
        "matched": matched,
        "text_snippet": dm_text[:400],
        "overall": "verified" if ok else "unverified",
    }
    print(f"  DailyMed → {status}  matched={matched}  snip={dm_text[:120]}")
    print()

out_path = OUT / "phase2_pdf_wrongpmid_results.json"
out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved to {out_path}")

print("\n=== FINAL TALLY ===")
verified = sum(1 for r in results.values() if r.get("overall") == "verified")
unverified = sum(1 for r in results.values() if r.get("overall") == "unverified")
print(f"Verified:   {verified}")
print(f"Unverified: {unverified}")
for name, r in sorted(results.items()):
    print(f"  {name:30s}: {r.get('overall','?')}")
