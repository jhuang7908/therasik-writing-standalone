"""Read sample cards from each tab to compare structure and CSS."""
path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
content = open(path, encoding='utf-8').read()

# Grid boundaries
grids = {
    'programs':    (21625,  199611),
    'antigens':   (199611,  448503),
    'payload':    (448503,  629096),
    'linker':     (629096,  742044),
    'conjugation':(742044,  802945),
    'experiments':(802945,  len(content)),
}

for name, (start, end) in grids.items():
    sec = content[start:end]
    # Count cards
    import re
    cards = re.findall(r'<div class="card"', sec)
    
    # Sample first card structure
    first_card_start = sec.find('<div class="card"')
    if first_card_start >= 0:
        # Find card-body content
        body_pos = sec.find('<div class="card-body">', first_card_start)
        brief_pos = sec.find('class="cc-brief"', first_card_start)
        has_subtitle = 'card-subtitle' in sec[first_card_start:first_card_start+500]
        has_tags = 'badge-target' in sec[first_card_start:first_card_start+500] or 'badge-' in sec[first_card_start:first_card_start+300]
        has_info_rows = 'info-row' in sec[first_card_start:first_card_start+3000]
        
        # Count info-row types in first card
        card_block = sec[first_card_start:first_card_start+4000]
        card_end = card_block.find('\n</div>\n</div>\n</div>\n</div>')
        if card_end > 0:
            card_block = card_block[:card_end]
        info_rows = len(re.findall(r'info-row', card_block))
        sections = len(re.findall(r'font-weight:700.*?uppercase', card_block))
        
        print(f"\n=== {name.upper()} ({len(cards)} cards) ===")
        print(f"  has subtitle: {has_subtitle}")
        print(f"  has badge tags: {has_tags}")
        print(f"  has info-rows: {has_info_rows} (count: {info_rows})")
        print(f"  section headers: {sections}")
        print(f"  First 400 chars of first card:")
        print(f"  {sec[first_card_start:first_card_start+400]}")
