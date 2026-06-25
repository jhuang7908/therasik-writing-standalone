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

# 1. Add Legend Section
legend_html = """
    <div class="page-card-hint" style="margin-bottom:20px; background: #fffbeb; border-color: #fde68a; color: #92400e;">
      <strong>Data Attribution Legend:</strong> 
      <span style="margin-left:15px;"><strong>(D) Direct</strong>: Quantitative experimental data.</span>
      <span style="margin-left:15px;"><strong>(I) Inferred</strong>: Logical biological inference.</span>
      <span style="margin-left:15px;"><strong>(C) Clinical</strong>: Inferred from clinical drug performance.</span>
    </div>
"""

# Insert legend above gridAntigens
if '<div class="card-grid" id="gridAntigens">' in html_content:
    # Find the ctrl-row before gridAntigens
    parts = html_content.split('<div class="card-grid" id="gridAntigens">')
    # The last ctrl-row before the grid
    header_part = parts[0]
    # We want to insert it before the last </div> that closes the ctrl-row container or just before the grid
    new_html = header_part + legend_html + '<div class="card-grid" id="gridAntigens">' + parts[1]
    html_content = new_html

# 2. Sync HTML Cards
# We need to find each card in gridAntigens and update its values
# A card starts with <div class="card" ... data-search="... target_name ...">
# We can use regex to find cards and update them based on the target name

def update_card(match):
    card_full = match.group(0)
    # Extract target name from card-title
    title_match = re.search(r'<div class="card-title">([^<]+)', card_full)
    if not title_match:
        return card_full
    
    target_name = title_match.group(1).strip
    if target_name not in antigen_properties:
        return card_full
    
    props = antigen_properties[target_name]
    if not isinstance(props, dict):
        return card_full
    
    density = props.get('density', '?')
    internalization = props.get('internalization_rate', '?')
    heterogeneity = props.get('heterogeneity', '?')
    
    # Update cc-brief
    # <div class="cc-brief">: ... · : ... · : ...</div>
    new_brief = f'<div class="cc-brief">: {density} · : {internalization} · : {heterogeneity}</div>'
    card_full = re.sub(r'<div class="cc-brief">[^<]+</div>', new_brief, card_full)
    
    # Update info-rows in cc-detail
    # Density
    card_full = re.sub(r'(<span class="info-label"> \(\)</span><span class="info-value">)([^<]+)(</span>)', 
                       rf'\1{density}\3', card_full)
    # Internalization
    card_full = re.sub(r'(<span class="info-label"></span><span class="info-value">)([^<]+)(</span>)', 
                       rf'\1{internalization}\3', card_full)
    # Heterogeneity
    card_full = re.sub(r'(<span class="info-label"></span><span class="info-value">)([^<]+)(</span>)', 
                       rf'\1{heterogeneity}\3', card_full)
    
    # Update data-attributes for filtering
    # data-intern="...", data-het="...", data-density="..."
    # Note: filters expect clean values (high, moderate, low)
    def clean_val(v):
        v = v.lower
        if 'high' in v: return 'high'
        if 'moderate' in v or 'medium' in v: return 'moderate'
        if 'low' in v: return 'low'
        return 'unknown'

    card_full = re.sub(r'data-intern="[^"]*"', f'data-intern="{clean_val(internalization)}"', card_full)
    card_full = re.sub(r'data-het="[^"]*"', f'data-het="{clean_val(heterogeneity)}"', card_full)
    card_full = re.sub(r'data-density="[^"]*"', f'data-density="{clean_val(density)}"', card_full)
    
    return card_full

# Find all cards in the gridAntigens section
grid_start = html_content.find('<div class="card-grid" id="gridAntigens">')
grid_end = html_content.find('<!-- ═══ PAYLOADS ═══ -->', grid_start)
if grid_end == -1: grid_end = len(html_content)

grid_content = html_content[grid_start:grid_end]
# Regex for a card: <div class="card" ... </div> (non-greedy)
# This is tricky because of nested divs. We'll use a simpler approach: 
# split by <div class="card" and process each piece.
card_pieces = grid_content.split('<div class="card"')
new_grid_content = card_pieces[0]
for piece in card_pieces[1:]:
    # Find the end of this card (it ends before the next <div class="card" or at the end of grid)
    # But wait, cards are nested. Let's assume cards don't contain other cards.
    # We need to find the matching </div> for the card.
    # For simplicity, we'll just process the piece until the next card or end.
    full_piece = '<div class="card"' + piece
    # We only want to update the first card in this piece if there are multiple (unlikely in this structure)
    updated_piece = update_card(re.compile(r'<div class="card".*?</div>\s*</div>\s*</div>', re.DOTALL).search(full_piece))
    if updated_piece:
        # Re-assemble
        new_grid_content += updated_piece.group(0) if hasattr(updated_piece, 'group') else updated_piece
    else:
        new_grid_content += full_piece

html_content = html_content[:grid_start] + new_grid_content + html_content[grid_end:]

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print("HTML sync complete.")
