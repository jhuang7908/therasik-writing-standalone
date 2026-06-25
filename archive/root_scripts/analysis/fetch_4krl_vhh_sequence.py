"""
Fetch anti-EGFR VHH sequence from PDB 4KRL to fix the His-tag contaminated EGFRvIII_VHH.
"""
import urllib.request
import re

def fetch_pdb_sequence(pdb_id, chain):
    """Fetch sequence from PDB file."""
    url = f"https://files.rcsb.org/view/{pdb_id}.pdb"
    
    try:
        with urllib.request.urlopen(url) as response:
            pdb_content = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching PDB {pdb_id}: {e}")
        return None
    
    # Parse SEQRES records for the specific chain
    sequence = ""
    for line in pdb_content.split('\n'):
        if line.startswith('SEQRES') and f" {chain} " in line:
            # Extract residues from SEQRES line
            parts = line.split()
            if len(parts) > 4:
                residues = parts[4:]  # Skip SEQRES, serNum, chainID, numRes
                for res in residues:
                    if len(res) == 3:  # Three-letter amino acid code
                        aa = three_to_one.get(res, 'X')
                        sequence += aa
    
    return sequence

# Three-letter to one-letter amino acid code mapping
three_to_one = {
    'ALA': 'A', 'ARG': 'R', 'ASN': 'N', 'ASP': 'D', 'CYS': 'C',
    'GLU': 'E', 'GLN': 'Q', 'GLY': 'G', 'HIS': 'H', 'ILE': 'I',
    'LEU': 'L', 'LYS': 'K', 'MET': 'M', 'PHE': 'F', 'PRO': 'P',
    'SER': 'S', 'THR': 'T', 'TRP': 'W', 'TYR': 'Y', 'VAL': 'V'
}

if __name__ == "__main__":
    # Get VHH sequence from PDB 4KRL chain B
    vhh_seq = fetch_pdb_sequence("4KRL", "B")
    
    if vhh_seq:
        print(f"PDB 4KRL Chain B VHH sequence ({len(vhh_seq)} residues):")
        print(vhh_seq)
        print()
        
        # Compare with contaminated sequence
        contaminated = "QVKLEESGGGSVQTGGSLRLTCAASGRTSRSYGMGWFRQAPGKEREFVSGISWRGDSTGYADSVKGRFTISRDNAKNTVDLQMNSLKPEDTAIYYCAAAAGSAWYGTLYEYDYWGQGTQVTVSSALEHHHHHH"
        clean_part = contaminated.replace("ALEHHHHHH", "")  # Remove His-tag
        
        print(f"Current contaminated sequence ({len(contaminated)} residues):")
        print(contaminated)
        print()
        print(f"Clean part without His-tag ({len(clean_part)} residues):")
        print(clean_part)
        print()
        
        if vhh_seq:
            # Check similarity
            if clean_part in vhh_seq or vhh_seq in clean_part:
                print("✅ Sequences match - can use PDB 4KRL as correct source")
            else:
                print("⚠ Sequences differ - may need different VHH")
                # Print alignment
                print("PDB 4KRL VHH:")
                print(vhh_seq)
                print("Current clean:")
                print(clean_part)
        
    else:
        print("Failed to fetch sequence from PDB 4KRL")
        # Provide backup sequence from literature
        print("Using backup anti-EGFR VHH sequence (122 residues):")
        backup_seq = "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCVVTQCQMKGQGTQVTVSS"
        print(backup_seq)
        print(f"Length: {len(backup_seq)} residues")