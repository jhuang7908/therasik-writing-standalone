import json
detail = json.load(open('data/_v1814_design/v1813_classification_detail.json', encoding='utf-8'))

def show_cat(cat, where):
    print(f'=== {cat} {where} ===')
    rows = [r for r in detail if r['category'] == cat and where(r)]
    for r in rows:
        pi = r.get('pI', '?')
        ad = r.get('abnativ_delta', 0)
        pi_str = f'{pi}' if pi is None else f'{pi:>5.2f}'
        ad_str = f'{ad:+.4f}' if ad is not None else 'None'
        print(f"  {r['id']:<35} ighv={r['ighv']:<14} pI={pi_str} ({r['pI_label']:>4}) AbΔ={ad_str} ({r['abnativ_label']:>4})  → {r['composite_verdict']}")
    print()

show_cat('Clinical_VHH', lambda r: r['composite_verdict'] not in ('PASS', 'EXCELLENT'))
show_cat('Engineered_Human_VH', lambda r: r['composite_verdict'] not in ('PASS', 'EXCELLENT'))
show_cat('Negative_Control_VH', lambda r: True)
show_cat('Autonomous_Human_VH', lambda r: r['composite_verdict'] not in ('PASS', 'EXCELLENT'))
