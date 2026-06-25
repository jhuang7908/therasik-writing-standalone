"""
NCBI BLAST local search utility for Therasik/InSynBio Assistant.
"""
import subprocess
import tempfile
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path("api/.data/ncbi_blast/pdb_seqres")

def is_blast_ready() -> bool:
    """Check if BLAST+ is installed and database exists."""
    # Check for blastp executable
    try:
        subprocess.run(["blastp", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    
    # Check if database files exist (at least one .pin or .psq)
    db_files = list(DB_PATH.parent.glob(f"{DB_PATH.name}.p*"))
    return len(db_files) > 0

def search_pdb_seqres(sequence: str, max_hits: int = 3) -> List[Dict[str, Any]]:
    """
    Run a local blastp search against pdb_seqres.
    Returns a list of top hits with alignment details.
    """
    if not is_blast_ready():
        return []

    if not sequence or len(sequence) < 10:
        return []

    # Create a temporary FASTA file for the query
    with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as tmp:
        tmp.write(f">query\n{sequence}\n")
        tmp_path = tmp.name

    try:
        # Run blastp with JSON output format
        cmd = [
            "blastp",
            "-query", tmp_path,
            "-db", str(DB_PATH),
            "-outfmt", "15", # JSON output
            "-max_target_seqs", str(max_hits),
            "-num_threads", "2"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if not result.stdout:
            return []

        data = json.loads(result.stdout)
        hits = []
        
        # Parse BLAST JSON structure
        search_results = data.get("BlastOutput2", [{}])[0].get("report", {}).get("results", {}).get("search", {})
        for hit in search_results.get("hits", []):
            desc = hit.get("description", [{}])[0]
            hsps = hit.get("hsps", [{}])[0]
            
            hits.append({
                "pdb_id": desc.get("accession", "Unknown"),
                "title": desc.get("title", ""),
                "identity": round(hsps.get("identity", 0) / hsps.get("align_len", 1) * 100, 1),
                "e_value": hsps.get("evalue", 0),
                "align_len": hsps.get("align_len", 0)
            })
            
        return hits

    except Exception as e:
        print(f"NCBI BLAST Error: {e}")
        return []
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def format_hits_for_assistant(hits: List[Dict[str, Any]]) -> str:
    """Format BLAST hits into a concise string for the LLM context."""
    if not hits:
        return "No significant structural matches found in NCBI PDB_seqres."
    
    lines = ["NCBI Structural Evidence (Top Matches from PDB_seqres):"]
    for hit in hits:
        lines.append(f"- PDB {hit['pdb_id']}: {hit['title']} (Identity: {hit['identity']}%, E-value: {hit['e_value']})")
    
    return "\n".join(lines)
