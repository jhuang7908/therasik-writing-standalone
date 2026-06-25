import re, json

c = open(r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html', encoding='utf-8').read()

# Find JS programs array
m = re.search(r'const programs\s*=\s*(\[.*?\]);', c, re.DOTALL)
if m:
    data = json.loads(m.group(1))
    print(f'Programs: {len(data)}')
    stages = {}
    for d in data:
        s = d.get('stage','?')
        stages[s] = stages.get(s,0)+1
    print(f'Stages: {dict(sorted(stages.items()))}')
    print(f'Keys: {list(data[0].keys())}')
    # Check field completeness
    for field in ['name','target','payload','linker','conjugation','DAR','company','nct','ref_pmid']:
        filled = sum(1 for d in data if d.get(field) not in (None,'','N/A','Unknown','-','unknown'))
        print(f'  {field}: {filled}/{len(data)} ({100*filled//len(data)}%)')
else:
    print('programs array not found')
    # Find any big array
    arrays = re.findall(r'const \w+\s*=\s*\[', c)
    print(f'Array declarations: {arrays}')
    # Check card-based
    pc = re.findall(r'class="program-card"', c)
    print(f'program-card: {len(pc)}')
    # size
    print(f'File size: {len(c):,}')
