import requests
import json
import time
from pathlib import Path
import io
import pandas as pd

def build_insynbio_hspa_v2(out_dir: Path):
    """
    Build the InSynBio Human Surface Peptide Atlas (HSPA) V2.0.
    Expanded to include more proteins and broader secretome definitions.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Expanded query: Cell membrane, Secreted, Extracellular space/matrix
    # SL-0039: Cell membrane
    # SL-0243: Secreted
    # SL-0112: Extracellular space
    # SL-0111: Extracellular matrix
    query = 'taxonomy_id:9606 AND (cc_scl_term:SL-0039 OR cc_scl_term:SL-0243 OR cc_scl_term:SL-0112 OR cc_scl_term:SL-0111) AND (existence:1 OR existence:2)'
    url = "https://rest.uniprot.org/uniprotkb/search"
    
    peptides = set()
    protein_count = 0
    total_proteins_to_fetch = 5000 # Increased for V2
    
    print(f"Starting HSPA V2 build. Query: {query}")
    
    next_url = f"{url}?query={query}&format=tsv&fields=accession,sequence&size=500"
    
    try:
        while next_url and protein_count < total_proteins_to_fetch:
            response = requests.get(next_url)
            if response.status_code != 200:
                print(f"Error fetching data: {response.status_code}")
                break
            
            df = pd.read_csv(io.StringIO(response.text), sep="\t")
            if df.empty:
                break
                
            for _, row in df.iterrows():
                seq = str(row["Sequence"])
                if not seq or seq == "nan" or len(seq) < 9:
                    continue
                
                # Chop into 9-mers
                for i in range(len(seq) - 8):
                    peptides.add(seq[i:i+9])
                
                protein_count += 1
            
            print(f"Processed {protein_count} proteins... Unique 9-mers: {len(peptides)}")
            
            # Pagination
            link = response.headers.get("Link")
            if link and 'rel="next"' in link:
                next_url = link.split(";")[0][1:-1]
            else:
                next_url = None
            
            time.sleep(0.5)

        # Save as a compact JSON
        hspa_data = {
            "version": "2.0.0",
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "protein_source": "UniProt Human Surfaceome & Secretome (Top 5000)",
            "protein_count": protein_count,
            "peptide_count": len(peptides),
            "peptides": sorted(list(peptides))
        }
        
        out_path = out_dir / "human_surface_peptide_atlas_v2.json"
        with open(out_path, "w") as f:
            json.dump(hspa_data, f)
        
        print(f"HSPA V2.0 build complete. Saved to {out_path}")
        print(f"Total Unique 9-mers: {len(peptides)}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    build_insynbio_hspa_v2(Path("data/hspa"))
