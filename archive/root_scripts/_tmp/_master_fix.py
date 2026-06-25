"""
Master fix script: align Payload/Linker/Conjugation/Experiments tabs 
with the visual and structural quality of Programs/Antigens tabs.
"""
import re

path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
content = open(path, encoding='utf-8').read

# ─────────────────────────────────────────────────────────
# 1. FIX STRUCTURAL BUGS
# ─────────────────────────────────────────────────────────

# Fix conjugation section title typo
content = content.replace(
    '<h2 class="section-title">nologies</h2>',
    '<h2 class="section-title">Conjugation Technologies</h2>'
)

# Fix conjugation section description mixed language
content = content.replace(
    'From stochastic cysteine to site-specific enzymatic (FGE, Sortase)  glycan remodeling — DAR homogeneity, CMC complexity,  patent / FTO analysis.',
    'From stochastic cysteine to site-specific enzymatic (FGE, Sortase) and glycan remodeling — DAR homogeneity, CMC complexity, and patent / FTO analysis.'
)

# Fix experiments section description mixed language
content = content.replace(
    'In vitro  in vivo experimental methods for ADC characterization, from binding assays to PDX efficacy models.',
    'In vitro and in vivo experimental methods for ADC characterization, from binding assays to PDX efficacy models.'
)

# Fix conjugation filter — remove duplicate english options
old_filter = '''      <select class="filter-sel" id="filterConjHomo">
        <option value="">All homogeneity</option>
        <option value=""> (Very High, DAR CV&lt;5%)</option>
        <option value=""> (High, DAR CV 5–10%)</option>
        <option value=""> (Medium, DAR CV 10–20%)</option>
        <option value=""> (Low, DAR CV&gt;20%)</option>
    <option value="very_high">Very High</option>
    <option value="high">High</option>
    <option value="moderate">Moderate</option>
    <option value="low">Low</option>
      </select>'''
new_filter = '''      <select class="filter-sel" id="filterConjHomo">
        <option value="">All DAR Homogeneity</option>
        <option value=""> — Very High (DAR CV &lt;5%)</option>
        <option value=""> — High (DAR CV 5–10%)</option>
        <option value=""> — Medium (DAR CV 10–20%)</option>
        <option value=""> — Low (DAR CV &gt;20%)</option>
      </select>'''
content = content.replace(old_filter, new_filter)

# ─────────────────────────────────────────────────────────
# 2. FIX DOUBLE-ESCAPED HTML ENTITIES
# ─────────────────────────────────────────────────────────
# &amp;gt; → &gt;  and  &amp;lt; → &lt;  and  &amp;#x27; → &#x27;
content = content.replace('&amp;gt;', '&gt;')
content = content.replace('&amp;lt;', '&lt;')
content = content.replace('&amp;#x27;', '&#x27;')

print("✓ Fixed structural bugs and HTML entities")

# ─────────────────────────────────────────────────────────
# 3. FIX CC-BRIEF FOR ALL PAYLOAD CARDS WITH ISSUES
# ─────────────────────────────────────────────────────────

# Map: title → clean cc-brief  (max ~90 chars, ≤3 items, no literal "…")
payload_briefs = {
    'MMAE': 'IC50: 0.1–1 nM ·  · : ',
    'DXd': 'IC50: 0.3 nM · Top I · : ',
    'PNU-159682': 'IC50: &lt;0.0001 nM ·  DNA /Topo II · ',
    'DGN462': 'IC50: &lt;0.001 nM · DNA  ·  · : ',
    'Exatecan': 'IC50: 0.3–3 nM · Top I · : ',
    'Belotecan': 'IC50: 1–10 nM · Top I · : ',
    'Topotecan': 'IC50: 5–50 nM · Top I · : ',
    'Alpha-amanitin': 'IC50: 0.001–0.01 nM · RNA Pol II · : ',
    'Thailanstatin A': 'IC50: 0.001–0.01 nM ·  SF3b  · G2/M ',
    'KSP71': 'IC50: 1–10 nM · KSP/Eg5  · ',
    'Navitoclax-derivative': 'IC50: 1–100 nM · Bcl-xL/Bcl-2  · ',
    'TLR7-agonist-1': 'EC50: 10–100 nM · TLR7  · （ISAC）',
    'STING-agonist-1': 'EC50: 1–50 nM · STING  · ',
    'Thorium-227': 'α  · : 40–80 μm · ',
    'Auristatin E': 'IC50: 0.5–5 nM ·  · : ',
}

for title, new_brief in payload_briefs.items:
    # Match: card title then eventually cc-brief
    pattern = rf'(<div class="card-title">{re.escape(title)}</div>.*?<div class="cc-brief">)[^<]*…[^<]*?(</div>)'
    replacement = rf'\g<1>{new_brief}\g<2>'
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    if new_content == content:
        # try without ellipsis at end (just too long)
        pattern2 = rf'(<div class="card-title">{re.escape(title)}</div>.*?<div class="cc-brief">)[^<]{{80,}}(</div>)'
        new_content = re.sub(pattern2, replacement, content, flags=re.DOTALL)
    if new_content != content:
        content = new_content
        print(f"  ✓ Payload cc-brief: {title}")
    else:
        print(f"  ✗ No match for payload: {title}")

# ─────────────────────────────────────────────────────────
# 4. FIX CC-BRIEF FOR ALL LINKER CARDS WITH ISSUES
# ─────────────────────────────────────────────────────────

linker_briefs = {
    'mc-val-cit-PABC': 't½: &gt;7 d  · : Cathepsin B · : ',
    'GGFG': 't½: &gt;7 d  · :  · ',
    'Glucuronide-MMAE': 't½: &gt;7 d · : β-Glucuronidase  · ',
    'VA-PABC': 't½: &gt;7 d · : Cathepsin B  · ',
    'Pyrophosphate-diester': 't½: – · :   · pH ',
    'Legumain-cleavable': 't½: &gt;7 d · : Legumain (Asn ) · ',
    'beta-galactoside-cleavable': 't½: &gt;7 d · : β-Galactosidase  · ',
    'Sulfatase-cleavable': 't½: &gt;7 d · :  · ',
    'Phosphatase-cleavable': 't½:  · : / · ',
    'Fmoc-vc-PABC': 't½:  (Fmoc ) · : Cathepsin B · ',
    'Dde-vc-PABC': 't½:  (Dde ) · : Cathepsin B · ',
    'Hydrazone-disulfide': 't½:  · : pH  + GSH  · ',
    'Thioether-cleavable': 't½:  · :  (GSH) · ',
    'Peptide-MMAF': 't½: &gt;7 d · : Cathepsin B ·  payload',
    'Mal-PEG4-NHS': 't½: &gt;7 d  · :  · PEG ',
    'SMPEG24': 't½: &gt;7 d  · :  ·  PEG ',
    'Sulfo-SMCC': 't½: &gt;10 d  · :  · Kadcyla ',
    'Ildc Ligase Genequantum': 'DAR: 2 ·  ·  iLDC ',
}

for title, new_brief in linker_briefs.items:
    # Match card title (could be partial match)
    # Need to handle case where title in HTML might differ
    # Use flexible pattern
    pattern = rf'(<div class="card-title">{re.escape(title)}[^<]*?</div>.*?<div class="cc-brief">)[^<]*?(</div>)'
    new_content = re.sub(pattern, rf'\g<1>{new_brief}\g<2>', content, flags=re.DOTALL)
    if new_content != content:
        content = new_content
        print(f"  ✓ Linker cc-brief: {title}")
    else:
        print(f"  ✗ No match for linker: {title}")

# ─────────────────────────────────────────────────────────
# 5. FIX CC-BRIEF FOR CONJUGATION CARDS WITH ISSUES
# ─────────────────────────────────────────────────────────

conj_briefs = {
    'Enzyme Fge Smartag': 'DAR: 2.0 · FGE  Cys →  (fGly) →  · ',
    'Ildc Ligase Genequantum': 'DAR: 2.0 · iLDC  · ',
}

for title, new_brief in conj_briefs.items:
    pattern = rf'(<div class="card-title">{re.escape(title)}[^<]*?</div>.*?<div class="cc-brief">)[^<]*?(</div>)'
    new_content = re.sub(pattern, rf'\g<1>{new_brief}\g<2>', content, flags=re.DOTALL)
    if new_content != content:
        content = new_content
        print(f"  ✓ Conj cc-brief: {title}")
    else:
        print(f"  ✗ No match for conj: {title}")

# ─────────────────────────────────────────────────────────
# 6. FIX CC-BRIEF FOR EXPERIMENTS CARDS
# ─────────────────────────────────────────────────────────

exp_briefs = {
    'Binding Affinity': ': SPR / BLI / FACS · KD : pM–nM · :  ADC vs ',
    'Bystander Effect': ': co-culture (/)·  ·  payload ',
}

for title, new_brief in exp_briefs.items:
    pattern = rf'(<div class="card-title">{re.escape(title)}</div>.*?<div class="cc-brief">)[^<]*?(</div>)'
    new_content = re.sub(pattern, rf'\g<1>{new_brief}\g<2>', content, flags=re.DOTALL)
    if new_content != content:
        content = new_content
        print(f"  ✓ Exp cc-brief: {title}")
    else:
        print(f"  ✗ No match for exp: {title}")

print("\n✓ cc-brief fixes applied")

# ─────────────────────────────────────────────────────────
# 7. ADD  TO CONJUGATION CARDS (all 22 cards missing it)
# ─────────────────────────────────────────────────────────

# Evidence levels for conjugation technologies
conj_evidence = {
    'Glycan Remodeling': '',
    'Unnatural Amino Acid': '',
    'Enzyme Fge Smartag': '',
    'Sortase A Mediated': '',
    'Ildc Ligase Genequantum': '',
    'Site Specific Engineered Cys': '',
    'Enzymatic Transglutaminase': '',
    'Ajicap': '',
    'Tub Tag Tubulin Ligase': '',
    'Stochastic Cysteine': '',
    'Lysine Coupling': '',
    'Thiobridge Polytherics': '',
    'C Lock Bms': '',
    'Snap Tag': '',
    'Platinum Based Linkage': '',
    'Ajicap V2': '',
    'Sortase A Nbe': '',
    'Formylglycine Smartag': '',
    'Glycoconnect Synaffix': '',
    'Pclick Technology': '',
    'Multi Arm Star Peg': '',
    'Thiobridge': '',
}

# Color map
color_map = {'': '#1a7a4a', '': '#b45309', '': '#991b1b'}
label_map = {'': '', '': '', '': ''}

added = 0
for title, level in conj_evidence.items:
    color = color_map.get(level, '#888')
    evidence_html = f'<div style="font-size:10px;color:{color};font-weight:600;margin-top:2px">：{level}</div>'
    
    # Find the card and check if it already has 
    pattern = rf'(<div class="card-title">{re.escape(title)}[^<]*?</div>.*?cc-brief">[^<]*</div>)((?!\s*<div[^>]*>))'
    def add_evidence(m):
        return m.group(1) + '\n    ' + evidence_html + m.group(2)
    
    new_content = re.sub(pattern, add_evidence, content, flags=re.DOTALL)
    if new_content != content:
        content = new_content
        added += 1

print(f"✓ Added  to {added} conjugation cards")

# ─────────────────────────────────────────────────────────
# 8. ADD  TO EXPERIMENTS CARDS  
# ─────────────────────────────────────────────────────────

exp_evidence = {
    'Binding Affinity': '',
    'Internalization': '',
    'Cytotoxicity': '',
    'Bystander Effect': '',
    'Plasma Stability': '',
    'Linker Cleavage': '',
    'Efficacy Models': '',
    'Pharmacokinetics Pk': '',
}

added = 0
for title, level in exp_evidence.items:
    color = color_map.get(level, '#888')
    evidence_html = f'<div style="font-size:10px;color:{color};font-weight:600;margin-top:2px">：{level}</div>'
    pattern = rf'(<div class="card-title">{re.escape(title)}[^<]*?</div>.*?cc-brief">[^<]*</div>)((?!\s*<div[^>]*>))'
    def add_evidence(m):
        return m.group(1) + '\n    ' + evidence_html + m.group(2)
    new_content = re.sub(pattern, add_evidence, content, flags=re.DOTALL)
    if new_content != content:
        content = new_content
        added += 1

print(f"✓ Added  to {added} experiments cards")

# ─────────────────────────────────────────────────────────
# 9. ADD BADGES TO EXPERIMENTS CARDS
# ─────────────────────────────────────────────────────────

exp_badges = {
    'Binding Affinity': ('Binding Assay', 'badge-target'),
    'Internalization': ('Cell Trafficking', 'badge-target'),
    'Cytotoxicity': ('Cell-Based', 'badge-target'),
    'Bystander Effect': ('Cell-Based', 'badge-target'),
    'Plasma Stability': ('PK/Stability', 'badge-linker'),
    'Linker Cleavage': ('Biochemical', 'badge-linker'),
    'Efficacy Models': ('In Vivo', 'badge-approved'),
    'Pharmacokinetics Pk': ('PK/PD', 'badge-linker'),
}

added = 0
for title, (badge_text, badge_class) in exp_badges.items:
    badge_html = f'<span class="badge {badge_class}">{badge_text}</span>'
    # Add badge to card-header — after card-title, if no badge present
    pattern = rf'(<div class="card-title">{re.escape(title)}</div>\s*)(</div>\s*<div class="card-body">)'
    def add_badge(m):
        return m.group(1) + badge_html + '\n  ' + m.group(2)
    new_content = re.sub(pattern, add_badge, content, flags=re.DOTALL)
    if new_content != content:
        content = new_content
        added += 1
    else:
        # Try header pattern without wrapping div
        pattern2 = rf'(<div class="card-header">\s*<div class="card-title">{re.escape(title)}</div>)(\s*</div>)'
        def add_badge2(m):
            return m.group(1) + '\n    ' + badge_html + m.group(2)
        new_content = re.sub(pattern2, add_badge2, content, flags=re.DOTALL)
        if new_content != content:
            content = new_content
            added += 1

print(f"✓ Added badges to {added} experiments cards")

# ─────────────────────────────────────────────────────────
# 10. ADD DEVELOPER SUBTITLES TO PAYLOAD CARDS
# ─────────────────────────────────────────────────────────

payload_subtitles = {
    'MMAE': 'Seagen / Pfizer · Adcetris, Padcev, Polivy',
    'DXd': 'Daiichi Sankyo · Enhertu (T-DXd)',
    'MMAD': 'AbbVie / ImmunoGen',
    'Auristatin F': 'Seagen ',
    'Auristatin E': 'Seagen ',
    'PF-06380101': 'Pfizer ',
    'Tubulysin A': 'Syntarga / Roche · ',
    'Tubulysin M': 'Syntarga · ',
    'Cryptophycin 52': 'Eli Lilly ',
    'PNU-159682': 'ADC Therapeutics · ',
    'DGN462': 'ImmunoGen · IMGN632 (mirvetuximab)',
    'Exatecan': 'Daiichi Sankyo · DS-8201 ',
    'Belotecan': 'CJ Healthcare ',
    'Topotecan': 'GSK /  ',
    'Alpha-amanitin': 'Heidelberg Pharma · ATAC ',
    'Thailanstatin A': 'NCI / ',
    'Spliceostatin A': 'NCI / ',
    'KSP71': 'Merck / ',
    'SB-743921': 'Cytokinetics / ',
    'Navitoclax-derivative': 'AbbVie · ',
    'TLR7-agonist-1': 'ADC Therapeutics / ',
    'STING-agonist-1': 'Bolt Biotherapeutics · BDC-1001',
    'Thorium-227': 'Bayer · Targeted Thorium Conjugate (TTC)',
    'Astatine-211': 'NovaBay /  ',
    'Radium-223': 'Bayer · Xofigo ',
    'Lead-212': 'Orano Med / ',
    'Bismuth-213': 'ORNL / ',
    'Saporin': 'Advanced Targeting Systems',
    'Gelonin': 'ImmunoGen ',
    'Diphtheria toxin': ' / IT ',
    'Ricin A chain': '',
    'Shiga toxin': '',
    'DM1 (Emtansine)': 'ImmunoGen · Kadcyla (T-DM1)',
    'DM4 (Ravtansine)': 'ImmunoGen · Elahere',
    'MMAF (Monomethyl Auristatin F)': 'Seagen / Pfizer ',
    'SN-38': 'Gilead · Trodelvy (Sacituzumab govitecan)',
    'Calicheamicin (γ1I)': 'Pfizer · Mylotarg, Besylomab',
    'PBD Dimer (SG3199 / Tesirine)': 'ADC Therapeutics · Zynlonta',
    'Lutetium-177 (¹⁷⁷Lu)': 'Novartis · Pluvicto (PSMA-617)',
    'PROTAC-ADC Payload (DAC-TPD)': ' · ',
}

added = 0
for title, subtitle in payload_subtitles.items:
    # Check if already has subtitle
    check_pattern = rf'class="card-title">{re.escape(title)}</div>\s*<div class="card-subtitle"'
    if re.search(check_pattern, content, re.DOTALL):
        continue  # already has subtitle
    
    # Add subtitle after card-title
    pattern = rf'(<div class="card-title">{re.escape(title)}</div>)(\s*<span class="badge)'
    subtitle_html = f'<div class="card-subtitle" style="font-size:11px;color:var(--primary)">{subtitle}</div>'
    
    new_content = re.sub(pattern, rf'\g<1>\n    {subtitle_html}\g<2>', content, flags=re.DOTALL)
    if new_content == content:
        # Card title div might be the only child in header div — add after title
        pattern2 = rf'(<div class="card-title">{re.escape(title)}</div>)(\s*</div>\s*<span class="badge)'
        new_content = re.sub(pattern2, rf'\g<1>\n    {subtitle_html}\g<2>', content, flags=re.DOTALL)
    if new_content != content:
        content = new_content
        added += 1

print(f"✓ Added developer subtitles to {added} payload cards")

# ─────────────────────────────────────────────────────────
# 11. ADD/UPDATE CSS FOR VISUAL PARITY
# ─────────────────────────────────────────────────────────

# Find the style block and add new CSS rules
new_css = '''
  /* ── Payload/Linker/Conj/Exp tab enhancements (align with Programs/Antigens) ── */
  .card { display:flex; flex-direction:column; }
  .card-body { flex:1; display:flex; flex-direction:column; }
  .cc-brief { -webkit-line-clamp:2; display:-webkit-box; -webkit-box-orient:vertical; overflow:hidden; }
  
  .card-subtitle { font-size:11px; color:var(--primary); margin-top:1px; font-weight:500; }
  
  /* Section header inside expanded card detail */
  .sec-hdr { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.6px; 
             color:#888; margin:10px 0 4px; border-top:1px solid #eee; padding-top:8px; }
  
  /* Consistent card header alignment */
  .card-header { align-items:flex-start; }
  .card-header > div { flex:1; min-width:0; }
  .card-title { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  
  /* Badge variants */
  .badge-conj { background:rgba(124,58,237,0.1); color:#5b21b6; }
  .badge-exp  { background:rgba(14,165,233,0.1); color:#0369a1; }
  
  /* Experiment tab card header */
  #panel-experiments .card-header { flex-wrap:wrap; gap:4px; }
'''

# Insert before closing </style>
style_close = content.find('</style>')
if style_close >= 0:
    content = content[:style_close] + new_css + content[style_close:]
    print("✓ Added CSS enhancements")

# ─────────────────────────────────────────────────────────
# 12. FIX AURISTATIN E (NO_EVIDENCE)
# ─────────────────────────────────────────────────────────
# It shows IC50: ? nM which needs fixing
old_ae = '<div class="cc-brief">IC50: ? nM · : ?</div>'
new_ae = '<div class="cc-brief">IC50: 0.5–5 nM ·  · : </div>'
if old_ae in content:
    content = content.replace(old_ae, new_ae)
    print("✓ Fixed Auristatin E cc-brief")

# Check if Auristatin E has  — add if missing
if 'Auristatin E' in content:
    ae_pattern = r'(<div class="card-title">Auristatin E</div>.*?cc-brief">[^<]*</div>)(\s*<span class="exp-toggle">)'
    def add_ae_evidence(m):
        ev = '<div style="font-size:10px;color:#1a7a4a;font-weight:600;margin-top:2px">：</div>'
        return m.group(1) + '\n    ' + ev + '\n    ' + m.group(2).lstrip
    new_content = re.sub(ae_pattern, add_ae_evidence, content, flags=re.DOTALL)
    if new_content != content:
        content = new_content
        print("✓ Added  to Auristatin E")

# ─────────────────────────────────────────────────────────
# 13. REPLACE INLINE SEC-HDR STYLE WITH CLASS WHERE POSSIBLE
# ─────────────────────────────────────────────────────────
# Replace verbose inline section header style with class
old_sec_style = 'style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"'
new_sec_style = 'class="sec-hdr"'
count_replaced = content.count(old_sec_style)
content = content.replace(old_sec_style, new_sec_style)
print(f"✓ Replaced {count_replaced} inline sec-hdr styles with class")

# ─────────────────────────────────────────────────────────
# 14. FIX BROKEN COLLAPSE-BAR IN MMAE CARD
# ─────────────────────────────────────────────────────────
# Looking for unclosed collapse-bar div
broken = '<div class="collapse-bar"><div class="collapse-progress"></div>\n      <div class="sec-hdr"'
fixed = '<div class="collapse-bar"><div class="collapse-progress"></div></div>\n      <div class="sec-hdr"'
if broken in content:
    content = content.replace(broken, fixed)
    print("✓ Fixed broken collapse-bar in MMAE card")
else:
    # Try with original style
    broken2 = '<div class="collapse-bar"><div class="collapse-progress"></div>\n      <div class="sec-hdr"'
    if broken2 in content:
        content = content.replace(broken2, fixed)
        print("✓ Fixed broken collapse-bar (variant)")
    else:
        print("  (collapse-bar check: no broken pattern found)")

# ─────────────────────────────────────────────────────────
# WRITE OUTPUT
# ─────────────────────────────────────────────────────────
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ All fixes written to Therasik_ADC_Database.html")
print(f"   File size: {len(content):,} bytes")
