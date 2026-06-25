"""Audit all knowledge bases for content, authenticity, and coverage."""
import re, json, os

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source'

# ── ADC database ──────────────────────────────────────────────────
print("=" * 60)
print("ADC DATABASE")
c = open(os.path.join(ROOT, 'Therasik_ADC_Database.html'), encoding='utf-8').read
cards = re.findall(r'class="drug-card"', c)
h3s = re.findall(r'<h3[^>]*>([^<]{2,60})</h3>', c)
phases = re.findall(r'Phase\s*(I{1,3}V?|1|2|3|4)\b', c)
approved = re.findall(r'(FDA[- ]?Approved|EMA[- ]?Approved||Approved)', c, re.I)
targets = re.findall(r'Target[^:]*:\s*([A-Z][A-Z0-9\-]+)', c)
print(f"Drug cards: {len(cards)}")
print(f"H3 headings (drugs): {len(h3s)}, first 8: {h3s[:8]}")
print(f"Phase mentions: {len(phases)}, sample: {phases[:10]}")
print(f"Approved mentions: {len(approved)}")

# ── ADA database ──────────────────────────────────────────────────
print("\n" + "=" * 60)
print("ADA DATABASE")
ada_json = json.loads(open(os.path.join(ROOT, 'ada_db_data.json'), encoding='utf-8').read)
print(f"Records: {len(ada_json)}")
tiers = {}
for r in ada_json:
    t = r.get('tier','?')
    tiers[t] = tiers.get(t,0)+1
print(f"Tier breakdown: {dict(sorted(tiers.items))}")
# Check field completeness
fields = ['name','origin','ada_pct','disease_class','tier','mhcii_net_clusters','route','fc_isotype','moa_class']
for f in fields:
    filled = sum(1 for r in ada_json if r.get(f) not in (None,'',[],'Unknown','unknown'))
    print(f"  {f}: {filled}/{len(ada_json)} ({100*filled//len(ada_json)}%)")

# ── CAR component library ─────────────────────────────────────────
print("\n" + "=" * 60)
print("CAR COMPONENT LIBRARY")
comp_json = json.loads(open(os.path.join(ROOT, 'component_library_public.json'), encoding='utf-8').read)
print(f"Total components: {len(comp_json)}")
cats = {}
for item in comp_json:
    cat = item.get('category', item.get('type','?'))
    cats[cat] = cats.get(cat,0)+1
print(f"Categories: {dict(sorted(cats.items))}")
# Check completeness of key fields
fields_car = ['name','category','target','evidence_level','sequence']
for f in fields_car:
    filled = sum(1 for r in comp_json if r.get(f) not in (None,'',[],'Unknown'))
    print(f"  {f}: {filled}/{len(comp_json)} ({100*filled//len(comp_json)}%)")

# ── Vaccine KB ────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("VACCINE KB")
vac_json = json.loads(open(os.path.join(ROOT, 'vaccine_kb_data.json'), encoding='utf-8').read)
# It might be a dict with sections
if isinstance(vac_json, dict):
    print(f"Sections: {list(vac_json.keys)}")
    for k, v in vac_json.items:
        if isinstance(v, list):
            print(f"  {k}: {len(v)} records")
elif isinstance(vac_json, list):
    print(f"Records: {len(vac_json)}")

# ── Antibody Guide ────────────────────────────────────────────────
print("\n" + "=" * 60)
print("ANTIBODY GUIDE")
c = open(os.path.join(ROOT, 'Therasik_Antibody_Guide.html'), encoding='utf-8').read
tabs = re.findall(r'data-tab="([^"]+)"', c)
tables = re.findall(r'<table', c)
rows = re.findall(r'<tr', c)
print(f"Tabs: {tabs}")
print(f"Tables: {len(tables)}, Total rows: {len(rows)}")
# Count Fc mutations
fc_muts = re.findall(r'[A-Z]\d+[A-Z]', c)
print(f"Fc mutation notations found: {len(set(fc_muts))}, sample: {list(set(fc_muts))[:12]}")
