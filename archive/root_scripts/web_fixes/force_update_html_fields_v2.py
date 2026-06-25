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

def update_field(card_html, label, new_value):
    if new_value is None or new_value == "":
        new_value = "NA"
    
    # Escape the label for regex
    escaped_label = re.escape(label)
    # Use a non-capturing group for the label part to avoid sub issues with backslashes
    pattern = re.compile(rf'(<span class="info-label">{escaped_label}</span>\s*<span class="info-value">)([^<]*)(</span>)')
    
    # Use a lambda to avoid backslash issues in the replacement string
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

# Split into individual cards
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
    # Clean up name (remove badges)
    name = re.sub(r'<span.*</span>', '', name).strip
    
    if name not in antigens:
        # Try case-insensitive
        found = False
        for k in antigens:
            if k.lower == name.lower:
                name = k
                found = True
                break
        if not found:
            updated_cards.append(card)
            continue
            
    props = antigens[name]
    if not isinstance(props, dict):
        updated_cards.append(card)
        continue

    new_card = card
    
    # Update fields
    field_map = {
        ' ': 'density',
        ' ': 'density_quantitative',
        '': 'internalization_rate',
        ' (t1/2)': 'internalization_t12',
        '': 'internalization_mechanism',
        '': 'heterogeneity',
        '': 'shedding_rate',
        '': 'recycling_after_internalization',
        ' (Design Logic)': 'design_logic'
    }
    
    for label, prop_key in field_map.items:
        if prop_key in props:
            new_card = update_field(new_card, label, props[prop_key])

    updated_cards.append(new_card)

new_grid_html = "".join(updated_cards)
new_html = html[:grid_start] + new_grid_html + html[grid_end:]

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Successfully updated all antigen cards with re-annotated data.")
