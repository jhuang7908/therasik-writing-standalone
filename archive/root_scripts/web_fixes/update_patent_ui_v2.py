
import re

path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Patent Badges to Payloads (panel-payloads)
def update_payloads(content):
    panel_start = content.find('<div class="tab-panel" id="panel-payloads">')
    panel_end = content.find('<div class="tab-panel"', panel_start + 10)
    section = content[panel_start:panel_end]
    
    def add_payload_patent(match):
        card_html = match.group(0)
        title = re.search(r'<div class="card-title">(.*?)</div>', card_html).group(1)
        
        patent_info = "Public Domain"
        color = "#666"
        bg = "#f3f4f6"
        border = "#ddd"
        
        if "DXd" in title or "Exatecan" in title:
            patent_info = "Daiichi Sankyo (Proprietary)"
            color = "#856404"
            bg = "#fff3cd"
            border = "#ffeeba"
        elif "MMAE" in title or "MMAF" in title:
            patent_info = "Public Domain / Seagen"
        elif "DM1" in title or "DM4" in title:
            patent_info = "Public Domain / ImmunoGen"
        elif "PBD" in title or "SG3" in title:
            patent_info = "Spirogen / AstraZeneca"
            color = "#004085"
            bg = "#cce5ff"
            border = "#b8daff"
        elif "PROTAC" in title or "ISAC" in title or "Oligonucleotide" in title:
            patent_info = "Emerging / IP Protected"
            color = "#155724"
            bg = "#d4edda"
            border = "#c3e6cb"
            
        badge_html = f'<div style="display:flex;gap:5px;align-items:center;margin-top:4px"><span class="badge" style="background:{bg};color:{color};border:1px solid {border};font-size:9px">Patent: {patent_info}</span></div>'
        
        # Insert before closing card-header
        if '</div>\n    <span class="badge' in card_html:
             card_html = card_html.replace('</div>\n    <span class="badge', f'  {badge_html}\n    </div>\n    <span class="badge')
        elif '</div>\n    <div style="display:flex;gap:5px;align-items:center;margin-top:4px">' not in card_html:
             card_html = card_html.replace('</div>\n    <span class="badge', f'  {badge_html}\n    </div>\n    <span class="badge')
             
        # Alternative insertion if structure is different
        if badge_html not in card_html:
            card_html = re.sub(r'(<div class="card-title">.*?</div>)', r'\1' + badge_html, card_html)

        return card_html

    updated_section = re.sub(r'<div class="card" onclick="toggleCard\(this\)" data-cls=".*?".*?</div>\s*</div>\s*</div>', add_payload_patent, section, flags=re.DOTALL)
    return content[:panel_start] + updated_section + content[panel_end:]

# 2. Add Patent Badges to Conjugation (panel-conjugation)
def update_conjugation(content):
    panel_start = content.find('<div class="tab-panel" id="panel-conjugation">')
    panel_end = content.find('<div class="tab-panel"', panel_start + 10)
    if panel_end == -1: panel_end = content.find('<!--', panel_start + 10)
    section = content[panel_start:panel_end]
    
    def add_conj_patent(match):
        card_html = match.group(0)
        title = re.search(r'<div class="card-title">(.*?)</div>', card_html).group(1)
        
        patent_info = "Check FTO"
        color = "#666"
        bg = "#f3f4f6"
        border = "#ddd"
        
        if "Glycan" in title:
            patent_info = "Synaffix (Lonza)"
            color = "#856404"
            bg = "#fff3cd"
            border = "#ffeeba"
        elif "Unnatural" in title or "Ambrx" in title:
            patent_info = "Ambrx / Sutro"
            color = "#004085"
            bg = "#cce5ff"
            border = "#b8daff"
        elif "Stochastic Cysteine" in title or "Lysine" in title:
            patent_info = "Public Domain"
        elif "ThioBridge" in title:
            patent_info = "Abzena"
            color = "#155724"
            bg = "#d4edda"
            border = "#c3e6cb"
            
        badge_html = f'<div style="display:flex;gap:5px;align-items:center;margin-top:4px"><span class="badge" style="background:{bg};color:{color};border:1px solid {border};font-size:9px">Patent: {patent_info}</span></div>'
        
        if badge_html not in card_html:
            card_html = re.sub(r'(<div class="card-title">.*?</div>)', r'\1' + badge_html, card_html)
            
        return card_html

    updated_section = re.sub(r'<div class="card" onclick="toggleCard\(this\)" data-homo=".*?".*?</div>\s*</div>\s*</div>', add_conj_patent, section, flags=re.DOTALL)
    return content[:panel_start] + updated_section + content[panel_end:]

# 3. Update Linker Patent Colors
def update_linker_colors(content):
    panel_start = content.find('<div class="tab-panel" id="panel-linkers">')
    panel_end = content.find('<div class="tab-panel"', panel_start + 10)
    section = content[panel_start:panel_end]
    
    def color_linker_patent(match):
        badge_html = match.group(0)
        if "Daiichi Sankyo" in badge_html:
            return badge_html.replace('background:#f3f4f6;color:#666;border:1px solid #ddd', 'background:#fff3cd;color:#856404;border:1px solid #ffeeba')
        if "Seagen" in badge_html:
            return badge_html.replace('background:#f3f4f6;color:#666;border:1px solid #ddd', 'background:#cce5ff;color:#004085;border:1px solid #b8daff')
        return badge_html

    updated_section = re.sub(r'<span class="badge" style="background:#f3f4f6;color:#666;border:1px solid #ddd;font-size:9px">Patent: .*?</span>', color_linker_patent, section)
    return content[:panel_start] + updated_section + content[panel_end:]

# Apply all
content = update_payloads(content)
content = update_conjugation(content)
content = update_linker_colors(content)

with open(path, 'w', encoding='utf-8') as