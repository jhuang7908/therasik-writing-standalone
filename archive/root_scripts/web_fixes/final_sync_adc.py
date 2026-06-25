import json
import os
import re

json_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\adc_atlas\adc_design_rules.json'
html_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

antigen_properties = data.get('antigen_properties', {})

with open(html_path, 'r', encoding='utf-8') as f:
    html_content = f.read

# 1. Update design_logic in JSON to remove "Unknown"
for target, props in antigen_properties.items:
    if not isinstance(props, dict): continue
    dl = props.get('design_logic', '')
    if 'Unknown density' in dl or 'Unknown internalization' in dl:
        density = props.get('density', 'Moderate (I)')
        intern = props.get('internalization_rate', 'Moderate (I)')
        # Re-construct a basic design logic if it was using placeholders
        new_dl = dl.replace('Unknown density', density).replace('Unknown internalization', intern)
        props['design_logic'] = new_dl

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# 2. Re-run HTML sync with more robust replacement
def clean_val(v):
    v = str(v).lower
    if 'high' in v: return 'high'
    if 'moderate' in v or 'medium' in v: return 'moderate'
    if 'low' in v: return 'low'
    return 'unknown'

# Split by cards to avoid regex greediness issues
grid_start_marker = '<div class="card-grid" id="gridAntigens">'
grid_end_marker = '<!-- ═══ PAYLOADS ═══ -->'
start_idx = html_content.find(grid_start_marker)
end_idx = html_content.find(grid_end_marker, start_idx)

if start_idx != -1 and end_idx != -1:
    grid_section = html_content[start_idx:end_idx]
    # Split into individual cards
    cards = grid_section.split('<div class="card"')
    new_cards = [cards[0]]
    
    for card_body in cards[1:]:
        full_card = '<div class="card"' + card_body
        # Extract target
        target_match = re.search(r'<div class="card-title">([^<]+)', full_card)
        if target_match:
            target_name = target_match.group(1).split('<')[0].strip
            if target_name in antigen_properties:
                props = antigen_properties[target_name]
                dens = props.get('density', 'Moderate (I)')
                intern = props.get('internalization_rate', 'Moderate (I)')
                het = props.get('heterogeneity', 'Moderate (I)')
                dl = props.get('design_logic', '')
                
                # Update attributes
                full_card = re.sub(r'data-intern="[^"]*"', f'data-intern="{clean_val(intern)}"', full_card)
                full_card = re.sub(r'data-het="[^"]*"', f'data-het="{clean_val(het)}"', full_card)
                full_card = re.sub(r'data-density="[^"]*"', f'data-density="{clean_val(dens)}"', full_card)
                
                # Update cc-brief
                full_card = re.sub(r'<div class="cc-brief">: [^·]+ · : [^·]+ · : [^<]+</div>', 
                                   f'<div class="cc-brief">: {dens} · : {intern} · : {het}</div>', full_card)
                
                # Update info-values
                full_card = re.sub(r'(<span class="info-label"> \(\)</span><span class="info-value">)([^<]+)(</span>)', 
                                   rf'\1{dens}\3', full_card)
                full_card = re.sub(r'(<span class="info-label"></span><span class="info-value">)([^<]+)(</span>)', 
                                   rf'\1{intern}\3', full_card)
                full_card = re.sub(r'(<span class="info-label"></span><span class="info-value">)([^<]+)(</span>)', 
                                   rf'\1{het}\3', full_card)
                
                # Update design logic block
                if dl:
                    full_card = re.sub(r'(<div class="info-row" style="background:#f0f7f4;padding:8px;border-radius:4px;border-left:3px solid #1a7a4a;margin-bottom:8px">\s*<span class="info-value" style="color:#1a7a4a;font-weight:500">)([^<]+)(</span>)',
                                       rf'\1{dl}\3', full_card)
        
        new_cards.append(full_card)
    
    new_grid_section = "".join(new_cards)
    html_content = html_content[:start_idx] + new_grid_section + html_content[end_idx:]

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Final sync complete.")
