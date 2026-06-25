
import re

path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Track depth and find where page div closes
depth = 0
page_open_line = None

for i, line in enumerate(lines):
    opens = len(re.findall(r'<div[\s>]', line))
    closes = line.count('</div>')
    
    old_depth = depth
    depth += opens - closes
    
    if 'class="page"' in line and 'max-width' in line:
        page_open_line = i + 1
        page_open_depth = old_depth
        print(f"Line {i+1}: .page div OPENS (depth {old_depth} -> {depth})")
    
    # Check if depth went from 1 to 0 after page opened
    if page_open_line and old_depth == 1 and depth == 0:
        print(f"Line {i+1}: DEPTH DROPS TO 0 - .page div likely CLOSED here")
        print(f"  Content: {line.rstrip()[:100]}")
        # Show context
        for j in range(max(0, i-3), min(len(lines), i+3)):
            print(f"    L{j+1}: {lines[j].rstrip()[:100]}")
        print()

print(f"\nFinal depth: {depth}")

# Also check what's between antigen panel end and payload panel start
ag_end = None
payload_start = None
for i, line in enumerate(lines):
    if 'id="panel-antigens"' in line:
        ag_panel_start = i + 1
    if 'id="panel-payloads"' in line:
        payload_start = i + 1

if ag_panel_start and payload_start:
    print(f"\nAntigens panel starts at: {ag_panel_start}")
    print(f"Payloads panel starts at: {payload_start}")
    print(f"\nContent between antigens panel end and payloads panel start:")
    # Find where antigens panel ends
    depth2 = 0
    for i in range(ag_panel_start, payload_start):
        line = lines[i]
        opens = len(re.findall(r'<div[\s>]', line))
        closes = line.count('</div>')
        depth2 += opens - closes
        if depth2 < 0 and i < payload_start - 5:
            print(f"  L{i+1}: depth={depth2} {line.rstrip()[:100]}")
