"""Merge per-figure Results into the revised frontiers draft → final JSON + TXT."""
import json
import re
from pathlib import Path

SMOKE = Path(__file__).resolve().parent


def wc(t: str) -> int:
    return len(re.findall(r"[A-Za-z0-9'-]+", t or ""))


# Load revised draft
rev = json.loads((SMOKE / "huNSG_QUAD_frontiers_revised.json").read_text(encoding="utf-8"))

# Load latest refined results
results_files = sorted(SMOKE.glob("huNSG_QUAD_results_refined_*.json"), reverse=True)
if not results_files:
    raise FileNotFoundError("No huNSG_QUAD_results_refined_*.json found in smoke/")
rf = json.loads(results_files[0].read_text(encoding="utf-8"))
results_text = rf["assembled_results_text"]
extra_refs = rf.get("merged_reference_list") or []

# Replace Results section
for s in rev["sections"]:
    if s["key"] == "results":
        s["text"] = results_text
        break

# Merge refs (dedup)
existing_refs = list(rev.get("merged_reference_list") or [])
seen = set(existing_refs)
for r in extra_refs:
    if r not in seen:
        existing_refs.append(r)
        seen.add(r)
rev["merged_reference_list"] = existing_refs
rev["revision_note"] = (
    rev.get("revision_note", "") + " + per-figure Results v2 (3207 words)."
)

# Save JSON
out_json = SMOKE / "huNSG_QUAD_frontiers_final.json"
out_json.write_text(json.dumps(rev, indent=2, ensure_ascii=False), encoding="utf-8")

# Save TXT manuscript
plan = rev.get("plan") or {}
title = (
    plan.get("suggested_title")
    or "Development of human innate immune responses in humanized NSG-QUAD mice"
)
lines: list[str] = ["=" * 80, title.upper(), "=" * 80, ""]
for s in rev["sections"]:
    w = wc(s["text"])
    lines += ["", "-" * 80, f"{s['key'].upper()}  [{w} words]", "-" * 80, ""]
    lines.append(s["text"].strip())
lines += ["", "-" * 80, f"REFERENCES  [{len(existing_refs)} entries]", "-" * 80, ""]
for i, r in enumerate(existing_refs, 1):
    lines.append(f"{i}. {r}")

out_txt = SMOKE / "huNSG_QUAD_frontiers_final.txt"
out_txt.write_text("\n".join(lines), encoding="utf-8")

expert = {
    "abstract": 251, "introduction": 565,
    "methods": 1375, "results": 3233, "discussion": 1927,
}
print("=== Final merged draft word counts ===")
total = 0
for s in rev["sections"]:
    w = wc(s["text"])
    ex = expert.get(s["key"], 0)
    total += w
    pct = round(w / ex * 100) if ex else "?"
    print(f"  {s['key']:14s} {w:5d} / {ex:5d} ({pct}%)")
print(f"  {'TOTAL':14s} {total:5d} / 7351 ({round(total/7351*100)}%)")
print(f"  {'Refs':14s} {len(existing_refs):5d} / 44")
print(f"\nSaved: {out_json.name}")
print(f"Saved: {out_txt.name}")
