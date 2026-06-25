import os
import re
import glob
import urllib.parse

base_dir = "www.nextvivo.com.cn"
dom_dir = os.path.join(base_dir, "dom")

if not os.path.exists(dom_dir):
    print("dom dir not found")
    exit(0)

print("Starting PDF fix...")

pdf_files = [f for f in os.listdir(dom_dir) if f.startswith("Download.php")]
renames = {}

for f in pdf_files:
    match = re.search(r'id=(\d+)', f)
    if match:
        doc_id = match.group(1)
        new_name = f"document_{doc_id}.pdf"
        renames[doc_id] = new_name
    else:
        new_name = f"{f}.pdf"
        renames[f] = new_name
    
    old_path = os.path.join(dom_dir, f)
    new_path = os.path.join(dom_dir, new_name)
    
    os.rename(old_path, new_path)
    print(f"Renamed: {f} -> {new_name}")

html_files = glob.glob(f"{base_dir}/**/*.html", recursive=True)
updated_count = 0
for html_file in html_files:
    try:
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
        original_content = content
        for doc_id, new_name in renames.items():
            # Replace Download.php links with the new PDF filename
            # The HTML might have: href="/dom/Download.php?username=nextvivo&amp;type=1&amp;id=23"
            # Or: href="../dom/Download.php?username=nextvivo&type=1&id=23"
            pattern = r'Download\.php[^\"\']*?id=' + str(doc_id) + r'[^\"\']*'
            # We want to replace just the filename part, keeping the path if possible, 
            # but since they are all in /dom/, we can just replace the whole Download.php... string with new_name
            content = re.sub(pattern, new_name, content)
                
        if content != original_content:
            with open(html_file, 'w', encoding='utf-8') as file:
                file.write(content)
            updated_count += 1
            print(f"Updated links in: {html_file}")
    except Exception as e:
        print(f"Error processing {html_file}: {e}")

print(f"PDF fix complete. Updated {updated_count} HTML files.")
