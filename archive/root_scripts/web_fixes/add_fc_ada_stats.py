"""
Compute clinical ADA statistics by Fc isotype/engineering type from ADA master.
Then inject a new tab/section into the Antibody Guide for 'Fc  ADA '.
"""
import csv, json, re, statistics

MASTER = r'data\ada_master_136_curated.csv'
rows = list(csv.DictReader(open(MASTER, encoding='utf-8')))

def parse_pct(v):
    if not v or v.strip in ('', 'unknown', 'Unknown', 'N/A', 'nan'):
        return None
    # Try to extract first percentage
    m = re.search(r'(\d+\.?\d*)\s*%', str(v))
    if m:
        return float(m.group(1))
    return None

# Group by fc_effector_status
groups = {
    'IgG1  ': [],
    'IgG2/IgG4 ': [],
    'Fc  (LALA/N297)': [],
    'ADCC ': [],
    ' (YTE/LS)': [],
    'ADC': [],
}

for r in rows:
    pct = parse_pct(r.get('ada_value_display', ''))
    if pct is None:
        continue
    fe = (r.get('fc_effector_status','') or '').lower
    fi = (r.get('fc_isotype','') or '')
    fn = (r.get('fc_mutation_notes','') or '').lower
    fing = (r.get('fc_engineering','') or '').lower

    if 'adc' in fing or 'adc' in fn:
        groups['ADC'].append(pct)
    elif 'no_effector' in fe or 'lala' in fn or 'lala' in fing or 'p329' in fn or 'n297' in fn or 'silenc' in fe:
        groups['Fc  (LALA/N297)'].append(pct)
    elif 'enhanced' in fe or 'adcc-enh' in fing or 'afucosyl' in fing or 's239d' in fn or 'gasdalie' in fn:
        groups['ADCC '].append(pct)
    elif 'yte' in fn or 'yte' in fing or 'm252' in fn or 'm428' in fn or 'half-life' in fn:
        groups[' (YTE/LS)'].append(pct)
    elif fi in ('2',) or 'igg2' in fing or fi == '4' or 'igg4' in fing:
        groups['IgG2/IgG4 '].append(pct)
    else:
        groups['IgG1  '].append(pct)

print("=== Clinical ADA by Fc Type ===")
summary = {}
for grp, vals in groups.items:
    if vals:
        med = statistics.median(vals)
        mn = min(vals)
        mx = max(vals)
        lo_risk = sum(1 for v in vals if v < 10)
        print(f"\n{grp} (n={len(vals)})")
        print(f"  Median: {med:.1f}%  Range: {mn:.1f}–{mx:.1f}%  Low-risk (<10%): {lo_risk}/{len(vals)}")
        summary[grp] = {'n': len(vals), 'median': round(med,1), 'min': round(mn,1), 'max': round(mx,1), 'low_risk_n': lo_risk}

with open('data/reference/fc_ada_stats.json', 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print("\nSaved: data/reference/fc_ada_stats.json")

# Generate HTML for the guide section
html_block = '''
<!-- ── Fc  ADA  (inserted by add_fc_ada_stats.py) ── -->
<div id="domain-fcada" class="domain-content" style="display:none">
  <div class="domain-header">
    <h2>Fc  ×  ADA </h2>
    <p> Therasik 138  ADA  Fc 。ADA （、、、）， Fc 。</p>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;margin-bottom:28px;">
'''

color_map = {
    'IgG1  ': '#0d9488',
    'IgG2/IgG4 ': '#0891b2',
    'Fc  (LALA/N297)': '#7c3aed',
    'ADCC ': '#b91c1c',
    ' (YTE/LS)': '#059669',
    'ADC': '#d97706',
}
icon_map = {
    'IgG1  ': '🟢',
    'IgG2/IgG4 ': '🔵',
    'Fc  (LALA/N297)': '🟣',
    'ADCC ': '🔴',
    ' (YTE/LS)': '🟩',
    'ADC': '🟡',
}

for grp, s in summary.items:
    color = color_map.get(grp, '#374151')
    med = s['median']
    bar_w = min(100, med * 1.5)
    low_pct = round(100 * s['low_risk_n'] / s['n'])
    html_block += f'''    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px;border-top:3px solid {color}">
      <div style="font-size:13px;font-weight:700;color:{color};margin-bottom:12px">{grp}</div>
      <div style="font-size:11px;color:#6b7280;margin-bottom:6px"> ADA </div>
      <div style="font-size:28px;font-weight:700;color:{color};font-family:'Cormorant Garamond',serif;margin-bottom:6px">{med:.1f}%</div>
      <div style="background:#f3f4f6;border-radius:4px;height:6px;margin-bottom:10px"><div style="width:{bar_w}%;background:{color};border-radius:4px;height:6px;transition:width .6s"></div></div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;font-size:11px">
        <div style="text-align:center"><div style="font-weight:700">{s['n']}</div><div style="color:#9ca3af"></div></div>
        <div style="text-align:center"><div style="font-weight:700">{s['min']:.1f}–{s['max']:.1f}%</div><div style="color:#9ca3af"></div></div>
        <div style="text-align:center"><div style="font-weight:700;color:#059669">{low_pct}%</div><div style="color:#9ca3af"></div></div>
      </div>
    </div>
'''

html_block += '''  </div>
  <div style="background:#f0fdf9;border:1px solid rgba(13,148,136,0.2);border-radius:12px;padding:20px;font-size:13px;line-height:1.8">
    <div style="font-weight:700;color:#0d4a43;margin-bottom:10px">⚠ </div>
    <ul style="margin:0;padding-left:18px;color:#374151">
      <li><strong></strong>：Gen 1 ELISA  Gen 3 ECL， 10 </li>
      <li><strong></strong>：SC  ADA  IV，Fc （ YTE  SC ）</li>
      <li><strong></strong>：，ADA ； MTX ，ADA </li>
      <li><strong></strong>：Fc ，， ADA </li>
    </ul>
  </div>
</div>
'''

print("\n=== Generated HTML block ===")
print(f"Length: {len(html_block)} chars")

# Write to a temp file for inspection
with open('_fc_ada_stats_block.html', 'w', encoding='utf-8') as f:
    f.write(html_block)
print("Saved preview: _fc_ada_stats_block.html")
