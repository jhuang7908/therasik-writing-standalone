import requests
import json
import time
from pathlib import Path
import io
import pandas as pd

def build_insynbio_hspa(out_dir: Path):
    """
    Build the InSynBio Human Surface Peptide Atlas (HSPA).
    Uses UniProt TSV download for robustness.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Simplified query for UniProt TSV
    query = 'taxonomy_id:9606 AND (cc_scl_term:SL-0039 OR cc_scl_term:SL-0243) AND (existence:1 OR existence:2)'
    url = "https://rest.uniprot.org/uniprotkb/search"
    params = {
        "query": query,
        "format": "tsv",
        "fields": "accession,sequence",
        "size": 500
    }

    peptides = set()
    protein_count = 0
    
    print(f"Starting HSPA build. Query: {query}")
    
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"Error fetching data: {response.status_code}")
            print(response.text)
            return
        
        df = pd.read_csv(io.StringIO(response.text), sep="\t")
        print(f"Downloaded {len(df)} proteins.")
        
        for _, row in df.iterrows():
            seq = str(row["Sequence"])
            if len(seq) < 9:
                continue
            
            # Chop into 9-mers
            for i in range(len(seq) - 8):
                peptides.add(seq[i:i+9])
            
            protein_count += 1
            if protein_count % 100 == 0:
                print(f"Processed {protein_count} proteins...")

        # Save as a compact JSON
        hspa_data = {
            "version": "1.0.0",
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "protein_source": "UniProt Human Surfaceome (Top 500)",
            "protein_count": protein_count,
            "peptide_count": len(peptides),
            "peptides": sorted(list(peptides))
        }
        
        out_path = out_dir / "human_surface_peptide_atlas_v1.json"
        with open(out_path, "w") as f:
            json.dump(hspa_data, f)
        
        print(f"HSPA V1.0 build complete. Saved to {out_path}")
        print(f"Total Unique 9-mers: {len(peptides)}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    build_insynbio_hspa(Path("data/hspa"))
