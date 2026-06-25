"""Test IEDB IQ-API with correct PostgREST syntax for EBV epitopes."""
import urllib.request, json

# EBV = Human herpesvirus 4 = taxon 10376
# PostgREST syntax: field=eq.value (equality), field=ilike.*string* (like)

endpoints = [
    # T cell assays for EBV
    ('tcell_search', 'https://query-api.iedb.org/tcell_search?source_organism_id=eq.10376&limit=5'),
    # B cell assays for EBV
    ('bcell_search', 'https://query-api.iedb.org/bcell_search?source_organism_id=eq.10376&limit=5'),
    # Epitopes from EBV
    ('epitope_search', 'https://query-api.iedb.org/epitope_search?source_organism_id=eq.10376&limit=5'),
    # Antigens from EBV
    ('antigen_search', 'https://query-api.iedb.org/antigen_search?source_organism_id=eq.10376&limit=5'),
    # Try by organism name
    ('antigen_by_name', 'https://query-api.iedb.org/antigen_search?source_organism_name=ilike.*Epstein*&limit=5'),
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'application/json',
}

for name, url in endpoints:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
            print(f"OK [{name}]: {len(data)} records returned")
            if data and len(data) > 0:
                print(f"   Fields: {list(data[0].keys())[:10]}")
                if 'epitope_linear_sequence' in data[0]:
                    print(f"   First: {data[0].get('epitope_linear_sequence', 'N/A')}")
                elif 'source_antigen_name' in data[0]:
                    print(f"   First antigen: {data[0].get('source_antigen_name', 'N/A')}")
    except urllib.request.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"FAIL [{name}] HTTP {e.code}: {body}")
    except Exception as e:
        print(f"FAIL [{name}]: {type(e).__name__}: {str(e)[:200]}")
    print()
