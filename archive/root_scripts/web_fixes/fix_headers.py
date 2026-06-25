import re
import glob

# 1. Read the standard header from therasik_index.html
with open("docs/therasik_index.html", "r", encoding="utf-8") as f:
    content = f.read()

header_match = re.search(r'(<header class="top-header">.*?</header>)', content, re.DOTALL)
if not header_match:
    print("Could not find header in therasik_index.html")
    exit(1)

standard_header = header_match.group(1)

# 2. Find all Therasik HTML files
files = glob.glob("docs/Therasik_*.html")

for file_path in files:
    with open(file_path, "r", encoding="utf-8") as f:
        page_content = f.read()
    
    # Check if this page has a header-badge (like ADA Database)
    badge_match = re.search(r'(<div class="header-badge"[^>]*>.*?</div>)', page_content)
    
    # Replace the existing header
    new_content = re.sub(r'<header class="top-header">.*?</header>', standard_header, page_content, flags=re.DOTALL)
    
    # If it had a badge, we need to inject it back into the new header before the closing </header>
    if badge_match and "header-badge" not in new_content:
        badge_html = badge_match.group(1)
        new_content = new_content.replace('</header>', f'  {badge_html}\n</header>')
        
    if new_content != page_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {file_path}")
    else:
        print(f"No changes needed for {file_path}")
