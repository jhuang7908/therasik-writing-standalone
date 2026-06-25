"""
EBV Epitope Query via IEDB IQ-API — correct pagination with order parameter
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

def fetch_all(endpoint, params, order_field, page_size=1000):
    """Fetch all records using keyset-style pagination with order."""
    all_records = []
    offset = 0
    while True:
        url = f'{BASE}/{endpoint}?{params}&order={order_field}&limit={page_size}&offset={offset}'
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                batch = json.loads(r.read().decode())
                if not batch:
                    break
                all_records.extend(batch)
                print(f"  [{endpoint}] fetched {len(all_records)}", end='\r')
                if len(batch) < page_size:
                    break
                offset += page_size
        except urllib.request.HTTPError as e:
            body = e.read().decode()
            print(f"\n  HTTP {e.code}: {body[:300]}")
            break
        except Exception as e:
            print(f"\n  Error: {e}")
            break
    print()
    return all_records

# ─── T CELL EPITOPES ───
print("=== QUERYING EBV T CELL EPITOPES ===")
tcell = fetch_all('tcell_search', f'source_organism_iri=eq.{ORG_IRI_ENC}', 'tcell_id')
print(f"Total T cell assay records: {len(tcell)}")

# Get unique epitopes
tcell_epis = {}
for r in tcell:
    seq = r.get('linear_sequence', '')
    sid = r.get('structure_id')
    antigen = r.get('curated_source_antigen') or {}
    ag_name = antigen.get('name', '') if antigen else ''
    mhc = r.get('mhc_allele', '') or ''
    
    if sid not in tcell_epis:
        tcell_epis[sid] = {
            'sequence': seq,
            'antigen': ag_name,
            'mhc_alleles': set(),
            'assay_count': 0,
        }
    if mhc:
        tcell_epis[sid]['mhc_alleles'].add(mhc)
    tcell_epis[sid]['assay_count'] += 1

print(f"Unique T cell epitope structures: {len(tcell_epis)}")

# ─── B CELL EPITOPES ───
print("\n=== QUERYING EBV B CELL EPITOPES ===")
bcell = fetch_all('bcell_search', f'source_organism_iri=eq.{ORG_IRI_ENC}', 'bcell_id')
print(f"Total B cell assay records: {len(bcell)}")

bcell_epis = {}
for r in bcell:
    seq = r.get('linear_sequence', '')
    sid = r.get('structure_id')
    antigen = r.get('curated_source_antigen') or {}
    ag_name = antigen.get('name', '') if antigen else ''
    
    if sid not in bcell_epis:
        bcell_epis[sid] = {
            'sequence': seq,
            'antigen': ag_name,
            'assay_count': 0,
        }
    bcell_epis[sid]['assay_count'] += 1

print(f"Unique B cell epitope structures: {len(bcell_epis)}")

# ─── ALL EPITOPES ───
print("\n=== QUERYING ALL EBV EPITOPES ===")
epis = fetch_all('epitope_search', f'source_organism_iris=cs.{{{ORG_IRI_ENC}}}', 'structure_id')
print(f"Total unique epitope records: {len(epis)}")

# ─── SUMMARY ───
print("\n" + "="*60)
print("EBV EPITOPE DATABASE SUMMARY (IEDB)")
print("="*60)
print(f"Source: IEDB IQ-API | Organism: Human herpesvirus 4 (EBV)")
print(f"NCBI Taxon: 10376 | Query date: 2026-04-09")
print("-"*60)
print(f"T cell assay records:    {len(tcell):>6,}")
print(f"T cell unique epitopes:  {len(tcell_epis):>6,}")
print(f"B cell assay records:    {len(bcell):>6,}")
print(f"B cell unique epitopes:  {len(bcell_epis):>6,}")
print(f"All unique epitopes:     {len(epis):>6,}")

# T cell by antigen
from collections import Counter
print("\n--- T cell epitopes by antigen (top 15) ---")
ag_cnt = Counter(v['antigen'] for v in tcell_epis.values())
for ag, cnt in ag_cnt.most_common(15):
    print(f"  {cnt:4d}  {ag[:65]}")

print("\n--- Top T cell epitopes (by assay count) ---")
top_t = sorted(tcell_epis.items(), key=lambda x: x[1]['assay_count'], reverse=True)[:20]
print(f"  {'Sequence':<30} {'Antigen':<45} {'#Assays'}")
print(f"  {'-'*30} {'-'*45} {'-'*7}")
for sid, e in top_t:
    mhc_str = ', '.join(sorted(e['mhc_alleles']))[:25]
    print(f"  {e['sequence']:<30} {e['antigen'][:45]:<45} {e['assay_count']:>4}")

print("\n--- Top B cell epitopes (by assay count) ---")
top_b = sorted(bcell_epis.items(), key=lambda x: x[1]['assay_count'], reverse=True)[:20]
print(f"  {'Sequence':<35} {'Antigen':<40} {'#Assays'}")
print(f"  {'-'*35} {'-'*40} {'-'*7}")
for sid, e in top_b:
    print(f"  {e['sequence']:<35} {e['antigen'][:40]:<40} {e['assay_count']:>4}")

# ─── SAVE CSV ───
def save_csv(fname, epis_dict, extra_fields=[]):
    with open(fname, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['structure_id', 'sequence', 'seq_length', 'antigen', 'assay_count'])
        for sid, e in sorted(epis_dict.items(), key=lambda x: x[1]['assay_count'], reverse=True):
            w.writerow([sid, e['sequence'], len(e['sequence']), e['antigen'], e['assay_count']])
    print(f"Saved: {fname}")

save_csv('ebv_tcell_epitopes.csv', tcell_epis)
save_csv('ebv_bcell_epitopes.csv', bcell_epis)

# Also save complete record for first tcell and bcell
if tcell:
    print("\n--- Sample T cell record (all fields) ---")
    print(json.dumps(tcell[0], indent=2)[:800])
if bcell:
    print("\n--- Sample B cell record (all fields) ---")
    print(json.dumps(bcell[0], indent=2)[:800])
