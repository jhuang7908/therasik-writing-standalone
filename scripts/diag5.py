import json
from pathlib import Path
ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")

# Check selected strategy for all 6 samples
SAMPLES = [
    ("sp34_murine_vh_blinatumomab", "SP34"),
    ("teplizumab_vh_vl",            "Teplizumab"),
    ("okt3_humanized_scfv_actes",   "OKT3"),
    ("otelixizumab_vh_vl",          "Otelixizumab"),
    ("foralumab_vh_vl",             "Foralumab"),
    ("visilizumab_vh_vl",           "Visilizumab"),
]

print(f"{'Sample':<20} {'selected_strategy':<35} {'template':<30} {'converted_seq[:40]'}")
print("-" * 120)
for suf, name in SAMPLES:
    d = json.loads((ROOT / f".job_storage/cd3_v2v_{suf}/result.json").read_text())
    strat = d.get("selected_strategy") or "?"
    tmpl  = d.get("selected_template_id") or "?"
    seq   = d.get("converted_sequence") or ""
    print(f"{name:<20} {strat:<35} {tmpl:<30} {seq[:40]}")

print()

# Also check the cohort: k44/k45/k47 distribution
csv_p = ROOT / "data/reference/AutonomousHumanVH_Cohort_v1.csv"
import csv
rows = list(csv.DictReader(csv_p.open(encoding="utf-8")))
print(f"\n=== AutonomousHumanVH_Cohort_v1 Hallmark positions (n={len(rows)}) ===")
from collections import Counter
k44c = Counter(r["k44"] for r in rows)
k45c = Counter(r["k45"] for r in rows)
k47c = Counter(r["k47"] for r in rows)
print(f"Kabat 44: {dict(k44c)}  <- VHH uses R or E, human autonomous VH uses G/A")
print(f"Kabat 45: {dict(k45c)}  <- VHH uses R, human autonomous VH keeps L!")
print(f"Kabat 47: {dict(k47c)}  <- VHH uses F, human autonomous VH keeps W")
print()
print("Key insight: Real autonomous human VH molecules keep L45/W47 (VH-like).")
print("VHH hallmarks are R45/F47. CDR grafting onto VHH scaffold produces a VHH chimera, NOT an autonomous human VH.")
