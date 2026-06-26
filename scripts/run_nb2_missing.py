"""
run_nb2_missing.py
==================
Run NanoBodyBuilder2 on the 7 clinical VHH entries missing predicted structures,
then update unified_vhh_reference_db.json with the new structure paths.
"""

import sys, json, os
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import scripts.anarci_shim  # noqa — must be before ImmuneBuilder

from ImmuneBuilder import NanoBodyBuilder2

OUT_DIR = BASE / "reports" / "Round1_NanoBodyBuilder2_missing7"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = BASE / "data" / "unified_vhh_reference_db.json"

with open(DB_PATH) as f:
    db = json.load(f)

missing = [e for e in db if e.get("structure_type") == "sequence_only"]
print(f"Entries to model: {len(missing)}")

predictor = NanoBodyBuilder2()

results = {}
for i, e in enumerate(missing):
    name = e.get("name", f"entry_{i}")
    seq  = e.get("sequence", "").strip()
    safe = name.replace(" ", "_").replace("/", "_").replace("\\", "_")[:60]
    out_dir = OUT_DIR / safe
    out_dir.mkdir(exist_ok=True)
    out_pdb = out_dir / "rank0_unrefined.pdb"

    print(f"\n[{i+1}/{len(missing)}] {name[:55]}")
    print(f"  seq len={len(seq)}")

    try:
        nanobody = predictor.predict({"H": seq})
        nanobody.save(str(out_pdb))
        print(f"  → saved: {out_pdb}")
        results[name] = (str(out_pdb), "nb2_predicted_unrefined")
    except Exception as ex:
        print(f"  ERROR: {ex}")
        results[name] = (None, "sequence_only")

# Update unified DB
updated = 0
for e in db:
    n = e.get("name","")
    if n in results:
        path, stype = results[n]
        if path:
            e["structure_path"] = path
            e["structure_type"] = stype
            updated += 1

with open(DB_PATH, "w", encoding="utf-8") as f:
    json.dump(db, f, indent=2, ensure_ascii=False)

print(f"\nUpdated {updated} entries in unified_vhh_reference_db.json")

# Final coverage summary
from collections import Counter
stypes = Counter(e.get("structure_type","?") for e in db)
print("\nFinal structure coverage:")
for k, v in stypes.most_common():
    print(f"  {k}: {v}")
