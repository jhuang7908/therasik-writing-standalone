#!/usr/bin/env python3
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

clinical_idx = REPO / "data/ADA_reliable_package/clinical_db/clinical_ada_db_index.json"
verif_idx    = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_index.json"
excl_file    = REPO / "data/ADA_reliable_package/verifiable_classified/verifiable_ada_excluded.json"

ci = json.loads(clinical_idx.read_text(encoding="utf-8"))
vi = json.loads(verif_idx.read_text(encoding="utf-8"))
ex = json.loads(excl_file.read_text(encoding="utf-8"))

n_ci   = len(ci["index"])
n_vi   = len(vi["index"])
n_excl = len(ex["excluded"])

print(f"clinical_ada_db_index (all entries): {n_ci}")
print(f"verifiable_ada_index  (included)   : {n_vi}")
print(f"verifiable_ada_excluded            : {n_excl}")
print(f"Sum included + excluded            : {n_vi + n_excl}")
print()

print("=== Exclusion reasons ===")
reasons: dict[str, int] = {}
for e in ex["excluded"]:
    k = e.get("reason", "?")
    reasons[k] = reasons.get(k, 0) + 1
for k, v in sorted(reasons.items(), key=lambda x: -x[1]):
    print(f"  {k:55s}: {v}")

print()
print("=== Full excluded entries list ===")
for e in sorted(ex["excluded"], key=lambda x: x.get("antibody_name", "")):
    name   = e.get("antibody_name", "?")
    reason = e.get("reason", "?")
    es     = e.get("evidence_source", "")[:45]
    detail = e.get("detail", "")[:60]
    print(f"  {name:30s}  [{reason}]")
    if es:
        print(f"    evidence_source: {es}")
    if detail:
        print(f"    detail: {detail}")
