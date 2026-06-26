#!/usr/bin/env python3
"""
Full-text reverse verification for the 31 unverified entries.

Strategy per entry:
  1. If PMC URL → extract PMCID, fetch full-text XML
  2. If PMID → PMID→PMCID elink, then PMC full-text XML
  3. If FDA label URL → DailyMed SPL XML (immunogenicity section)
  4. If EMA URL → new PubMed search "{drug} immunogenicity ADA" + DailyMed
  5. If all fail → targeted PubMed search for specific ADA % + drug name
"""
from __future__ import annotations
import csv, json, re, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

REPO = Path(__file__).resolve().parents[1]
IDX_PATH = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_index.json"
P1_PATH  = REPO / "data/ADA_reliable_package/verification/full_reverification_report.json"
OUT_DIR  = REPO / "data/ADA_reliable_package/verification"

EUTILS  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DAILYMED = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
HEADERS  = {"User-Agent": "InSynBio-ADA-Verifier/1.0"}
RATE     = 0.4


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def _get(url: str, timeout: int = 15) -> str:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            enc = r.headers.get_content_charset() or "utf-8"
            return raw.decode(enc, errors="replace")
    except Exception as e:
        return f"__ERR__:{e}"


def strip_html(h: str) -> str:
    h = re.sub(r"<[^>]+>", " ", h)
    h = re.sub(r"&[a-z#0-9]+;", " ", h)
    return re.sub(r"\s+", " ", h).strip()


# ─── NCBI helpers ─────────────────────────────────────────────────────────────

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


def fetch_pmc_text(pmcid: str) -> str:
    url = f"{EUTILS}/efetch.fcgi?db=pmc&rettype=full&retmode=xml&id={pmcid}"
    xml_text = _get(url); time.sleep(RATE)
    if xml_text.startswith("__ERR__"):
        return xml_text
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return "__XML_ERR__"
    parts: list[str] = []
    for el in root.iter():
        if el.text and el.text.strip():
            parts.append(el.text.strip())
        if el.tail and el.tail.strip():
            parts.append(el.tail.strip())
    return re.sub(r"\s+", " ", " ".join(parts))


def fetch_pubmed_abstract(pmid: str) -> str:
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


def pubmed_search_fulltext(query: str, retmax: int = 5) -> list[str]:
    q = urllib.parse.quote(query)
    url = f"{EUTILS}/esearch.fcgi?db=pubmed&retmode=json&retmax={retmax}&term={q}"
    r = _get(url); time.sleep(RATE)
    if r.startswith("__ERR__"):
        return []
    try:
        return json.loads(r).get("esearchresult", {}).get("idlist", [])
    except Exception:
        return []


def dailymed_immuno(drug_name: str) -> tuple[str, str]:
    """Return (setid, immunogenicity_text_section)."""
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
        # Broader fallback
        all_text = " ".join(el.text for el in root.iter() if el.text)
        idx = all_text.lower().find("immunogen")
        if idx >= 0:
            return setid, all_text[max(0, idx - 50):idx + 3000]
        return setid, "no_immuno_section"
    except ET.ParseError:
        return setid, "__XML_ERR__"


# ─── ADA matching ─────────────────────────────────────────────────────────────

def pct_match(display: str, text: str) -> tuple[bool, list[float]]:
    """Return (any_match, list_of_matched_pcts)."""
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


# ─── main ─────────────────────────────────────────────────────────────────────

def verify_entry(row: dict) -> dict:
    name    = row["antibody_name"]
    display = row.get("ada_value_display") or ""
    pmids   = [str(p) for p in (row.get("pmids_extracted") or []) if str(p).strip().isdigit()]
    urls    = [u for u in (row.get("citation_urls") or []) if isinstance(u, str)]

    result = {
        "antibody_name": name,
        "ada_value_display": display,
        "claimed_pcts": [float(m) for m in re.findall(r"(\d+\.?\d*)\s*%",
                         re.sub(r"9[0-9]\s*%\s*CI","",display,flags=re.I)) if 0 < float(m) <= 100],
        "strategies_tried": [],
        "verified": False,
        "matched_pcts": [],
        "verified_source": None,
        "verified_snippet": "",
    }

    def _record(strategy, text, source_label):
        ok, matched = pct_match(display, text)
        result["strategies_tried"].append({
            "strategy": strategy,
            "source": source_label[:80],
            "ok": ok,
            "matched": matched,
            "snippet": text[:300] if not text.startswith("__") else text[:100],
        })
        if ok and not result["verified"]:
            result["verified"] = True
            result["matched_pcts"] = matched
            result["verified_source"] = source_label[:80]
            result["verified_snippet"] = text[:400]

    # ── Strategy 1: PMC full text via PMC URL ───────────────────────────────
    for url in urls:
        m = re.search(r"pmc\.ncbi\.nlm\.nih\.gov/articles/PMC(\d+)", url, re.I)
        if m:
            pmcid = m.group(1)
            print(f"  S1 PMC {pmcid}...")
            txt = fetch_pmc_text(pmcid)
            _record("pmc_fulltext_url", txt, f"PMC{pmcid}")
            if result["verified"]:
                return result

    # ── Strategy 2: PMID → PMCID → PMC full text ───────────────────────────
    for pmid in pmids:
        print(f"  S2 PMID→PMCID {pmid}...")
        pmcid = pmid_to_pmcid(pmid)
        if pmcid:
            print(f"     PMCID={pmcid}, fetching full text...")
            txt = fetch_pmc_text(pmcid)
            _record(f"pmc_via_pmid_{pmid}", txt, f"PMC{pmcid}")
            if result["verified"]:
                return result
        else:
            # Fall back to abstract
            print(f"  S2b no PMC, abstract {pmid}...")
            txt = fetch_pubmed_abstract(pmid)
            _record(f"pubmed_abstract_{pmid}", txt, f"PMID{pmid}")
            if result["verified"]:
                return result

    # ── Strategy 3: DailyMed for FDA label URLs ─────────────────────────────
    has_fda_url = any("accessdata.fda.gov" in u or "rxabbvie" in u for u in urls)
    if has_fda_url or not pmids:
        print(f"  S3 DailyMed {name}...")
        setid, dm_text = dailymed_immuno(name)
        _record("dailymed_spl", dm_text, f"DailyMed setid={setid}")
        if result["verified"]:
            return result

    # ── Strategy 4: EMA URL → targeted PubMed search ───────────────────────
    has_ema = any("ema.europa.eu" in u for u in urls)
    if has_ema:
        q = f"{name} immunogenicity anti-drug antibody ADA incidence"
        print(f"  S4 PubMed search: {q[:60]}...")
        new_pmids = pubmed_search_fulltext(q, retmax=6)
        for nid in new_pmids:
            pmcid = pmid_to_pmcid(nid)
            if pmcid:
                print(f"     PMID {nid}→PMC{pmcid}")
                txt = fetch_pmc_text(pmcid)
            else:
                txt = fetch_pubmed_abstract(nid)
            _record(f"pubmed_search_pmid_{nid}", txt, f"PMID{nid}")
            if result["verified"]:
                return result

    # ── Strategy 5: Targeted search with ADA % in query ────────────────────
    claimed_pcts = result["claimed_pcts"]
    if claimed_pcts and not result["verified"]:
        pct_str = " ".join(f"{p}%" for p in claimed_pcts[:2])
        q = f"{name} {pct_str} immunogenicity ADA antibody"
        print(f"  S5 targeted search: {q[:70]}...")
        new_pmids = pubmed_search_fulltext(q, retmax=5)
        for nid in new_pmids:
            pmcid = pmid_to_pmcid(nid)
            if pmcid:
                txt = fetch_pmc_text(pmcid)
            else:
                txt = fetch_pubmed_abstract(nid)
            _record(f"targeted_search_{nid}", txt, f"PMID{nid}")
            if result["verified"]:
                return result

    return result


def main() -> None:
    idx_blob = json.loads(IDX_PATH.read_text(encoding="utf-8"))
    targets = [
        e for e in idx_blob["index"]
        if e.get("verification_status") == "unverified_pct_not_in_abstract_fulltext_needed"
    ]
    print(f"Reverse verifying {len(targets)} entries...\n")

    results: list[dict] = []
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for i, row in enumerate(sorted(targets, key=lambda x: x["antibody_name"]), 1):
        print(f"[{i:02d}/{len(targets)}] {row['antibody_name']}  pcts={row.get('ada_value_display','')[:50]}")
        res = verify_entry(row)
        results.append(res)
        status = "✓ VERIFIED" if res["verified"] else "✗ UNVERIFIED"
        print(f"  → {status}  matched={res['matched_pcts']}  src={res.get('verified_source','')}")
        # Checkpoint every 10
        if i % 10 == 0:
            _write(results, OUT_DIR, partial=True)
    _write(results, OUT_DIR, partial=False)

    verified = sum(1 for r in results if r["verified"])
    print(f"\n=== FINAL: {verified}/{len(results)} verified ===")
    for r in results:
        status = "✓" if r["verified"] else "✗"
        print(f"  {status} {r['antibody_name']:30s}  matched={r['matched_pcts']}  src={r.get('verified_source','')}")


def _write(results: list[dict], out_dir: Path, partial: bool = False) -> None:
    suffix = "_partial" if partial else ""
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "verified": sum(1 for r in results if r["verified"]),
        "results": results,
    }
    (out_dir / f"fulltext_reverification{suffix}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    csv_path = out_dir / f"fulltext_reverification{suffix}.csv"
    fields = ["antibody_name", "ada_value_display", "claimed_pcts",
              "verified", "matched_pcts", "verified_source", "verified_snippet"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in results:
            row = dict(r)
            row["claimed_pcts"] = str(r.get("claimed_pcts", []))
            row["matched_pcts"] = str(r.get("matched_pcts", []))
            row["verified_snippet"] = (r.get("verified_snippet") or "")[:300]
            w.writerow(row)


if __name__ == "__main__":
    main()
