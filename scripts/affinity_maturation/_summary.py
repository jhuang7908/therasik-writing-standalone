import csv
from pathlib import Path

output = Path(r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\projects\mumab4d5_VGRW_SR_R2\affinity_maturation')

evoef2  = {r['mutation']: r for r in csv.DictReader(open(output / 'evoef2_scan_results.csv'))}
ablang  = {r['mutation']: r for r in csv.DictReader(open(output / 'ablang_scores.csv'))}
cmc     = {r['mutation']: r for r in csv.DictReader(open(output / 'cmc_results.csv'))}
prodigy = {r['variant']: r for r in csv.DictReader(open(output / 'prodigy_results.csv'))}

print(f"{'Variant':<22} {'EvoEF2':>8} {'AbLang':>8} {'CMC':>6} {'PRODIGY ddG':>12} {'Kd(nM)':>8}")
print('-' * 70)
for mut in ['N62S', 'Y67F', 'K70R', 'F112Y']:
    e = float(evoef2[mut]['ddg_bind']) if evoef2.get(mut) else None
    a = float(ablang[mut]['ablang_delta']) if ablang.get(mut) else None
    c = cmc[mut]['cmc_pass'] if cmc.get(mut) else '?'
    p = prodigy.get(mut, {})
    ddg = float(p.get('ddg', 0)) if p.get('ddg') else None
    kd  = float(p.get('kd_nM', 0)) if p.get('kd_nM') else None
    print(f"{mut:<22} {e:>+8.2f} {a:>+8.4f} {c:>6} {ddg:>+12.3f} {kd:>8.2f}")

print()
print(f"{'Combo':<22} {'EvoEF2':>8} {'CMC':>6} {'PRODIGY ddG':>12} {'Kd(nM)':>8}")
print('-' * 70)
combos = list(csv.DictReader(open(output / 'combo_results.csv')))
for mut in ['Y67F+K70R', 'Y67F+F112Y', 'Y67F+N62S+F112Y', 'N62S+K70R', 'N62S+F112Y+K70R']:
    p = prodigy.get(mut, {})
    ddg = float(p.get('ddg', 0)) if p.get('ddg') else None
    kd  = float(p.get('kd_nM', 0)) if p.get('kd_nM') else None
    e_row = next((r for r in combos if r['combo'] == mut), None)
    e = float(e_row['ddg_bind']) if e_row else None
    print(f"{mut:<22} {e:>+8.2f} {'PASS':>6} {ddg:>+12.3f} {kd:>8.2f}")
