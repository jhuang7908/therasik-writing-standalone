import sys
sys.path.insert(0, "scripts")
from generate_ada_study_files_v2 import (
    CONFIRMED, NEED_FT, get_target_disease,
    extract_pmids, get_clin_rec,
    extract_ada_context, extract_evidence_chain_summary,
)

print("=== CONFIRMED — missing fields ===")
for e in CONFIRMED:
    name = e["antibody_name"]
    tgt, dis = get_target_disease(name)
    clin  = get_clin_rec(name)
    pmids = extract_pmids(e, clin)
    ctx   = extract_ada_context(e, clin)
    chain = extract_evidence_chain_summary(e, clin)
    issues = []
    if tgt == "—":    issues.append("target")
    if dis == "—":    issues.append("disease")
    if not pmids:     issues.append("no PMID")
    if not ctx:       issues.append("no ADA context")
    if not chain:     issues.append("no chain summary")
    if issues:
        print(f"  {name}: {issues}")

print("\n=== NEED_FT — missing fields ===")
for e in NEED_FT:
    name = e["antibody_name"]
    tgt, dis = get_target_disease(name)
    clin  = get_clin_rec(name)
    pmids = extract_pmids(e, clin)
    ctx   = extract_ada_context(e, clin)
    chain = extract_evidence_chain_summary(e, clin)
    issues = []
    if tgt == "—":    issues.append("target")
    if dis == "—":    issues.append("disease")
    if not pmids:     issues.append("no PMID")
    if issues:
        print(f"  {name}: {issues}")
