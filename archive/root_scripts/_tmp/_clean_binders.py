"""
Cleaning up 'Unknown' binder names for key ADC programs.
"""
import json, pathlib

fp = pathlib.Path('data/adc_atlas/adc_master_internal.json')
master = json.loads(fp.read_text())

binder_updates = {
    "Mersana XMT-1592": "Humanized anti-NaPi2b IgG1",
    "Mersana XMT-1536": "Humanized anti-NaPi2b IgG1",
    "Raludotatug deruxtecan": "Humanized anti-CDH6 IgG1 (DS-6000)",
    "DS-3939a": "Humanized anti-MUC1 IgG1",
    "Kelun-Biotech SKB315": "Humanized anti-CLDN18.2 IgG1",
    "Hengrui SHR-A1904": "Humanized anti-CLDN18.2 IgG1",
    "Lepu Biopharma MRG002": "Humanized anti-HER2 IgG1",
    "Ambrx ARX517": "Humanized anti-PSMA IgG1",
    "Lepu Biopharma MRG003": "Humanized anti-EGFR IgG1",
    "AstraZeneca AZD0901": "Humanized anti-CLDN18.2 IgG1",
    "RemeGen RC118": "Humanized anti-CLDN18.2 IgG1",
    "LaNova LM-302": "Humanized anti-CLDN18.2 IgG1"
}

updated = 0
for p in master:
    name = p.get('canonical_name')
    if name in binder_updates:
        p['binder_name'] = binder_updates[name]
        updated += 1

fp.write_text(json.dumps(master, indent=2, ensure_ascii=False))
print(f'Updated {updated} binder names.')
