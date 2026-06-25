import os
import glob
import re

base_dir = "www.nextvivo.com.cn"

print("Starting deep fix for mojibake and expired banner...")

html_files = glob.glob(f"{base_dir}/**/*.html", recursive=True)
updated_count = 0

# Regex to match the expired banner div block
banner_pattern = re.compile(
    r'<div[^>]*id="evMo_SVNeT"[^>]*>[\s\S]*?，，543567413[\s\S]*?</div>\s*</div>\s*</div>',
    re.IGNORECASE
)

for html_file in html_files:
    try:
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read
            
        original_content = content
        
        # 1. Remove the expired banner
        content = banner_pattern.sub('', content)
        
        # Also remove any stray text just in case
        content = re.sub(r'，，543567413', '', content)
        
        # 2. Ensure <meta charset="utf-8"> is the FIRST thing in <head>
        if '<meta charset="utf-8">' not in content:
            content = re.sub(r'(<head>)', r'\1\n    <meta charset="utf-8">', content, count=1, flags=re.IGNORECASE)
            
        if content != original_content:
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(content)
            updated_count += 1
            
    except Exception as e:
        print(f"Error processing {html_file}: {e}")

print(f"Deep fix complete. Updated {updated_count} HTML files.")
