import requests
import json
import time
from pathlib import Path
import io
import pandas as pd

def fetch_uniprot_peptides(query: str, label: str, limit: int = 1000) -> set:
    """Fetch 9-mers from UniProt for a given query."""
    url = "https://rest.uniprot.org/uniprotkb/search"
    params = {
        "query": query,
        "format": "tsv",
        "fields": "accession,sequence",
        "size": 500
    }
    
    peptides = set()
    protein_count = 0
    
    print(f"Fetching {label}... Query: {query}")
    
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"Error fetching {label}: {response.status_code}")
            return peptides
        
        df = pd.read_csv(io.StringIO(response.text), sep="\t")
        for _, row in df.iterrows():
            seq = str(row["Sequence"])
            if not seq or seq == "nan" or len(seq) < 9:
                continue
            for i in range(len(seq) - 8):
                peptides.add(seq[i:i+9])
            protein_count += 1
            if protein_count >= limit:
                break
        
        print(f"Completed {label}: {protein_count} proteins, {len(peptides)} unique 9-mers.")
    except Exception as e:
        print(f"Error in {label}: {e}")
        
    return peptides

def build_insynbio_tolerance_atlas(out_dir: Path):
    """Build multi-subset Tolerance Atlas."""
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Human Surfaceome (Subset A) - Re-using logic but keeping it separate
    query_human = 'taxonomy_id:9606 AND (cc_scl_term:SL-0039 OR cc_scl_term:SL-0243 OR cc_scl_term:SL-0112 OR cc_scl_term:SL-0111) AND (existence:1 OR existence:2)'
    pep_human = fetch_uniprot_peptides(query_human, "Human Surfaceome", limit=2000)
    
    # 2. Core Microbiome (Subset B)
    # Bacteroides (817), Bifidobacterium (1653), Lactobacillus (1579)
    query_microbiome = 'taxonomy_id:817 OR taxonomy_id:1653 OR taxonomy_id:1579'
    pep_microbiome = fetch_uniprot_peptides(query_microbiome, "Core Microbiome", limit=1000)
    
    # 3. Common Virome (Subset C)
    # EBV (10376), CMV (10359), HBV (10407)
    query_virome = 'taxonomy_id:10376 OR taxonomy_id:10359 OR taxonomy_id:10407'
    pep_virome = fetch_uniprot_peptides(query_virome, "Common Virome", limit=500)
    
    # Full Set
    pep_full = pep_human | pep_microbiome | pep_virome
    
    atlas_data = {
        "version": "1.0.0",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "subsets": {
            "human_surfaceome": {
                "count": len(pep_human),
                "peptides": sorted(list(pep_human))
            },
            "core_microbiome": {
                "count": len(pep_microbiome),
                "peptides": sorted(list(pep_microbiome))
            },
            "common_virome": {
                "count": len(pep_virome),
                "peptides": sorted(list(pep_virome))
            }
        },
        "full_set": {
            "total_unique_count": len(pep_full),
            "peptides": sorted(list(pep_full))
        }
    }
    
    out_path = out_dir / "insynbio_tolerance_atlas_v1.json"
    with open(out_path, "w") as f:
        json.dump(atlas_data, f)
    
    print(f"\nInSynBio Tolerance Atlas V1.0 built successfully.")
    print(f"Full Set Size: {len(pep_full)} unique 9-mers.")
    print(f"Saved to: {out_path}")

if __name__ == "__main__":
    build_insynbio_tolerance_atlas(Path("data/atlas"))
