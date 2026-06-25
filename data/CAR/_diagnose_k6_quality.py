"""
Diagnose quality gaps between K6 new elements and original 200.
Check: sequence accuracy, gene_annotation, qa completeness, category consistency.
"""
import json
from pathlib import Path
from collections import defaultdict

CAR_DIR = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\CAR")
lib = json.loads((CAR_DIR / "CART_LIBRARY_V3.json").read_text(encoding="utf-8"))
elements = lib["elements"]

K6_IDS = {
    "c_Jun_OE","BATF_OE","NR4A1_DN","TOX2_DN","REGNASE1_KO_guide",
    "CCR2b","CXCR3","GPC3_scFv","PTPN2_KO_guide","CD39_KO_guide",
    "CD5_scFv_InVivo_Targeting","SleepingBeauty_SB100X",
    "DAP12_signaling","mbIL15_Armor","NKG2D_Full_CAR_NK",
    "iNKT_TCR_Va24Vb11","CD1d_Lipid_Loading_Signal",
    "FcgRI_TM_cyto_CARM","CD68_Promoter_CARM","Helios_OE",
    "HLA_E_NK_Evasion","CD47_DontEatMe","CIITA_KO_guide",
    "BCL11B_T_lineage","RUNX3_OE","BCMA_scFv_AutoImmune"
}

# Fields checked in quality assessment
FIELDS = ["sequence","regulatory_tier","usage_context","design_notes",
          "qa","clinical_trials","references","gene_annotation"]

def score_element(e):
    scores = {}
    scores["has_seq"]         = bool(e.get("sequence") and len(e.get("sequence",""))>5)
    scores["has_tier"]        = bool(e.get("regulatory_tier"))
    scores["has_usage"]       = bool(e.get("usage_context"))
    scores["has_notes"]       = len(e.get("design_notes","")) > 80
    scores["has_qa_method"]   = bool(e.get("qa",{}).get("method"))
    scores["has_qa_source"]   = bool(e.get("qa",{}).get("source"))
    scores["has_qa_gene"]     = bool(e.get("qa",{}).get("gene_symbol") or
                                     e.get("qa",{}).get("uniprot") or
                                     e.get("gene_annotation"))
    scores["has_clinical"]    = bool(e.get("clinical_trials") or e.get("references"))
    scores["has_gene_annot"]  = bool(e.get("gene_annotation"))
    total = sum(scores.values())
    return scores, total

print("="*72)
print("QUALITY COMPARISON: K6 (26 new) vs Original 200")
print("="*72)

k6_scores = []
orig_scores = []

for e in elements:
    _, total = score_element(e)
    if e["id"] in K6_IDS:
        k6_scores.append((e["id"], total, score_element(e)[0]))
    else:
        orig_scores.append((e["id"], total, score_element(e)[0]))

orig_avg = sum(s for _,s,_ in orig_scores) / len(orig_scores)
k6_avg   = sum(s for _,s,_ in k6_scores)  / len(k6_scores)

print(f"\n  Original 200 avg quality score: {orig_avg:.2f} / 9")
print(f"  K6 new 26 avg quality score:    {k6_avg:.2f} / 9")
print(f"\n  Gap: {orig_avg - k6_avg:.2f} points\n")

# Field-by-field comparison
fields = ["has_seq","has_tier","has_usage","has_notes",
          "has_qa_method","has_qa_source","has_qa_gene","has_clinical","has_gene_annot"]
print(f"  {'Field':<20} {'Orig %':>8}  {'K6 %':>8}  {'Gap':>8}")
print(f"  {'-'*20} {'-'*8}  {'-'*8}  {'-'*8}")
for f in fields:
    orig_pct = 100 * sum(1 for _,_,sc in orig_scores if sc.get(f)) / len(orig_scores)
    k6_pct   = 100 * sum(1 for _,_,sc in k6_scores   if sc.get(f)) / len(k6_scores)
    gap = k6_pct - orig_pct
    flag = " ❌" if gap < -15 else (" ⚠" if gap < -5 else " ✅")
    print(f"  {f:<20} {orig_pct:>7.0f}%  {k6_pct:>7.0f}%  {gap:>+7.0f}%{flag}")

print("\n  K6 elements with score < 6 (need fixing):")
for eid, score, sc in sorted(k6_scores, key=lambda x: x[1]):
    if score < 7:
        missing = [k for k,v in sc.items() if not v]
        print(f"    {eid:<35} score={score}  missing={missing}")

print("\n  Category consistency issues (non-standard categories in K6):")
all_cats = defaultdict(int)
for e in elements:
    all_cats[e.get("category","?")] += 1
orig_top_cats = {k for k,v in all_cats.items() if v >= 5}
k6_cats = {e.get("category") for e in elements if e["id"] in K6_IDS}
new_cats = k6_cats - orig_top_cats
print(f"    K6 introduces {len(new_cats)} fragmented new categories:")
for c in sorted(new_cats):
    print(f"    - '{c}' (count: {all_cats[c]})")

print("\n  Sequence length anomalies in K6:")
expected = {
    "BATF_OE": (160, 170, "UniProt Q16520 should be 166aa"),
    "SleepingBeauty_SB100X": (300, 400, "SB100X should be ~340aa"),
    "NR4A1_DN": (150, 200, "NR4A1 DBD+LBD ~180aa (ok)"),
    "TOX2_DN": (90, 130, "TOX2 HMG box ~105aa (ok)"),
}
idx = {e["id"]: e for e in elements}
for eid, (lo, hi, note) in expected.items():
    e = idx.get(eid)
    if e:
        l = e.get("length", 0)
        flag = "✅" if lo <= l <= hi else "❌"
        print(f"    {flag} {eid}: {l}aa (expected {lo}-{hi}) — {note}")
