#!/usr/bin/env python3
"""
VHH：、Hallmark、
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys
import os

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠️  requests，")

try:
    from Bio.PDB import PDBParser, NeighborSearch
    from Bio.PDB.DSSP import DSSP
    HAS_BIO = True
except ImportError:
    HAS_BIO = False
    print("⚠️  BioPython，")

# 
HYDROPHOBIC = {'A', 'V', 'L', 'I', 'M', 'F', 'W', 'P', 'C'}
HYDROPHILIC = {'D', 'E', 'K', 'R', 'H', 'N', 'Q', 'S', 'T', 'Y', 'G'}

# VHH Hallmark（IMGT）
HALLMARK_POSITIONS = {
    37: {"typical": "F", "role": ""},
    44: {"typical": "Q", "role": "，"},
    45: {"typical": "R", "role": "，"},
    47: {"typical": "G", "role": ""}
}

def download_pdb_structure(pdb_id: str, output_path: Path) -> bool:
    """PDB"""
    if not HAS_REQUESTS:
        return False
    
    url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(response.text)
            return True
    except Exception as e:
        print(f"  ⚠️  : {e}")
    return False

def parse_pdb_structure(pdb_file: Path) -> Optional[Dict]:
    """PDB"""
    if not HAS_BIO:
        return None
    
    try:
        parser = PDBParser(QUIET=True)
        structure = parser.get_structure('VHH', str(pdb_file))
        
        # （VHH）
        model = structure[0]
        chains = list(model.get_chains())
        
        if not chains:
            return None
        
        # VHH（HSA）
        vhh_chain = None
        for chain in chains:
            if len(list(chain.get_residues())) < 200:  # VHH<200
                vhh_chain = chain
                break
        
        if not vhh_chain:
            vhh_chain = chains[0]  # 
        
        return {
            "structure": structure,
            "model": model,
            "vhh_chain": vhh_chain,
            "chain_id": vhh_chain.id
        }
    except Exception as e:
        print(f"  ⚠️  : {e}")
        return None

def calculate_hydrophobic_surface(sequence: str) -> Dict:
    """/（）"""
    seq = sequence.upper()
    
    hydrophobic_count = sum(1 for aa in seq if aa in HYDROPHOBIC)
    hydrophilic_count = sum(1 for aa in seq if aa in HYDROPHILIC)
    total = len(seq)
    
    # （FR）
    # ：FR1/FR2/FR360%，CDR80%
    
    return {
        "total_residues": total,
        "hydrophobic_count": hydrophobic_count,
        "hydrophilic_count": hydrophilic_count,
        "hydrophobic_percentage": hydrophobic_count / total * 100,
        "hydrophilic_percentage": hydrophilic_count / total * 100,
        "hydrophobicity_score": (hydrophobic_count - hydrophilic_count) / total,
        "note": "，"
    }

def estimate_cdr_positions(sequence: str) -> Dict:
    """CDR（VHH）"""
    seq = sequence.upper()
    
    # VHH
    # FR1: 1-26, CDR1: 27-38, FR2: 39-55, CDR2: 56-65, FR3: 66-104, CDR3: 105-117
    
    # WVRQWFRQ
    fr2_marker = None
    for i in range(len(seq) - 4):
        if seq[i:i+4] in ["WVRQ", "WFRQ", "WIRQ"]:
            fr2_marker = i
            break
    
    if fr2_marker:
        # 
        fr1_end = max(26, fr2_marker - 12)
        cdr1_start = fr1_end + 1
        cdr1_end = fr2_marker - 1
        fr2_start = fr2_marker - 10
        fr2_end = fr2_marker + 15
        cdr2_start = fr2_end + 1
        cdr2_end = cdr2_start + 10
        fr3_start = cdr2_end + 1
        fr3_end = len(seq) - 15
        cdr3_start = fr3_end + 1
        cdr3_end = len(seq)
    else:
        # 
        fr1_end = 26
        cdr1_start = 27
        cdr1_end = 38
        fr2_start = 39
        fr2_end = 55
        cdr2_start = 56
        cdr2_end = 65
        fr3_start = 66
        fr3_end = 104
        cdr3_start = 105
        cdr3_end = len(seq)
    
    return {
        "FR1": (1, fr1_end),
        "CDR1": (cdr1_start, cdr1_end),
        "FR2": (fr2_start, fr2_end),
        "CDR2": (cdr2_start, cdr2_end),
        "FR3": (fr3_start, fr3_end),
        "CDR3": (cdr3_start, cdr3_end),
        "note": "VHH，IMGT"
    }

def calculate_hallmark_cdr_distances(sequence: str, positions: Dict) -> Dict:
    """HallmarkCDR"""
    seq = sequence.upper()
    
    # HallmarkFR2
    fr2_start, fr2_end = positions["FR2"]
    
    # hallmark（FR2）
    # IMGT 37FR211，4418，4519，4721
    hallmark_seq_positions = {}
    
    for imgt_pos, info in HALLMARK_POSITIONS.items():
        # ：FR239，IMGT 3737
        seq_pos = fr2_start + (imgt_pos - 26)  # 
        if 0 <= seq_pos < len(seq):
            hallmark_seq_positions[imgt_pos] = {
                "sequence_position": seq_pos + 1,
                "residue": seq[seq_pos],
                "typical": info["typical"],
                "role": info["role"]
            }
    
    # CDR
    distances = {}
    
    for imgt_pos, hallmark_info in hallmark_seq_positions.items():
        hallmark_pos = hallmark_info["sequence_position"]
        
        cdr_distances = {}
        for cdr_name, (cdr_start, cdr_end) in positions.items():
            if cdr_name.startswith("CDR"):
                # CDR
                cdr_center = (cdr_start + cdr_end) / 2
                distance = abs(hallmark_pos - cdr_center)
                
                cdr_distances[cdr_name] = {
                    "distance_aa": distance,
                    "cdr_center": cdr_center,
                    "cdr_range": (cdr_start, cdr_end),
                    "proximity": "close" if distance < 20 else "medium" if distance < 40 else "far"
                }
        
        distances[imgt_pos] = {
            "hallmark_info": hallmark_info,
            "cdr_distances": cdr_distances,
            "min_distance_to_cdr": min([d["distance_aa"] for d in cdr_distances.values()])
        }
    
    return distances

def assess_support_role(distances: Dict, sequence: str) -> Dict:
    """Hallmark"""
    support_assessment = {}
    
    for imgt_pos, dist_info in distances.items():
        hallmark_info = dist_info["hallmark_info"]
        min_dist = dist_info["min_distance_to_cdr"]
        
        # 
        support_score = 0
        support_reasons = []
        
        # 1. （<20 AA）
        if min_dist < 15:
            support_score += 3
            support_reasons.append(f"CDR（{min_dist:.1f} AA），")
        elif min_dist < 25:
            support_score += 2
            support_reasons.append(f"CDR（{min_dist:.1f} AA），")
        else:
            support_score += 1
            support_reasons.append(f"CDR（{min_dist:.1f} AA），")
        
        # 2. 
        role = hallmark_info["role"]
        if "" in role or "" in role:
            support_score += 2
            support_reasons.append("，")
        elif "" in role:
            support_score += 1
            support_reasons.append("，")
        
        # 3. 
        residue = hallmark_info["residue"]
        typical = hallmark_info["typical"]
        
        if residue == typical:
            support_score += 1
            support_reasons.append(f"hallmark（{typical}）")
        else:
            support_reasons.append(f"（{residue} vs {typical}），")
        
        support_assessment[imgt_pos] = {
            "support_score": support_score,
            "max_score": 7,
            "support_level": "strong" if support_score >= 5 else "moderate" if support_score >= 3 else "weak",
            "reasons": support_reasons,
            "hallmark_info": hallmark_info,
            "min_distance_to_cdr": min_dist
        }
    
    return support_assessment

def analyze_structure(pdb_id: str, sequence: str) -> Dict:
    """"""
    print(f"\nPDB: {pdb_id}")
    print("=" * 60)
    
    # 1. （）
    pdb_file = Path(f"projects/anti_HSA_VHH/structures/{pdb_id}.pdb")
    if not pdb_file.exists() and HAS_REQUESTS:
        print(f"PDB: {pdb_id}")
        download_pdb_structure(pdb_id, pdb_file)
    
    # 2. 
    print("\n1. /...")
    surface_analysis = calculate_hydrophobic_surface(sequence)
    print(f"   : {surface_analysis['hydrophobic_count']} ({surface_analysis['hydrophobic_percentage']:.1f}%)")
    print(f"   : {surface_analysis['hydrophilic_count']} ({surface_analysis['hydrophilic_percentage']:.1f}%)")
    
    # 3. CDR
    print("\n2. CDR...")
    cdr_positions = estimate_cdr_positions(sequence)
    for region, value in cdr_positions.items():
        if region.startswith("CDR") and isinstance(value, tuple):
            start, end = value
            print(f"   {region}: {start}-{end}")
    
    # 4. HallmarkCDR
    print("\n3. HallmarkCDR...")
    # 
    positions_only = {k: v for k, v in cdr_positions.items() if isinstance(v, tuple)}
    distances = calculate_hallmark_cdr_distances(sequence, positions_only)
    
    for imgt_pos, dist_info in distances.items():
        hallmark = dist_info["hallmark_info"]
        print(f"\n   IMGT{imgt_pos} ({hallmark['residue']}, : {hallmark['typical']}):")
        print(f"   : {hallmark['sequence_position']}")
        for cdr_name, cdr_dist in dist_info["cdr_distances"].items():
            print(f"     {cdr_name}: {cdr_dist['distance_aa']:.1f} AA ({cdr_dist['proximity']})")
    
    # 5. 
    print("\n4. Hallmark...")
    support_assessment = assess_support_role(distances, sequence)
    
    for imgt_pos, assessment in support_assessment.items():
        print(f"\n   IMGT{imgt_pos}:")
        print(f"   : {assessment['support_score']}/7")
        print(f"   : {assessment['support_level']}")
        print(f"   CDR: {assessment['min_distance_to_cdr']:.1f} AA")
        for reason in assessment['reasons']:
            print(f"     - {reason}")
    
    # 6. PDB（）
    structure_data = None
    if pdb_file.exists() and HAS_BIO:
        print("\n5. PDB...")
        structure_data = parse_pdb_structure(pdb_file)
        if structure_data:
            print(f"   ✅ ，ID: {structure_data['chain_id']}")
            print(f"   ⚠️  DSSP")
        else:
            print("   ⚠️  ")
    
    return {
        "pdb_id": pdb_id,
        "sequence": sequence,
        "surface_analysis": surface_analysis,
        "cdr_positions": cdr_positions,
        "hallmark_cdr_distances": distances,
        "support_assessment": support_assessment,
        "structure_available": structure_data is not None
    }

def main():
    """"""
    print("=" * 60)
    print("VHH：、Hallmark、")
    print("=" * 60)
    
    # ALB8
    fasta_file = Path("projects/anti_HSA_VHH/input/anti_hsa_vhh_alb8_only.fasta")
    if not fasta_file.exists():
        print("❌ ALB8")
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
    
    print(f"\n: ALB8")
    print(f": {len(sequence)} aa")
    print(f"PDB: 8Z8V")
    
    # 
    results = analyze_structure("8Z8V", sequence)
    
    # 
    output_file = Path("projects/anti_HSA_VHH/structure_analysis_hallmark.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ : {output_file}")
    
    # 
    generate_report(results)

def generate_report(results: Dict):
    """"""
    report_file = Path("projects/anti_HSA_VHH/_Hallmark.md")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# VHH：、Hallmark、\n\n")
        f.write(f"**PDB ID**: {results['pdb_id']}\n")
        f.write(f"****: {len(results['sequence'])} aa\n")
        f.write(f"****: 2025-12-17\n\n")
        f.write("---\n\n")
        
        # 
        f.write("## 1. /\n\n")
        surface = results['surface_analysis']
        f.write(f"- ****: {surface['total_residues']}\n")
        f.write(f"- ****: {surface['hydrophobic_count']} ({surface['hydrophobic_percentage']:.1f}%)\n")
        f.write(f"- ****: {surface['hydrophilic_count']} ({surface['hydrophilic_percentage']:.1f}%)\n")
        f.write(f"- ****: {surface['hydrophobicity_score']:.3f}\n")
        f.write(f"  - ，\n")
        f.write(f"- ****: {surface['note']}\n\n")
        
        # CDR
        f.write("## 2. CDR\n\n")
        for region, value in results['cdr_positions'].items():
            if region.startswith("CDR") and isinstance(value, tuple):
                start, end = value
                f.write(f"- **{region}**: {start}-{end} (: {end-start+1} aa)\n")
        if 'note' in results['cdr_positions']:
            f.write(f"\n⚠️  {results['cdr_positions']['note']}\n\n")
        
        # Hallmark
        f.write("## 3. HallmarkCDR\n\n")
        for imgt_pos, dist_info in results['hallmark_cdr_distances'].items():
            hallmark = dist_info['hallmark_info']
            f.write(f"### IMGT{imgt_pos}: {hallmark['residue']} (: {hallmark['typical']})\n\n")
            f.write(f"- ****: {hallmark['sequence_position']}\n")
            f.write(f"- ****: {hallmark['role']}\n")
            f.write(f"- **CDR**:\n")
            
            for cdr_name, cdr_dist in dist_info['cdr_distances'].items():
                f.write(f"  - **{cdr_name}**: {cdr_dist['distance_aa']:.1f} AA ({cdr_dist['proximity']})\n")
            
            f.write(f"- **CDR**: {dist_info['min_distance_to_cdr']:.1f} AA\n\n")
        
        # 
        f.write("## 4. Hallmark\n\n")
        for imgt_pos, assessment in results['support_assessment'].items():
            f.write(f"### IMGT{imgt_pos}\n\n")
            f.write(f"- ****: {assessment['support_score']}/7\n")
            f.write(f"- ****: **{assessment['support_level'].upper()}**\n")
            f.write(f"- **CDR**: {assessment['min_distance_to_cdr']:.1f} AA\n")
            f.write(f"- ****:\n")
            for reason in assessment['reasons']:
                f.write(f"  - {reason}\n")
            f.write("\n")
        
        # 
        f.write("## 5. \n\n")
        f.write("### Hallmark\n\n")
        
        strong_support = [pos for pos, a in results['support_assessment'].items() 
                         if a['support_level'] == 'strong']
        moderate_support = [pos for pos, a in results['support_assessment'].items() 
                           if a['support_level'] == 'moderate']
        weak_support = [pos for pos, a in results['support_assessment'].items() 
                      if a['support_level'] == 'weak']
        
        if strong_support:
            f.write(f"****: IMGT {', '.join(map(str, strong_support))}\n")
            f.write("- CDR，\n\n")
        
        if moderate_support:
            f.write(f"****: IMGT {', '.join(map(str, moderate_support))}\n")
            f.write("- CDR\n\n")
        
        if weak_support:
            f.write(f"****: IMGT {', '.join(map(str, weak_support))}\n")
            f.write("- CDR，\n\n")
        
        f.write("### \n\n")
        f.write("1. **Hallmark**: hallmark（Q44, R45, G47）\n")
        f.write("2. ****: hallmark\n")
        f.write("3. ****: hallmark\n")
        f.write("4. ****: HallmarkCDR，\n\n")
    
    print(f"✅ : {report_file}")

if __name__ == '__main__':
    main()
