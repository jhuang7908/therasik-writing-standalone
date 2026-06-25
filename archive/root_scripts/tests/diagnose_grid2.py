
import re

path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the programs panel
panel_start = content.find('<div class="tab-panel active" id="panel-programs">')
panel_end = content.find('<div class="tab-panel"', panel_start + 10)
panel = content[panel_start:panel_end]

# Find where the card-grid starts
grid_start = panel.find('<div class="card-grid" id="gridPrograms">')
print(f"Grid starts at offset: {grid_start}")

# Get grid content
grid_content = panel[grid_start:]

# Check if there's anything between cards that's NOT a .card div
# Find all card starts and look for non-card content between them
card_positions = [m.start() for m in re.finditer(r'<div class="card"', grid_content)]
print(f"Number of card divs in grid: {len(card_positions)}")

# Look at the first few cards to check structure
# Count divs in each card to see if any are unbalanced
lines = panel.split('\n')
in_grid = False
card_num = 0
depth_in_grid = 0
card_divs = 0
card_start_line = None

for i, line in enumerate(lines):
    if 'id="gridPrograms"' in line:
        in_grid = True
        depth_in_grid = 0
        continue
    
    if in_grid:
        if '<div class="card"' in line:
            card_num += 1
            card_start_line = i
            card_divs = 1  # count the opening card div
        elif card_num > 0:
            opens = line.count('<div')
            closes = line.count('</div>')
            card_divs += opens - closes
            if card_divs == 0 and card_num > 0:
                # Card just closed
                if card_num <= 5 or card_num >= 95:
                    print(f"Card {card_num} spans lines {card_start_line+1} to {i+1} in panel")
                card_start_line = None

print(f"\nTotal cards counted: {card_num}")

# Now check whether any element appears OUTSIDE card divs but inside the grid
# by looking for non-card, non-whitespace content between card divs
import re
grid_section = panel[grid_start:]
# Remove all card contents
# Find text between </div> closing a card and next <div class="card"
between = re.findall(r'</div>\s*\n?\s*(?!<div class="card"|$)(.*?)(?=<div class="card"|</div>)', grid_section[:card_positions[-1] + 1000 if len(card_positions) > 0 else -1])
non_empty = [b for b in between if b.strip()]
if non_empty:
    print("\nContent found BETWEEN cards in grid:")
    for b in non_empty[:10]:
        print(f"  '{b[:100]}'")
else:
    print("\nNo non-card content found between cards in grid.")
