import re

c = open(r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html', encoding='utf-8').read()

# Count filter options = distinct targets / stages
targets = re.findall(r'<option value="([^"]+)">.*?</option>', c)
print(f'Filter options total: {len(targets)}')

# Find where actual program rows/cards start
# Look for a pattern like the first drug entry
idx = c.find('T-DM1')
if idx > 0:
    print(f'\nT-DM1 context:')
    print(repr(c[max(0,idx-100):idx+300]))

# Count grid/table entries by looking for repeated structural patterns
# The page seems to use a dynamic table rendered by JS - check if data is inline in HTML
# Count all <tr class= patterns (including dynamic rows)
trs_with_class = re.findall(r'<tr\s+class=', c)
print(f'\n<tr class=... : {len(trs_with_class)}')

# Count number of option values for stage filter
stage_opts = re.findall(r'filterStage.*?</select>', c, re.DOTALL)
if stage_opts:
    stages = re.findall(r'<option value="([^"]+)"', stage_opts[0])
    print(f'Stage options: {stages}')

# Target count
target_sel = re.findall(r'filterTarget.*?</select>', c, re.DOTALL)
if target_sel:
    tgt_vals = re.findall(r'<option value="([^"]+)"', target_sel[0])
    print(f'Targets: {len(tgt_vals)}: {tgt_vals}')

# Count cards by looking for a repeating data pattern
# Each program likely has a data-name or similar
data_items = re.findall(r'data-stage="([^"]+)"', c)
print(f'\ndata-stage entries: {len(data_items)}')
data_names = re.findall(r'data-name="([^"]+)"', c)
print(f'data-name entries: {len(data_names)}, first 5: {data_names[:5]}')
