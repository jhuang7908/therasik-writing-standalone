"""
Round 2: Fetch sequences from patent databases
- Try NCBI ptnaa (patent amino acid) database
- Try specific NCBI accession IDs from patent filings
"""
import json, re, time
from pathlib import Path
from urllib import request

CAR_DIR = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\CAR")
V3_PATH  = CAR_DIR / "CART_LIBRARY_V3.json"
with open(V3_PATH, encoding="utf-8") as f:
    lib = json.load(f)
v3 = {e["id"]: e for e in lib["elements"]}

G4S3 = "GGGGSGGGGSGGGGS"

def ncbi_search_pat(term, db="protein"):
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    url = f"{base}esearch.fcgi?db={db}&term={term}&retmax=20&retmode=json"
    try:
        with request.urlopen(url, timeout=15) as r:
            res = json.loads(r.read().decode())
        time.sleep(0.4)
        return res.get("esearchresult",{}).get("idlist",[])
    except Exception as ex:
        print(f"  search error: {ex}"); return []

def ncbi_fetch(uid, db="protein"):
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
           f"db={db}&id={uid}&rettype=fasta&retmode=text")
    try:
        with request.urlopen(url, timeout=15) as r:
            fa = r.read().decode()
        time.sleep(0.3)
        lines = fa.strip().splitlines()
        return lines[0], "".join(l for l in lines if not l.startswith(">"))
    except: return "", ""

def is_vh(s): return any(s[:8].startswith(p) for p in ["QVQLVQ","EVQLVQ","EVQLVE","DVQLVE","QVQLQQ"])
def is_vl(s): return any(s[:8].startswith(p) for p in ["DIQMTQ","EIVLTQ","QIVLTQ","DIVMTQ","SSELTQ","QAVVTQ"])
def find_vh_end(s):
    for p in ["WGQGTLVTVSS","WGAGTTVTVSS","WGQGTTVTVSS","WGAGTVTVSS"]:
        i = s.find(p)
        if i > 50: return i+len(p)
    return 0
def find_vl_end(s):
    for p in ["FGQGTKVEIK","FGPGTKLEIK","FGGGTKVEIK","FGGGTKLTVL"]:
        i = s.find(p)
        if i > 50: return i+len(p)
    return 0

# ════════════════════════════════════════════════════════════════════
print("=== 1. MAGE-A4/HLA-A2 from WO2021122875A1 ===\n")
# Try patent-specific search terms in NCBI
mage_found = False
for search_term in [
    "WO2021122875 MAGE",
    "Weinzierl MAGE-A4 HLA antibody",
    "GVYDGREHTV antibody variable heavy",
    "HCDR1 HCDR2 HCDR3 MAGE-A4 pMHC VH Roche",
    '"MAGE-A4" "HLA-A2" antibody scFv patent VH VL 2021',
]:
    ids = ncbi_search_pat(search_term)
    if ids:
        print(f"  NCBI hits for '{search_term[:50]}': {ids[:5]}")
        for uid in ids[:3]:
            hdr, seq = ncbi_fetch(uid)
            if 80 < len(seq) < 300:
                if is_vh(seq) or is_vl(seq):
                    print(f"    ✓ {uid}: {len(seq)}aa {seq[:40]}")
                    print(f"      {hdr[:100]}")
                    mage_found = True

# Try fetching PDF sequence listing (patent PDF → text)
# WO2021122875 - look for sequence listing in supplementary
# From patent body we know: VH=SEQ39, VL=SEQ40, Molecule D
# CDR seqs from patent text body:
# HCDR1 = SEQ9, HCDR2 = SEQ10, HCDR3 = SEQ11
# LCDR1 = SEQ12, LCDR2 = SEQ13, LCDR3 = SEQ14
# Full VH = SEQ39, Full VL = SEQ40 (Molecule D in patent)
# Try to directly look up these accessions in GenBank

# From CN114174345A patent (Chinese parallel) - sequences for MAGE-A4 CAR
# Try the Chinese patent number too
for search_term in [
    "CN114174345 MAGE-A4",
    "anti-MAGE-A4-HLA-A2-CAR VH variable heavy patent 2022",
]:
    ids = ncbi_search_pat(search_term)
    if ids:
        print(f"  CN patent hits: {ids[:5]}")

# ════════════════════════════════════════════════════════════════════
print("\n=== 2. GPRC5D from US10562968B2 (Janssen) ===\n")
# Try to find talquetamab VH/VL sequences in NCBI
gprc5d_found = False
for search_term in [
    "US10562968 GPRC5D",
    "talquetamab GPRC5D heavy chain variable",
    "JNJ-64407564 GPRC5D antibody VH VL",
    "Pillarisetti GPRC5D Janssen antibody 2017",
    "GPRC5D myeloma bispecific antibody VH CDR",
]:
    ids = ncbi_search_pat(search_term)
    if ids:
        print(f"  Hits for '{search_term[:50]}': {ids[:5]}")
        for uid in ids[:3]:
            hdr, seq = ncbi_fetch(uid)
            if 100 < len(seq) < 300:
                if is_vh(seq) or is_vl(seq):
                    print(f"    ✓ {uid}: {len(seq)}aa  {seq[:40]}")
                    gprc5d_found = True

# ════════════════════════════════════════════════════════════════════
print("\n=== 3. KRAS G12D TCR from EP3494133B1 ===\n")
# EP3494133B1 / WO2018027025 / US20180127466
# TCR alpha variable SEQ15, TCR beta variable SEQ16 or SEQ24
# Inventors: Tran, Lu, Robbins, Rosenberg, Zheng (NCI/NIH)
kras_found = False
for search_term in [
    "EP3494133 KRAS G12D TCR",
    "Tran 2016 KRAS G12D HLA-C TCR alpha beta NCI",
    "WO2018027025 KRAS TCR alpha chain",
    "KRAS G12D VVGADGVGK TCR alpha variable 2017",
    "GADGVGKSA HLA-C TCR variable alpha",
]:
    ids = ncbi_search_pat(search_term)
    if ids:
        print(f"  Hits for '{search_term[:50]}': {ids[:5]}")
        for uid in ids[:3]:
            hdr, seq = ncbi_fetch(uid)
            if 50 < len(seq) < 400:
                print(f"    {uid}: {len(seq)}aa  {seq[:40]}")
                print(f"    {hdr[:100]}")
                kras_found = True

# ════════════════════════════════════════════════════════════════════
# Audit ALL library elements for patent citations and improve accuracy
print("\n=== Audit patent citations in library ===\n")
with open(V3_PATH, encoding="utf-8") as f:
    lib = json.load(f)

patent_cited = []
for e in lib["elements"]:
    qa_src = e.get("qa",{}).get("source","")
    notes  = e.get("design_notes","")
    combined = qa_src + " " + notes
    # Find patent numbers: WO, US, EP, CN patterns
    patents = re.findall(r'(?:WO|US|EP|CN|AU|JP)\d+[\w/]*', combined)
    if patents:
        patent_cited.append((e["id"], patents, bool(e.get("sequence"))))

print(f"Elements with patent citations: {len(patent_cited)}")
print()
for eid, pats, has_seq in sorted(patent_cited):
    status = "✅" if has_seq else "❌ STUB"
    print(f"  {status} {eid:<30} → {', '.join(pats[:3])}")
