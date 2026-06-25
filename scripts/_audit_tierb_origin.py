import json, pathlib

blob  = json.loads(pathlib.Path("data/ADA_reliable_package/clinical_db/clinical_ada_db_data.json").read_text(encoding="utf-8"))
records = blob["records"]

conf  = json.loads(pathlib.Path("data/ADA_reliable_package/final_three_files/confirmed_ada.json").read_text(encoding="utf-8"))
nft   = json.loads(pathlib.Path("data/ADA_reliable_package/final_three_files/need_fulltext.json").read_text(encoding="utf-8"))

all_entries = conf["entries"] + nft["entries"]
tierb = [e for e in all_entries if e.get("class_evidence_tier") == "B"]
tiera = [e for e in all_entries if e.get("class_evidence_tier") == "A"]

print(f"Tier A: {len(tiera)}  |  Tier B: {len(tierb)}")
print()

# Count evidence_source patterns in Tier B
from collections import Counter
src_counter = Counter(e.get("evidence_source","") for e in tierb)
extr_counter = Counter(e.get("ada_value_extraction","") for e in tierb)

print("=== Tier B evidence_source breakdown ===")
for k, v in src_counter.most_common():
    print(f"  {repr(k)}: {v}")

print()
print("=== Tier B ada_value_extraction breakdown ===")
for k, v in extr_counter.most_common():
    print(f"  {repr(k)}: {v}")

print()
print("=== Sample Tier B entries — full origin trace ===")
for e in tierb[:8]:
    name  = e["antibody_name"]
    pr    = records.get(name.lower(), {})
    chain = pr.get("evidence_chain", "")
    print(f"--- {name}")
    print(f"  evidence_source:      {e.get('evidence_source')}")
    print(f"  source_type:          {e.get('source_type')}")
    print(f"  ada_value_extraction: {e.get('ada_value_extraction')}")
    print(f"  tier_rationale:       {e.get('tier_rationale')}")
    print(f"  citation_urls:        {str(e.get('citation_urls'))[:100]}")
    print(f"  verification_status:  {e.get('verification_status')}")
    # Show who generated the chain
    if "" in (chain[:50]):
        print(f"  chain header: AI-batch generated")
    elif chain:
        print(f"  chain[0:80]: {chain[:80]}")
    print()
