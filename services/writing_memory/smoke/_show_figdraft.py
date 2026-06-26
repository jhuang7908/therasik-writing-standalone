import json, re
from pathlib import Path

d = json.loads(Path(
    r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\services\writing_memory\smoke"
    r"\huNSG_QUAD_figdraft_20260527T011815Z.json"
).read_text(encoding="utf-8"))

secs = {s["key"]: s for s in d["sections"]}

def wc(t): return len(re.findall(r"[A-Za-z0-9'-]+", t or ""))

bench = {"abstract": 251, "introduction": 565, "methods": 1375, "results": 3233, "discussion": 1927, "total": 7351, "refs": 44}

print("=== Word count vs expert ===")
for k in ("abstract","introduction","methods","results","discussion"):
    a = wc(secs[k]["text"])
    e = bench[k]
    print(f"  {k:<14} {a:>5} / {e:>5}  ({round(a/e*100)}%)  fills={secs[k]['fill_count']}")
total = sum(wc(s["text"]) for s in d["sections"])
refs = d["merged_reference_count"]
print(f"  {'TOTAL':<14} {total:>5} / {bench['total']:>5}  ({round(total/bench['total']*100)}%)")
print(f"  {'References':<14} {refs:>5} / {bench['refs']:>5}  ({round(refs/bench['refs']*100)}%)")

print("\n=== QC ===")
qc = d["qc"]
print(f"  Overall: {qc['overall_score']} ({qc['overall_verdict']})")
print(f"  FAIL: {qc['dimensions_failed']}")
print(f"  WARN: {qc.get('dimensions_warned')}")
for k, v in qc["dimensions"].items():
    stars = "FAIL" if v["verdict"] == "fail" else ("WARN" if v["verdict"] == "warn" else "pass")
    print(f"  [{stars}] {k:<28} {v['score']:>3}  {v['summary'][:75]}")

print("\n=== Results section (first 1500 chars) ===")
print(secs["results"]["text"][:1500])
