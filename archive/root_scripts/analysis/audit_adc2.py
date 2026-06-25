import re

c = open(r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html', encoding='utf-8').read()

# Find the script section
scripts = re.findall(r'<script[^>]*>(.*?)</script>', c, re.DOTALL)
print(f'Script blocks: {len(scripts)}')
for i, s in enumerate(scripts):
    if len(s) > 100:
        print(f'\nScript {i} ({len(s):,} chars), first 200:')
        print(s[:200])
        # Count arrays/objects
        arrays = re.findall(r'\{[^}]{5,}name[^}]+\}', s)
        print(f'  Object literals with "name": {len(arrays)}')
