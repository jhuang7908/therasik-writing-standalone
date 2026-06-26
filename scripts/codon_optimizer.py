import argparse

# Optimized Codon Table for Human/CHO (simplified based on high frequency codons)
OPTIMIZED_CODONS = {
    'A': 'GCC', 'C': 'TGC', 'D': 'GAC', 'E': 'GAG', 'F': 'TTC',
    'G': 'GGC', 'H': 'CAC', 'I': 'ATC', 'K': 'AAG', 'L': 'CTG',
    'M': 'ATG', 'N': 'AAC', 'P': 'CCC', 'Q': 'CAG', 'R': 'CGC',
    'S': 'AGC', 'T': 'ACC', 'V': 'GTG', 'W': 'TGG', 'Y': 'TAC',
    '*': 'TGA' # Stop codon
}

def optimize_sequence(aa_seq):
    """Converts Amino Acid sequence to optimized DNA sequence."""
    dna_seq = []
    for aa in aa_seq.upper():
        dna_seq.append(OPTIMIZED_CODONS.get(aa, 'NNN'))
    return "".join(dna_seq)

def main():
    parser = argparse.ArgumentParser(description="Codon Optimization for Human/CHO Expression")
    parser.add_argument("--seq", required=True, help="Amino Acid sequence to optimize")
    parser.add_argument("--name", default="optimized_dna", help="Name for the output")

    args = parser.parse_args()

    dna = optimize_sequence(args.seq)
    
    print(f"\n--- {args.name} ---")
    print(f"AA Length: {len(args.seq)}")
    print(f"DNA Length: {len(dna)} bp")
    print(f"G/C Content: {round((dna.count('G') + dna.count('C')) / len(dna) * 100, 2)}%")
    print(f"DNA Sequence:\n{dna}\n")

if __name__ == "__main__":
    main()
