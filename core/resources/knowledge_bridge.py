import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
import json

class InSynBioKnowledgeBridge:
    """
    Knowledge Bridge for InSynBio Antibody Engineer Suite.
    Provides free REST API access to UniProt, PubMed, and PDB.
    """
    
    def __init__(self):
        self.uniprot_url = "https://rest.uniprot.org/uniprotkb/"
        self.pubmed_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        self.rcsb_url = "https://search.rcsb.org/rcsbsearch/v2/query"
        self.pdb_data_url = "https://data.rcsb.org/rest/v1/core/entry/"

    def fetch_uniprot_info(self, accession: str) -> Dict[str, Any]:
        """Fetch protein details, PTMs, and features from UniProt."""
        try:
            response = requests.get(f"{self.uniprot_url}{accession}.json")
            response.raise_for_status()
            data = response.json()
            
            features = data.get("features", [])
            ptms = [f for f in features if f.get("type") in ["Glycosylation", "Modified residue", "Disulfide bond"]]
            
            return {
                "name": data.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value"),
                "organism": data.get("organism", {}).get("scientificName"),
                "ptms": ptms,
                "function": data.get("comments", [{}])[0].get("texts", [{}])[0].get("value") if data.get("comments") else "N/A"
            }
        except Exception as e:
            return {"error": f"UniProt fetch failed: {str(e)}"}

    def search_pubmed(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Search PubMed for recent literature and return abstracts."""
        try:
            # 1. Search for IDs
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmode": "json",
                "retmax": max_results
            }
            search_res = requests.get(f"{self.pubmed_url}esearch.fcgi", params=search_params)
            ids = search_res.json().get("esearchresult", {}).get("idlist", [])
            
            if not ids:
                return []

            # 2. Fetch summaries
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "json"
            }
            fetch_res = requests.get(f"{self.pubmed_url}esummary.fcgi", params=fetch_params)
            summaries = fetch_res.json().get("result", {})
            
            results = []
            for uid in ids:
                item = summaries.get(uid, {})
                results.append({
                    "title": item.get("title"),
                    "pubdate": item.get("pubdate"),
                    "doi": item.get("elocationid"),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
                })
            return results
        except Exception as e:
            return [{"error": f"PubMed search failed: {str(e)}"}]

    def find_pdb_structures(self, target_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find relevant PDB structures for a target protein."""
        query = {
            "query": {
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "rcsb_entity_source_organism.scientific_name",
                    "operator": "contains",
                    "value": "Homo sapiens"
                }
            },
            "request_options": {
                "return_all_hits": False,
                "paginate": {"start": 0, "rows": limit}
            },
            "return_type": "entry"
        }
        # Refine query for target name
        query["query"] = {
            "type": "group",
            "logical_operator": "and",
            "nodes": [
                {"type": "terminal", "service": "text", "parameters": {"attribute": "struct.title", "operator": "contains", "value": target_name}},
                {"type": "terminal", "service": "text", "parameters": {"attribute": "rcsb_entry_info.polymer_entity_count_protein", "operator": "greater", "value": 0}}
            ]
        }
        
        try:
            response = requests.post(self.rcsb_url, json=query)
            response.raise_for_status()
            hits = response.json().get("result_set", [])
            
            results = []
            for hit in hits:
                pdb_id = hit.get("identifier")
                # Fetch basic metadata for each PDB
                meta_res = requests.get(f"{self.pdb_data_url}{pdb_id}")
                if meta_res.status_code == 200:
                    meta = meta_res.json()
                    results.append({
                        "pdb_id": pdb_id,
                        "title": meta.get("struct", {}).get("title"),
                        "resolution": meta.get("rcsb_entry_info", {}).get("resolution_combined", [None])[0],
                        "method": meta.get("exptl", [{}])[0].get("method")
                    })
            return results
        except Exception as e:
            return [{"error": f"PDB search failed: {str(e)}"}]

if __name__ == "__main__":
    # Quick test
    bridge = InSynBioKnowledgeBridge()
    print("Testing UniProt (HER2 - P04626)...")
    print(json.dumps(bridge.fetch_uniprot_info("P04626"), indent=2, ensure_ascii=False))
