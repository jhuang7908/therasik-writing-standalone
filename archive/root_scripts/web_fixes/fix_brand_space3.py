import glob
import re

html_files = glob.glob("docs/Therasik_*.html") + ["docs/therasik_index.html"]

for file in html_files:
    with open(file, "r", encoding="utf-8") as f:
        content = f.read

    # The user says "therasiklogo salogon"
    # This means they are wrapping. Let's check the CSS for .brand and .slogan
    # In therasik_index.html, .brand is `display: flex; align-items: center; flex-wrap: nowrap;`
    # But maybe the slogan is causing wrapping because of its container?
    # Let's fix the CSS in all files to ensure they are on one line.
    
    # We want them to be on ONE line. The user said "therasiklogo salogon" (Therasik's logo and slogan are two rows, not one row) - implying they *should* be one row but are currently two rows.
    
    if '.top-header .brand {' in content:
        # It's already in the CSS block, let's make sure it has white-space: nowrap
        content = re.sub(r'\.top-header \.brand \{[^}]+\}', '.top-header .brand { font-family: \'Cormorant Garamond\', Georgia, serif; font-weight: 700; font-size: 26px; letter-spacing: -0.03em; display: flex; align-items: center; flex-wrap: nowrap; min-width: max-content; white-space: nowrap; }', content)
        content = re.sub(r'\.top-header \.slogan \{[^}]+\}', '.top-header .slogan { font-size: 14px; color: var(--text-muted); padding-left: 14px; border-left: 1px solid var(--border); margin-left: 14px; font-weight: 600; white-space: nowrap; display: inline-flex; align-items: center; flex-shrink: 0; }', content)
    
    # Also check if there's any other CSS for .brand
    if '.brand {' in content and '.top-header .brand {' not in content:
        content = re.sub(r'\.brand \{[^}]+\}', '.brand { font-family: \'Cormorant Garamond\', Georgia, serif; font-weight: 700; font-size: 26px; letter-spacing: -0.03em; display: flex; align-items: center; flex-wrap: nowrap; min-width: max-content; white-space: nowrap; }', content)
        content = re.sub(r'\.slogan \{[^}]+\}', '.slogan { font-size: 14px; color: var(--text-muted); padding-left: 14px; border-left: 1px solid var(--border); margin-left: 14px; font-weight: 600; white-space: nowrap; display: inline-flex; align-items: center; flex-shrink: 0; }', content)

    with open(file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Fixed CSS for brand and slogan in {file}")
