import os
import re
import glob
import urllib.request
import time
from pathlib import Path

base_dir = "."
img_dir = os.path.join(base_dir, "images")
os.makedirs(img_dir, exist_ok=True)

html_files = glob.glob(f"{base_dir}/**/*.html", recursive=True)

img_urls = set()
for html_file in html_files:
    content = open(html_file, 'r', encoding='utf-8', errors='ignore').read()
    matches = re.findall(r'src=["\'](https?://aimg8\.dlssyht\.cn[^"\']+)["\']', content)
    img_urls.update(matches)

print(f"Found {len(img_urls)} unique images to download.")

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

success = 0
fail = 0
mapping = {}  # original_url -> local_path

for i, url in enumerate(sorted(img_urls)):
    # Create a clean filename from the URL
    # e.g. https://aimg8.dlssyht.cn/u/2297474/module/.../filename.jpg
    parts = url.split('/')
    # Get last meaningful filename part
    filename_part = parts[-1].split('?')[0]  # strip query params like ?x-oss-process=...
    ext = os.path.splitext(filename_part)[1] or '.jpg'
    # Use a numbered name to avoid duplicates
    clean_name = f"img_{i+1:03d}_{filename_part.split('?')[0]}"
    local_path = os.path.join(img_dir, clean_name)
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read()
        with open(local_path, 'wb') as f:
            f.write(data)
        size_kb = len(data) // 1024
        mapping[url] = f"images/{clean_name}"
        print(f"[{i+1}/{len(img_urls)}] OK  {clean_name} ({size_kb} KB)")
        success += 1
    except Exception as e:
        print(f"[{i+1}/{len(img_urls)}] FAIL {url[:60]} -> {e}")
        fail += 1
    
    time.sleep(0.1)  # polite delay

print(f"\nDone: {success} downloaded, {fail} failed.")

# Save URL -> local path mapping for later use in rebuilding
with open(os.path.join(base_dir, "image_map.txt"), 'w', encoding='utf-8') as f:
    for url, local in sorted(mapping.items()):
        f.write(f"{local}|{url}\n")

print("Saved image_map.txt for use in new site build.")
