"""
Fix two issues across all InSynBio HTML pages:
1. Mobile dropdown sub-menus were being shown flat (opacity:1 visibility:visible) - hide them instead
2. Logo font-size and header height consistency
"""
import re
from pathlib import Path

SRC = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source")

# Old rule that expands all dropdown menus on mobile (very bad UX)
OLD_DD = (
    r"\.nav-dropdown \.dropdown-menu,\s*\.std-nav-dd \.std-dd-menu\s*\{"
    r"\s*position: static !important;[^}]+\}"
)
NEW_DD = ".nav-dropdown .dropdown-menu, .std-nav-dd .std-dd-menu { display: none !important; }"

# Also fix logo font-size if still at 28px
OLD_FONT = "font-size: 28px !important; /* Increased font size */"
NEW_FONT = "font-size: 17px !important;"

# Fix header height if still at 80px (V6 block)
OLD_H = 'height: 80px !important; /* Increased height slightly for larger logo */'
NEW_H = 'height: 68px !important;'

# Fix body padding-top from 80px to 68px
OLD_PT80 = "padding-top: 80px; ; overflow-x: hidden;"
NEW_PT68 = "padding-top: 68px; overflow-x: hidden;"

OLD_PT80b = "padding-top: 80px; overflow-x: hidden;"
NEW_PT68b = "padding-top: 68px; overflow-x: hidden;"

files_fixed = 0
for html_file in sorted(SRC.glob("*.html")):
    content = html_file.read_text(encoding="utf-8")
    original = content
    
    # Fix 1: Hide dropdown menus on mobile instead of showing flat
    content_new = re.sub(OLD_DD, NEW_DD, content, flags=re.DOTALL)
    if content_new != content:
        content = content_new
    
    # Fix 2: Logo font-size 28px → 17px
    content = content.replace(OLD_FONT, NEW_FONT)
    
    # Fix 3: Header height 80px → 68px (V6 block specific text)
    content = content.replace(OLD_H, NEW_H)
    
    # Fix 4: body padding-top
    content = content.replace(OLD_PT80, NEW_PT68)
    content = content.replace(OLD_PT80b, NEW_PT68b)
    
    if content != original:
        html_file.write_text(content, encoding="utf-8")
        files_fixed += 1
        print(f"  Fixed: {html_file.name}")

print(f"\nDone. Fixed {files_fixed} files.")
