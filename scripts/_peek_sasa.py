import json
from pathlib import Path
d = Path("projects/CD3_VH2VHH_Batch_20260515/v1816_sasa_reports")
for f in sorted(d.glob("*_sasa.json")):
    r = json.loads(f.read_text())
    z1 = r.get("v1816_zone1_sasa", {})
    k45 = z1.get("K45", {})
    k47 = z1.get("K47", {})
    k37 = z1.get("K37", {})
    gate = r.get("v1816_gate_verdict")
    action = r.get("v1816_action")
    print(f"{r['sample']:<14} CDR3={r.get('cdr3_len')} fam={r.get('ighv_family')} | "
          f"k45={k45.get('aa','?')} {k45.get('sasa','?'):.1f}A2 | "
          f"k47={k47.get('aa','?')} {k47.get('sasa','?'):.1f}A2 | "
          f"k37={k37.get('aa','?')} {k37.get('sasa','?'):.1f}A2 | gate={gate}")
