#!/usr/bin/env python3
"""
7D12，SR
：
1. （ASCII art）
2. PyMOL
3. matplotlib 2D（）
4. BioPython（）
"""

import sys
from pathlib import Path
import pandas as pd

# 
try:
    from Bio.PDB import PDBParser, NeighborSearch
    HAS_BIOPYTHON = True
except ImportError:
    HAS_BIOPYTHON = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.colors import LinearSegmentedColormap
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "7D12"
FIGURES_DIR = PROJECT_ROOT / "paper" / "figures"
PDB_FILE = OUTPUT_DIR / "4KRL.pdb"
SURFACE_METRICS = OUTPUT_DIR / "7d12_4krl_per_residue_surface_metrics.csv"

# SR
SR_MUTATIONS = {
    12: {"from": "S", "to": "L", "relSASA": 0.71, "surface": True},
    40: {"from": "G", "to": "S", "relSASA": 0.01, "surface": False},
    42: {"from": "F", "to": "V", "relSASA": 0.01, "surface": False},
    83: {"from": "A", "to": "S", "relSASA": 0.78, "surface": True},
    96: {"from": "P", "to": "A", "relSASA": 0.45, "surface": True},
    101: {"from": "I", "to": "V", "relSASA": 0.27, "surface": True},
}

# CDR
CDR_REGIONS = [
    ("CDR1", 27, 38),
    ("CDR2", 56, 65),
    ("CDR3", 105, 117),
]

def generate_structure_description():
    """（）"""
    
    surface_sites = [pos for pos, info in SR_MUTATIONS.items() if info["surface"]]
    buried_sites = [pos for pos, info in SR_MUTATIONS.items() if not info["surface"]]
    
    description = f"""
## 7D12

****：PDB 4KRL，B（7D12 VHH）

**SR**：
- ****（，relSASA ≥0.25）：IMGT {', '.join(map(str, surface_sites))}（{len(surface_sites)}）
- ****（，relSASA <0.25）：IMGT {', '.join(map(str, buried_sites))}（{len(buried_sites)}）
- **CDR**（）：CDR1 (27-38), CDR2 (56-65), CDR3 (105-117)

****：
- 6SR{len(surface_sites)}（{len(surface_sites)/6*100:.0f}%）
- SR：，

****：
PyMOL、ChimeraXPyMolView。PDB：`{PDB_FILE}`

**PyMOL**：
```
load {PDB_FILE}, 7d12
select surface_muts, resi {'+'.join(map(str, surface_sites))} and chain B
select buried_muts, resi {'+'.join(map(str, buried_sites))} and chain B
select cdrs, resi 27-38+56-65+105-117 and chain B
color blue, surface_muts
color red, buried_muts
color green, cdrs
show surface
ray
save output/7D12/7d12_4krl_structure_with_sr_mutations.png
```
"""
    
    return description.strip()

def generate_text_based_structure_diagram():
    """（ASCII art）"""
    
    # 
    if SURFACE_METRICS.exists():
        df = pd.read_csv(SURFACE_METRICS)
        df = df[df["imgt_pos"].notna()].copy()
        df["imgt_pos"] = df["imgt_pos"].astype(int)
    else:
        print(f"[] : {SURFACE_METRICS}")
        return None
    
    # 
    diagram = []
    diagram.append("=" * 80)
    diagram.append("7D12 (PDB 4KRL)  - SR")
    diagram.append("=" * 80)
    diagram.append("")
    diagram.append("：")
    diagram.append("  [S] = SR (relSASA ≥0.25)")
    diagram.append("  [B] = SR (relSASA <0.25)")
    diagram.append("  [C] = CDR")
    diagram.append("  [.] = ")
    diagram.append("")
    diagram.append("-" * 80)
    diagram.append("")
    
    # 
    regions = [
        ("FR1", 1, 26),
        ("CDR1", 27, 38),
        ("FR2", 39, 55),
        ("CDR2", 56, 65),
        ("FR3", 66, 104),
        ("CDR3", 105, 117),
        ("FR4", 118, 128),
    ]
    
    for region_name, start, end in regions:
        diagram.append(f"{region_name} ({start}-{end}):")
        region_df = df[(df["imgt_pos"] >= start) & (df["imgt_pos"] <= end)].copy()
        
        line = []
        labels = []
        for _, row in region_df.iterrows():
            pos = int(row["imgt_pos"])
            is_sr = pos in SR_MUTATIONS.keys()
            is_cdr = region_name.startswith("CDR")
            rel_sasa = float(row["rel_sasa"]) if pd.notna(row["rel_sasa"]) else 0
            
            if is_cdr:
                line.append("[C]")
                labels.append(f"{pos}")
            elif is_sr:
                if rel_sasa >= 0.25:
                    line.append("[S]")
                else:
                    line.append("[B]")
                labels.append(f"{pos}")
            else:
                line.append("[.]")
                labels.append("  ")
        
        # 10
        for i in range(0, len(line), 10):
            chunk = line[i:i+10]
            label_chunk = labels[i:i+10]
            diagram.append(" ".join(chunk))
            diagram.append(" ".join(f"{l:>3}" for l in label_chunk))
        
        diagram.append("")
    
    diagram.append("-" * 80)
    diagram.append("")
    diagram.append("SR：")
    for pos, info in sorted(SR_MUTATIONS.items()):
        status = "" if info["surface"] else ""
        diagram.append(f"  IMGT {pos:3d}: {info['from']}→{info['to']:2s} | relSASA={info['relSASA']:.2f} | {status}")
    
    return "\n".join(diagram)

def generate_pymol_script():
    """PyMOL"""
    surface_sites = [pos for pos, info in SR_MUTATIONS.items() if info["surface"]]
    buried_sites = [pos for pos, info in SR_MUTATIONS.items() if not info["surface"]]
    
    script = f"""# PyMOL：7D12（SR）
# ：PyMOL @{OUTPUT_DIR / "7d12_structure_pymol.pml"}

# 
load {PDB_FILE}, 7d12

# 
show cartoon, 7d12
show surface, 7d12
set surface_mode, 1

# SR
select surface_muts, resi {'+'.join(map(str, surface_sites))} and chain B
select buried_muts, resi {'+'.join(map(str, buried_sites))} and chain B
select cdrs, resi 27-38+56-65+105-117 and chain B

# 
color gray90, 7d12
color blue, surface_muts
color red, buried_muts
color green, cdrs

# 
show spheres, surface_muts
show spheres, buried_muts
show sticks, cdrs

# 
orient
zoom center, 50

# 
label surface_muts and name CA, "resi"
label buried_muts and name CA, "resi"

# 
ray 1200, 1200
png {OUTPUT_DIR / "7d12_4krl_structure_with_sr_mutations.png"}, dpi=300

print(": {OUTPUT_DIR / "7d12_4krl_structure_with_sr_mutations.png"}")
"""
    return script

def generate_structure_summary_table():
    """（Markdown）"""
    surface_sites = [pos for pos, info in SR_MUTATIONS.items() if info["surface"]]
    buried_sites = [pos for pos, info in SR_MUTATIONS.items() if not info["surface"]]
    
    table = """## SR

| IMGT | Native | SR |  | relSASA |  |  |
|---------|--------|----|----|---------|---------|---------|
"""
    for pos in sorted(SR_MUTATIONS.keys()):
        info = SR_MUTATIONS[pos]
        region = "FR1" if pos <= 26 else "FR2" if pos <= 55 else "FR3"
        status = "" if info["surface"] else ""
        color = "" if info["surface"] else ""
        table += f"| {pos} | {info['from']} | {info['to']} | {region} | {info['relSASA']:.2f} | {status} | {color} |\n"
    
    table += f"""
****：
- （{len(surface_sites)}）：IMGT {', '.join(map(str, surface_sites))}
- （{len(buried_sites)}）：IMGT {', '.join(map(str, buried_sites))}
- ：{len(surface_sites)}/6 = {len(surface_sites)/6*100:.0f}%
"""
    return table

def main():
    print("=" * 60)
    print("7D12")
    print("=" * 60)
    print()
    
    # 
    print("[] ...")
    print(f"  BioPython: {'✓' if HAS_BIOPYTHON else '✗ ()'}")
    print(f"  Matplotlib: {'✓' if HAS_MATPLOTLIB else '✗ ()'}")
    print()
    
    # 
    print("[1/4] ...")
    description = generate_structure_description()
    desc_file = OUTPUT_DIR / "7d12_structure_visualization_description.md"
    with open(desc_file, 'w', encoding='utf-8') as f:
        f.write(description)
    print(f"  ✓ : {desc_file}")
    
    # 
    print("[2/4] ...")
    text_diagram = generate_text_based_structure_diagram()
    if text_diagram:
        diagram_file = OUTPUT_DIR / "7d12_structure_text_diagram.txt"
        with open(diagram_file, 'w', encoding='utf-8') as f:
            f.write(text_diagram)
        print(f"  ✓ : {diagram_file}")
    
    # PyMOL
    print("[3/4] PyMOL...")
    pymol_script = generate_pymol_script()
    pymol_file = OUTPUT_DIR / "7d12_structure_pymol.pml"
    with open(pymol_file, 'w', encoding='utf-8') as f:
        f.write(pymol_script)
    print(f"  ✓ : {pymol_file}")
    print(f"  : PyMOL @{pymol_file}")
    
    # 
    print("[4/4] ...")
    summary_table = generate_structure_summary_table()
    summary_file = OUTPUT_DIR / "7d12_structure_summary_table.md"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(summary_table)
    print(f"  ✓ : {summary_file}")
    
    print()
    print("=" * 60)
    print("！")
    print("=" * 60)
    print()
    print("：")
    print(f"  1. : {desc_file}")
    if text_diagram:
        print(f"  2. : {diagram_file}")
    print(f"  3. PyMOL: {pymol_file}")
    print(f"  4. : {summary_file}")
    print()
    print("：")
    print("  1. PyMOL3D：")
    print(f"     pymol @{pymol_file}")
    print("  2. PyMOL（）")
    print("  3. ")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
