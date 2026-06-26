import json, sys
VALID = set('ACDEFGHIKLMNPQRSTVWY')
data = json.load(open('config/cart_components_registry.json', encoding='utf-8'))
lnp = [e for e in data['elements'] if e.get('subcategory') == 'LNP/mRNA Targeting Ligand']
for e in lnp:
    seq = ''.join(c for c in (e.get('sequence','') or '').upper() if c.isalpha())
    bad = sorted(set(seq) - VALID)
    status = e.get('sequence_status', '(missing)')
    field_len = e.get('length', '?')
    print(f"{e['id'][:44]:<46} len={len(seq):3}  field={str(field_len):<5}  status={status:<12}  bad={bad}")
