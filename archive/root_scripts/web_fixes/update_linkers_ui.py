
import re

path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update data-ltype and add patent badges to cards
def update_linkers(match):
    card_html = match.group(0)
    title = re.search(r'<div class="card-title">(.*?)</div>', card_html).group(1)
    
    # Determine type and patent
    ltype = "Protease-cleavable"
    patent_info = "Public Domain"
    
    if "val-cit" in title.lower() or "GGFG" in title or "peptide" in title.lower() or "PEG8-vc" in title:
        ltype = "Protease-cleavable"
    elif "hydrazone" in title.lower() or "acid-labile" in title.lower() or "AcBut" in title:
        ltype = "pH-cleavable"
    elif "disulfide" in title.lower() or "SPDB" in title or "sulfo-SPDB" in title:
        ltype = "Disulfide-cleavable"
    elif "SMCC" in title or "non-cleavable" in title.lower() or "Mal-PEG4-NHS" in title or "SMPEG24" in title:
        ltype = "Non-cleavable"
        
    if "GGFG" in title:
        patent_info = "Daiichi Sankyo (Proprietary)"
    elif "val-cit" in title.lower():
        patent_info = "Public Domain / Seagen"
    elif "SMCC" in title:
        patent_info = "Public Domain / ImmunoGen"
    
    # Update data-ltype
    card_html = re.sub(r'data-ltype=".*?"', f'data-ltype="{ltype}"', card_html)
    
    # Add patent badge to header
    badge_html = f'<div style="display:flex;gap:5px;align-items:center;margin-top:4px"><span class="badge" style="background:#f3f4f6;color:#666;border:1px solid #ddd;font-size:9px">Patent: {patent_info}</span></div>'
    card_html = card_html.replace('</span>\n  </div>', f'</span>\n    {badge_html}\n  </div>')
    
    # Update badge text if it was "Cleavable"
    card_html = card_html.replace('<span class="badge badge-linker">Cleavable</span>', f'<span class="badge badge-linker">{ltype}</span>')
    
    return card_html

# Find the linkers panel
panel_start = content.find('<div class="tab-panel" id="panel-linkers">')
panel_end = content.find('<div class="tab-panel"', panel_start + 10)
linkers_section = content[panel_start:panel_end]

updated_section = re.sub(r'<div class="card" onclick="toggleCard\(this\)" data-ltype=".*?".*?</div>\s*</div>\s*</div>', update_linkers, linkers_section, flags=re.DOTALL)

# Write back
new_content = content[:panel_start] + updated_section + content[panel_end:]
with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Linker cards updated with specific types and patent badges")
