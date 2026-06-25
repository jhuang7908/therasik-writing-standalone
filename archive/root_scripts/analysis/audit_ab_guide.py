import re
from collections import Counter

html = open('therasik-web-source/Therasik_Antibody_Guide.html', encoding='utf-8').read()

fc_ids = re.findall(r"{id:'(fc\d+[a-z]?)',", html)
print(f"Fc entries in JS: {len(fc_ids)} — IDs: {fc_ids}")

all_cats = re.findall(r"cat:'([^']+)'", html)
print(f"\nCategories ({len(all_cats)} total):\n  " + '\n  '.join(f"{v:3d}x {k}" for k,v in Counter(all_cats).most_common()))

# Check what fields each entry has
entry_pattern = re.compile(r"\{id:'(fc\d+[a-z]?)',.*?(?=\{id:'|//\s*──|$)", re.DOTALL)
sample = entry_pattern.search(html)
if sample:
    print(f"\nSample entry keys:")
    fields = re.findall(r"(\w+):", sample.group())
    print(f"  {set(fields)}")
