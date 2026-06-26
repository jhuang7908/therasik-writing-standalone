"""
 IG 

：
-  (Homo_sapiens)
-  (Mus_musculus)
-  (Rattus_norvegicus)
-  (Oryctolagus_cuniculus)
-  (Canis_lupus_familiaris)
-  (Felis_catus)
-  (Vicugna_pacos)
-  (Bos_taurus)
-  (Chondrichthyes)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional
from anarci import run_anarci


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMGT_BASE_DIR = PROJECT_ROOT / "data" / "germlines" / "IMGT_V-" / "IMGT_V-QUEST_reference_directory"

# ： -> IMGT 
SPECIES_MAP = {
    "": "Homo_sapiens",
    "": "Mus_musculus",
    "": "Rattus_norvegicus",
    "": "Oryctolagus_cuniculus",
    "": "Canis_lupus_familiaris",
    "": "Felis_catus",
    "": "Vicugna_pacos",
    "": "Bos_taurus",
    "": "Chondrichthyes",
}

# 
OUTPUT_DIR = PROJECT_ROOT / "data" / "germlines" / "multi_species_ig_aa"


def load_fasta_multi(path: Path) -> Dict[str, str]:
    """ FASTA"""
    seqs = {}
    header = None
    buf = []
    
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"[WARN]  {path}: {e}")
        return {}
    
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                seqs[header] = "".join(buf)
            header = line[1:].strip()
            buf = []
        else:
            buf.append(line)
    if header is not None:
        seqs[header] = "".join(buf)
    return seqs


def translate_dna_to_aa(dna_seq: str) -> str:
    """
     DNA 
    
    """
    codon_table = {
        'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L',
        'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
        'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*',
        'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W',
        'CTT': 'L', 'CTC': 'L', 'CTA': 'L', 'CTG': 'L',
        'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
        'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q',
        'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
        'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M',
        'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',
        'AAT': 'N', 'AAC': 'N', 'AAA': 'K', 'AAG': 'K',
        'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
        'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V',
        'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',
        'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
        'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G',
    }
    
    dna_seq = dna_seq.upper().replace('U', 'T')  #  RNA
    aa_seq = []
    
    for i in range(0, len(dna_seq) - 2, 3):
        codon = dna_seq[i:i+3]
        if len(codon) == 3:
            aa = codon_table.get(codon, 'X')  # X 
            if aa != '*':  # 
                aa_seq.append(aa)
    
    return ''.join(aa_seq)


def is_amino_acid_sequence(seq: str) -> bool:
    """"""
    valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
    seq_clean = seq.upper().replace('-', '').replace('.', '')
    return len(seq_clean) > 0 and all(c in valid_aa for c in seq_clean)


def extract_species_ig_aa(species_name: str, species_dir: str) -> Optional[Dict]:
    """
     IG 
    
    Args:
        species_name: 
        species_dir: IMGT 
    
    Returns:
        ， None
    """
    print(f"\n[INFO] ：{species_name} ({species_dir})", flush=True)
    print(f"[DEBUG] IMGT_BASE_DIR: {IMGT_BASE_DIR}", flush=True)
    print(f"[DEBUG] IMGT_BASE_DIR exists: {IMGT_BASE_DIR.exists()}", flush=True)
    
    #  IG_aa （）
    aa_dir = IMGT_BASE_DIR / species_dir / "IG_aa"
    ig_dir = IMGT_BASE_DIR / species_dir / "IG"
    
    print(f"[DEBUG] aa_dir: {aa_dir}", flush=True)
    print(f"[DEBUG] aa_dir exists: {aa_dir.exists()}", flush=True)
    print(f"[DEBUG] ig_dir: {ig_dir}", flush=True)
    print(f"[DEBUG] ig_dir exists: {ig_dir.exists()}", flush=True)
    
    fasta_files = []
    
    #  IG_aa 
    if aa_dir.exists():
        fasta_files = list(aa_dir.glob("IGHV*.fasta")) + list(aa_dir.glob("IGHV*.fa"))
        if fasta_files:
            print(f"[INFO]  IG_aa ：{aa_dir}", flush=True)
            print(f"[INFO]  {len(fasta_files)}  FASTA ", flush=True)
    
    # ， IG （）
    if not fasta_files and ig_dir.exists():
        fasta_files = list(ig_dir.glob("IGHV*.fasta")) + list(ig_dir.glob("IGHV*.fa"))
        if fasta_files:
            print(f"[INFO]  IG （）：{ig_dir}", flush=True)
            print(f"[INFO]  {len(fasta_files)}  FASTA ", flush=True)
    
    if not fasta_files:
        print(f"[WARN]  {species_name}  IGHV FASTA ")
        return None
    
    all_sequences = {}
    
    for fasta_file in fasta_files:
        print(f"[LOAD] ：{fasta_file.name}")
        seqs = load_fasta_multi(fasta_file)
        
        for header, seq in seqs.items():
            # 
            if not is_amino_acid_sequence(seq):
                print(f"[TRANSLATE] ：{header[:50]}...")
                seq = translate_dna_to_aa(seq)
            
            # （ gap ）
            seq = seq.replace('-', '').replace('.', '').upper()
            
            if len(seq) < 50:  # 
                continue
            
            all_sequences[header] = seq
    
    if not all_sequences:
        print(f"[WARN] {species_name} ")
        return None
    
    result = {
        "species_name": species_name,
        "species_dir": species_dir,
        "sequences": all_sequences,
        "count": len(all_sequences),
    }
    
    print(f"[OK] {species_name} ：{len(all_sequences)} ", flush=True)
    return result


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description=" IG ")
    parser.add_argument(
        "--species",
        nargs="+",
        choices=list(SPECIES_MAP.keys()) + ["all"],
        default=["all"],
        help="（：all）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="（：data/germlines/multi_species_ig_aa/）",
    )
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 
    if "all" in args.species:
        species_to_process = list(SPECIES_MAP.items())
    else:
        species_to_process = [(name, SPECIES_MAP[name]) for name in args.species if name in SPECIES_MAP]
    
    print(f"[INFO]  {len(species_to_process)}  IG ", flush=True)
    print(f"[INFO] IMGT ：{IMGT_BASE_DIR}", flush=True)
    print(f"[INFO] IMGT ：{IMGT_BASE_DIR.exists()}", flush=True)
    print(f"[INFO] ：{output_dir}", flush=True)
    
    all_results = {}
    
    for species_name, species_dir in species_to_process:
        result = extract_species_ig_aa(species_name, species_dir)
        if result:
            all_results[species_name] = result
            
            # 
            species_file = output_dir / f"{species_dir}_IGHV_aa.json"
            species_data = {
                "species_name": species_name,
                "species_dir": species_dir,
                "library_name": f"{species_dir}_IGHV_aa",
                "version": "extracted_MVP1",
                "entries": [
                    {
                        "id": header.split("|")[0] if "|" in header else header,
                        "raw_header": header,
                        "sequence_aa": seq,
                    }
                    for header, seq in result["sequences"].items()
                ],
            }
            species_file.write_text(
                json.dumps(species_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            print(f"[SAVED] {species_name} ：{species_file}", flush=True)
    
    # 
    summary = {
        "library_name": "multi_species_IGHV_aa",
        "version": "extracted_MVP1",
        "species_count": len(all_results),
        "total_sequences": sum(r["count"] for r in all_results.values()),
        "species": {
            name: {
                "species_dir": result["species_dir"],
                "sequence_count": result["count"],
            }
            for name, result in all_results.items()
        },
    }
    
    summary_file = output_dir / "multi_species_summary.json"
    summary_file.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    print(f"\n[SUCCESS] ！", flush=True)
    print(f"[INFO]  {len(all_results)} ", flush=True)
    print(f"[INFO] ：{summary['total_sequences']}", flush=True)
    print(f"[INFO] ：{summary_file}", flush=True)


if __name__ == "__main__":
    main()




















