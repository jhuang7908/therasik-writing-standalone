#!/usr/bin/env python3
"""
PDB：IMGT/Kabat
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
import sys
import os

# anarcii
try:
    from anarci import anarci
    HAS_ANARCI = True
except ImportError:
    HAS_ANARCI = False
    print("⚠️  anarcii，")

# BioPython
try:
    from Bio.PDB import PDBParser
    HAS_BIO = True
except ImportError:
    HAS_BIO = False
    print("⚠️  BioPython，")

def extract_sequence_from_pdb(pdb_file: Path) -> Optional[str]:
    """PDB"""
    if not pdb_file.exists():
        return None
    
    sequence = ""
    with open(pdb_file, 'r') as f:
        for line in f:
            if line.startswith('ATOM') and line[12:16].strip() == 'CA':  # CA
                resname = line[17:20].strip()
                # 
                aa_map = {
                    'ALA': 'A', 'ARG': 'R', 'ASN': 'N', 'ASP': 'D',
                    'CYS': 'C', 'GLN': 'Q', 'GLU': 'E', 'GLY': 'G',
                    'HIS': 'H', 'ILE': 'I', 'LEU': 'L', 'LYS': 'K',
                    'MET': 'M', 'PHE': 'F', 'PRO': 'P', 'SER': 'S',
                    'THR': 'T', 'TRP': 'W', 'TYR': 'Y', 'VAL': 'V'
                }
                aa = aa_map.get(resname, 'X')
                sequence += aa
    
    return sequence if sequence else None

def annotate_with_anarci(sequence: str, scheme: str = 'imgt') -> Optional[Dict]:
    """anarciiIMGT/Kabat"""
    if not HAS_ANARCI:
        return None
    
    try:
        numbered, alignment_details, hit_tables = anarci(
            [("VHH", sequence)], 
            scheme=scheme,
            output=False
        )
        
        if numbered and numbered[0] and numbered[0][0]:
            numbering = numbered[0][0][0]  # 
            
            # 
            regions = {
                "FR1": [],
                "CDR1": [],
                "FR2": [],
                "CDR2": [],
                "FR3": [],
                "CDR3": [],
                "FR4": []
            }
            
            # IMGT
            # FR1: 1-26, CDR1: 27-38, FR2: 39-55, CDR2: 56-65, FR3: 66-104, CDR3: 105-117, FR4: 118-128
            
            for (chain, pos), aa in numbering:
                if chain == 'H':  # 
                    if 1 <= pos <= 26:
                        regions["FR1"].append((pos, aa))
                    elif 27 <= pos <= 38:
                        regions["CDR1"].append((pos, aa))
                    elif 39 <= pos <= 55:
                        regions["FR2"].append((pos, aa))
                    elif 56 <= pos <= 65:
                        regions["CDR2"].append((pos, aa))
                    elif 66 <= pos <= 104:
                        regions["FR3"].append((pos, aa))
                    elif 105 <= pos <= 117:
                        regions["CDR3"].append((pos, aa))
                    elif 118 <= pos <= 128:
                        regions["FR4"].append((pos, aa))
            
            # hallmark
            hallmark_positions = {}
            for (chain, pos), aa in numbering:
                if chain == 'H':
                    if pos in [37, 44, 45, 47]:
                        hallmark_positions[pos] = {
                            "imgt_position": pos,
                            "residue": aa,
                            "scheme": scheme
                        }
            
            return {
                "scheme": scheme,
                "numbering": numbering,
                "regions": regions,
                "hallmark_positions": hallmark_positions,
                "total_residues": len(numbering)
            }
    except Exception as e:
        print(f"  ⚠️  anarcii: {e}")
        return None

def analyze_pdb_structure(pdb_id: str, sequence: Optional[str] = None) -> Dict:
    """PDB"""
    print(f"\nPDB: {pdb_id}")
    print("=" * 60)
    
    pdb_file = Path(f"projects/anti_HSA_VHH/structures/{pdb_id}.pdb")
    
    # 1. 
    if not sequence:
        if pdb_file.exists():
            print("PDB...")
            sequence = extract_sequence_from_pdb(pdb_file)
        else:
            print("❌ PDB，")
            return {"error": "PDB"}
    
    if not sequence:
        return {"error": ""}
    
    print(f": {len(sequence)} aa")
    print(f": {sequence}\n")
    
    results = {
        "pdb_id": pdb_id,
        "sequence": sequence,
        "sequence_length": len(sequence),
        "annotations": {}
    }
    
    # 2. IMGT
    print("IMGT...")
    imgt_result = annotate_with_anarci(sequence, scheme='imgt')
    if imgt_result:
        results["annotations"]["imgt"] = imgt_result
        print(f"  ✅ IMGT")
        print(f"  : {imgt_result['total_residues']}")
        
        # 
        print("\n  IMGT:")
        for region_name, positions in imgt_result["regions"].items():
            if positions:
                start_pos = positions[0][0]
                end_pos = positions[-1][0]
                seq = ''.join([aa for _, aa in positions])
                print(f"    {region_name}: IMGT {start_pos}-{end_pos} ({len(positions)} aa)")
                print(f"      : {seq}")
        
        # hallmark
        print("\n  Hallmark (IMGT):")
        for pos, info in imgt_result["hallmark_positions"].items():
            print(f"    {pos}: {info['residue']}")
    else:
        print("  ⚠️  IMGT")
        results["annotations"]["imgt"] = None
    
    # 3. Kabat
    print("\nKabat...")
    kabat_result = annotate_with_anarci(sequence, scheme='kabat')
    if kabat_result:
        results["annotations"]["kabat"] = kabat_result
        print(f"  ✅ Kabat")
        print(f"  : {kabat_result['total_residues']}")
    else:
        print("  ⚠️  Kabat")
        results["annotations"]["kabat"] = None
    
    # 4. anarcii，
    if not HAS_ANARCI:
        print("\n⚠️  ...")
        results["annotations"]["simplified"] = estimate_regions_simple(sequence)
    
    return results

def estimate_regions_simple(sequence: str) -> Dict:
    """（VHH）"""
    seq = sequence.upper()
    
    # VHH
    # FR1: 1-26, CDR1: 27-38, FR2: 39-55, CDR2: 56-65, FR3: 66-104, CDR3: 105-117
    
    regions = {
        "FR1": {"start": 1, "end": 26, "sequence": seq[0:26]},
        "CDR1": {"start": 27, "end": 38, "sequence": seq[26:38]},
        "FR2": {"start": 39, "end": 55, "sequence": seq[38:55]},
        "CDR2": {"start": 56, "end": 65, "sequence": seq[55:65]},
        "FR3": {"start": 66, "end": 104, "sequence": seq[65:104]},
        "CDR3": {"start": 105, "end": len(seq), "sequence": seq[104:]}
    }
    
    # hallmark（）
    hallmark_estimates = {
        37: {"sequence_position": 37, "residue": seq[36] if len(seq) > 36 else "?"},
        44: {"sequence_position": 44, "residue": seq[43] if len(seq) > 43 else "?"},
        45: {"sequence_position": 45, "residue": seq[44] if len(seq) > 44 else "?"},
        47: {"sequence_position": 47, "residue": seq[46] if len(seq) > 46 else "?"}
    }
    
    return {
        "regions": regions,
        "hallmark_estimates": hallmark_estimates,
        "note": "VHH，IMGT"
    }

def generate_report(results: Dict):
    """"""
    report_file = Path("projects/anti_HSA_VHH/PDBIMGT_Kabat.md")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# PDBIMGT/Kabat\n\n")
        f.write(f"**PDB ID**: {results['pdb_id']}\n")
        f.write(f"****: {results['sequence_length']} aa\n")
        f.write(f"****: 2025-12-17\n\n")
        f.write("---\n\n")
        
        # IMGT
        if results['annotations'].get('imgt'):
            imgt = results['annotations']['imgt']
            f.write("## IMGT\n\n")
            f.write("### \n\n")
            
            for region_name, positions in imgt['regions'].items():
                if positions:
                    start_pos = positions[0][0]
                    end_pos = positions[-1][0]
                    seq = ''.join([aa for _, aa in positions])
                    f.write(f"#### {region_name}\n\n")
                    f.write(f"- **IMGT**: {start_pos}-{end_pos}\n")
                    f.write(f"- ****: {len(positions)} aa\n")
                    f.write(f"- ****: `{seq}`\n\n")
            
            # Hallmark
            if imgt['hallmark_positions']:
                f.write("### Hallmark (IMGT)\n\n")
                f.write("| IMGT |  |  |\n")
                f.write("|----------|------|------|\n")
                for pos, info in sorted(imgt['hallmark_positions'].items()):
                    typical = {"37": "F", "44": "Q", "45": "R", "47": "G"}.get(str(pos), "?")
                    status = "✅" if info['residue'] == typical else "⚠️"
                    f.write(f"| {pos} | {info['residue']} (: {typical}) | {status} |\n")
                f.write("\n")
        else:
            f.write("## IMGT\n\n")
            f.write("⚠️  IMGT（anarcii）\n\n")
        
        # Kabat
        if results['annotations'].get('kabat'):
            kabat = results['annotations']['kabat']
            f.write("## Kabat\n\n")
            f.write("✅ Kabat\n")
            f.write(f": {kabat['total_residues']}\n\n")
        else:
            f.write("## Kabat\n\n")
            f.write("⚠️  Kabat（anarcii）\n\n")
        
        # 
        if results['annotations'].get('simplified'):
            simplified = results['annotations']['simplified']
            f.write("## \n\n")
            f.write("⚠️  {}\n\n".format(simplified['note']))
            f.write("### \n\n")
            for region_name, region_info in simplified['regions'].items():
                f.write(f"- **{region_name}**: {region_info['start']}-{region_info['end']} ({len(region_info['sequence'])} aa)\n")
                f.write(f"  : `{region_info['sequence']}`\n")
            f.write("\n")
    
    print(f"\n✅ : {report_file}")

def main():
    """"""
    print("=" * 60)
    print("PDBIMGT/Kabat")
    print("=" * 60)
    
    # ALB8
    fasta_file = Path("projects/anti_HSA_VHH/input/anti_hsa_vhh_alb8_only.fasta")
    if not fasta_file.exists():
        print("❌ ")
        return
    
    with open(fasta_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        sequence = ""
        for line in lines:
            if not line.startswith('>'):
                sequence += line.strip()
    
    if not sequence:
        print("❌ ")
        return
    
    # 
    results = analyze_pdb_structure("8Z8V", sequence)
    
    # 
    output_file = Path("projects/anti_HSA_VHH/pdb_imgt_kabat_analysis.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ : {output_file}")
    
    # 
    generate_report(results)

if __name__ == '__main__':
    main()
