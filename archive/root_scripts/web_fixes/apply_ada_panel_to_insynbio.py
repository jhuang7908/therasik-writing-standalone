"""
Apply the same ADA panel upgrade to insynbio-web-source/ada_database.html
by syncing it from the updated Therasik version (same panel JS logic).
The two files share identical panel/JS code; only the nav/hero differ.
"""
import re

SRC = r'therasik-web-source\Therasik_ADA_Database.html'
DST = r'insynbio-web-source\ada_database.html'

src = open(SRC, encoding='utf-8').read()
dst = open(DST, encoding='utf-8').read()

# Extract the <style> block from src
src_style = re.search(r'(<style>.*?</style>)', src, re.DOTALL)
dst_style = re.search(r'(<style>.*?</style>)', dst, re.DOTALL)

# Extract the <script> block (main data+panel JS)
src_script = re.search(r'(<script>\s*// Security.*?</script>)', src, re.DOTALL)
dst_script = re.search(r'(<script>\s*// Security.*?</script>)', dst, re.DOTALL)

n = 0
if src_style and dst_style:
    dst = dst.replace(dst_style.group(1), src_style.group(1), 1)
    n += 1
    print("Replaced <style> block")
else:
    print("WARNING: Could not find style block")

if src_script and dst_script:
    dst = dst.replace(dst_script.group(1), src_script.group(1), 1)
    n += 1
    print("Replaced <script> block")
else:
    print("WARNING: Could not find script block")

# Also sync the detail panel HTML (dp-body, dp-name, etc.)
src_panel_html = re.search(
    r'(<!-- ── Detail panel ──.*?<!-- ── Footer note ──)',
    src, re.DOTALL
)
dst_panel_html = re.search(
    r'(<!-- ── Detail panel ──.*?<!-- ── Footer note ──)',
    dst, re.DOTALL
)
if src_panel_html and dst_panel_html:
    dst = dst.replace(dst_panel_html.group(1), src_panel_html.group(1), 1)
    n += 1
    print("Replaced detail panel HTML")
else:
    print("WARNING: Could not find panel HTML section")

open(DST, 'w', encoding='utf-8').write(dst)
print(f"Done ({n} blocks replaced) → {DST}")

# Quick verify
txt = open(DST, encoding='utf-8').read()
print(f"  mkSection: {'mkSection' in txt}")
print(f"  collapsed: {'detail-section.collapsed' in txt}")
print(f"  fc_mutation_notes: {'fc_mutation_notes' in txt}")
print(f"  CDR-H1: {'CDR-H1' in txt}")
