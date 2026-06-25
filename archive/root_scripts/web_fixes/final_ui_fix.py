
import re

path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read

# 1. Update Linker cards specifically for pH-cleavable
def fix_linker_cards_final(content):
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
        if any(x in title.lower for x in ["disulfide", "spdb"]):
            ltype = "Disulfide-cleavable"
        elif any(x in title.lower for x in ["hydrazone", "acid-labile", "acbut", "ph-cleavable", "ph-sensitive"]):
            ltype = "pH-cleavable"
        elif any(x in title.lower for x in ["smcc", "non-cleavable", "peg4-nhs", "smpeg24", "thioether"]):
            ltype = "Non-cleavable"
            
        # Update data-ltype and badge
        card_html = re.sub(r'data-ltype=".*?"', f'data-ltype="{ltype}"', card_html)
        card_html = re.sub(r'<span class="badge badge-linker">.*?</span>', f'<span class="badge badge-linker">{ltype}</span>', card_html)
        
        return card_html

    updated_section = re.sub(r'<div class="card" onclick="toggleCard\(this\)" data-ltype=".*?".*?</div>\s*</div>\s*</div>', update_card, section, flags=re.DOTALL)
    return content[:panel_start] + updated_section + content[panel_end:]

# 2. Force English labels in ALL dropdowns (Antigens, Payloads, Linkers, Conjugation)
def force_english_dropdowns(content):
    # Linkers
    content = content.replace('<option value="Protease-cleavable">Protease-cleavable </option>', '<option value="Protease-cleavable">Protease-cleavable</option>')
    content = content.replace('<option value="pH-cleavable">pH-cleavable </option>', '<option value="pH-cleavable">pH-cleavable</option>')
    content = content.replace('<option value="Disulfide-cleavable">Disulfide-cleavable </option>', '<option value="Disulfide-cleavable">Disulfide-cleavable</option>')
    content = content.replace('<option value="Non-cleavable">Non-cleavable </option>', '<option value="Non-cleavable">Non-cleavable</option>')
    
    # Payloads
    content = re.sub(r'<option value="Radionuclide">.*?</option>', '<option value="Radionuclide">Radionuclide</option>', content)
    content = re.sub(r'<option value="PROTACs">.*?</option>', '<option value="PROTACs">PROTACs</option>', content)
    content = re.sub(r'<option value="ISACs">.*?</option>', '<option value="ISACs">ISACs</option>', content)
    content = re.sub(r'<option value="Oligonucleotide">.*?</option>', '<option value="Oligonucleotide">Oligonucleotide</option>', content)
    
    # Conjugation
    content = re.sub(r'<option value="">.*?</option>', '<option value="">Very High</option>', content)
    content = re.sub(r'<option value="">.*?</option>', '<option value="">High</option>', content)
    content = re.sub(r'<option value="">.*?</option>', '<option value="">Moderate</option>', content)
    content = re.sub(r'<option value="">.*?</option>', '<option value="">Low</option>', content)
    
    # Antigens
    content = re.sub(r'<option value="">.*?</option>', '<option value="">Solid Tumor</option>', content)
    
    return content

content = fix_linker_cards_final(content)
content = force_english_dropdowns(content)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Final fix: Corrected pH-cleavable cards and forced pure English dropdowns.")
