"""
Fetch patent sequences from NCBI for patent-cited antibodies
Patents:
1. WO2021122875A1 - Roche anti-MAGE-A4/HLA-A2 antibody (VH SEQ39, VL SEQ40)
2. US10562968B2    - Janssen anti-GPRC5D (talquetamab)
3. EP3494133B1     - NCI anti-KRAS G12D TCR
"""
import json, re, time
from pathlib import Path
from urllib import request

CAR_DIR = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\CAR")
V3_PATH  = CAR_DIR / "CART_LIBRARY_V3.json"

def ncbi_search(term, db="protein", retmax=10):
    """Search NCBI for patent sequences"""
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    url = f"{base}esearch.fcgi?db={db}&term={term}&retmax={retmax}&retmode=json"
    try:
        with request.urlopen(url, timeout=15) as r:
            res = json.loads(r.read().decode())
        time.sleep(0.3)
        return res.get("esearchresult",{}).get("idlist",[])
    except: return []

def ncbi_fetch(uid, db="protein"):
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
           f"db={db}&id={uid}&rettype=fasta&retmode=text")
    try:
        with request.urlopen(url, timeout=15) as r:
            fa = r.read().decode()
        time.sleep(0.3)
        lines = fa.strip().splitlines()
        header = lines[0] if lines else ""
        seq = "".join(l for l in lines if not l.startswith(">"))
        return header, seq
    except: return "", ""

# Search for MAGE-A4/HLA-A2 antibody sequences from Roche patent WO2021122875
print("=== WO2021122875A1: Roche anti-MAGE-A4/HLA-A2 ===")
# Try patent-specific NCBI search
for term in [
    "WO2021122875[Patent Number]",
    "WO/2021/122875 MAGE-A4 antibody",
    "HLA-A2 MAGE-A4 scFv antibody Hoffmann Roche",
    "GVYDGREHTV HLA-A2 antibody VH",
]:
    ids = ncbi_search(f"{term}", "protein")
    if ids:
        print(f"  Found {len(ids)} hits for: {term}")
        for uid in ids[:3]:
            h, seq = ncbi_fetch(uid)
            if seq and 50 < len(seq) < 300:
                print(f"    ID:{uid}  {len(seq)}aa  {seq[:40]}")
                print(f"    Header: {h[:100]}")
    time.sleep(0.3)

# Search for KRAS G12D TCR sequences from EP3494133
print("\n=== EP3494133B1: NCI anti-KRAS G12D TCR ===")
for term in [
    "EP3494133[Patent Number]",
    "KRAS G12D HLA-C TRAV12 TCR alpha beta Tran Rosenberg",
]:
    ids = ncbi_search(term, "protein")
    if ids:
        print(f"  Found {len(ids)} hits for: {term}")
        for uid in ids[:3]:
            h, seq = ncbi_fetch(uid)
            if seq and 50 < len(seq) < 400:
                print(f"    ID:{uid}  {len(seq)}aa  {seq[:40]}")

# Search for GPRC5D anti-talquetamab sequences from US10562968
print("\n=== US10562968B2: Janssen anti-GPRC5D (talquetamab) ===")
for term in [
    "US10562968[Patent Number]",
    "JNJ-64407564 talquetamab GPRC5D antibody VH",
    "talquetamab heavy chain variable domain",
]:
    ids = ncbi_search(term, "protein")
    if ids:
        print(f"  Found {len(ids)} hits for: {term}")
        for uid in ids[:3]:
            h, seq = ncbi_fetch(uid)
            if seq and 100 < len(seq) < 400:
                print(f"    ID:{uid}  {len(seq)}aa  {seq[:40]}")
                print(f"    Header: {h[:100]}")
    time.sleep(0.3)

print("\nDone.")
