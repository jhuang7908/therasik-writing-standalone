"""Deep audit: CAR categories + Vaccine + ADC stage breakdown."""
import re, json

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source'

# ADC stage distribution
c = open(ROOT + r'\Therasik_ADC_Database.html', encoding='utf-8').read()
stages = re.findall(r'data-stage="([^"]+)"', c)
stage_dist = {}
for s in stages: stage_dist[s] = stage_dist.get(s,0)+1
print("ADC stages:", dict(sorted(stage_dist.items())))
print(f"ADC total: {len(stages)}")

# CAR components breakdown
comp = json.loads(open(ROOT + r'\component_library_public.json', encoding='utf-8').read())
elements = comp.get('elements',[])
print(f"\nCAR elements: {len(elements)}")
if elements and isinstance(elements[0], dict):
    types = {}
    ev_levels = {}
    seq_filled = 0
    for e in elements:
        t = e.get('type', e.get('category','?'))
        types[t] = types.get(t,0)+1
        ev = e.get('evidence_level', e.get('evidence','?'))
        ev_levels[ev] = ev_levels.get(ev,0)+1
        if e.get('sequence'): seq_filled += 1
    print("Types:", dict(sorted(types.items(), key=lambda x:-x[1])))
    print("Evidence levels:", dict(sorted(ev_levels.items())))
    print(f"Sequence filled: {seq_filled}/{len(elements)}")
    # Sample entry
    print("Sample keys:", list(elements[0].keys()))

# Vaccine KB detail
vac = json.loads(open(ROOT + r'\vaccine_kb_data.json', encoding='utf-8').read())
print("\nVaccine KB breakdown:")
for k, v in vac.items():
    if k.startswith('_'): continue
    if isinstance(v, list) and v:
        if isinstance(v[0], dict):
            fields = list(v[0].keys())
            # count field completeness
            print(f"  {k} ({len(v)} records): fields={fields[:6]}")
            for f in fields[:4]:
                filled = sum(1 for r in v if r.get(f))
                print(f"    {f}: {filled}/{len(v)}")
