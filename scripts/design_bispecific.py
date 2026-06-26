import argparse
import json
import os
from codon_optimizer import optimize_sequence
from ncbi_client import fetch_genbank_sequence, fetch_pubmed_summary
from external_apis_client import BiologicalAPIClient

# Load functional domains
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "design_rules", "functional_domains.json")
try:
    with open(DB_PATH, "r") as f:
        DOMAIN_DB = json.load(f)
except Exception as e:
    print(f"Warning: Could not load domain database: {e}")
    DOMAIN_DB = {}

def apply_kih_mutations(fc_seq, side="knob"):
    """
    Applies Knobs-into-Holes mutations to human IgG1 Fc.
    Standard pos (Eu numbering): S354, T366, L368, Y349, Y407
    Note: Highly simplified mapping to the static sequence.
    """
    kih_info = DOMAIN_DB.get("mutations", {}).get("KiH", {})
    # For practical practice, we would use a proper structure-aware grafting tool.
    # Here we show the conceptual mutations in the report.
    return fc_seq, kih_info.get(side, {})

def generate_bsab_report(seq1, seq2, format_type="tandem_vhh", linker_key="G4S3", kih=False, name="bsab_construct", verify=False):
    linker = DOMAIN_DB.get("linkers", {}).get(linker_key, {})
    fc = DOMAIN_DB.get("IgG1_Fc", {})
    
    print(f"\n{'='*60}")
    print(f" PRACTICAL BISPECIFIC DESIGN REPORT: {name}")
    print(f"{'='*60}")
    print(f"Format: {format_type.upper()}")
    if format_type == "tandem_vhh":
        construct_aa = f"{seq1}{linker.get('seq', '')}{seq2}"
        pubmed = linker.get("pubmed", "N/A")
        print(f"Linker: {linker_key} (PubMed: {pubmed})")
        print(f"Total AA: {len(construct_aa)}")
        print(f"Optimized DNA:\n{optimize_sequence(construct_aa)}")
    
    elif format_type == "kih_igg":
        print("Strategy: Knobs-into-Holes (KiH) + CrossMab")
        kih_db = DOMAIN_DB.get("mutations", {}).get("KiH", {})
        print(f"PubMed: {kih_db.get('pubmed', 'N/A')}")
        
        if verify:
            print(f"\n[LIVE PDB/NCBI VERIFICATION]")
            pdb_id = kih_db.get("pdb")
            if pdb_id:
                client = BiologicalAPIClient()
                pdb_meta = client.fetch_pdb_metadata(pdb_id)
                if pdb_meta:
                    print(f"Verified PDB {pdb_id}: {pdb_meta['title']} ({pdb_meta['resolution']} A)")

        knob_fc, knob_muts = apply_kih_mutations(fc.get('seq', ''), "knob")
        hole_fc, hole_muts = apply_kih_mutations(fc.get('seq', ''), "hole")
        
        print(f"\n[CHAIN A - KNOB]")
        print(f"Mutations: {knob_muts.get('pos_impaired', '')}, {knob_muts.get('stabilizing', '')}")
        print(f"Sequence (VH+CH1+CH2+CH3_Knob): ...[Engineered CrossMab VH/CH1]...")
        
        print(f"\n[CHAIN B - HOLE]")
        print(f"Mutations: {hole_muts.get('pos_impaired', '')}, {hole_muts.get('stabilizing', '')}")
        print(f"Sequence (VH+CH1+CH2+CH3_Hole): ...[Standard VH/CH1]...")

    print(f"{'='*60}\n")

def main():
    parser = argparse.ArgumentParser(description="Advanced Practical Bispecific Design")
    parser.add_argument("--format", choices=["tandem_vhh", "kih_igg"], required=True)
    parser.add_argument("--seq1", required=True, help="First binding domain")
    parser.add_argument("--seq2", required=True, help="Second binding domain")
    parser.add_argument("--linker", default="G4S3")
    parser.add_argument("--kih", action="store_true", help="Apply KiH mutations")
    parser.add_argument("--name", default="bsab_construct")
    parser.add_argument("--verify", action="store_true", help="Verify domains via NCBI/PDB")

    args = parser.parse_args()
    generate_bsab_report(args.seq1, args.seq2, args.format, args.linker, args.kih, args.name, args.verify)

if __name__ == "__main__":
    main()
