import requests
import json

base = 'https://write.insynbio.com'
headers = {'Content-Type': 'application/json'}

tests = [
    ('/lab/create_entry', {
        'entity': 'experiments',
        'title': 'VHH Expression Test - Batch 001',
        'body': 'Transient expression in HEK293 cells. Target: HER2-VHH.',
        'tags': ['VHH', 'Expression']
    }),
    ('/lab/create_entry', {
        'entity': 'items',
        'title': 'Anti-His Tag Antibody (HRP)',
        'body': 'Supplier: Abcam, Cat#: ab1187. Concentration: 1mg/ml.',
        'tags': ['Antibody', 'Reagent']
    }),
    ('/lab/create_entry', {
        'entity': 'resources',
        'title': 'AKTA Pure 25 Chromatography System',
        'body': 'Location: Lab 402. Status: Calibrated.',
        'tags': ['Instrument', 'Purification']
    }),
    ('/lab/save_sop', {
        'title': 'Standard VHH Purification Protocol',
        'sections': {
            'Purpose & Scope': 'Purification of His-tagged VHH from cell culture supernatant.',
            'Materials & Equipment': 'AKTA Pure, HisTrap Excel column, PBS buffer.',
            'Procedure': '1. Filter supernatant. 2. Load to column. 3. Wash with 20mM Imidazole. 4. Elute with 500mM Imidazole.'
        },
        'entity': 'experiments'
    })
]

for path, data in tests:
    try:
        r = requests.post(base + path, json=data, headers=headers, timeout=10)
        print(f'{path}: {r.status_code} {r.text}')
    except Exception as e:
        print(f'{path}: Error - {e}')
