import json, os

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\data'

# Check the fully annotated CAR database
car_full = json.loads(open(ROOT + r'\CAR\car_fully_annotated\CAR__v1.0.json', encoding='utf-8').read)
elements = car_full.get('elements', [])
print(f"Full annotated CAR elements: {len(elements)}")
if elements:
    e = elements[0]
    print(f"Keys: {list(e.keys)}")
    # Check sequence coverage
    seq_filled = sum(1 for e in elements if e.get('canonical_sequence') or e.get('sequence') or e.get('aa_sequence'))
    print(f"Has sequence: {seq_filled}/{len(elements)}")
    # Check evidence
    ev_filled = sum(1 for e in elements if e.get('evidence_level') and e.get('evidence_level') != '?')
    print(f"Evidence level: {ev_filled}/{len(elements)}")
    ev_vals = {}
    for e in elements:
        ev = e.get('evidence_level','?')
        ev_vals[ev] = ev_vals.get(ev,0)+1
    print(f"Evidence dist: {ev_vals}")
    # Sample
    print(f"\nSample element: {json.dumps(elements[0], ensure_ascii=False)[:500]}")

# Check actes sequences more carefully
actes = json.loads(open(ROOT + r'\actes_sequences\sequence_db.json', encoding='utf-8').read)
entries = actes.get('entries', [])
print(f"\nACTES entries: {len(entries)}")
if entries and isinstance(entries, list):
    e0 = entries[0]
    print(f"Keys: {list(e0.keys)}")
    print(f"Sample: {json.dumps(e0, ensure_ascii=False)[:400]}")
    # Check canonical_sequence
    seq_f = sum(1 for e in entries if e.get('canonical_sequence'))
    print(f"canonical_sequence filled: {seq_f}/{len(entries)}")

# Check Fc-related data
print("\n=== Fc/Atlas check ===")
for atlas in ['engineered_459_atlas', 'natural_380_atlas', 'whole_mab_chimeric_atlas']:
    d = ROOT + '\\' + atlas
    if os.path.exists(d):
        files = [f for f in os.listdir(d) if f.endswith('.csv') or f.endswith('.json')]
        print(f"{atlas}: {files[:5]}")

# Check design_rules for Fc content
rules_dir = ROOT + r'\design_rules'
if os.path.exists(rules_dir):
    print(f"\ndesign_rules: {os.listdir(rules_dir)[:10]}")
