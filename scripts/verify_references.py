"""
verify_references.py — Verify scientific references via public APIs.

Checks:
  1. PMID   → PubMed E-utilities (eutils.ncbi.nlm.nih.gov)
  2. DOI    → CrossRef API (api.crossref.org)
  3. PDB ID → RCSB PDB (data.rcsb.org)

Usage:
  python scripts/verify_references.py <report.md>
"""
import sys, re, json, time
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

TIMEOUT = 15

def fetch_json(url):
    req = Request(url, headers={"User-Agent": "InSynBio-RefCheck/1.0"})
    try:
        with urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except (HTTPError, URLError, Exception) as e:
        return {"error": str(e)}

def verify_pmid(pmid):
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
    data = fetch_json(url)
    if "error" in data:
        return False, f"API error: {data['error']}"
    result = data.get("result", {})
    entry = result.get(str(pmid), {})
    if "error" in entry:
        return False, f"PMID not found: {entry['error']}"
    title = entry.get("title", "?")
    source = entry.get("source", "?")
    pubdate = entry.get("pubdate", "?")
    authors = entry.get("authors", [])
    first_author = authors[0]["name"] if authors else "?"
    return True, f"{first_author}, {source} ({pubdate}) — {title[:80]}"

def verify_doi(doi):
    url = f"https://api.crossref.org/works/{doi}"
    data = fetch_json(url)
    if "error" in data:
        return False, f"API error: {data['error']}"
    msg = data.get("message", {})
    if not msg:
        return False, "DOI not found"
    title_list = msg.get("title", ["?"])
    title = title_list[0] if title_list else "?"
    journal = msg.get("short-container-title", msg.get("container-title", ["?"]))
    journal = journal[0] if journal else "?"
    issued = msg.get("issued", {}).get("date-parts", [[]])
    year = issued[0][0] if issued and issued[0] else "?"
    authors = msg.get("author", [])
    first = f"{authors[0].get('family', '?')}" if authors else "?"
    return True, f"{first}, {journal} ({year}) — {title[:80]}"

def verify_pdb(pdb_id):
    url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
    data = fetch_json(url)
    if "error" in data:
        return False, f"PDB API error: {data['error']}"
    struct = data.get("struct", {})
    title = struct.get("title", "?")
    return True, f"PDB {pdb_id}: {title[:80]}"

def extract_refs_from_md(md_text):
    refs = []
    in_refs = False
    for line in md_text.splitlines():
        if re.match(r"^##\s+.*[Rr]ef|^##\s+.*", line):
            in_refs = True
            continue
        if in_refs and re.match(r"^##\s+", line):
            break
        if in_refs and line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.",
                                                 "7.", "8.", "9.", "10.", "11.", "12.",
                                                 "13.", "14.", "15.")):
            refs.append(line.strip())
    return refs

def extract_pmid(text):
    m = re.search(r"PMID[:\s]*(\d+)", text)
    return m.group(1) if m else None

def extract_doi(text):
    m = re.search(r"(?:DOI[:\s]*|doi[:\s]*)(10\.\d{4,}/[^\s,;]+)", text)
    return m.group(1).rstrip(".") if m else None

def extract_pdb_ids(md_text):
    return list(set(re.findall(r"PDB\s+(\d[A-Z0-9]{3})", md_text)))

def main(md_path):
    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()

    refs = extract_refs_from_md(md_text)
    pdb_ids = extract_pdb_ids(md_text)

    print("=" * 70)
    print("REFERENCE VERIFICATION REPORT")
    print("=" * 70)

    pass_count = 0
    fail_count = 0
    unverifiable = 0

    for ref in refs:
        print(f"\n--- {ref[:90]}")
        pmid = extract_pmid(ref)
        doi = extract_doi(ref)
        verified = False

        if pmid:
            ok, detail = verify_pmid(pmid)
            status = "PASS" if ok else "FAIL"
            print(f"  PMID {pmid}: [{status}] {detail}")
            if ok:
                pass_count += 1
                verified = True
            else:
                fail_count += 1
            time.sleep(0.4)

        if doi:
            ok, detail = verify_doi(doi)
            status = "PASS" if ok else "FAIL"
            print(f"  DOI {doi}: [{status}] {detail}")
            if ok:
                if not verified:
                    pass_count += 1
                verified = True
            else:
                if not verified:
                    fail_count += 1
            time.sleep(0.4)

        if not pmid and not doi:
            print(f"  [UNVERIFIABLE] No PMID or DOI — manual check required")
            unverifiable += 1

    if pdb_ids:
        print(f"\n{'=' * 70}")
        print("PDB STRUCTURE VERIFICATION")
        print("=" * 70)
        for pdb_id in sorted(pdb_ids):
            ok, detail = verify_pdb(pdb_id)
            status = "PASS" if ok else "FAIL"
            print(f"  {pdb_id}: [{status}] {detail}")
            if ok:
                pass_count += 1
            else:
                fail_count += 1
            time.sleep(0.3)

    print(f"\n{'=' * 70}")
    print(f"SUMMARY: {pass_count} PASS | {fail_count} FAIL | {unverifiable} UNVERIFIABLE")
    print("=" * 70)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_references.py <report.md>")
        sys.exit(1)
    main(sys.argv[1])
