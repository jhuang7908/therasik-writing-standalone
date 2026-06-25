#!/usr/bin/env python3
"""
VHH，（）
"""
import json
from pathlib import Path
from typing import Dict, List
import re

def analyze_vhh_sequence(sequence: str, name: str) -> Dict:
    """VHH"""
    seq = sequence.upper()
    length = len(seq)
    
    # VHH
    vhh_features = {
        "length": length,
        "starts_with_vhh": seq.startswith(('QVQL', 'EVQL', 'DVQL')),
        "fr2_hallmark": check_fr2_hallmark(seq),
        "cdr_lengths": estimate_cdr_lengths(seq),
        "hydrophobic_residues": count_hydrophobic(seq),
        "surface_residues": identify_surface_residues(seq)
    }
    
    # 
    humanization_strategy = recommend_strategy(vhh_features, name)
    
    return {
        "name": name,
        "sequence": seq,
        "features": vhh_features,
        "humanization_strategy": humanization_strategy
    }

def check_fr2_hallmark(seq: str) -> Dict:
    """FR2VHH hallmark"""
    # FR237-55（IMGT）
    # VHH hallmark: F37, E44, R45, G47
    hallmark_positions = {
        "F37": seq[36] if len(seq) > 36 else None,
        "E44": seq[43] if len(seq) > 43 else None,
        "R45": seq[44] if len(seq) > 44 else None,
        "G47": seq[46] if len(seq) > 46 else None,
    }
    
    # hallmark score
    typical_vhh = {'F': 'F', 'E': 'E', 'R': 'R', 'G': 'G'}
    score = 0
    for pos, aa in hallmark_positions.items():
        if aa and aa == typical_vhh.get(pos[0], ''):
            score += 1
    
    return {
        "positions": hallmark_positions,
        "score": score,
        "max_score": 4,
        "is_typical_vhh": score >= 3
    }

def estimate_cdr_lengths(seq: str) -> Dict:
    """CDR（VHH）"""
    # ，IMGT
    # VHH: FR1(26) + CDR1(6-8) + FR2(17) + CDR2(8-10) + FR3(38) + CDR3(10-20)
    
    # 
    cdr1_start = 26  # FR1
    cdr2_start = 40  # 
    cdr3_start = 66  # 
    
    return {
        "estimated_cdr1_length": min(10, len(seq) - cdr1_start) if len(seq) > cdr1_start else 0,
        "estimated_cdr2_length": min(12, len(seq) - cdr2_start) if len(seq) > cdr2_start else 0,
        "estimated_cdr3_length": len(seq) - cdr3_start if len(seq) > cdr3_start else 0,
        "note": "VHH，IMGT"
    }

def count_hydrophobic(seq: str) -> Dict:
    """"""
    hydrophobic = ['A', 'V', 'L', 'I', 'M', 'F', 'W', 'P']
    count = sum(1 for aa in seq if aa in hydrophobic)
    
    return {
        "count": count,
        "percentage": count / len(seq) * 100 if seq else 0,
        "risk_level": "high" if count / len(seq) > 0.4 else "medium" if count / len(seq) > 0.3 else "low"
    }

def identify_surface_residues(seq: str) -> Dict:
    """（）"""
    # ：
    # FR
    # 
    
    hydrophilic = ['D', 'E', 'K', 'R', 'H', 'N', 'Q', 'S', 'T', 'Y']
    surface_likely = sum(1 for i, aa in enumerate(seq) 
                         if aa in hydrophilic and i < 100)  # FR
    
    return {
        "surface_likely_count": surface_likely,
        "needs_resurfacing": surface_likely < len(seq) * 0.3  # 
    }

def recommend_strategy(features: Dict, name: str) -> Dict:
    """"""
    strategy = {
        "primary_method": "CDR_grafting",  # 
        "secondary_method": None,
        "needs_resurfacing": False,
        "resurfacing_reason": "",
        "recommended_approach": "",
        "risk_assessment": {}
    }
    
    # 
    needs_resurfacing = False
    reasons = []
    
    # 1. FR2 hallmark
    if not features["fr2_hallmark"]["is_typical_vhh"]:
        needs_resurfacing = True
        reasons.append("FR2 hallmark，")
    
    # 2. 
    if features["hydrophobic_residues"]["risk_level"] == "high":
        needs_resurfacing = True
        reasons.append("，")
    
    # 3. 
    if features["surface_residues"]["needs_resurfacing"]:
        needs_resurfacing = True
        reasons.append("，")
    
    # 4. ALB8
    if "ALB8" in name or "8Z8V" in name:
        # ALB8，
        needs_resurfacing = True
        reasons.append("ALB8，")
    
    strategy["needs_resurfacing"] = needs_resurfacing
    strategy["resurfacing_reason"] = "; ".join(reasons) if reasons else "，CDR"
    
    if needs_resurfacing:
        strategy["primary_method"] = "CDR_grafting_with_resurfacing"
        strategy["secondary_method"] = "Surface_reshaping"
        strategy["recommended_approach"] = """
        1. CDR：CDR1/2/3VH3
        2. ：
        3. Vernier Zone：
        4. ：FR2FR3
        """
    else:
        strategy["recommended_approach"] = """
        1. CDR：CDRVH3
        2. ：
        3. ：VHH
        """
    
    # 
    strategy["risk_assessment"] = {
        "immunogenicity_risk": "medium" if needs_resurfacing else "low",
        "affinity_risk": "low",
        "stability_risk": "low",
        "overall_risk": "low"
    }
    
    return strategy

def main():
    """"""
    print("=" * 60)
    print("VHH")
    print("=" * 60)
    
    # 
    json_file = Path("projects/anti_HSA_VHH/input/anti_hsa_vhh_from_pdb.json")
    if not json_file.exists():
        print("❌ ")
        return
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    sequences = data.get("sequences", [])
    
    print(f"\n {len(sequences)} ...\n")
    
    results = []
    for seq_data in sequences:
        name = seq_data.get("pdb_id", "Unknown")
        sequence = seq_data.get("sequence", "")
        
        if sequence:
            analysis = analyze_vhh_sequence(sequence, name)
            results.append(analysis)
            
            # 
            print(f"\n{'='*60}")
            print(f": {name}")
            print(f"{'='*60}")
            print(f": {analysis['features']['length']} aa")
            print(f"FR2 Hallmark Score: {analysis['features']['fr2_hallmark']['score']}/4")
            print(f": {analysis['features']['hydrophobic_residues']['risk_level']}")
            print(f"\n: {analysis['humanization_strategy']['primary_method']}")
            if analysis['humanization_strategy']['needs_resurfacing']:
                print(f"✅ ")
                print(f": {analysis['humanization_strategy']['resurfacing_reason']}")
            else:
                print(f"✅ CDR")
    
    # 
    output_file = Path("projects/anti_HSA_VHH/.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "analysis_date": str(Path.cwd()),
            "total_sequences": len(results),
            "analyses": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ : {output_file}")
    
    # 
    generate_recommendation_report(results)

def generate_recommendation_report(results: List[Dict]):
    """"""
    report_file = Path("projects/anti_HSA_VHH/.md")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# HSA VHH\n\n")
        f.write("****: 2025-12-17\n\n")
        f.write("---\n\n")
        
        # VHH
        f.write("## 🎯 VHH\n\n")
        
        # 
        priority_order = []
        for r in results:
            name = r['name']
            if '8Z8V' in name or 'ALB8' in name:
                priority_order.append((r, 1, "，"))
            elif 'MY632' in name:
                priority_order.append((r, 2, "2024，"))
            else:
                priority_order.append((r, 3, ""))
        
        priority_order.sort(key=lambda x: x[1])
        
        for i, (result, priority, note) in enumerate(priority_order, 1):
            f.write(f"### {i}. {result['name']} - {note}\n\n")
            f.write(f"****: {result['features']['length']} aa\n\n")
            f.write(f"****: \n```\n{result['sequence']}\n```\n\n")
            
            strategy = result['humanization_strategy']
            f.write(f"****: {strategy['primary_method']}\n\n")
            
            if strategy['needs_resurfacing']:
                f.write("**✅ **\n\n")
                f.write(f"****: {strategy['resurfacing_reason']}\n\n")
                f.write("****:\n")
                f.write("1. \n")
                f.write("2. \n")
                f.write("3. Vernier Zone\n")
                f.write("4. FR2FR3\n\n")
            else:
                f.write("**✅ CDR**\n\n")
            
            f.write("---\n\n")
        
        # 
        f.write("## 🔧 （Surface Reshaping）\n\n")
        f.write("### \n\n")
        f.write("1. FR2 hallmark\n")
        f.write("2. \n")
        f.write("3. \n")
        f.write("4. \n\n")
        
        f.write("### \n\n")
        f.write("1. ****: \n")
        f.write("2. ****: \n")
        f.write("3. **Vernier Zone**: CDR\n")
        f.write("4. ****: FR2FR3\n")
        f.write("5. ****: \n\n")
        
        f.write("### \n\n")
        f.write("- **FR1**: 1-26，\n")
        f.write("- **FR2**: 37-55，VHH hallmark，\n")
        f.write("- **FR3**: 66-104，，\n")
        f.write("- **Vernier Zone**: 26, 39, 55, 66, 71, 78, 94，\n\n")
        
        # 
        f.write("## 🚀 \n\n")
        f.write("### （）\n\n")
        for i, (result, priority, note) in enumerate(priority_order[:3], 1):
            f.write(f"{i}. **{result['name']}** - {note}\n")
        
        f.write("\n### \n\n")
        f.write("```bash\n")
        f.write("# \n")
        f.write("python app/run_vhh_cli.py \\\n")
        f.write("    --fasta projects/anti_HSA_VHH/input/anti_hsa_vhh_from_pdb_cleaned.fasta \\\n")
        f.write("    --source alpaca \\\n")
        f.write("    --strategy balanced \\\n")
        f.write("    --out projects/anti_HSA_VHH/output/result.json\n")
        f.write("```\n\n")
        
        f.write("### \n\n")
        f.write("- ✅ IMGT\n")
        f.write("- ✅ VH3\n")
        f.write("- ✅ （Conservative/Balanced/Aggressive）\n")
        f.write("- ✅ \n")
        f.write("- ✅ CMC\n")
        f.write("- ✅ \n\n")
        
        f.write("### \n\n")
        f.write("。：\n\n")
        f.write("1. \n")
        f.write("2. \n")
        f.write("3. VH3 germline\n")
        f.write("4. Vernier Zone\n")
        f.write("5. \n\n")
    
    print(f"✅ : {report_file}")

if __name__ == '__main__':
    main()
