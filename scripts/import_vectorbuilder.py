#!/usr/bin/env python3
"""
Import VectorBuilder sequences from raw text into ACTES sequence_db.json.
Performs DNA->Protein translation for coding sequences.
Updates ACTES_sequences_canonical.fasta (Protein) and ACTES_promoters.fasta (DNA).
"""

import json
import re
import hashlib
from pathlib import Path

# Genetic code for translation
CODON_TABLE = {
    'ATA':'I', 'ATC':'I', 'ATT':'I', 'ATG':'M',
    'ACA':'T', 'ACC':'T', 'ACG':'T', 'ACT':'T',
    'AAC':'N', 'AAT':'N', 'AAA':'K', 'AAG':'K',
    'AGC':'S', 'AGT':'S', 'AGA':'R', 'AGG':'R',
    'CTA':'L', 'CTC':'L', 'CTG':'L', 'CTT':'L',
    'CCA':'P', 'CCC':'P', 'CCG':'P', 'CCT':'P',
    'CAC':'H', 'CAT':'H', 'CAA':'Q', 'CAG':'Q',
    'CGA':'R', 'CGC':'R', 'CGG':'R', 'CGT':'R',
    'GTA':'V', 'GTC':'V', 'GTG':'V', 'GTT':'V',
    'GCA':'A', 'GCC':'A', 'GCG':'A', 'GCT':'A',
    'GAC':'D', 'GAT':'D', 'GAA':'E', 'GAG':'E',
    'GGA':'G', 'GGC':'G', 'GGG':'G', 'GGT':'G',
    'TCA':'S', 'TCC':'S', 'TCG':'S', 'TCT':'S',
    'TTC':'F', 'TTT':'F', 'TTA':'L', 'TTG':'L',
    'TAC':'Y', 'TAT':'Y', 'TAA':'_', 'TAG':'_',
    'TGC':'C', 'TGT':'C', 'TGA':'_', 'TGG':'W',
}

def translate_dna(dna):
    dna = dna.upper().replace(" ", "").replace("\n", "")
    protein = ""
    if len(dna) % 3 == 0:
        for i in range(0, len(dna), 3):
            codon = dna[i:i+3]
            protein += CODON_TABLE.get(codon, 'X')
    return protein

def parse_vectorbuilder_text(text):
    entries = []
    current_entry = {}
    
    # Split by double newlines or "Name:" start
    lines = text.splitlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("Name:"):
            if current_entry:
                entries.append(current_entry)
            current_entry = {"Name": line.split("Name:")[1].strip()}
        elif line.startswith("Description:"):
            current_entry["Description"] = line.split("Description:")[1].strip()
        elif line.startswith("Sequence(Length:"):
            # Next line is sequence
            pass
        elif re.match(r'^[ATCG]+$', line.upper()):
            current_entry["Sequence"] = line.upper()
        elif line.startswith("Copy Sequence"):
            pass # Ignore
        else:
            # Other fields like Application Notes, Type, etc.
            pass
            
    if current_entry:
        entries.append(current_entry)
        
    return entries

# Mapping from VB Name to ACTES entry_id and Type
# Type: "protein" (translate) or "dna" (keep as is)
MAPPING = {
    "CD8-leader": {"id": "CD8a_SP", "type": "protein"},
    "CD8-hinge": {"id": "CD8a_Short", "type": "protein"},
    "CD28-hinge": {"id": "CD28_Medium", "type": "protein"},
    "CD8-TM": {"id": "CD8a_TM", "type": "protein"},
    "CD28-TM": {"id": "CD28_TM", "type": "protein"},
    "CD3zeta": {"id": "CD3z_cyto", "type": "protein"},
    "CD28": {"id": "CD28_cyto", "type": "protein"},
    "4-1BB": {"id": "4-1BB_cyto", "type": "protein"},
    "CD19-scFv": {"id": "FMC63_scFv", "type": "protein"},
    "EF1A": {"id": "EF1a", "type": "dna"},
    "EFS": {"id": "EFS", "type": "dna"},
    "SFFV": {"id": "SFFV", "type": "dna"},
    "MSCV": {"id": "MSCV_LTR", "type": "dna"},
    "hPGK": {"id": "PGK", "type": "dna"},
    "hPGK+intron": {"id": "PGK_Intron", "type": "dna"},
    "TRE3G": {"id": "TRE3G", "type": "dna"},
    "WPRE": {"id": "WPRE", "type": "dna"},
    "WPRE3": {"id": "WPRE3", "type": "dna"},
    "oPRE": {"id": "oPRE", "type": "dna"},
    "3xGGGGS": {"id": "G4S3", "type": "protein"},
    "3xGS": {"id": "GGS3", "type": "protein"},
    "T2A": {"id": "T2A", "type": "protein"},
    "P2A": {"id": "P2A", "type": "protein"}
}

def verify_entry(entry):
    """
    Compare sequences from all sources in the entry.
    Updates 'alignment' and 'status' fields.
    """
    sources = entry.get("sources", [])
    if not sources:
        return

    # If only one source, it's verified by default (or verified_vectorbuilder)
    if len(sources) < 2:
        # Keep existing status if it's already set to something meaningful
        if entry.get("status") == "verified_vectorbuilder":
            pass 
        elif entry.get("status") == "static_single_source":
            pass
        else:
            # Default single source status
            pass
        return

    # Compare all sources against the first one (or canonical if present)
    # Usually first source is UniProt if available
    
    # Prefer UniProt as reference
    ref_source = next((s for s in sources if s["name"] == "UniProt"), sources[0])
    ref_seq = ref_source["sequence"]
    
    all_match = True
    mismatches = []
    
    for source in sources:
        if source == ref_source:
            continue
            
        seq = source["sequence"]
        if seq != ref_seq:
            all_match = False
            mismatches.append(f"{source['name']} differs from {ref_source['name']}")
            # Calculate identity ratio (simple exact match check for now, can be improved)
            # For now, if not exact match, identity is < 1.0
            
    if all_match:
        entry["alignment"] = {
            "identity_ratio": 1.0,
            "verified": True,
            "note": f"All {len(sources)} sources match exactly."
        }
        entry["status"] = "verified"
        # If VectorBuilder is one of the sources, we can say verified_vectorbuilder if we want, 
        # but "verified" (multi-source match) is stronger.
        # Let's stick to "verified" for multi-source matches.
    else:
        entry["alignment"] = {
            "identity_ratio": 0.0, # Placeholder for mismatch
            "verified": False,
            "note": "; ".join(mismatches)
        }
        entry["status"] = "mismatch_review"
        print(f"Mismatch detected for {entry['entry_id']}: {mismatches}")


def main():
    base_dir = Path("data/actes_sequences")
    raw_file = base_dir / "vectorbuilder_raw.txt"
    db_file = base_dir / "sequence_db.json"
    
    if not raw_file.exists():
        print(f"Error: {raw_file} not found.")
        return

    raw_text = raw_file.read_text(encoding="utf-8")
    vb_entries = parse_vectorbuilder_text(raw_text)
    
    with open(db_file, 'r', encoding='utf-8') as f:
        db = json.load(f)
        
    db_entries_map = {e["entry_id"]: e for e in db.get("entries", [])}
    
    for vb in vb_entries:
        vb_name = vb["Name"]
        if vb_name not in MAPPING:
            # print(f"Skipping unmapped entry: {vb_name}")
            continue
            
        mapping = MAPPING[vb_name]
        entry_id = mapping["id"]
        seq_type = mapping["type"]
        dna_seq = vb["Sequence"]
        
        if seq_type == "protein":
            final_seq = translate_dna(dna_seq)
            # Remove trailing stop codon if present
            if final_seq.endswith("_"):
                final_seq = final_seq[:-1]
        else:
            final_seq = dna_seq
            
        # Create source object
        source_obj = {
            "name": "VectorBuilder",
            "id": vb_name,
            "sequence": final_seq,
            "length": len(final_seq),
            "dna_sequence": dna_seq if seq_type == "protein" else None # Store original DNA
        }
        
        # Update or Create Entry
        if entry_id in db_entries_map:
            entry = db_entries_map[entry_id]
            # Check if source exists, if not append
            # Also update if exists to ensure latest sequence
            existing_source = next((s for s in entry["sources"] if s.get("name") == "VectorBuilder"), None)
            if existing_source:
                existing_source.update(source_obj)
            else:
                entry["sources"].append(source_obj)
                print(f"Updated {entry_id} with VectorBuilder source.")
            
            # Verify alignment after update
            verify_entry(entry)
                
        else:
            # Create new entry
            new_entry = {
                "entry_id": entry_id,
                "name": vb.get("Description", vb_name),
                "sources": [source_obj],
                "alignment": {
                    "identity_ratio": 1.0, # Single source for now
                    "verified": True
                },
                "status": "verified_vectorbuilder",
                "canonical_sequence": final_seq,
                "sequence_sha256_16": hashlib.sha256(final_seq.encode('utf-8')).hexdigest()[:16],
                "type": seq_type # Add type field
            }
            db["entries"].append(new_entry)
            db_entries_map[entry_id] = new_entry
            print(f"Created new entry {entry_id} ({seq_type}).")
            
    # Save DB
    with open(db_file, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
        
    # Regenerate FASTAs
    canonical_fasta = base_dir / "ACTES_sequences_canonical.fasta"
    promoters_fasta = base_dir / "ACTES_promoters.fasta"
    
    with open(canonical_fasta, 'w', encoding='utf-8') as f_prot, \
         open(promoters_fasta, 'w', encoding='utf-8') as f_dna:
        
        for entry in db["entries"]:
            seq = entry.get("canonical_sequence", "")
            if not seq: continue
            
            # Determine type if not set (heuristic)
            etype = entry.get("type")
            if not etype:
                if set(seq).issubset(set("ATCGN")):
                    etype = "dna"
                else:
                    etype = "protein"
            
            header = f">{entry['entry_id']} | {entry['name']} | len={len(seq)} | status={entry.get('status','unknown')}"
            
            if etype == "protein":
                f_prot.write(f"{header}\n{seq}\n")
            else:
                f_dna.write(f"{header}\n{seq}\n")
                
    print("Updated sequence_db.json and FASTA files with verification.")

if __name__ == "__main__":
    main()
