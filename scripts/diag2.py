import json
from pathlib import Path
ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
for suf, name in [
    ("sp34_murine_vh_blinatumomab", "SP34"),
    ("foralumab_vh_vl", "Foralumab"),
    ("otelixizumab_vh_vl", "Otelixizumab"),
    ("teplizumab_vh_vl", "Teplizumab"),
]:
    d = json.loads((ROOT / f".job_storage/cd3_v2v_{suf}/result.json").read_text())
    print(f"=== {name} ===")
    print(f"  mutations_applied : {d.get('mutations_applied')}")
    print(f"  already_canonical : {d.get('already_canonical')}")
    print(f"  phase45_mutations : {d.get('phase45_mutations')}")
    print(f"  phase45_skipped   : {d.get('phase45_skipped')}")
    print(f"  conversion_error  : {d.get('conversion_error')}")
    print(f"  result keys       : {list(d.keys())[:20]}")
    print()
