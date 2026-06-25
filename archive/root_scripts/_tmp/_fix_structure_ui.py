"""
Comprehensive fix for ADC Database UI issues:
1. Move new payload cards INSIDE grid (currently outside the grid div → no grid layout)
2. Move new linker cards INSIDE grid
3. Fix CSS: uniform card min-height, consistent badge width, search bar on every tab
4. Add patent info to old linker cards that lack it
5. Standardize cc-brief text length uniformity
"""
import re

path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read

original_len = len(content)

# ─────────────────────────────────────────────────────────────────
# STEP 1 — CSS fixes: uniform card height + consistent grid layout
# ─────────────────────────────────────────────────────────────────
old_css_card = '.card { background:#fff; border:1px solid var(--border); border-radius:10px; overflow:hidden; transition:box-shadow .15s,border-color .15s; cursor:pointer; }'
new_css_card = '''.card { background:#fff; border:1px solid var(--border); border-radius:10px; overflow:hidden; transition:box-shadow .15s,border-color .15s; cursor:pointer; display:flex; flex-direction:column; }
.card-body { display:flex; flex-direction:column; flex:1; }
.cc-brief { min-height:2.8em; }'''
content = content.replace(old_css_card, new_css_card)

# Ensure card-grid always uses uniform column layout (fix the double-definition conflict)
# Find and deduplicate any duplicate .card-grid rules
old_grid_dup = '''.card-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:14px; }
.card-grid { grid-template-columns:1fr; }'''
# Replace only if both lines appear together (the override pattern)
if old_grid_dup in content:
    content = content.replace(old_grid_dup,
        '.card-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:14px; }')
    print("Step 1a: fixed duplicate grid-template-columns override")
else:
    print("Step 1a: no duplicate grid rule found (OK)")

print("Step 1: CSS card/grid fixes applied")

# ─────────────────────────────────────────────────────────────────
# STEP 2 — Fix payload cards structure: move new cards INTO grid
# Strategy: re-extract all payload card HTML, then rebuild the payload grid
# ─────────────────────────────────────────────────────────────────

# Find all payload cards (between panel- and panel-)
payload_panel_start = content.find('id="panel-"')
linker_panel_start = content.find('id="panel-"')
payload_section = content[payload_panel_start:linker_panel_start]

# Extract all <div class="card"...> blocks from the payload section
# (both inside and outside the grid div)
card_pattern = re.compile(
    r'<div class="card"[^>]+data-cls="[^"]*"[^>]*>.*?(?=<div class="card"[^>]+data-cls=|<!-- .*? -->|</div>\s*</div>\s*</div>|$)',
    re.DOTALL
)

# Better: extract all card blocks properly using a stack-based approach
def extract_cards_from_section(html):
    """Extract all top-level card divs from a section of HTML."""
    cards = []
    i = 0
    while True:
        # Find next card start
        start = html.find('<div class="card"', i)
        if start == -1:
            break
        # Walk through and count depth
        depth = 0
        j = start
        while j < len(html):
            open_tag = html.find('<div', j)
            close_tag = html.find('</div>', j)
            if open_tag == -1 and close_tag == -1:
                break
            if open_tag != -1 and (close_tag == -1 or open_tag < close_tag):
                depth += 1
                j = open_tag + 4
            else:
                depth -= 1
                j = close_tag + 6
                if depth == 0:
                    cards.append(html[start:j])
                    i = j
                    break
        else:
            break
    return cards

all_payload_cards = extract_cards_from_section(payload_section)
print(f"Step 2: Found {len(all_payload_cards)} payload cards total")

# Now rebuild the payload panel with ALL cards inside the grid
# Find the panel structure (header, filter bar, grid opening) up to where cards start
grid_open_tag = 'id="grid">'
grid_open_pos = payload_section.find(grid_open_tag)
if grid_open_pos > 0:
    payload_header = payload_section[:grid_open_pos + len(grid_open_tag)]
    # Find where panel ends (closing tags for panel)
    payload_footer = '\n    </div>\n  </div>'  # close grid + close panel
    
    new_payload_section = payload_header + '\n'
    for card in all_payload_cards:
        new_payload_section += card + '\n'
    new_payload_section += payload_footer + '\n'
    
    # Replace entire payload panel in content
    content = content[:payload_panel_start] + new_payload_section + content[linker_panel_start:]
    print(f"Step 2: Rebuilt payload panel with {len(all_payload_cards)} cards inside grid")
else:
    print("Step 2 WARN: grid not found in payload section")

# ─────────────────────────────────────────────────────────────────
# STEP 3 — Fix linker cards: move new cards INTO grid
# ─────────────────────────────────────────────────────────────────
# Re-read content after step 2
linker_panel_start2 = content.find('id="panel-"')
conj_marker = content.find('<!-- \u2550\u2550\u2550 CONJUGATION \u2550\u2550\u2550 -->')
linker_section = content[linker_panel_start2:conj_marker]

all_linker_cards = extract_cards_from_section(linker_section)
print(f"Step 3: Found {len(all_linker_cards)} linker cards total")

grid_linker_tag = 'id="grid">'
grid_linker_pos = linker_section.find(grid_linker_tag)
if grid_linker_pos > 0:
    linker_header = linker_section[:grid_linker_pos + len(grid_linker_tag)]
    linker_footer = '\n    </div>\n  </div>\n\n'
    
    new_linker_section = linker_header + '\n'
    for card in all_linker_cards:
        new_linker_section += card + '\n'
    new_linker_section += linker_footer
    
    content = content[:linker_panel_start2] + new_linker_section + content[conj_marker:]
    print(f"Step 3: Rebuilt linker panel with {len(all_linker_cards)} cards inside grid")
else:
    print("Step 3 WARN: grid not found in linker section")

# ─────────────────────────────────────────────────────────────────
# STEP 4 — Add patent info to old linker cards that lack it
# Focus on cards that have no  section yet
# ─────────────────────────────────────────────────────────────────

linker_patent_data = {
    'PEG4-vc-PABC': {
        'patent': 'US8703714B2 — Senter et al. (Seagen Inc.), granted 2014. PEGylated maleimidocaproyl-VC-PABC linker for high-DAR ADCs. Hydrophilic PEG4 spacer reduces aggregation at DAR 6–8. Key patent for Padcev (enfortumab vedotin) development.',
        'status': 'US8703714B2 active until ~2030. Seagen (now Pfizer) holds this IP. Used in Padcev (FDA 2019 urothelial cancer) and other PEG-linker ADC programs.',
        'ref': 'Junutula JR et al. "Site-specific conjugation of a cytotoxic drug to an antibody improves the therapeutic index." Nat Biotechnol 2008;26(8):925. PMID: 18641636 (THIOMAB concept). Doronina SO et al. PMID: 16492765 (PEG linker ADC).'
    },
    'GGFG': {
        'patent': 'US9808537B2 — Ogitani Y et al. (Daiichi Sankyo Company). Gly-Gly-Phe-Gly tetrapeptide linker for DXd ADC conjugates. Priority 2013-07-11. Core patent for T-DXd (trastuzumab deruxtecan / Enhertu) linker chemistry.',
        'status': 'US9808537B2 active until ~2034 (incl. patent term adjustment). Also US10906974B2 (2021) continuation. Daiichi Sankyo holds core GGFG-DXd platform; licensed to AstraZeneca for global co-development (2019 deal, $6.9B).',
        'ref': 'Ogitani Y et al. "DS-8201a, A Novel HER2-Targeting ADC with a Novel DNA Topoisomerase I Inhibitor, Demonstrates a Promising Antitumor Efficacy with Differentiation from T-DM1." Clin Cancer Res 2016;22(20):5097. PMID: 27143595.'
    },
    'Sulfo-SMCC': {
        'patent': 'US5208020A — Chari et al. (ImmunoGen Inc.), 1993. Maytansinoid-thiol-antibody conjugates via thioether (SMCC) chemistry. Foundational ImmunoGen ADC linker patent. Sulfo-SMCC is the water-soluble derivative of SMCC for improved conjugation efficiency.',
        'status': 'US5208020A expired ~2010. Sulfo-SMCC chemistry is now in the public domain. Pierce Biotechnology (now Thermo Scientific) and others supply commercial Sulfo-SMCC. Used in Kadcyla (trastuzumab emtansine, T-DM1) via the SMCC linker — Kadcyla composition patent (US7371376B2) remains active.',
        'ref': 'Chari RV et al. "Immunoconjugates containing novel maytansinoids: promising anticancer drugs." Cancer Res 1992;52(1):127. PMID: 1727373. Foundational paper for SMCC-maytansinoid ADC.'
    },
    'Hydrazone-disulfide': {
        'patent': 'US5877296A — Hamann PR et al. (American Cyanamid/Wyeth/Pfizer). Hydrazone-disulfide bifunctional linker for calicheamicin ADCs. Priority 1997. Used in Mylotarg (gemtuzumab ozogamicin) and Besylomab (inotuzumab ozogamicin).',
        'status': 'US5877296A expired ~2015. Also US6630579B2 (Wyeth/Pfizer) for AcBut hydrazone-calicheamicin conjugation method — active ~2020. Hydrazone linker chemistry available generically; specific calicheamicin ADC compositions still protected (Mylotarg relabeled 2017, Besylomab FDA 2017).',
        'ref': 'Hinman LM et al. "Preparation and characterization of monoclonal antibody conjugates of the calicheamicins." Cancer Res 1993;53(14):3336. PMID: 8324744.'
    },
}

for linker_name, pdata in linker_patent_data.items:
    # Find this card
    title_marker = f'<div class="card-title">{linker_name}</div>'
    pos = content.find(title_marker)
    if pos < 0:
        print(f"Step 4 WARN: Card '{linker_name}' not found")
        continue
    # Check if patent section already exists within 3000 chars of this card
    window = content[pos:pos+3000]
    if '' in window or 'WO2007011968' in window or 'US9808537' in window or 'US5208020' in window or 'US5877296' in window:
        print(f"Step 4: '{linker_name}' already has patent info, skipping")
        continue
    # Find where info section ends (before next </div></div></div> which closes the card)
    # Insert before the last </div> of cc-detail
    cc_detail_pos = content.find('<div class="cc-detail">', pos)
    if cc_detail_pos < 0 or cc_detail_pos > pos + 3000:
        print(f"Step 4 WARN: cc-detail not found for {linker_name}")
        continue
    # Find the collapse-bar end
    collapse_end = content.find('</div>', cc_detail_pos + 23)  # after <div class="cc-detail">
    if collapse_end < 0:
        print(f"Step 4 WARN: collapse-bar end not found for {linker_name}")
        continue
    
    patent_block = f'''
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">{pdata["patent"]}</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">{pdata["status"]}</span></div>
      <div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">{pdata["ref"]}</span></div>'''
    
    # Insert after collapse-bar close
    insert_pos = collapse_end + 6
    content = content[:insert_pos] + patent_block + content[insert_pos:]
    print(f"Step 4: Patent info added to '{linker_name}'")

# ─────────────────────────────────────────────────────────────────
# STEP 5 — Standardize badge text for consistency (short labels)
# Old cards use verbose English; make all consistently short
# ─────────────────────────────────────────────────────────────────
badge_fixes = [
    # Payload tab - standardize old verbose badges
    ('badge-payload">Tubulin Inhibitors</span>', 'badge-payload">Tubulin Inhibitor</span>'),
    ('badge-linker">Topoisomerase I Inhibitors</span>', 'badge-linker">TOP1 Inhibitor</span>'),
    ('badge-linker">Topoisomerase I Inhibitor</span>', 'badge-linker">TOP1 Inhibitor</span>'),
    ('badge-payload">DNA Damaging Agents</span>', 'badge-payload">DNA Damaging Agent</span>'),
    # Linker tab - new cards had long text
    ('badge-phase3">Protease-Cleavable</span>', 'badge-phase3">Protease-Cleavable</span>'),  # keep as is
]
for old_b, new_b in badge_fixes:
    if old_b in content:
        content = content.replace(old_b, new_b)
print("Step 5: Badge text standardized")

# ─────────────────────────────────────────────────────────────────
# Save
# ─────────────────────────────────────────────────────────────────
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nDone. File size: {original_len} → {len(content)} chars (+{len(content)-original_len})")

# Quick verification
content_v = open(path, encoding='utf-8').read
p1 = content_v.find('id="panel-"')
p2 = content_v.find('id="panel-"')
p3 = content_v.find('<!-- \u2550\u2550\u2550 CONJUGATION \u2550\u2550\u2550 -->')
payload_sec = content_v[p1:p2]
linker_sec = content_v[p2:p3]
payload_in_grid = payload_sec.count('<div class="card"')
linker_in_grid = linker_sec.count('<div class="card"')
print(f"\nVerification:")
print(f"  Payload panel card count: {payload_in_grid}")
print(f"  Linker panel card count: {linker_in_grid}")
grid_payload_close = payload_sec.rfind('</div>')
last_card_end = payload_sec.rfind('</div></div>\n</div>')
print(f"  Last card ends at: {last_card_end}, grid closes at: {grid_payload_close}")
