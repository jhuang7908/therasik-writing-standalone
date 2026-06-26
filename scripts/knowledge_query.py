import sys
import os
import argparse
import json
from core.resources.knowledge_bridge import InSynBioKnowledgeBridge

def main():
    parser = argparse.ArgumentParser(description="InSynBio Knowledge CLI - Fetch biological context for antibody engineering.")
    parser.add_argument("--target", type=str, help="Target protein name (e.g., HER2, PD-L1)")
    parser.add_argument("--uniprot", type=str, help="UniProt Accession (e.g., P04626)")
    parser.add_argument("--pubmed", type=str, help="PubMed search query")
    parser.add_argument("--limit", type=int, default=5, help="Max results for PubMed/PDB")
    
    args = parser.parse_args()
    bridge = InSynBioKnowledgeBridge()
    
    results = {}
    
    if args.uniprot:
        print(f"[*] Fetching UniProt data for {args.uniprot}...")
        results["uniprot"] = bridge.fetch_uniprot_info(args.uniprot)
        
    if args.target:
        print(f"[*] Searching PDB structures for {args.target}...")
        results["pdb"] = bridge.find_pdb_structures(args.target, limit=args.limit)
        if not args.pubmed:
            args.pubmed = f"{args.target} antibody therapy"
            
    if args.pubmed:
        print(f"[*] Searching PubMed for '{args.pubmed}'...")
        results["pubmed"] = bridge.search_pubmed(args.pubmed, max_results=args.limit)
        
    if not results:
        parser.print_help()
        return

    # Output as formatted JSON for the Agent to read
    print("\n=== KNOWLEDGE SUMMARY ===")
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
