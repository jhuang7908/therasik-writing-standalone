import urllib.request
import json
import time

def fetch_ncbi_protein(accession):
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=protein&id={accession}&rettype=fasta&retmode=text"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            fasta = response.read().decode('utf-8')
            lines = fasta.split('\n')
            if len(lines) > 1:
                seq = ''.join([line.strip() for line in lines[1:]])
                return seq
    except Exception as e:
        print(f"Error fetching {accession}: {e}")
    return None

accessions = {
    'Cat_IgG1a': 'BAA32229.1',
    'Cat_IgG1b': 'BAA32230.1',
    'Cat_IgG2': 'AHH34165.1'
}

results = {}
for name, acc in accessions.items():
    print(f"Fetching {name} ({acc})...")
    seq = fetch_ncbi_protein(acc)
    if seq:
        results[name] = seq
        print(f"Successfully fetched: {len(seq)} amino acids")
        print(seq)
    time.sleep(1) # Be nice to NCBI

with open('cat_fc_tmp.json', 'w') as f:
    json.dump(results, f, indent=2)
