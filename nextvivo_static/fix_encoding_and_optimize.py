import os
import glob
import re

base_dir = "www.nextvivo.com.cn"
dom_dir = os.path.join(base_dir, "dom")

print("Starting fix...")

# 1. Rename PDFs
renames = {}
if os.path.exists(dom_dir):
    pdf_files = [f for f in os.listdir(dom_dir) if f.startswith("Download.php")]
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

# 2. Create CSS
mobile_css = """
/* InSynBio AI Auto-Optimization: Mobile & Modernization */
:root {
    --primary-color: #2c3e50;
    --text-color: #333333;
    --bg-color: #ffffff;
}
@media screen and (max-width: 1200px) {
    .wrapper, .wrapper-1200, .container, .main-content, #wrapper {
        width: 100% !important;
        max-width: 100% !important;
        padding-left: 15px !important;
        padding-right: 15px !important;
        box-sizing: border-box !important;
        overflow-x: hidden !important;
    }
    img { max-width: 100% !important; height: auto !important; }
    table { width: 100% !important; display: block; overflow-x: auto; }
    .col, .column, .box, li { width: 100% !important; display: block !important; margin-bottom: 15px; }
    body, p, span, div { font-size: 16px !important; line-height: 1.6 !important; }
    h1, h2, h3 { font-size: 1.5em !important; line-height: 1.3 !important; word-wrap: break-word; }
}
body { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
a { transition: color 0.3s ease, opacity 0.3s ease; }
a:hover { opacity: 0.8; }
html { scroll-behavior: smooth; }
"""
css_path = os.path.join(base_dir, "mobile_opt.css")
with open(css_path, "w", encoding="utf-8") as f:
    f.write(mobile_css)

# 3. Process HTML files
html_files = glob.glob(f"{base_dir}/**/*.html", recursive=True)
viewport_tag = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />\n'

for html_file in html_files:
    try:
        # READ AS GBK (Original encoding of the website)
        with open(html_file, 'r', encoding='gbk', errors='ignore') as f:
            content = f.read()
            
        # Replace PDF links
        for doc_id, new_name in renames.items():
            pattern = r'Download\.php[^\"\']*?id=' + str(doc_id) + r'[^\"\']*'
            content = re.sub(pattern, new_name, content)
            
        # Add mobile meta
        content = re.sub(r'<meta name="applicable-device" content="pc"\s*/?>', 
                         '<meta name="applicable-device" content="pc,mobile" />', 
                         content)
        if 'name="viewport"' not in content:
            content = re.sub(r'(<head[^>]*>)', r'\1\n    ' + viewport_tag, content, count=1, flags=re.IGNORECASE)
            
        # Add CSS link
        depth = html_file.replace(base_dir, "").count(os.sep) - 1
        if depth <= 0:
            css_href = "./mobile_opt.css"
        else:
            css_href = "../" * depth + "mobile_opt.css"
        css_link = f'<link rel="stylesheet" type="text/css" href="{css_href}" />\n'
        if 'mobile_opt.css' not in content:
            content = re.sub(r'(</head>)', r'    ' + css_link + r'\1', content, count=1, flags=re.IGNORECASE)
            
        # CONVERT ENCODING META TAG TO UTF-8
        content = re.sub(r'charset=gbk', 'charset=utf-8', content, flags=re.IGNORECASE)
        content = re.sub(r'charset="gbk"', 'charset="utf-8"', content, flags=re.IGNORECASE)
        content = re.sub(r'charset=gb2312', 'charset=utf-8', content, flags=re.IGNORECASE)
            
        # WRITE AS UTF-8
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
    except Exception as e:
        print(f"Error processing {html_file}: {e}")

print("Fix complete.")
