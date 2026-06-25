"""Comprehensive audit of all CAR-T library sources and their current status."""
import json
from pathlib import Path

AES_ROOT = Path(r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite")

files = {
    "functional_domains": AES_ROOT / "ACTES_CART_Engine_v1.0/resources/functional_domains.json",
    "sequence_db":        AES_ROOT / "data/actes_sequences/sequence_db.json",
    "kb_v2":              AES_ROOT / "data/CAR/CAR_KNOWLEDGE_BASE_V2.json",
    "old_L1_clinical":    AES_ROOT / "data/CAR/car_integrated_results/CAR__1_.json",
}

# ── 1. functional_domains.json audit ─────────────────────────────
with open(files["functional_domains"], encoding="utf-8") as f:
    fd = json.load(f)

print("="*65)
print("1. functional_domains.json  (ACTES primary design file)")
print("="*65)

def is_data_node(v):
    return isinstance(v, dict) and ("seq" in v or "components" in v)

stats = {}
seq_present = 0
seq_missing = 0
qa_present = 0

def walk(obj, depth=0, category=""):
    global seq_present, seq_missing, qa_present
    if not isinstance(obj, dict):
        return
    for k, v in obj.items:
        if k.startswith("_"):
            continue
        if isinstance(v, dict):
            if "seq" in v:
                has_seq = bool(v["seq"])
                has_qa  = "qa" in v and bool(v.get("qa",{}).get("source",""))
                seq_present += (1 if has_seq else 0)
                seq_missing += (0 if has_seq else 1)
                qa_present  += (1 if has_qa else 0)
            else:
                walk(v, depth+1, category or k)

for cat, items in fd.items:
    if cat.startswith("_"): continue
    n_entries = sum(1 for k in items if not k.startswith("_"))
    
    # Count leaf seq nodes within this category
    n_seq_ok = 0
    n_seq_miss = 0
    def count_seqs(obj):
        global n_seq_ok, n_seq_miss
        if isinstance(obj, dict):
            if "seq" in obj:
                if obj["seq"]: n_seq_ok += 1
                else:          n_seq_miss += 1
            for v in obj.values:
                count_seqs(v)
    n_seq_ok = 0; n_seq_miss = 0
    count_seqs(items)
    stats[cat] = {"entries": n_entries, "seq_ok": n_seq_ok, "seq_missing": n_seq_miss}

total_entries = sum(v["entries"] for v in stats.values)
total_seq_ok  = sum(v["seq_ok"] for v in stats.values)
total_missing = sum(v["seq_missing"] for v in stats.values)

print(f"\n{'Category':<30} {'Entries':>7} {'Seq✓':>6} {'Seq?':>6}")
print("-"*52)
for cat, s in sorted(stats.items, key=lambda x: -x[1]["entries"]):
    print(f"  {cat:<28} {s['entries']:>7} {s['seq_ok']:>6} {s['seq_missing']:>6}")
print("-"*52)
print(f"  {'TOTAL':<28} {total_entries:>7} {total_seq_ok:>6} {total_missing:>6}")

# ── 2. sequence_db.json audit ─────────────────────────────────────
with open(files["sequence_db"], encoding="utf-8") as f:
    sdb = json.load(f)
entries = sdb["entries"]
with_seq  = [e for e in entries if e.get("canonical_sequence","")]
with_uni  = [e for e in entries if e.get("design_info",{}).get("uniprot_id")]
with_range= [e for e in entries if e.get("design_info",{}).get("residue_range")]

print(f"\n{'='*65}")
print("2. sequence_db.json  (ACTES sequence registry)")
print(f"{'='*65}")
print(f"  Total entries:    {len(entries)}")
print(f"  With sequence:    {len(with_seq)} ({100*len(with_seq)//len(entries)}%)")
print(f"  With UniProt ID:  {len(with_uni)} ({100*len(with_uni)//len(entries)}%)")
print(f"  Residue ranges:   {len(with_range)} ({100*len(with_range)//len(entries)}%)")
print(f"  Seq-less (stubs): {len(entries)-len(with_seq)}")

# ── 3. CAR_KNOWLEDGE_BASE_V2 audit ────────────────────────────────
with open(files["kb_v2"], encoding="utf-8") as f:
    kb2 = json.load(f)
elems = kb2.get("elements", [])
kb_cats = {}
for e in elems:
    c = e.get("category","")
    kb_cats.setdefault(c, []).append(e)

print(f"\n{'='*65}")
print("3. CAR_KNOWLEDGE_BASE_V2.json  (deeply verified 26-element set)")
print(f"{'='*65}")
for cat, es in sorted(kb_cats.items):
    print(f"  {cat:<25}: {len(es)} elements")
print(f"  {'TOTAL':<25}: {len(elems)}")
verified = [e for e in elems if e.get("qa_status","").lower.startswith("verified")]
print(f"  Verified:             {len(verified)}/{len(elems)}")
print(f"  Avg sequence length:  {sum(len(e.get('sequence','')) for e in elems)//max(len(elems),1)} aa")

# ── 4. Tier classification check ─────────────────────────────────
print(f"\n{'='*65}")
print("4. Tier classification (Clinical Approved / Trial / Research)")
print(f"{'='*65}")
has_tier = sum(1 for e in elems if "tier" in e or "approval_status" in e or "clinical_status" in e)
print(f"  Elements with tier field: {has_tier}/{len(elems)}")
if has_tier == 0:
    print("  ⚠️  NO tier classification field currently in any source library.")
    print("  → Requires new 'regulatory_tier' field to be added.")

# ── 5. Cross-library overlap ──────────────────────────────────────
print(f"\n{'='*65}")
print("5. Cross-library merge status")
print(f"{'='*65}")
kb2_ids  = set(e.get("id","") for e in elems)
fd_ids   = set
for cat, items in fd.items:
    if cat.startswith("_"): continue
    for k, v in items.items:
        if not k.startswith("_"): fd_ids.add(k)
sdb_ids  = set(e["entry_id"] for e in entries)

print(f"  KB_V2 element IDs:         {len(kb2_ids)}")
print(f"  functional_domains IDs:    {len(fd_ids)}")
print(f"  sequence_db entry IDs:     {len(sdb_ids)}")

overlap_fd_sdb  = fd_ids & sdb_ids
overlap_kb2_sdb = kb2_ids & sdb_ids
print(f"  FD ∩ SeqDB overlap:        {len(overlap_fd_sdb)} items")
print(f"  KB_V2 ∩ SeqDB overlap:     {len(overlap_kb2_sdb)} items")
print(f"  Three-way unified IDs:     ~{len(fd_ids | sdb_ids | kb2_ids)}")

print(f"\n{'='*65}")
print("6. Old data/CAR AI-generated library (errors found)")
print(f"{'='*65}")
try:
    with open(files["old_L1_clinical"], encoding="utf-8") as f:
        old = json.load(f)
    old_elems = old.get("elements", [])
    PLACEHOLDER = "MGSSHHHHHHSSGLVPRGSHMASMTGGQQMGRDLYDDDDKDRWGS"
    placeholders = [e for e in old_elems if e.get("sequence","") == PLACEHOLDER]
    empty        = [e for e in old_elems if not e.get("sequence","")]
    real_seqs    = [e for e in old_elems if e.get("sequence","") and e.get("sequence","") != PLACEHOLDER]
    print(f"  Total elements (old):      {len(old_elems)}")
    print(f"  His-tag placeholder:       {len(placeholders)}")
    print(f"  Empty sequence:            {len(empty)}")
    print(f"  'Real' sequences:          {len(real_seqs)}")
    print(f"  ❌ Original data NOT merged into new library (replaced, not merged).")
except Exception as e:
    print(f"  (Could not read old file: {e})")

print(f"\n{'='*65}")
print("SUMMARY: InSynBio ACTES vs Website (insynbio.com) comparison")
print(f"{'='*65}")
