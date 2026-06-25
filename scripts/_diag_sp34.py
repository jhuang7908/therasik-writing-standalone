import json

d = json.load(open('projects/CD3_VH2VHH_Batch_20260515/v1813_reports/SP34_v1813.json', encoding='utf-8'))
orig = d['input_seq']
eng = d['final_seq']
print('Input  :', orig)
print('EngVHH :', eng)
print()
print(f'IGHV family: {d["ighv_family"]}')
print(f'CDR3 length: {d["cdr3_len"]} aa')
print(f'predicted_pI: {d["v1813_pi_prediction"]["predicted_pi_post_engineering"]}')
print(f'pI correction path: {d["v1813_pi_prediction"]["pi_correction_path"]}')
print(f'Total mutations: {len(d["all_mutations"])}')
print()
print('--- All mutations ---')
for m in d['all_mutations']:
    print(f'  {m["tier"]:<37} {m["orig_aa"]}->{m["target_aa"]}  {m["label_kabat"]:<15} pos{m["idx"]+1}')
print()
print('--- Tier log ---')
for tl in d['tier_log']:
    st = tl.get('stage', '?')
    pm = tl.get('post_metrics', {})
    v = tl.get('verdict', tl.get('reason', 'SKIPPED'))
    apps = tl.get('applied', [])
    print(f'  STAGE: {st}')
    if tl.get('skipped'):
        print(f'    SKIPPED: {tl.get("reason")[:80]}')
    else:
        print(f'    applied ({len(apps)}): {apps}')
        if pm:
            print(f'    post-metrics: pI={pm.get("pI")}  AbΔ={pm.get("abnativ_delta")}')
        print(f'    verdict: {v}; escalate={tl.get("escalate", False)}')
    print()

print(f'K count: original VH = {orig.count("K")}; engineered VHH = {eng.count("K")}')
print()
print('K positions in ORIGINAL SP34 VH:')
for i, aa in enumerate(orig):
    if aa == 'K':
        ctx = orig[max(0,i-4):i] + '[K]' + orig[i+1:i+5]
        was_changed = 'KEPT' if (i < len(eng) and eng[i] == 'K') else f'CHANGED to {eng[i]}'
        print(f'  pos {i+1:>3}  context: {ctx}   {was_changed}')

# Check the Stealth positions the algorithm tried but skipped
print()
print('What positions WOULD V1.8.13 Tier 1 STANDARD Stealth scan have looked at?')
print('  Targets: [K13, K19, K74, K83, K94] (CDR3 = 10 → STANDARD depth)')
positions = {
    'K13': 12, 'K19': 18, 'K74_approx': None, 'K83_approx': None, 'K94_approx': None
}
# Use the find_canonical_cys2 pattern
import re
m = re.search(r'[A-Z]C[AS][KR]', orig[85:115])
if m:
    cys2_idx = 85 + m.start() + 1
    print(f'  Cys2 (canonical, before CDR3): pos {cys2_idx+1}')
    print(f'  K94 maps to: pos {cys2_idx+2}  (residue={orig[cys2_idx+1]})')
    print(f'  K83 maps to: pos {cys2_idx-10}  (residue={orig[cys2_idx-11]})')
    print(f'  K74 maps to: pos {cys2_idx-19}  (residue={orig[cys2_idx-20]})')
    print(f'  K72 maps to: pos {cys2_idx-21}  (residue={orig[cys2_idx-22]})')
print(f'  K13 (pos 13): residue={orig[12]}')
print(f'  K19 (pos 19): residue={orig[18]}')
