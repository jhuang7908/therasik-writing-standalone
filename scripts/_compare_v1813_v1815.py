"""Compare V1.8.13 vs V1.8.15 mutation outputs for the 6 CD3 samples."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
root = ROOT / "projects" / "CD3_VH2VHH_Batch_20260515"

NAMES = ["SP34", "Teplizumab", "OKT3", "Visilizumab", "Otelixizumab", "Foralumab"]

print("=" * 115)
print(f"{'Sample':<14} {'V1813 stopped':<22} {'V1813 n':<8} {'V1815 stopped':<22} {'Gate':<10} {'V1815 n':<8} New mutations in V1.8.15")
print("=" * 115)

for name in NAMES:
    p13 = root / "v1813_reports" / f"{name}_v1813.json"
    p15 = root / "v1815_reports" / f"{name}_v1815.json"
    if not p13.exists() or not p15.exists():
        print(f"{name:<14} file missing")
        continue
    r13 = json.loads(p13.read_text())
    r15 = json.loads(p15.read_text())
    stop13 = r13["stopped_at"][:20]
    stop15 = r15["stopped_at"][:20]
    gate = r15.get("vl_safety_gate", "—")[:8]
    n13 = len(r13["all_mutations"])
    n15 = len(r15["all_mutations"])
    muts13 = {f"{m['orig_aa']}{m['label_kabat']}{m['target_aa']}" for m in r13["all_mutations"]}
    muts15 = {f"{m['orig_aa']}{m['label_kabat']}{m['target_aa']}" for m in r15["all_mutations"]}
    new_muts = muts15 - muts13
    print(f"{name:<14} {stop13:<22} {n13:<8} {stop15:<22} {gate:<10} {n15:<8} +{sorted(new_muts)}")

print()
print("VL-interface key residue status after engineering:")
print(f"{'Sample':<14} {'V1813 k45 final':<17} {'V1815 k45 final':<17} {'V1813 k47 final':<17} {'V1815 k47 final'}")
print("-" * 85)
for name in NAMES:
    p13 = root / "v1813_reports" / f"{name}_v1813.json"
    p15 = root / "v1815_reports" / f"{name}_v1815.json"
    if not p13.exists() or not p15.exists():
        continue
    r13 = json.loads(p13.read_text())
    r15 = json.loads(p15.read_text())
    # Find k45, k47 in mutation lists (by label_kabat)
    def get_final(result, label):
        for m in result["all_mutations"]:
            if m["label_kabat"] == label:
                return f"{m['orig_aa']}→{m['target_aa']}"
        # Not mutated — find in sequence
        from Bio.SeqUtils.ProtParam import ProteinAnalysis
        import re
        seq = result["input_seq"]
        m = re.search(r'[GA][LRA][EQ][WLY]', seq[35:55])
        if m:
            base = 35 + m.start()
            positions = {"K44": base, "K45": base + 1, "K47": base + 3}
            idx = positions.get(label)
            if idx is not None:
                aa = seq[idx]
                return f"{aa} (no chg)"
        return "?"
    k45_13 = get_final(r13, "K45")
    k45_15 = get_final(r15, "K45")
    k47_13 = get_final(r13, "K47")
    k47_15 = get_final(r15, "K47")
    print(f"{name:<14} {k45_13:<17} {k45_15:<17} {k47_13:<17} {k47_15}")
