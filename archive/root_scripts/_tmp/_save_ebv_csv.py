"""Save EBV epitopes — run after _ebv_epitopes_v2 has populated dicts in memory.
This is a standalone complete script.
"""
import urllib.request, json, csv
from urllib.parse import quote
from collections import Counter

HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
BASE = 'https://query-api.iedb.org'
ORG_IRI_ENC = quote('NCBITaxon:10376', safe='')

def fetch_all(endpoint, params, order_field, page_size=1000):
    all_records = []
    offset = 0
    while True:
        url = f'{BASE}/{endpoint}?{params}&order={order_field}&limit={page_size}&offset={offset}'
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                batch = json.loads(r.read().decode())
                if not batch: break
                all_records.extend(batch)
                print(f"\r  {endpoint}: {len(all_records)} records...", end='', flush=True)
                if len(batch) < page_size: break
                offset += page_size
        except Exception as e:
            print(f"\n  Error: {e}"); break
    print()
    return all_records

print("Fetching T cell data...")
tcell = fetch_all('tcell_search', f'source_organism_iri=eq.{ORG_IRI_ENC}', 'tcell_id')

print("Fetching B cell data...")
bcell = fetch_all('bcell_search', f'source_organism_iri=eq.{ORG_IRI_ENC}', 'bcell_id')

# Build deduplicated epitope tables
tcell_epis = {}
for r in tcell:
    sid = r.get('structure_id')
    seq = r.get('linear_sequence') or ''
    antigen = r.get('curated_source_antigen') or {}
    ag_name = antigen.get('name', '') if isinstance(antigen, dict) else ''
    ag_acc = antigen.get('accession', '') if isinstance(antigen, dict) else ''
    ag_start = antigen.get('starting_position', '') if isinstance(antigen, dict) else ''
    ag_end = antigen.get('ending_position', '') if isinstance(antigen, dict) else ''
    mhc = r.get('mhc_allele') or ''
    host = r.get('host_organism_name') or ''
    
    if sid not in tcell_epis:
        tcell_epis[sid] = {
            'sequence': seq,
            'length': len(seq),
            'antigen': ag_name,
            'accession': ag_acc,
            'start': ag_start,
            'end': ag_end,
            'mhc_alleles': set(),
            'hosts': set(),
            'assay_count': 0,
        }
    if mhc: tcell_epis[sid]['mhc_alleles'].add(mhc)
    if host: tcell_epis[sid]['hosts'].add(host)
    tcell_epis[sid]['assay_count'] += 1

bcell_epis = {}
for r in bcell:
    sid = r.get('structure_id')
    seq = r.get('linear_sequence') or ''
    antigen = r.get('curated_source_antigen') or {}
    ag_name = antigen.get('name', '') if isinstance(antigen, dict) else ''
    ag_acc = antigen.get('accession', '') if isinstance(antigen, dict) else ''
    ag_start = antigen.get('starting_position', '') if isinstance(antigen, dict) else ''
    ag_end = antigen.get('ending_position', '') if isinstance(antigen, dict) else ''
    isotype = r.get('antibody_isotype') or ''
    
    if sid not in bcell_epis:
        bcell_epis[sid] = {
            'sequence': seq,
            'length': len(seq),
            'antigen': ag_name,
            'accession': ag_acc,
            'start': ag_start,
            'end': ag_end,
            'isotypes': set(),
            'assay_count': 0,
        }
    if isotype: bcell_epis[sid]['isotypes'].add(isotype)
    bcell_epis[sid]['assay_count'] += 1

# Save T cell CSV
with open('ebv_tcell_epitopes.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['structure_id', 'sequence', 'length', 'antigen', 'accession',
                'start', 'end', 'mhc_alleles', 'assay_count'])
    for sid, e in sorted(tcell_epis.items(), key=lambda x: x[1]['assay_count'], reverse=True):
        w.writerow([sid, e['sequence'], e['length'], e['antigen'], e['accession'],
                    e['start'], e['end'], '|'.join(sorted(e['mhc_alleles'])), e['assay_count']])

# Save B cell CSV
with open('ebv_bcell_epitopes.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['structure_id', 'sequence', 'length', 'antigen', 'accession',
                'start', 'end', 'isotypes', 'assay_count'])
    for sid, e in sorted(bcell_epis.items(), key=lambda x: x[1]['assay_count'], reverse=True):
        w.writerow([sid, e['sequence'], e['length'], e['antigen'], e['accession'],
                    e['start'], e['end'], '|'.join(sorted(e['isotypes'])), e['assay_count']])

print(f"\n✅ Saved ebv_tcell_epitopes.csv ({len(tcell_epis)} unique epitopes)")
print(f"✅ Saved ebv_bcell_epitopes.csv ({len(bcell_epis)} unique epitopes)")

print("\n=== FINAL SUMMARY ===")
print(f"T cell assay records:    {len(tcell):,}")
print(f"T cell unique epitopes:  {len(tcell_epis):,}")
print(f"B cell assay records:    {len(bcell):,}")
print(f"B cell unique epitopes:  {len(bcell_epis):,}")

print("\n--- TOP T CELL EPITOPES (immunodominant) ---")
top_t = sorted(tcell_epis.items(), key=lambda x: x[1]['assay_count'], reverse=True)[:15]
for sid, e in top_t:
    mhc_str = '|'.join(sorted(e['mhc_alleles']))[:40]
    print(f"  {e['sequence']:<28}  assays={e['assay_count']:>4}  {e['antigen'][:45]}")

print("\n--- TOP B CELL EPITOPES (most studied) ---")
top_b = sorted(bcell_epis.items(), key=lambda x: x[1]['assay_count'], reverse=True)[:15]
for sid, e in top_b:
    print(f"  {(e['sequence'] or 'N/A'):<35}  assays={e['assay_count']:>4}  {e['antigen'][:45]}")
