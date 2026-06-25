#!/usr/bin/env python3
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
report = json.loads(
    (REPO / "data/ADA_reliable_package/verification/full_reverification_report.json").read_text(encoding="utf-8")
)
results = report["results"]

groups: dict = {}
for r in results:
    groups.setdefault(r["verdict"], []).append(r)

print("=== ALL_MATCHED (42) ===")
for r in sorted(groups.get("all_matched", []), key=lambda x: x["antibody_name"]):
    name = r["antibody_name"]
    tier = r["tier"]
    pcts = r["claimed_pcts"]
    print(f"  OK  [{tier}] {name:30s}  pcts={pcts}")

print()
print("=== PARTIAL_MATCH (8) ===")
for r in sorted(groups.get("partial_match", []), key=lambda x: x["antibody_name"]):
    chk = r.get("check", {})
    name = r["antibody_name"]
    tier = r["tier"]
    matched = chk.get("matched")
    unmatched = chk.get("unmatched")
    print(f"  ~   [{tier}] {name:30s}  matched={matched}  UNMATCHED={unmatched}")

print()
print("=== NOT_FOUND (45) ===")
for r in sorted(groups.get("not_found", []), key=lambda x: x["antibody_name"]):
    name = r["antibody_name"]
    tier = r["tier"]
    pcts = r["claimed_pcts"]
    src = str(r.get("source_tried", ""))[:60]
    snip = r.get("text_snippet", "")[:80]
    print(f"  FAIL[{tier}] {name:30s}  pcts={pcts}")
    print(f"       src={src}")
    print(f"       snip={snip}")

print()
print("=== FETCH_FAILED (23) ===")
for r in sorted(groups.get("fetch_failed", []), key=lambda x: x["antibody_name"]):
    name = r["antibody_name"]
    tier = r["tier"]
    src = str(r.get("source_tried", ""))[:55]
    note = (r.get("notes") or [""])[0][:80]
    print(f"  ERR [{tier}] {name:30s}  src={src}")
    print(f"       {note}")
