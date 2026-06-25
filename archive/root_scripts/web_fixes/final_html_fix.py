import json
import os
import re

json_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\adc_atlas\adc_design_rules.json'
html_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

antigens = data['antigen_properties']

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read

def update_info_row(card_html, label, new_value):
    if new_value is None or new_value == "":
        new_value = "NA"
    escaped_label = re.escape(label)
    pattern = re.compile(rf'(<span class="info-label">{escaped_label}</span>\s*<span class="info-value">)([^<]*)(</span>)')
    return pattern.sub(lambda m: m.group(1) + str(new_value) + m.group(3), card_html)

# The card grid section
start_marker = '<!-- ═══ ANTIGENS ═══ -->'
end_marker = '<!-- ═══ PAYLOADS ═══ -->'
grid_start = html.find(start_marker)
grid_end = html.find(end_marker)

if grid_start == -1 or grid_end == -1:
    print("Markers not found")
    exit(1)

grid_html = html[grid_start:grid_end]

# Split into individual cards - keep newlines
cards = re.split(r'(?=<div class="card")', grid_html)
updated_cards = []

for card in cards:
    if not card.strip: continue
    
    # Get antigen name from card-title
    title_match = re.search(r'<div class="card-title">([^<]*)', card)
    if not title_match:
        updated_cards.append(card)
        continue
    
    name = title_match.group(1).strip
    name = re.sub(r'<span.*</span>', '', name).strip
    
    # Match name in antigens
    props = None
    if name in antigens:
        props = antigens[name]
    else:
        for k in antigens:
            if k.lower == name.lower:
                props = antigens[k]
                break
                
    if not props or not isinstance(props, dict):
        updated_cards.append(card)
        continue

    new_card = card
    
    # 1. Update data attributes for filtering
    def get_filter_val(val):
        val = str(val).lower
        if 'high' in val: return 'high'
        if 'moderate' in val or 'medium' in val: return 'moderate'
        if 'low' in val: return 'low'
        return '?'

    d_density = get_filter_val(props.get('density', '?'))
    d_intern = get_filter_val(props.get('internalization_rate', '?'))
    d_het = get_filter_val(props.get('heterogeneity', '?'))
    d_risk = get_filter_val(props.get('on_target_off_tumor_risk', '?'))

    new_card = re.sub(r'data-density="[^"]*"', f'data-density="{d_density}"', new_card)
    new_card = re.sub(r'data-intern="[^"]*"', f'data-intern="{d_intern}"', new_card)
    new_card = re.sub(r'data-het="[^"]*"', f'data-het="{d_het}"', new_card)
    new_card = re.sub(r'data-risk="[^"]*"', f'data-risk="{d_risk}"', new_card)

    # 2. Update data-search
    # Structure: data-search="tier ... name expr intern het density logic"
    search_match = re.search(r'data-search="([^"]*)"', new_card)
    if search_match:
        old_search = search_match.group(1)
        # Rebuild search string to remove ?
        tier = props.get('tier', '').lower
        expr = props.get('expression', '').lower
        logic = props.get('design_logic', '').lower
        
        new_search_parts = [tier, name.lower, expr, d_intern, d_het, d_density, logic]
        new_search = " ".join([p for p in new_search_parts if p and p != '?'])
        new_card = new_card.replace(f'data-search="{old_search}"', f'data-search="{new_search}"')

    # 3. Update cc-brief
    brief_density = props.get('density', '?')
    brief_intern = props.get('internalization_rate', '?')
    brief_het = props.get('heterogeneity', '?')
    new_brief = f'<div class="cc-brief">: {brief_density} · : {brief_intern} · : {brief_het}</div>'
    new_card = re.sub(r'<div class="cc-brief">.*?</div>', new_brief, new_card)

    # 4. Update info-rows in cc-detail
    field_map = {
        ' ': 'density',
        ' ': 'density_quantitative',
        '': 'internalization_rate',
        ' (t1/2)': 'internalization_t12',
        '': 'internalization_mechanism',
        '': 'heterogeneity',
        '': 'shedding_rate',
        '': 'recycling_after_internalization',
        ' (Design Logic)': 'design_logic',
        '': 'on_target_off_tumor_risk'
    }
    
    for label, prop_key in field_map.items:
        if prop_key in props:
            new_card = update_info_row(new_card, label, props[prop_key])

    updated_cards.append(new_card)

# Join with newlines to keep it readable and avoid layout issues
new_grid_html = "\n".join([c.strip for p in updated_cards for c in [p] if c.strip])
new_html = html[:grid_start] + start_marker + "\n" + new_grid_html + "\n" + html[grid_end:]

# Ensure legend is present and translated
legend_html = """
    <div class="page-card-hint" style="margin-bottom:20px; background: #f0fdfa; border-color: #5eead4; color: #0f766e;">
      <strong> (Evidence Attribution):</strong> 
      <span style="margin-left:15px;"><strong>(D) Direct</strong>: </span>
      <span style="margin-left:15px;"><strong>(I) Inferred</strong>: </span>
      <span style="margin-left:15px;"><strong>(C) Clinical</strong>: </span>
    </div>
"""

# Replace old legend if exists or add new one
if ' (Evidence Attribution)' not in new_html:
    new_html = new_html.replace('<div class="card-grid" id="gridAntigens">', legend_html + '<div class="card-grid" id="gridAntigens">')
else:
    new_html = re.sub(r'<div class="page-card-hint".*?.*?</div>', legend_html, new_html, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Final comprehensive fix with search and layout improvements completed.")
