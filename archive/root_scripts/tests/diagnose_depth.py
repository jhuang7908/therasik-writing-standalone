
# Count all divs in the file and verify the overall structure balance
# Also check the .page container

path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find key structural elements
page_start = None
page_end = None
depth = 0

# Track depth at key points
key_points = {}

for i, line in enumerate(lines):
    import re
    # Count div opens/closes (not self-closing)
    opens = len(re.findall(r'<div[\s>]', line))
    closes = line.count('</div>')
    
    old_depth = depth
    depth += opens - closes
    
    if 'class="page"' in line and 'max-width' not in line:
        page_start = i + 1
        key_points['page_open'] = (i+1, old_depth, depth)
    
    if 'id="panel-programs"' in line:
        key_points['programs_panel'] = (i+1, old_depth, depth)
    
    if 'id="gridPrograms"' in line:
        key_points['gridPrograms'] = (i+1, old_depth, depth)
    
    if 'id="panel-antigens"' in line:
        key_points['antigens_panel'] = (i+1, old_depth, depth)
    
    if 'id="panel-payloads"' in line:
        key_points['payloads_panel'] = (i+1, old_depth, depth)
    
    if 'id="panel-linkers"' in line:
        key_points['linkers_panel'] = (i+1, old_depth, depth)
    
    if 'id="panel-conjugation"' in line:
        key_points['conjugation_panel'] = (i+1, old_depth, depth)
    
    if 'id="panel-experiments"' in line:
        key_points['experiments_panel'] = (i+1, old_depth, depth)

print("Depth tracking at key elements (depth AFTER line processed):")
for name, (lineno, before, after) in key_points.items():
    print(f"  Line {lineno}: {name} (depth: {before} -> {after})")

print(f"\nFinal depth after all lines: {depth}")
print("(Expected: 0 for perfectly balanced HTML)")

# Also check the range lines 8001-8010
print("\nLines 8001-8010 with depth tracking:")
depth2 = 0
# Need to compute depth up to line 8000
for i, line in enumerate(lines[:7999]):
    opens = len(re.findall(r'<div[\s>]', line))
    closes = line.count('</div>')
    depth2 += opens - closes

for i, line in enumerate(lines[7999:8009]):
    import re
    lineno = i + 8000
    opens = len(re.findall(r'<div[\s>]', line))
    closes = line.count('</div>')
    depth2 += opens - closes
    print(f"  Line {lineno}: depth={depth2} | {line.rstrip()[:80]}")
