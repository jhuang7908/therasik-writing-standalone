import requests
import json
import os
import xml.etree.ElementTree as ET

# Load secrets
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRETS_PATH = os.path.join(BASE_DIR, "secrets.json")

def load_api_key():
    try:
        with open(SECRETS_PATH, "r") as f:
            secrets = json.load(f)
            return secrets.get("PUBMED_API_KEY")
    except Exception:
        return None

API_KEY = load_api_key()
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def fetch_pubmed_summary(pmid):
    """Fetches summary for a PubMed ID."""
    url = f"{BASE_URL}esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
    if API_KEY:
        url += f"&api_key={API_KEY}"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get("result", {}).get(str(pmid), {})
    return None

def fetch_genbank_sequence(accession, db="protein"):
    """Fetches sequence for a GenBank accession."""
    url = f"{BASE_URL}efetch.fcgi?db={db}&id={accession}&rettype=fasta&retmode=text"
    if API_KEY:
        url += f"&api_key={API_KEY}"
    
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    return None

if __name__ == "__main__":
    # Test with a known clinical CAR-T paper
    pmid = "25239938"
    print(f"Fetching summary for PMID: {pmid}...")
    summary = fetch_pubmed_summary(pmid)
    if summary:
        print(f"Title: {summary.get('title')}")
        print(f"Journal: {summary.get('fulljournalname')}")
    
    # Test with CD3 zeta protein sequence (RefSeq)
    acc = "NP_000725.1"
    print(f"\nFetching sequence for Accession: {acc}...")
    seq = fetch_genbank_sequence(acc)
    if seq:
        print(f"Sequence preview:\n{seq[:100]}...")
