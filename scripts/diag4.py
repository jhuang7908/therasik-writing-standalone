import json
from pathlib import Path
ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")

# AutonomousHumanVH cohort
d = json.loads((ROOT / "data/reference/AutonomousHumanVH_Cohort_v1.json").read_text())
meta = d.get("_meta", {})
entries = d.get("entries", [])
print(f"=== AutonomousHumanVH Cohort (n={len(entries)}) ===")
print(f"Version: {meta.get('version')}  description: {meta.get('description')}")
print()
if entries:
    print("Keys:", list(entries[0].keys()))
    print()
    for e in entries[:10]:
        nm = e.get("name") or e.get("vh_name") or "?"
        strategy = e.get("conversion_strategy") or e.get("engineering_approach") or e.get("method") or "?"
        muts = e.get("hallmark_mutations") or e.get("key_mutations") or e.get("mutations_applied") or "?"
        pub = e.get("source_pmid") or e.get("pubmed_id") or e.get("reference") or "?"
        print(f"  {nm[:35]:<35}  method={strategy}   muts={muts}   ref={pub}")

print()

# CSV version
import csv
csv_p = ROOT / "data/reference/AutonomousHumanVH_Cohort_v1.csv"
if csv_p.exists():
    rows = list(csv.DictReader(csv_p.open(encoding="utf-8")))
    print(f"=== CSV version (n={len(rows)}) ===")
    print("Columns:", list(rows[0].keys()) if rows else "empty")
    for r in rows[:5]:
        print(" ", dict(r))
