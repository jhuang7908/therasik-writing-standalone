#!/usr/bin/env python3
"""
NCBI Data Sync Script for Therasik/InSynBio.
Downloads and updates local BLAST databases from NCBI FTP.
"""
import os
import subprocess
import sys
from pathlib import Path

# Configuration
NCBI_FTP_BASE = "https://ftp.ncbi.nlm.nih.gov/blast/db"
DB_NAME = "pdb_seqres"
DATA_DIR = Path("api/.data/ncbi_blast")

def ensure_dir():
    if not DATA_DIR.exists():
        print(f"Creating directory: {DATA_DIR}")
        DATA_DIR.mkdir(parents=True, exist_ok=True)

def check_blast_installed():
    try:
        subprocess.run(["update_blastdb", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def sync_pdb_seqres():
    print(f"--- Syncing NCBI {DB_NAME} database ---")
    ensure_dir()
    
    # Use update_blastdb tool if available (part of ncbi-blast+ package)
    if check_blast_installed():
        print("Using update_blastdb utility...")
        try:
            cmd = [
                "update_blastdb",
                "--decompress",
                DB_NAME
            ]
            subprocess.run(cmd, cwd=str(DATA_DIR), check=True)
            print(f"Successfully updated {DB_NAME}")
        except subprocess.CalledProcessError as e:
            print(f"Error updating via update_blastdb: {e}")
            return False
    else:
        print("update_blastdb not found. Please install ncbi-blast+ package.")
        print("On Ubuntu: sudo apt-get install ncbi-blast+")
        return False
    
    return True

if __name__ == "__main__":
    if sync_pdb_seqres():
        print("NCBI sync completed successfully.")
    else:
        print("NCBI sync failed.")
        sys.exit(1)
