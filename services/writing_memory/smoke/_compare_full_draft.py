import json, re
from pathlib import Path

def wc(t):
    return len(re.findall(r"[A-Za-z0-9'-]+", t or ""))

d = json.loads(Path(
    r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\services\writing_memory\smoke"
    r"\huNSG_QUAD_full_20260527T005405Z.json"
).read_text(encoding="utf-8"))

bench = d["expert_benchmark"]
refs  = d["merged_reference_count"]
secs  = {s["key"]: s for s in d["sections"]}

print(f"{'Section':<14}| {'Draft':>8} | {'Expert':>7} | {'%':>5}")
print("-" * 44)
for k in ("abstract","introduction","methods","results","discussion"):
    a = wc(secs[k]["text"])
    e = bench["words_by_section"][k]
    print(f"{k:<14}| {a:>8} | {e:>7} | {round(a/e*100):>4}%")

total = sum(wc(s["text"]) for s in d["sections"])
e_total = bench["word_total"]
print("-" * 44)
print(f"{'TOTAL':<14}| {total:>8} | {e_total:>7} | {round(total/e_total*100):>4}%")
print(f"{'References':<14}| {refs:>8} | {bench['ref_count']:>7} | {round(refs/bench['ref_count']*100):>4}%")

print()
qc = d["qc"]
print(f"QC score: {qc['overall_score']} ({qc['overall_verdict']})")
print(f"FAIL: {qc['dimensions_failed']}")
print(f"WARN: {qc.get('dimensions_warned')}")

print()
print("Per-section fills and refs:")
for k, s in secs.items():
    print(f"  {k:<14} fills={s['fill_count']}  refs={s['reference_count']}")
