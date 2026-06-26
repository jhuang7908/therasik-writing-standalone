import json, re
from pathlib import Path

def wc(text):
    return len(re.findall(r"[A-Za-z0-9'-]+", text or ""))

root = Path(__file__).parent
for name in [
    "huNSG_QUAD_pnas_20260527T001202Z.json",
    "huNSG_QUAD_pnas_20260527T001202Z_cited_20260527T002450Z.json",
    "huNSG_QUAD_ordered_smoke_20260526T235930Z.json",
]:
    p = root / name
    if not p.exists():
        continue
    d = json.loads(p.read_text(encoding="utf-8"))
    secs = d.get("sections") or (d.get("step2_hungs") or {}).get("sections") or []
    full = "\n\n".join(s.get("text", "") for s in secs)
    per = {s["key"]: wc(s.get("text", "")) for s in secs}
    mr = d.get("merged_reference_count") or len(d.get("merged_reference_list") or [])
    print(name)
    print("  total_words", wc(full), "refs", mr, "per_section", per)
