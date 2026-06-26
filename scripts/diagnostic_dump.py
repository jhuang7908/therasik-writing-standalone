import json
from pathlib import Path

ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
samples = [
    ("sp34_murine_vh_blinatumomab", "SP34"),
    ("teplizumab_vh_vl", "Teplizumab"),
    ("okt3_humanized_scfv_actes", "OKT3"),
    ("otelixizumab_vh_vl", "Otelixizumab"),
    ("foralumab_vh_vl", "Foralumab"),
    ("visilizumab_vh_vl", "Visilizumab"),
]

for suffix, name in samples:
    p = ROOT / f".job_storage/cd3_v2v_{suffix}/result.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    c0 = d["candidates"][0] if d.get("candidates") else {}
    cmc = d["mini_cmc"]
    print(f"\n=== {name} ===")
    print(f"  input_seq    : {d['input_sequence']}")
    print(f"  converted_seq: {d['converted_sequence']}")
    print(f"  template     : {d['selected_template_id']}")
    print(f"  muts_applied : {d['mutations_applied']}")
    print(f"  abnativ_vh2  : {c0.get('abnativ_vh2')}")
    print(f"  abnativ_vhh2 : {c0.get('abnativ_vhh2')}")
    print(f"  abnativ_delta: {c0.get('abnativ_delta')}")
    print(f"  pI           : {cmc['pI']}")
    print(f"  GRAVY        : {cmc['GRAVY']}")
    print(f"  cdr3_Rg      : {cmc['cdr3_compactness']}")
    print(f"  cmc_status   : {d['cmc_status']}")
