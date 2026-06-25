"""Audit knowledge bases — fixed version."""
import re, json, os

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source'

# ── ADC database (HTML-embedded) ──────────────────────────────────
print("=" * 60)
print("ADC DATABASE (HTML)")
c = open(os.path.join(ROOT, 'Therasik_ADC_Database.html'), encoding='utf-8').read
# Structure: each ADC is a section with <h2> or specific class
sections = re.findall(r'<div[^>]+class="[^"]*adc-card[^"]*"', c)
drug_names = re.findall(r'<strong>([A-Za-z][a-zA-Z0-9\-]+(?:mab|zumab|ximab|umab)[^<]*)</strong>', c)
linkers = re.findall(r'(?:Linker|)[^:：]*[：:]\s*([^\n<]{5,50})', c)
payloads = re.findall(r'(?:Payload|)[^:：]*[：:]\s*([^\n<]{5,50})', c)
phase_lines = re.findall(r'Phase\s*[123IViv]+[^\n<]*', c)
approved_drugs = re.findall(r'(T-DM1|Kadcyla|Enhertu|Trodelvy|Adcetris|Padcev|Polivy|Zynlonta|Blenrep|Akalux)', c)
print(f"Phase mentions: {len(phase_lines)}, approved drug names found: {len(set(approved_drugs))}: {set(approved_drugs)}")
# Count by section headings
h2s = re.findall(r'<h2[^>]*>([^<]{3,80})</h2>', c)
print(f"H2 section count: {len(h2s)}, first 5: {h2s[:5]}")
# count unique drug/mab names
mab_names = re.findall(r'\b([A-Za-z]+(?:mab|zumab|ximab|umab|nib))\b', c)
uniq_mabs = set(m.lower for m in mab_names if len(m)>6)
print(f"Unique drug names (-mab/-nib): {len(uniq_mabs)}, sample: {sorted(uniq_mabs)[:15]}")

# ── ADA database ──────────────────────────────────────────────────
print("\n" + "=" * 60)
print("ADA DATABASE")
ada = json.loads(open(os.path.join(ROOT, 'ada_db_data.json'), encoding='utf-8').read)
print(f"Records: {len(ada)}")
tiers = {}
origins = {}
diseases = {}
for r in ada:
    tiers[r.get('tier','?')] = tiers.get(r.get('tier','?'),0)+1
    origins[r.get('origin','?')] = origins.get(r.get('origin','?'),0)+1
    diseases[r.get('disease_class','?')] = diseases.get(r.get('disease_class','?'),0)+1
print(f"Tier A/B: {tiers}")
print(f"Origin: {origins}")
print(f"Disease classes: {dict(sorted(diseases.items, key=lambda x:-x[1]))}")
# ADA range
ada_pcts = [r['ada_pct'] for r in ada if r.get('ada_pct') is not None]
print(f"ADA % range: {min(ada_pcts):.1f}–{max(ada_pcts):.1f}%, median: {sorted(ada_pcts)[len(ada_pcts)//2]:.1f}%")
# Check missing fields
for field in ['assay_gen','half_life','hydrophilic_frac','tcia_risk','vh_germline']:
    missing = sum(1 for r in ada if not r.get(field))
    print(f"  {field}: {missing} missing ({100*missing//len(ada)}%)")

# ── CAR component library ─────────────────────────────────────────
print("\n" + "=" * 60)
print("CAR COMPONENT LIBRARY")
raw = open(os.path.join(ROOT, 'component_library_public.json'), encoding='utf-8').read
comp_data = json.loads(raw)
# Handle both list and dict
if isinstance(comp_data, list):
    comps = comp_data
elif isinstance(comp_data, dict):
    comps = []
    for v in comp_data.values:
        if isinstance(v, list):
            comps.extend(v)
print(f"Total entries (raw JSON): {len(comp_data) if isinstance(comp_data,list) else 'dict'}")
print(f"Keys in JSON: {list(comp_data.keys) if isinstance(comp_data,dict) else 'list'}")
if isinstance(comp_data, dict):
    for k,v in comp_data.items:
        if isinstance(v,list): print(f"  {k}: {len(v)} entries")
        elif isinstance(v,dict): print(f"  {k}: dict with {len(v)} keys")

# Count from HTML instead
c_car = open(os.path.join(ROOT, 'Therasik_Component_Browser.html'), encoding='utf-8').read
comp_divs = re.findall(r'"component-card"', c_car)
print(f"Component cards in HTML: {len(comp_divs)}")
cats_car = re.findall(r'"type"\s*:\s*"([^"]+)"', c_car)
cat_counts = {}
for cat in cats_car:
    cat_counts[cat] = cat_counts.get(cat,0)+1
print(f"Component types: {dict(sorted(cat_counts.items, key=lambda x:-x[1]))}")

# ── Vaccine KB ────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("VACCINE KB")
vac = json.loads(open(os.path.join(ROOT, 'vaccine_kb_data.json'), encoding='utf-8').read)
if isinstance(vac, dict):
    print(f"Top-level keys: {list(vac.keys)}")
    for k, v in vac.items:
        if isinstance(v, list): print(f"  {k}: {len(v)} records")

# ── Antibody Guide ────────────────────────────────────────────────
print("\n" + "=" * 60)
print("ANTIBODY GUIDE")
c_ab = open(os.path.join(ROOT, 'Therasik_Antibody_Guide.html'), encoding='utf-8').read
tabs = re.findall(r'data-tab="([^"]+)"', c_ab)
print(f"Tabs: {tabs}")
trs = re.findall(r'<tr>', c_ab)
print(f"Table rows total: {len(trs)}")
