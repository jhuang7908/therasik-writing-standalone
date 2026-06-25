import json, os

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data'

# Main ACTES sequence database
d = json.loads(open(ROOT + r'\actes_sequences\sequence_db.json', encoding='utf-8').read())
entries = d.get('entries', [])
print(f"ACTES sequence_db entries: {len(entries)}")
if entries:
    sample = entries[0] if isinstance(entries, list) else list(entries.values())[0]
    print(f"Sample keys: {list(sample.keys())[:10]}")
    # Count seq-filled
    if isinstance(entries, list):
        seq_filled = sum(1 for e in entries if e.get('sequence') or e.get('aa_sequence') or e.get('nt_sequence'))
        print(f"Has sequence: {seq_filled}/{len(entries)}")
        types = {}
        for e in entries:
            t = e.get('type', e.get('category', e.get('domain_type', '?')))
            types[t] = types.get(t,0)+1
        print(f"Types: {dict(sorted(types.items(), key=lambda x:-x[1]))}")
    elif isinstance(entries, dict):
        seq_filled = sum(1 for e in entries.values() if e.get('sequence') or e.get('aa_sequence'))
        print(f"Has sequence: {seq_filled}/{len(entries)}")

# Check CAR car_fully_annotated
car_dir = ROOT + r'\CAR\car_fully_annotated'
if os.path.exists(car_dir):
    files = os.listdir(car_dir)
    print(f"\ncar_fully_annotated files: {len(files)}, types: {set(f.split('.')[-1] for f in files)}")
    # Check one JSON
    jsons = [f for f in files if f.endswith('.json')]
    if jsons:
        d2 = json.loads(open(os.path.join(car_dir, jsons[0]), encoding='utf-8').read())
        if isinstance(d2, list):
            print(f"  {jsons[0]}: {len(d2)} records, keys: {list(d2[0].keys())[:8] if d2 else []}")
        elif isinstance(d2, dict):
            print(f"  {jsons[0]}: dict keys: {list(d2.keys())[:8]}")

# Check main component library that powers the website
pub_lib = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\component_library_public.json'
pub = json.loads(open(pub_lib, encoding='utf-8').read())
elements = pub.get('elements', [])
print(f"\nPublic component lib: {len(elements)} elements")
# Sample with more detail
if elements:
    e = elements[0]
    print(f"First element keys: {list(e.keys())}")
    print(f"First element: {json.dumps(e, ensure_ascii=False)[:300]}")
