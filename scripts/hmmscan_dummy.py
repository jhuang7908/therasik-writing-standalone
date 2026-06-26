import sys
import os
import argparse
import pyhmmer
from pyhmmer.plan7 import HMMFile
import io

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", help="Output file")
    parser.add_argument("--cpu", type=int, help="Number of CPUs")
    parser.add_argument("hmm_file", help="HMM file")
    parser.add_argument("fasta_file", help="Fasta file")
    
    args, unknown = parser.parse_known_args()
    
    if not args.o or not args.hmm_file or not args.fasta_file:
        print("Usage: hmmscan_dummy.py -o output.txt hmm_file fasta_file")
        sys.exit(1)
        
    # Read fasta
    sequences = []
    with pyhmmer.easel.SequenceFile(args.fasta_file, digital=True) as seq_file:
        sequences = list(seq_file)
        
    # Read HMM
    with HMMFile(args.hmm_file) as hmm_file:
        all_top_hits = list(pyhmmer.hmmer.hmmscan(sequences, hmm_file, cpus=args.cpu or 1))
        
    # Write output
    with open(args.o, "wb") as fout:
        header = (
            "# HMMER 3.3.2 (Nov 2020); http://hmmer.org/\n"
            "# Copyright (C) 2020 Howard Hughes Medical Institute.\n"
            "# Freely distributed under the BSD open source license.\n"
            "# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -\n"
        )
        fout.write(header.encode())
        
        for i, th in enumerate(all_top_hits):
            query_name = sequences[i].name.decode()
            query_len = len(sequences[i])
            fout.write(f"Query:       {query_name}  [L={query_len}]\n".encode())
            th.write(fout)
            fout.write(b"//\n")

if __name__ == "__main__":
    main()
