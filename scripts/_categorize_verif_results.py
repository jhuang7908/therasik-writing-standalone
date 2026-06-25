#!/usr/bin/env python3
"""
Categorize verification results to understand why NOT_FOUND happened:
 A) PDF source (binary, can't parse text)
 B) Wrong PMID (paper is completely unrelated to the antibody)
 C) Right drug, value in full text not abstract
 D) Ambiguous
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
report = json.loads(
    (REPO / "data/ADA_reliable_package/verification/full_reverification_report.json").read_text(encoding="utf-8")
)

# Known categories from manual inspection of snippets
PDF_SOURCES = {
    "Adalimumab", "Benralizumab", "Bevacizumab", "Brentuximab", "Burosumab",
    "Enfortumab", "Erenumab", "Galcanezumab", "Infliximab", "Olaratumab",
    "Ranibizumab", "Risankizumab", "Sarilumab", "Satralizumab",
}

WRONG_PMID = {
    # PMID returned a completely unrelated paper
    "Abciximab":   ("15987447", "COX-2 inhibitor paper, unrelated to abciximab ADA"),
    "Belantamab":  ("31711027", "porous carbon materials paper, completely unrelated"),
    "Cadonilimab": ("34807181", "metal mirror manufacturing paper, completely unrelated"),
    "Golimumab":   ("23089571", "polycystic ovary syndrome adolescents paper, completely unrelated"),
    "Lecanemab":   ("38932388", "mRNA vaccine for Alzheimer's paper, not lecanemab clinical ADA data"),
    "Nirsevimab":  ("39572535", "broadly neutralizing antibody paper, not nirsevimab ADA incidence data"),
    "Naxitamab":   ("39177945", "omalizumab for anti-GD2 urticaria - tangentially related but not naxitamab ADA incidence"),
}

print("=== CATEGORIZATION OF NOT_FOUND ENTRIES ===\n")

results = {r["antibody_name"]: r for r in report["results"]}
not_found = [r for r in report["results"] if r["verdict"] == "not_found"]

pdf_group = []
wrong_pmid_group = []
right_drug_fulltext_group = []

for r in sorted(not_found, key=lambda x: x["antibody_name"]):
    name = r["antibody_name"]
    snip = r.get("text_snippet", "")
    src = r.get("source_tried", "")
    
    if name in PDF_SOURCES:
        pdf_group.append(r)
    elif name in WRONG_PMID:
        wrong_pmid_group.append(r)
    else:
        right_drug_fulltext_group.append(r)

print(f"A) PDF sources (binary, unparseable) — {len(pdf_group)} entries")
print("   These reference real FDA/EMA labels but we got binary PDF")
for r in pdf_group:
    print(f"   {r['antibody_name']:30s}  pcts={r['claimed_pcts']}  src={str(r.get('source_tried',''))[:55]}")

print()
print(f"B) Wrong PMID (paper unrelated to antibody ADA) — {len(wrong_pmid_group)} entries")
print("   CRITICAL: These PMIDs point to completely different studies")
for r in wrong_pmid_group:
    name = r["antibody_name"]
    pmid, reason = WRONG_PMID[name]
    snip = r.get("text_snippet","")[:80]
    print(f"   {name:30s}  PMID {pmid}")
    print(f"   REASON: {reason}")
    print(f"   SNIP: {snip}")
    print()

print(f"C) Right drug, % likely in full text not abstract — {len(right_drug_fulltext_group)} entries")
print("   Drug name matches source but ADA % not in fetched text")
for r in right_drug_fulltext_group:
    snip = r.get("text_snippet","")[:80]
    print(f"   {r['antibody_name']:30s}  pcts={r['claimed_pcts']}")
    print(f"   snip: {snip}")
    print()

print("\n=== FETCH_FAILED (all 403 Tier-B) ===")
fetch_failed = [r for r in report["results"] if r["verdict"] == "fetch_failed"]
print(f"Total: {len(fetch_failed)} entries — all paywalled/blocked URLs, all Tier B")
for r in sorted(fetch_failed, key=lambda x: x["antibody_name"]):
    print(f"  {r['antibody_name']:30s}  pcts={r['claimed_pcts']}")
