import json

with open('docs/vaccine_kb_data.json', encoding='utf-8') as f:
    data = json.load(f)

total = 0
has_id = 0
search_only = 0
no_url = 0
no_url_list = []

def check_list(epis, antigen, category):
    global total, has_id, search_only, no_url
    for e in epis:
        total += 1
        peptide = e.get('peptide', '?')
        if e.get('iedb_id'):
            has_id += 1
        elif e.get('iedb_url'):
            search_only += 1
        else:
            no_url += 1
            no_url_list.append(f"[{category}] {antigen}: {peptide}")

for t in data.get('taa', []):
    check_list(t.get('known_epitopes_mhc1', []), t['name'], 'TAA MHC-I')
    check_list(t.get('known_epitopes_mhc2', []), t['name'], 'TAA MHC-II')
for a in data.get('infectious', []):
    check_list(a.get('known_epitopes_mhc1', []), a['pathogen'], 'Infectious MHC-I')
    check_list(a.get('known_epitopes_mhc2', []), a['pathogen'], 'Infectious MHC-II')
for a in data.get('autoimmune', []):
    check_list(a.get('known_epitopes', []), a['target_antigen'], 'Autoimmune')

print(f"Total epitopes : {total}")
print(f"  Verified IEDB ID: {has_id} ({has_id/total*100:.0f}%)")
print(f"  IEDB search URL : {search_only} ({search_only/total*100:.0f}%)")
print(f"  No link at all  : {no_url}")

if no_url_list:
    print("\nEntries missing any link:")
    for x in no_url_list:
        print(" ", x)
else:
    print("\nAll epitopes have at least an IEDB link.")

# Also show all search-only (no confirmed ID) entries
print("\nSearch-link-only entries (not directly matched in IEDB):")
def show_search_only(epis, antigen, category):
    for e in epis:
        if not e.get('iedb_id') and e.get('iedb_url'):
            print(f"  [{category}] {antigen}: {e.get('peptide','?')} ({e.get('hla','?')})")
            print(f"    URL: {e.get('iedb_url','')[:80]}")

for t in data.get('taa', []):
    show_search_only(t.get('known_epitopes_mhc1', []), t['name'], 'TAA MHC-I')
    show_search_only(t.get('known_epitopes_mhc2', []), t['name'], 'TAA MHC-II')
for a in data.get('infectious', []):
    show_search_only(a.get('known_epitopes_mhc1', []), a['pathogen'], 'Infectious MHC-I')
    show_search_only(a.get('known_epitopes_mhc2', []), a['pathogen'], 'Infectious MHC-II')
for a in data.get('autoimmune', []):
    show_search_only(a.get('known_epitopes', []), a['target_antigen'], 'Autoimmune')
