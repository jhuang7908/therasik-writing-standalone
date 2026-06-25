import json
lib = json.load(open('CART_LIBRARY_V3.json',encoding='utf-8'))
stubs = [(e['id'],e.get('sequence','')[:20]) for e in lib['elements'] if not e.get('sequence') or len(e.get('sequence',''))<5]
print(f"Total: {len(lib['elements'])} | Stubs: {len(stubs)}")
for s in stubs: print(f"  {s[0]}: '{s[1]}'")
