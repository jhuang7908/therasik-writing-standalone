import json
rules = json.loads(open('data/adc_atlas/adc_design_rules.json').read())
comp = json.loads(open('data/adc_atlas/adc_components.json').read())
master = json.loads(open('data/adc_atlas/adc_master_internal.json').read())

print(f'--- Clinical Programs ({len(master)}) ---')
if master:
    p = master[0]
    print('Fields:', list(p.keys()))
    # Check if failure analysis exists for some
    failed = [m for m in master if m.get('development_stage') == 'discontinued']
    print(f'Discontinued programs: {len(failed)}')
    if failed:
        print('Sample failure analysis:', failed[0].get('failure_analysis', 'N/A'))

print('\n--- Target Antigens ---')
ag = rules['antigen_properties']
precise = [n for n, v in ag.items() if isinstance(v, dict) and v.get('internalization_mechanism') and not v.get('internalization_mechanism', '').startswith('Not specifically')]
print(f'Total: {len(ag)}')
print(f'Precisely enriched: {len(precise)}')

print('\n--- Payloads ---')
payloads = [c for c in comp if 'class' in c]
print(f'Total: {len(payloads)}')
if payloads:
    print('Fields:', [k for k in payloads[0].keys() if not k.startswith('_')])

print('\n--- Linkers ---')
linkers = [c for c in comp if 'type' in c and 'class' not in c]
print(f'Total: {len(linkers)}')
if linkers:
    print('Fields:', [k for k in linkers[0].keys() if not k.startswith('_')])

print('\n--- Conjugation Tech ---')
cj = rules['conjugation_technology']
print(f'Total: {len(cj)}')
if cj:
    sample = list(cj.values())[0]
    print('Fields:', list(sample.keys()))

print('\n--- Validation Assays ---')
ev = rules['experimental_methods']
invitro = ev.get('in_vitro', {})
invivo = ev.get('in_vivo', {})
print(f'Total: {len(invitro) + len(invivo)}')
if invitro:
    sample = list(invitro.values())[0]
    print('In vitro fields:', list(sample.keys()))
if invivo:
    sample = list(invivo.values())[0]
    print('In vivo fields:', list(sample.keys()))
