#!/usr/bin/env python3
"""
HSA VHH
"""
import json
from pathlib import Path
from datetime import datetime

# （）
PATENT_INFO = {
    "8Z8V_ALB8": {
        "name": "ALB8 (ozoralizumab)",
        "company": "Ablynx (/Sanofi)",
        "patent_status": "",
        "patent_family": "Ablynx ALB",
        "filing_date_estimate": "2000-2010",
        "expiration_estimate": "2020-2030",
        "note": "ALB8AblynxHSA VHH，。。",
        "risk_level": "HIGH",
        "academic_use": "",
        "commercial_use": ""
    },
    "8Y9S_MY6321": {
        "name": "MY6321",
        "company": "（）",
        "patent_status": "",
        "deposition_date": "2024-02-07",
        "note": "2024PDB，",
        "risk_level": "MEDIUM",
        "academic_use": "",
        "commercial_use": ""
    },
    "8Y9U_MY6323": {
        "name": "MY6323",
        "company": "（）",
        "patent_status": "",
        "deposition_date": "2024-02-07",
        "note": "2024PDB，",
        "risk_level": "MEDIUM",
        "academic_use": "",
        "commercial_use": ""
    },
    "8Y9T_MY6322": {
        "name": "MY6322",
        "company": "（）",
        "patent_status": "",
        "deposition_date": "2024-02-07",
        "note": "2024PDB，",
        "risk_level": "MEDIUM",
        "academic_use": "",
        "commercial_use": ""
    }
}

def analyze_patent_status():
    """"""
    print("=" * 60)
    print("HSA VHH")
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
    
    for seq in sequences:
        pdb_id = seq["pdb_id"]
        title = seq.get("title", "")
        
        # 
        if "ALB8" in title or pdb_id == "8Z8V":
            key = "8Z8V_ALB8"
        elif "MY6321" in title or pdb_id == "8Y9S":
            key = "8Y9S_MY6321"
        elif "MY6323" in title or pdb_id == "8Y9U":
            key = "8Y9U_MY6323"
        elif "MY6322" in title or pdb_id == "8Y9T":
            key = "8Y9T_MY6322"
        else:
            key = None
        
        if key and key in PATENT_INFO:
            info = PATENT_INFO[key]
            results.append({
                "pdb_id": pdb_id,
                "name": info["name"],
                "patent_status": info["patent_status"],
                "risk_level": info["risk_level"],
                "academic_use": info["academic_use"],
                "commercial_use": info["commercial_use"],
                "note": info["note"]
            })
    
    # 
    print(":\n")
    print("-" * 60)
    
    for result in results:
        print(f"\n{result['pdb_id']} - {result['name']}")
        print(f"  : {result['patent_status']}")
        print(f"  : {result['risk_level']}")
        print(f"  : {result['academic_use']}")
        print(f"  : {result['commercial_use']}")
        print(f"  : {result['note']}")
    
    # 
    print("\n" + "=" * 60)
    print("")
    print("=" * 60)
    
    print("\n1. :")
    print("   - ")
    print("   - Ablynx（2000）")
    print("   - FTO")
    
    print("\n2. :")
    print("   - MY6321/6322/6323: 2024，")
    print("   - ，")
    
    print("\n3. :")
    print("   - ALB8: Ablynx/，")
    
    print("\n4. :")
    print("   ✅ : ，")
    print("   ⚠️  : FTO")
    print("   ✅ : ")
    
    # 
    output_file = Path("projects/anti_HSA_VHH/.md")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# HSA VHH\n\n")
        f.write(f"****: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        for result in results:
            f.write(f"## {result['pdb_id']} - {result['name']}\n\n")
            f.write(f"- ****: {result['patent_status']}\n")
            f.write(f"- ****: {result['risk_level']}\n")
            f.write(f"- ****: {result['academic_use']}\n")
            f.write(f"- ****: {result['commercial_use']}\n")
            f.write(f"- ****: {result['note']}\n\n")
        
        f.write("---\n\n")
        f.write("## \n\n")
        f.write("1. ⚠️ ，\n")
        f.write("2. ⚠️ FTO\n")
        f.write("3. ⚠️ ，\n")
        f.write("4. ✅ \n")
    
    print(f"\n✅ : {output_file}")

if __name__ == '__main__':
    analyze_patent_status()
