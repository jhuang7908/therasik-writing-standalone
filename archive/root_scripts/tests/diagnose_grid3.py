
# Find ALL top-level elements inside the card-grid in the programs panel
# to detect anything outside of .card divs that might break the layout

path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Get the programs panel section
panel_start = content.find('<div class="tab-panel active" id="panel-programs">')
panel_end = content.find('<div class="tab-panel"', panel_start + 10)
panel = content[panel_start:panel_end]

# Find the card-grid
grid_start_offset = panel.find('<div class="card-grid" id="gridPrograms">')
grid_section = panel[grid_start_offset + len('<div class="card-grid" id="gridPrograms">'):]

# Parse top-level children of the grid
depth = 0
element_start = 0
i = 0
top_level_elements = []

while i < len(grid_section):
    if grid_section[i] == '<':
        # Check if it's a closing tag
        if i + 1 < len(grid_section) and grid_section[i+1] == '/':
            depth -= 1
            if depth == -1:
                # This is the closing tag of the grid itself
                print(f"Grid ends here, found {len(top_level_elements)} top-level elements")
                break
        else:
            # Check if it's self-closing
            end = grid_section.find('>', i)
            if end == -1:
                break
            tag_content = grid_section[i:end+1]
            if not tag_content.endswith('/>'):  # Not self-closing
                depth += 1
                if depth == 1:
                    # This is a top-level element
                    end_of_element = grid_section.find('>', i)
                    first_line = grid_section[i:min(i+150, end_of_element+1)]
                    top_level_elements.append((i, first_line.strip()[:100]))
    i += 1

print(f"\nTotal top-level elements in grid: {len(top_level_elements)}")
print("\nFirst 5:")
for idx, (pos, el) in enumerate(top_level_elements[:5]):
    print(f"  {idx+1}: {el}")
print("\nLast 5:")
for idx, (pos, el) in enumerate(top_level_elements[-5:]):
    print(f"  {len(top_level_elements)-4+idx}: {el}")

# Check if any top-level element is NOT a card
non_cards = [(i, el) for i, (pos, el) in enumerate(top_level_elements) if 'class="card"' not in el]
if non_cards:
    print(f"\nNon-card top-level elements ({len(non_cards)} found):")
    for idx, el in non_cards[:10]:
        print(f"  Element #{idx+1}: {el}")
else:
    print("\nAll top-level elements are .card divs - grid structure is clean")
