"""Compare VHH29 vs VHH42 CDR physchem distributions."""
import json

vhh42 = json.load(open('data/reference/CDR_physchem_VHH42_v1.json'))
vhh29 = json.load(open('data/reference/CDR_physchem_VHH29_v1.json'))

metrics_of_interest = ['length', 'gravy', 'longest_hydrophobic_run', 'net_charge_pH7',
                       'longest_charge_run', 'aromatic_fraction', 'n_glyc_motif',
                       'deamid_motif', 'isomer_motif', 'agg_motif', 'free_cys']

print(f"{'Locus':<15} {'Metric':<28} {'VHH42 (n=42)':<30} {'VHH29 (n=29)':<30}", flush=True)
print('-' * 105, flush=True)

for locus in ['vhh_cdr1', 'vhh_cdr2', 'vhh_cdr3']:
    b42 = vhh42['loci'].get(locus, {}).get('metrics', {})
    b29 = vhh29['loci'].get(locus, {}).get('metrics', {})
    for metric in metrics_of_interest:
        m42 = b42.get(metric, {})
        m29 = b29.get(metric, {})
        p50_42 = m42.get('p50', 'N/A')
        p95_42 = m42.get('p95', 'N/A')
        p50_29 = m29.get('p50', 'N/A')
        p95_29 = m29.get('p95', 'N/A')
        def fmt(p50, p95):
            if p50 == 'N/A': return 'N/A'
            return f'med={p50:.2f} p95={p95:.2f}'
        print(f'{locus:<15} {metric:<28} {fmt(p50_42, p95_42):<30} {fmt(p50_29, p95_29):<30}', flush=True)
    print('', flush=True)
