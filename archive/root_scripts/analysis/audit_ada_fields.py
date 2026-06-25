"""Compare what ADA master CSV has vs what's in the web JSON."""
import json, csv

MASTER = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\ada_master_136_curated.csv'
WEB_JSON = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\ada_db_data.json'

master_rows = list(csv.DictReader(open(MASTER, encoding='utf-8')))
web_records = json.loads(open(WEB_JSON, encoding='utf-8').read())

master_fields = set(master_rows[0].keys())
web_fields = set(web_records[0].keys()) if web_records else set()

in_master_not_web = master_fields - web_fields
in_web_not_master = web_fields - master_fields

print(f"Master CSV fields: {len(master_fields)}")
print(f"Web JSON fields:   {len(web_fields)}")
print(f"\nIn master but NOT web ({len(in_master_not_web)} fields):")
for f in sorted(in_master_not_web):
    # Show fill rate
    filled = sum(1 for r in master_rows if r.get(f) and r.get(f) not in ('','N/A','Unknown','unknown','none','None'))
    pct = 100*filled//len(master_rows)
    if pct > 20:  # only show useful fields
        print(f"  {f}: {filled}/{len(master_rows)} ({pct}%)")

print(f"\nIn web but NOT master: {sorted(in_web_not_master)}")

# Sample key fields that add quality
key_fields = ['fc_engineering','fc_effector_status','fc_mutation_notes',
              'concomitant_immuno_likely','checkpoint_inhibitor','immune_depleting',
              'ada_evidence_chain_excerpt','assay_platform','dose_mg','dose_freq',
              'approval_year','oncology_indication','immunosuppressant_context']
print("\n=== High-value missing fields ===")
for f in key_fields:
    if f in master_fields:
        filled = sum(1 for r in master_rows if r.get(f) and r.get(f) not in ('','N/A','Unknown','unknown','none','None','False','false'))
        vals = list({r.get(f) for r in master_rows if r.get(f) and r.get(f) not in ('','unknown','N/A','None','none','False')})[:5]
        print(f"  {f}: {filled}/{len(master_rows)} filled — examples: {vals}")
