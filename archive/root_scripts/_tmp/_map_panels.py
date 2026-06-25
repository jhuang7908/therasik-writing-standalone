"""Map exact panel boundaries and find structural issues."""
import re
path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
content = open(path, encoding='utf-8').read()

# Find all panel IDs
panels = [(m.start(), m.group(1)) for m in re.finditer(r'id="(panel-[^"]+)"', content)]
print("=== PANEL POSITIONS ===")
for pos, pid in panels:
    print(f"  {pos:8d}: {pid}")

# Find ctrl-rows
ctrl_rows = [(m.start(),) for m in re.finditer(r'<div class="ctrl-row"', content)]
print(f"\n=== CTRL-ROW POSITIONS ({len(ctrl_rows)} total) ===")
for (pos,) in ctrl_rows:
    # Get the search input id within 200 chars
    snippet = content[pos:pos+300]
    sid = re.search(r'id="(search[^"]*)"', snippet)
    fid = re.search(r'id="(filter[^"]*)"', snippet)
    print(f"  {pos:8d}: search={sid.group(1) if sid else 'NONE'}, filter={fid.group(1) if fid else 'NONE'}")

# Find grid IDs
grids = [(m.start(), m.group(1)) for m in re.finditer(r'id="(grid[^"]+)"', content)]
print(f"\n=== GRID POSITIONS ===")
for pos, gid in grids:
    print(f"  {pos:8d}: {gid}")

# Check what panel each ctrl-row belongs to
print("\n=== CTRL-ROW TO PANEL MAPPING ===")
panel_positions = [(pos, pid) for pos, pid in panels]
for (pos,) in ctrl_rows:
    # Find which panel this ctrl-row is inside
    containing_panel = None
    for ppos, pid in reversed(panel_positions):
        if ppos < pos:
            containing_panel = (ppos, pid)
            break
    snippet = content[pos:pos+300]
    sid = re.search(r'id="(search[^"]*)"', snippet)
    fid = re.search(r'id="(filter[^"]*)"', snippet)
    print(f"  ctrl-row@{pos} in {containing_panel[1] if containing_panel else 'UNKNOWN'}: "
          f"search={sid.group(1) if sid else 'NONE'}, filter={fid.group(1) if fid else 'NONE'}")
