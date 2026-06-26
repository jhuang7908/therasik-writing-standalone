"""Fix length fields for LNP targeting entries and remove OKT8 duplicate."""
import json, re

path = 'config/cart_components_registry.json'
data = json.load(open(path, encoding='utf-8'))

VALID = set('ACDEFGHIKLMNPQRSTVWY')
REMOVE_ID = 'OKT8_hu_scFv'   # duplicate of CD8_OKT8_LNP_Targeting_Alias

fixed = 0
removed = []
new_elements = []
for e in data['elements']:
    if e.get('id') == REMOVE_ID:
        removed.append(e['id'])
        continue
    if e.get('subcategory') == 'LNP/mRNA Targeting Ligand':
        seq = ''.join(c for c in (e.get('sequence','') or '').upper() if c.isalpha())
        actual = len(seq)
        if e.get('length') != actual:
            print(f"Fixing {e['id']}: {e.get('length')} -> {actual}")
            e['length'] = actual
            fixed += 1
    new_elements.append(e)

data['elements'] = new_elements
with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print(f"\nDone: {fixed} lengths fixed, removed: {removed}")
