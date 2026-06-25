
import sys
import os

path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'
if not os.path.exists(path):
    print(f"File not found: {path}")
    sys.exit(1)

with open(path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'id="panel-' in line:
            print(f"{i+1}: {line.strip()}")
