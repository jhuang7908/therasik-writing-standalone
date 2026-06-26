import urllib.request
import urllib.parse
import json
import time

def search_ncbi(query, db="protein"):
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db={db}&term={urllib.parse.quote(query)}&retmode=json&retmax=100"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data['esearchresult']['idlist']
    except Exception as e:
        print(f"Error searching: {e}")
        return []

def fetch_ncbi_fasta(id_list, db="protein"):
    ids = ",".join(id_list)
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db={db}&id={ids}&rettype=fasta&retmode=text"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            fasta = response.read().decode('utf-8')
            return fasta
    except Exception as e:
        print(f"Error fetching: {e}")
        return None

# Search for feline IGHV sequences
# Using query: "Felis catus"[Organism] AND (IGHV OR "immunoglobulin heavy chain variable")
query = '"Felis catus"[Organism] AND (IGHV OR "immunoglobulin heavy chain variable")'
print(f"Searching NCBI for: {query}")
id_list = search_ncbi(query)
print(f"Found {len(id_list)} sequences.")

if id_list:
    print("Fetching FASTA...")
    fasta = fetch_ncbi_fasta(id_list)
    if fasta:
        with open('data/germlines/fc_aa/fc_database/cat/IGHC_cat_vh_candidates.fasta', 'w') as f:
            f.write(fasta)
        print("Saved to IGHC_cat_vh_candidates.fasta")
