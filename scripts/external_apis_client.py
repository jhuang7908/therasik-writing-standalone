import requests
import json

class BiologicalAPIClient:
    def __init__(self):
        self.uniprot_base = "https://rest.uniprot.org/uniprotkb/"
        self.pdb_data_base = "https://data.rcsb.org/rest/v1/core/entry/"
        self.pdb_search_base = "https://search.rcsb.org/rcsbsearch/v2/query"

    def fetch_uniprot_features(self, uniprot_id):
        """Fetches protein features (domains, regions) from UniProt."""
        url = f"{self.uniprot_base}{uniprot_id}.json"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            features = data.get("features", [])
            # Filter for domains and regions
            domains = [f for f in features if f.get("type") in ["Domain", "Region"]]
            return {
                "id": uniprot_id,
                "name": data.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value"),
                "domains": domains,
                "sequence": data.get("sequence", {}).get("value")
            }
        return None

    def fetch_pdb_metadata(self, pdb_id):
        """Fetches structure metadata from RCSB PDB."""
        url = f"{self.pdb_data_base}{pdb_id}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            entry = data.get("rcsb_entry_info", {})
            return {
                "id": pdb_id,
                "title": data.get("struct", {}).get("title"),
                "method": data.get("exptl", [{}])[0].get("method"),
                "resolution": entry.get("resolution_combined", [None])[0],
                "release_date": data.get("rcsb_accession_info", {}).get("initial_release_date")
            }
        return None

    def search_pdb_by_sequence(self, sequence, identity_cutoff=0.9):
        """Searches PDB for structures matching a sequence."""
        query = {
            "query": {
                "type": "terminal",
                "service": "sequence",
                "parameters": {
                    "evalue_cutoff": 1,
                    "identity_cutoff": identity_cutoff,
                    "target": "pdb_protein_sequence",
                    "value": sequence
                }
            },
            "return_type": "entry"
        }
        response = requests.post(self.pdb_search_base, json=query)
        if response.status_code == 200:
            return response.json().get("result_set", [])
        return []

if __name__ == "__main__":
    client = BiologicalAPIClient()
    
    # Test UniProt: Human CD3 zeta (P20963)
    print("Testing UniProt API (CD3 zeta)...")
    up_data = client.fetch_uniprot_features("P20963")
    if up_data:
        print(f"Name: {up_data['name']}")
        print(f"Domains found: {len(up_data['domains'])}")
        for d in up_data['domains']:
            print(f"  - {d.get('description')} ({d.get('location', {}).get('start', {}).get('value')}-{d.get('location', {}).get('end', {}).get('value')})")

    # Test PDB: 5DI8 (KiH Fc Heterodimer)
    print("\nTesting PDB API (5DI8)...")
    pdb_data = client.fetch_pdb_metadata("5DI8")
    if pdb_data:
        print(f"Title: {pdb_data['title']}")
        print(f"Resolution: {pdb_data['resolution']} Å")
