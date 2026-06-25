import json
from pathlib import Path
lib = json.loads(Path('CART_LIBRARY_V3.json').read_text(encoding='utf-8'))
for e in lib['elements']:
    eid = e['id']
    cat = e.get('category','?')
    sub = e.get('subcategory','')[:35]
    print(f"{eid:<42} {cat:<28} {sub}")
