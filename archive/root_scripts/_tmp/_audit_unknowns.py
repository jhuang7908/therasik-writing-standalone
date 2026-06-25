import json
from pathlib import Path

def count_unknowns(data, fields_to_check):
    unknown_count = 0
    total_entries = 0
    
    if isinstance(data, list):
        total_entries = len(data)
        for entry in data:
            for field in fields_to_check:
                val = entry.get(field)
                if val is None or (isinstance(val, str) and val.lower() == 'unknown'):
                    unknown_count += 1
    elif isinstance(data, dict):
        total_entries = len(data)
        for key, entry in data.items():
            if not isinstance(entry, dict): continue
            for field in fields_to_check:
                val = entry.get(field)
                if val is None or (isinstance(val, str) and val.lower() == 'unknown'):
                    unknown_count += 1
    return unknown_count, total_entries

# Load files
master_path = Path('data/adc_atlas/adc_master_internal.json')
rules_path = Path('data/adc_atlas/adc_design_rules.json')
comp_path = Path('data/adc_atlas/adc_components.json')

master = json.loads(master_path.read_text(encoding='utf-8'))
rules = json.loads(rules_path.read_text(encoding='utf-8'))
comp = json.loads(comp_path.read_text(encoding='utf-8'))

print("=== ADC Knowledge Base 'Unknown' Audit ===")

# 1. Clinical Programs
fields = ['payload_name', 'linker_name', 'dar_mean', 'binder_name', 'target']
u, t = count_unknowns(master, fields)
print(f"Clinical Programs ({t} total):")
print(f"  - Unknowns in core fields: {u}")
# Specific check for programs with ANY unknown in these fields
any_u = 0
for p in master:
    if any(str(p.get(f)).lower() == 'unknown' for f in fields):
        any_u += 1
print(f"  - Programs with at least one unknown: {any_u}")

# 2. Target Antigens
ag = rules['antigen_properties']
ag_fields = ['internalization_mechanism', 'shedding_rate', 'biomarker_assay']
u_ag = 0
t_ag = 0
for name, props in ag.items():
    if name.startswith('_') or not isinstance(props, dict): continue
    t_ag += 1
    for f in ag_fields:
        val = props.get(f, '')
        if not val or 'unknown' in str(val).lower() or str(val).startswith('Not specifically'):
            u_ag += 1
print(f"\nTarget Antigens ({t_ag} total):")
print(f"  - Unknown/Generic mechanistic fields: {u_ag}")
precise = [n for n, p in ag.items() if isinstance(p, dict) and p.get('internalization_mechanism') and not p.get('internalization_mechanism', '').startswith('Not specifically')]
print(f"  - Precisely enriched antigens: {len(precise)}")
print(f"  - Remaining generic/unknown antigens: {t_ag - len(precise)}")

# 3. Payloads & Linkers
payloads = [c for c in comp if 'class' in c]
linkers = [c for c in comp if 'type' in c and 'class' not in c]

p_fields = ['ic50_nm', 'dlts', 'optimal_dar_range', 'log_p']
u_p, t_p = count_unknowns(payloads, p_fields)
print(f"\nPayload Molecules ({t_p} total):")
print(f"  - Unknowns in quantitative fields: {u_p}")

l_fields = ['plasma_t12', 'cleavage_enzyme', 'tumor_cleavage_efficiency']
u_l, t_l = count_unknowns(linkers, l_fields)
print(f"\nLinker Chemistry ({t_l} total):")
print(f"  - Unknowns in stability/cleavage fields: {u_l}")

# 4. Conjugation & Assays
cj = rules['conjugation_technology']
u_cj, t_cj = count_unknowns(cj, ['platform_name', 'cmc_detail', 'fto_detail'])
print(f"\nConjugation Tech ({t_cj} total):")
print(f"  - Unknowns in platform/CMC/FTO: {u_cj}")

print("\nAudit Complete.")
