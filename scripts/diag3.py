import json
from pathlib import Path
ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")

# 1. Check AutonomousHumanVH cohort
print("=== AutonomousHumanVH_Cohort_v1.json ===")
data = json.loads((ROOT / "data/reference/AutonomousHumanVH_Cohort_v1.json").read_text())
print(f"Total: {len(data)} entries")
if data:
    print("Keys:", list(data[0].keys()))
    for e in data[:8]:
        s = e.get("strategy") or e.get("conversion_method") or e.get("engineering_method") or "?"
        m = e.get("hallmark_mutations") or e.get("mutations") or e.get("key_mutations") or "?"
        print(f"  {e.get('name','?'):30s}  strategy={s}  mutations={m}")

print()

# 2. Check CD3 engineered VH panel
print("=== cd3_engineered_vh_panel_v1.json ===")
p2 = ROOT / "data/reference/cd3_engineered_vh_panel_v1.json"
if p2.exists():
    d2 = json.loads(p2.read_text())
    print(f"Total: {len(d2) if isinstance(d2,list) else 'dict'}")
    items = d2 if isinstance(d2, list) else list(d2.values())[:5]
    for e in items[:5]:
        print(f"  {e}")
else:
    print("File not found")
