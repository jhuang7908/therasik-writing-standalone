import json

with open('data/germlines/fc_aa/cat_scaffold_cmc_optimization_tier1_tier2_v1.json') as f:
    d = json.load(f)

vhs = [r for r in d['rows'] if r['chain'] == 'VH']
vhs.sort(key=lambda x: (
    x['cmc_full']['summary']['total_flags'],
    x.get('cmc_full',{}).get('metrics',{}).get('instability_index', 100)
))

print('Top 5 Cat VH Scaffolds by Developability (CMC):')
for i, v in enumerate(vhs[:5]):
    flags = v['cmc_full']['summary']['total_flags']
    inst = v.get('cmc_full',{}).get('metrics',{}).get('instability_index', 100)
    pi = v.get('cmc_full',{}).get('metrics',{}).get('pI', 0)
    print(f"{i+1}. {v['gene']} | Flags: {flags} | Inst: {float(inst):.1f} | pI: {float(pi):.2f}")

print('\nTop 5 Cat VL Scaffolds by Developability (CMC):')
vls = [r for r in d['rows'] if r['chain'] == 'VL']
vls.sort(key=lambda x: (
    x['cmc_full']['summary']['total_flags'],
    x.get('cmc_full',{}).get('metrics',{}).get('instability_index', 100)
))
for i, v in enumerate(vls[:5]):
    flags = v['cmc_full']['summary']['total_flags']
    inst = v.get('cmc_full',{}).get('metrics',{}).get('instability_index', 100)
    pi = v.get('cmc_full',{}).get('metrics',{}).get('pI', 0)
    print(f"{i+1}. {v['gene']} | Flags: {flags} | Inst: {float(inst):.1f} | pI: {float(pi):.2f}")
