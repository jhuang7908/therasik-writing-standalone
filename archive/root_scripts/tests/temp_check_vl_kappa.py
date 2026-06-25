import json

# Check VL κ resolved sites
with open('reports/mapping/pd1_6jbt_mouse_vl_kappa_dualmap.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

sites = d.get('functional_sites', {}).get('resolved_sites', {})
print('All resolved site IDs:')
for k in sorted(sites.keys()):
    print(f'  {k}')

# Check for VH/VHH sites
vh_sites = [k for k in sites.keys() if 'HALLMARK_VHH' in k or ('VH' in k.upper() and 'VL' not in k)]
print(f'\nVH/VHH sites in VL κ: {vh_sites}')

# Check for VL_LAMBDA sites
lambda_sites = [k for k in sites.keys() if 'VL_LAMBDA' in k]
print(f'VL_LAMBDA sites in VL κ: {lambda_sites}')

# Check for VL_GENERIC sites
generic_sites = [k for k in sites.keys() if 'VL_GENERIC' in k]
print(f'VL_GENERIC sites in VL κ: {len(generic_sites)} sites')
