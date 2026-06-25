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
    # Pattern to find <span class="info-label">LABEL</span><span class="info-value">...</span>
    pattern = re.compile(rf'(<span class="info-label">{label}</span>\s*<span class="info-value">)([^<]*)(</span>)')
    if new_value is None or new_value == "":
        new_value = "NA"
    return pattern.sub(rf'\1{new_value}\3', card_html)

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
    if name not in antigens:
        # Try to find the name in the keys (case-insensitive)
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

    # Update fields
    new_card = card
    
    # 1. Density 
    if 'density' in props:
        new_card = update_field(new_card, ' \(\)', props['density'])
    
    # 2. Density  - if exists
    if 'density_quantitative' in props:
        # Check if quantitative row exists, if not, we might need to add it, 
        # but for now let's just update if it exists.
        new_card = update_field(new_card, ' \(\)', props['density_quantitative'])
    
    # 3. Internalization Rate
    if 'internalization_rate' in props:
        new_card = update_field(new_card, '', props['internalization_rate'])
        
    # 4. Internalization T1/2
    if 'internalization_t12' in props:
        new_card = update_field(new_card, ' \(t1/2\)', props['internalization_t12'])

    # 5. Mechanism
    if 'internalization_mechanism' in props:
        new_card = update_field(new_card, '', props['internalization_mechanism'])

    # 6. Heterogeneity
    if 'heterogeneity' in props:
        new_card = update_field(new_card, '', props['heterogeneity'])

    # 7. Shedding
    if 'shedding_rate' in props:
        new_card = update_field(new_card, '', props['shedding_rate'])

    # 8. Recycling
    if 'recycling_after_internalization' in props:
        new_card = update_field(new_card, '', props['recycling_after_internalization'])

    # 9. Design Logic (already updated but let's be sure)
    if 'design_logic' in props:
        new_card = update_field(new_card, ' \(Design Logic\)', props['design_logic'])

    updated_cards.append(new_card)

new_grid_html = "".join(updated_cards)
new_html = html[:grid_start] + new_grid_html + html[grid_end:]

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Successfully updated all antigen cards with re-annotated data.")
