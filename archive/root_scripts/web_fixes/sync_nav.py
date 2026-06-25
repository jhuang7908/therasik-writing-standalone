import re
import glob

# 1. Read the standard nav from therasik_index.html
with open("docs/therasik_index.html", "r", encoding="utf-8") as f:
    content = f.read()

nav_match = re.search(r'(<nav class="top-header-nav">.*?</nav>)', content, re.DOTALL)
if not nav_match:
    print("Could not find nav in therasik_index.html")
    exit(1)

standard_nav = nav_match.group(1)

# 2. Find all Therasik HTML files
files = glob.glob("docs/Therasik_*.html")

for file_path in files:
    with open(file_path, "r", encoding="utf-8") as f:
        page_content = f.read()
    
    # Replace the existing nav
    new_content = re.sub(r'<nav class="top-header-nav">.*?</nav>', standard_nav, page_content, flags=re.DOTALL)
    
    if new_content != page_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Updated {file_path}")
    else:
        print(f"No changes needed for {file_path}")
