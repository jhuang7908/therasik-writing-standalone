import json

d = json.load(open('projects/CD3_VH2VHH_Batch_20260515/v1813_reports/Teplizumab_v1813.json', encoding='utf-8'))
orig = d['input_seq']
eng = d['final_seq']
print('Input  :', orig)
print('EngVHH :', eng)
print()
print(f'Total mutations: {len(d["all_mutations"])}')
print()
print('--- All mutations ---')
for m in d['all_mutations']:
    print(f'  {m["tier"]:<35} {m["orig_aa"]}->{m["target_aa"]}  {m["label_kabat"]:<15} pos{m["idx"]+1}')
print()
print(f'K count: original VH = {orig.count("K")}; engineered VHH = {eng.count("K")}')
print(f'R count: original VH = {orig.count("R")}; engineered VHH = {eng.count("R")}')
print()
print('K positions in ENGINEERED VHH:')
for i, aa in enumerate(eng):
    if aa == 'K':
        ctx = eng[max(0,i-4):i] + '[K]' + eng[i+1:i+5]
        print(f'  pos {i+1:>3}  context: {ctx}')

print()
print('K positions in ORIGINAL VH (for comparison):')
for i, aa in enumerate(orig):
    if aa == 'K':
        ctx = orig[max(0,i-4):i] + '[K]' + orig[i+1:i+5]
        was_changed = 'KEPT' if (i < len(eng) and eng[i] == 'K') else f'CHANGED to {eng[i]}'
        print(f'  pos {i+1:>3}  context: {ctx}   {was_changed}')
