
import re

path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the programs panel
start = content.find('<div class="tab-panel active" id="panel-programs">')
end = content.find('<div class="tab-panel"', start + 10)

panel = content[start:end]
lines = panel.split('\n')

# Find where card-grid starts and ends relative to cards
in_grid = False
grid_depth = 0
card_count_inside = 0
card_count_outside = 0
grid_end_line = None
for i, line in enumerate(lines):
    if 'id="gridPrograms"' in line:
        in_grid = True
        grid_depth = 0
        print(f"Grid starts at line {i+1}")
        continue
    if in_grid:
        opens = line.count('<div')
        closes = line.count('</div>')
        grid_depth += opens - closes
        if 'class="card"' in line or 'class="card ' in line:
            card_count_inside += 1
        if grid_depth < 0:
            in_grid = False
            grid_end_line = i + 1
            print(f"Grid CLOSES at panel-relative line {i+1}: {line.strip()[:80]}")
            break
    else:
        if 'class="card"' in line or 'class="card ' in line:
            card_count_outside += 1

print(f"Cards INSIDE grid: {card_count_inside}")
print(f"Cards OUTSIDE grid (after close): {card_count_outside}")

# Find total cards in programs panel
total_cards = panel.count('onclick="toggleCard(this)"')
print(f"Total cards in programs panel: {total_cards}")

# Show context around where grid closes
if grid_end_line:
    print("\nContext around grid close:")
    for i in range(max(0, grid_end_line-5), min(len(lines), grid_end_line+5)):
        print(f"  {i+1}: {lines[i][:100]}")
