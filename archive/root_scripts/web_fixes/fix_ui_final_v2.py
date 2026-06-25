
import re

path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read

# 1. Fix Disulfide-cleavable cards and localization
def fix_linkers(content):
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
        elif any(x in title.lower for x in ["hydrazone", "acid-labile", "acbut"]):
            ltype = "pH-cleavable"
        elif any(x in title.lower for x in ["smcc", "non-cleavable", "peg4-nhs", "smpeg24"]):
            ltype = "Non-cleavable"
            
        # Update data-ltype and badge
        card_html = re.sub(r'data-ltype=".*?"', f'data-ltype="{ltype}"', card_html)
        card_html = re.sub(r'<span class="badge badge-linker">.*?</span>', f'<span class="badge badge-linker">{ltype}</span>', card_html)
        
        # Patent coloring (fixing re.sub calls)
        if "Daiichi Sankyo" in card_html:
            card_html = card_html.replace('background:#f3f4f6;color:#666;border:1px solid #ddd', 'background:#fff3cd;color:#856404;border:1px solid #ffeeba')
        elif "Seagen" in card_html or "Spirogen" in card_html or "AstraZeneca" in card_html:
            card_html = card_html.replace('background:#f3f4f6;color:#666;border:1px solid #ddd', 'background:#cce5ff;color:#004085;border:1px solid #b8daff')
        elif "Synaffix" in card_html or "Ambrx" in card_html or "Protected" in card_html:
            card_html = card_html.replace('background:#f3f4f6;color:#666;border:1px solid #ddd', 'background:#d4edda;color:#155724;border:1px solid #c3e6cb')

        return card_html

    updated_section = re.sub(r'<div class="card" onclick="toggleCard\(this\)" data-ltype=".*?".*?</div>\s*</div>\s*</div>', update_card, section, flags=re.DOTALL)
    return content[:panel_start] + updated_section + content[panel_end:]

# 2. Fix Dropdown Localization
def fix_dropdowns(content):
    content = content.replace('<option value="Radionuclide">Radionuclide</option>', '<option value="Radionuclide"> (Radionuclide)</option>')
    content = content.replace('<option value="PROTACs">PROTACs</option>', '<option value="PROTACs"> (PROTACs)</option>')
    content = content.replace('<option value="ISACs">ISACs</option>', '<option value="ISACs"> (ISACs)</option>')
    content = content.replace('<option value="Oligonucleotide">Oligonucleotide</option>', '<option value="Oligonucleotide"> (Oligonucleotide)</option>')
    return content

# Apply
content = fix_linkers(content)
content = fix_dropdowns(content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed Disulfide-cleavable types, colored patents, and localized dropdowns.")
