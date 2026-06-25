"""Test IEDB with correct field names from error messages."""
import urllib.request, json
from urllib.parse import quote

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'application/json',
}

def fetch(name, url):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
            print(f"OK [{name}]: {len(data)} records")
            if data:
                print(f"   Fields: {list(data[0].keys())[:8]}")
                if len(data) > 0:
                    print(f"   Sample: {json.dumps(data[0], indent=2)[:400]}")
            return data
    except urllib.request.HTTPError as e:
        body = e.read().decode()[:400]
        print(f"FAIL [{name}] HTTP {e.code}: {body}")
        return []
    except Exception as e:
        print(f"FAIL [{name}]: {e}")
        return []

# Step 1: Get EBV antigen IRI using name search (we know this works)
print("=== Step 1: Find EBV antigen IRIs ===")
data = fetch('antigen_by_name',
    'https://query-api.iedb.org/antigen_search?parent_source_antigen_source_org_name=ilike.*Epstein*&limit=3')

if not data:
    # Try different field
    data = fetch('antigen_by_name2',
        'https://query-api.iedb.org/antigen_search?source_organism_name=ilike.*Epstein*&limit=3')

# Step 2: Get the organism IRI from the first result
print("\n=== Step 2: Find source organism IRI ===")
if data:
    org_iri = data[0].get('parent_source_antigen_source_org_iri', '')
    print(f"EBV organism IRI: {org_iri}")
    print(f"EBV organism name: {data[0].get('parent_source_antigen_source_org_name', '')}")
    
    # Step 3: Use IRI to query tcell and bcell
    if org_iri:
        print("\n=== Step 3: Query T cell epitopes with IRI ===")
        iri_encoded = quote(org_iri, safe='')
        
        # Try tcell_search with source_organism_iri
        fetch('tcell_EBV', 
            f'https://query-api.iedb.org/tcell_search?source_organism_iri=eq.{iri_encoded}&limit=5')
        
        fetch('bcell_EBV',
            f'https://query-api.iedb.org/bcell_search?source_organism_iri=eq.{iri_encoded}&limit=5')
        
        fetch('epitope_EBV',
            f'https://query-api.iedb.org/epitope_search?source_organism_iris=cs.{{{iri_encoded}}}&limit=5')

# Step 3 alt: try ilike on organism name
print("\n=== Step 3 alt: tcell/bcell by organism name ===")
fetch('tcell_EBV_name',
    'https://query-api.iedb.org/tcell_search?source_organism_name=ilike.*Epstein*&limit=5')

fetch('bcell_EBV_name', 
    'https://query-api.iedb.org/bcell_search?source_organism_name=ilike.*Epstein*&limit=5')
