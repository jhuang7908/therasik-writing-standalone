import json
from pathlib import Path

for name in ['Teplizumab', 'Foralumab', 'Otelixizumab']:
    p = Path(f'projects/CD3_VH2VHH_Batch_20260515/v1813_reports/{name}_v1813.json')
    d = json.loads(p.read_text())
    pred = d['v1813_pi_prediction']
    print(f'=== {name} ===')
    print(f'  Predicted pI: {pred["predicted_pi_post_engineering"]}  Path: {pred["pi_correction_path"]}  n_planned: {pred["n_corrections_planned"]}')
    print(f'  Mutations:')
    for m in d['all_mutations']:
        print(f'    {m["tier"]:<35} {m["orig_aa"]}→{m["target_aa"]}  {m["label_kabat"]}  pos{m["idx"]+1}')
    print(f'  pI: {d["initial_metrics"]["pI"]} → {d["final_metrics"]["pI"]}')
    print(f'  Tier log summary:')
    for tl in d['tier_log']:
        st = tl.get('stage', '?')
        v = tl.get('verdict', tl.get('reason', 'SKIPPED')[:40] if tl.get('skipped') else '')
        pi_post = tl.get('post_metrics', {}).get('pI', '—')
        print(f'    {st:<45} pI_post={pi_post}  {v}')
    print()
