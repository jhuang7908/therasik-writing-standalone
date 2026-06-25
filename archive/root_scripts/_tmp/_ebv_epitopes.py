"""
EBV Epitope Query via IEDB IQ-API (correct PostgREST syntax)
EBV = Human herpesvirus 4 = NCBITaxon:10376
"""
import urllib.request, json, csv
from urllib.parse import quote

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'application/json',
}
BASE = 'https://query-api.iedb.org'
ORG_IRI = 'NCBITaxon:10376'
ORG_IRI_ENC = quote(ORG_IRI, safe='')

def fetch_all(endpoint, params, page_size=1000):
    """Fetch all records using pagination."""
    all_records = []
    offset = 0
    while True:
        url = f'{BASE}/{endpoint}?{params}&limit={page_size}&offset={offset}'
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                batch = json.loads(r.read().decode())
                if not batch:
                    break
                all_records.extend(batch)
                if len(batch) < page_size:
                    break
                offset += page_size
                print(f"  ... fetched {len(all_records)} so far ...")
        except urllib.request.HTTPError as e:
            print(f"  HTTP {e.code}: {e.read().decode()[:200]}")
            break
        except Exception as e:
            print(f"  Error: {e}")
            break
    return all_records

# ─── T CELL EPITOPES ───
print("=== QUERYING EBV T CELL EPITOPES ===")
tcell = fetch_all('tcell_search', f'source_organism_iri=eq.{ORG_IRI_ENC}')
print(f"Total T cell assay records: {len(tcell)}")

# Get unique epitopes from T cell data
tcell_epis = {}
for r in tcell:
    seq = r.get('linear_sequence', '')
    sid = r.get('structure_id')
    antigen = r.get('curated_source_antigen', {})
    ag_name = antigen.get('name', '') if antigen else ''
    
    # Get response info
    response = r.get('response_frequency_pos', 0) or 0
    mhc = r.get('mhc_allele', '') or ''
    assay_type = r.get('assay_group', '') or r.get('method', '') or ''
    
    if sid not in tcell_epis:
        tcell_epis[sid] = {
            'sequence': seq,
            'antigen': ag_name,
            'mhc_alleles': set(),
            'assay_count': 0,
            'positive': 0,
        }
    if mhc:
        tcell_epis[sid]['mhc_alleles'].add(mhc)
    tcell_epis[sid]['assay_count'] += 1

print(f"Unique T cell epitopes: {len(tcell_epis)}")
if tcell:
    print("Sample T cell fields:", list(tcell[0].keys()))
    print("Sample T cell record:")
    print(json.dumps(tcell[0], indent=2)[:600])

# ─── B CELL EPITOPES ───
print("\n=== QUERYING EBV B CELL EPITOPES ===")
bcell = fetch_all('bcell_search', f'source_organism_iri=eq.{ORG_IRI_ENC}')
print(f"Total B cell assay records: {len(bcell)}")

bcell_epis = {}
for r in bcell:
    seq = r.get('linear_sequence', '')
    sid = r.get('structure_id')
    antigen = r.get('curated_source_antigen', {})
    ag_name = antigen.get('name', '') if antigen else ''
    
    if sid not in bcell_epis:
        bcell_epis[sid] = {
            'sequence': seq,
            'antigen': ag_name,
            'assay_count': 0,
        }
    bcell_epis[sid]['assay_count'] += 1

print(f"Unique B cell epitopes: {len(bcell_epis)}")

# ─── EPITOPE SEARCH ───
print("\n=== QUERYING ALL EBV EPITOPES ===")
epis = fetch_all('epitope_search', f'source_organism_iris=cs.{{{ORG_IRI_ENC}}}')
print(f"Total unique epitope records: {len(epis)}")

# ─── SUMMARY TABLE ───
print("\n=== EBV EPITOPE SUMMARY ===")
print(f"T cell assays:          {len(tcell):,}")
print(f"T cell unique epitopes: {len(tcell_epis):,}")
print(f"B cell assays:          {len(bcell):,}")
print(f"B cell unique epitopes: {len(bcell_epis):,}")
print(f"All unique epitopes:    {len(epis):,}")

# ─── TOP T CELL EPITOPES BY ANTIGEN ───
print("\n=== TOP 20 T CELL EPITOPES ===")
from collections import Counter
ag_counter = Counter(v['antigen'] for v in tcell_epis.values())
print("By antigen:")
for ag, cnt in ag_counter.most_common(10):
    print(f"  {cnt:4d}  {ag[:60]}")

print("\nFirst 15 T cell epitopes:")
for i, (sid, e) in enumerate(list(tcell_epis.items())[:15]):
    print(f"  {e['sequence']:25s}  {e['antigen'][:40]}")
    if i >= 14: break

print("\n=== TOP 15 B CELL EPITOPES ===")
for i, (sid, e) in enumerate(list(bcell_epis.items())[:15]):
    print(f"  {e['sequence']:30s}  {e['antigen'][:40]}")
    if i >= 14: break

# ─── SAVE TO CSV ───
# Save T cell
with open('ebv_tcell_epitopes.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['structure_id', 'sequence', 'antigen', 'assay_count'])
    for sid, e in tcell_epis.items():
        w.writerow([sid, e['sequence'], e['antigen'], e['assay_count']])
print(f"\nSaved T cell epitopes to ebv_tcell_epitopes.csv")

# Save B cell
with open('ebv_bcell_epitopes.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['structure_id', 'sequence', 'antigen', 'assay_count'])
    for sid, e in bcell_epis.items():
        w.writerow([sid, e['sequence'], e['antigen'], e['assay_count']])
print(f"Saved B cell epitopes to ebv_bcell_epitopes.csv")
