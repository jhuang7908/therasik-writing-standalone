
import re

path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read

# 1. UNIFY ALL DROPDOWNS TO PURE ENGLISH (No Chinese in labels)
# Linker Types
content = content.replace('<option value="Protease-cleavable">Protease-cleavable </option>', '<option value="Protease-cleavable">Protease-cleavable</option>')
content = content.replace('<option value="pH-cleavable">pH-cleavable </option>', '<option value="pH-cleavable">pH-cleavable</option>')
content = content.replace('<option value="Disulfide-cleavable">Disulfide-cleavable </option>', '<option value="Disulfide-cleavable">Disulfide-cleavable</option>')
content = content.replace('<option value="Non-cleavable">Non-cleavable </option>', '<option value="Non-cleavable">Non-cleavable</option>')

# Payload Mechanisms (Ensure no Chinese)
content = re.sub(r'<option value="Radionuclide">.*?</option>', '<option value="Radionuclide">Radionuclide</option>', content)
content = re.sub(r'<option value="PROTACs">.*?</option>', '<option value="PROTACs">PROTACs</option>', content)
content = re.sub(r'<option value="ISACs">.*?</option>', '<option value="ISACs">ISACs</option>', content)
content = re.sub(r'<option value="Oligonucleotide">.*?</option>', '<option value="Oligonucleotide">Oligonucleotide</option>', content)

# Conjugation Homogeneity
content = re.sub(r'<option value="">.*?</option>', '<option value="">Very High</option>', content)
content = re.sub(r'<option value="">.*?</option>', '<option value="">High</option>', content)
content = re.sub(r'<option value="">.*?</option>', '<option value="">Moderate</option>', content)
content = re.sub(r'<option value="">.*?</option>', '<option value="">Low</option>', content)

# Antigen Disease types
content = re.sub(r'<option value="">.*?</option>', '<option value="">Solid Tumor</option>', content)

# 2. FIX LINKER CARDS (Ensure pH-cleavable and Disulfide-cleavable are correctly tagged)
def fix_linker_cards(content):
    panel_start = content.find('<div class="tab-panel" id="panel-linkers">')
    panel_end = content.find('<div class="tab-panel"', panel_start + 10)
    if panel_end == -1: panel_end = content.find('<!--', panel_start + 10)
    section = content[panel_start:panel_end]
    
    def update_card(match):
        card_html = match.group(0)
        title_match = re.search(r'<div class="card-title">(.*?)</div>', card_html)
        if not title_match: return card_html
        title = title_match.group(1)
        
        # Determine correct type
        ltype = "Protease-cleavable"
        if any(x in title.lower for x in ["disulfide", "spdb", "thioether"]):
            ltype = "Disulfide-cleavable"
        elif any(x in title.lower for x in ["hydrazone", "acid-labile", "acbut", "ph-cleavable", "ph-sensitive"]):
            ltype = "pH-cleavable"
        elif any(x in title.lower for x in ["smcc", "non-cleavable", "peg4-nhs", "smpeg24"]):
            ltype = "Non-cleavable"
            
        # Update data-ltype and badge
        card_html = re.sub(r'data-ltype=".*?"', f'data-ltype="{ltype}"', card_html)
        card_html = re.sub(r'<span class="badge badge-linker">.*?</span>', f'<span class="badge badge-linker">{ltype}</span>', card_html)
        
        # 3. COLOR ALL PATENT BADGES
        if 'background:#f3f4f6;color:#666;border:1px solid #ddd' in card_html:
            if "Public Domain" in card_html:
                pass
            elif "Daiichi Sankyo" in card_html:
                card_html = card_html.replace('background:#f3f4f6;color:#666;border:1px solid #ddd', 'background:#fff3cd;color:#856404;border:1px solid #ffeeba')
            elif any(x in card_html for x in ["Seagen", "Spirogen", "AstraZeneca", "ImmunoGen"]):
                card_html = card_html.replace('background:#f3f4f6;color:#666;border:1px solid #ddd', 'background:#cce5ff;color:#004085;border:1px solid #b8daff')
            else:
                card_html = card_html.replace('background:#f3f4f6;color:#666;border:1px solid #ddd', 'background:#d4edda;color:#155724;border:1px solid #c3e6cb')

        return card_html

    # This regex is more robust to find the whole card div
    updated_section = re.sub(r'<div class="card" onclick="toggleCard\(this\)" data-ltype=".*?".*?</div>\s*</div>\s*</div>', update_card, section, flags=re.DOTALL)
    return content[:panel_start] + updated_section + content[panel_end:]

# Apply to all cards in all panels for patent colors
def color_all_patents(content):
    def color_match(match):
        badge = match.group(0)
        if "Public Domain" in badge: return badge
        if "Daiichi Sankyo" in badge:
            return badge.replace('background:#f3f4f6;color:#666;border:1px solid #ddd', 'background:#fff3cd;color:#856404;border:1px solid #ffeeba')
        if any(x in badge for x in ["Seagen", "Spirogen", "AstraZeneca", "ImmunoGen", "Ambrx", "Sutro", "Synaffix"]):
            return badge.replace('background:#f3f4f6;color:#666;border:1px solid #ddd', 'background:#cce5ff;color:#004085;border:1px solid #b8daff')
        return badge.replace('background:#f3f4f6;color:#666;border:1px solid #ddd', 'background:#d4edda;color:#155724;border:1px solid #c3e6cb')

    content = re.sub(r'<span class="badge" style="background:#f3f4f6;color:#666;border:1px solid #ddd;font-size:9px">Patent: .*?</span>', color_match, content)
    return content

content = fix_linker_cards(content)
content = color_all_patents(content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Unified all dropdowns to pure English. Fixed pH-cleavable cards. Colored all non-public patent badges.")
