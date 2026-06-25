import os
import glob
import re

base_dir = "www.nextvivo.com.cn"

# CSS for mobile optimization and modern styling
mobile_css = """
/* InSynBio AI Auto-Optimization: Mobile & Modernization */
:root {
    --primary-color: #2c3e50; /* A modern dark blue, adjust if needed */
    --text-color: #333333;
    --bg-color: #ffffff;
}

/* 1. Reset fixed widths for mobile */
@media screen and (max-width: 1200px) {
    .wrapper, .wrapper-1200, .container, .main-content, #wrapper {
        width: 100% !important;
        max-width: 100% !important;
        padding-left: 15px !important;
        padding-right: 15px !important;
        box-sizing: border-box !important;
        overflow-x: hidden !important;
    }
    
    /* Make images responsive */
    img {
        max-width: 100% !important;
        height: auto !important;
    }
    
    /* Adjust tables for mobile */
    table {
        width: 100% !important;
        display: block;
        overflow-x: auto;
    }
    
    /* Stack flex/float columns */
    .col, .column, .box, li {
        float: none !important;
        width: 100% !important;
        display: block !important;
        margin-bottom: 15px;
    }
    
    /* Adjust text sizes */
    body, p, span, div {
        font-size: 16px !important;
        line-height: 1.6 !important;
    }
    
    h1, h2, h3 {
        font-size: 1.5em !important;
        line-height: 1.3 !important;
        word-wrap: break-word;
    }
}

/* 2. Modern UI Enhancements (Subtle) */
body {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    color: var(--text-color);
}

/* Add subtle hover effects to links and buttons */
a {
    transition: color 0.3s ease, opacity 0.3s ease;
}
a:hover {
    opacity: 0.8;
}

/* Smooth scrolling */
html {
    scroll-behavior: smooth;
}

/* Better image rendering */
img {
    object-fit: cover;
}
"""

# Write the CSS file
css_path = os.path.join(base_dir, "mobile_opt.css")
with open(css_path, "w", encoding="utf-8") as f:
    f.write(mobile_css)
print("Created mobile_opt.css")

# Process all HTML files
html_files = glob.glob(f"{base_dir}/**/*.html", recursive=True)
updated_count = 0

viewport_tag = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />\n'

for html_file in html_files:
    try:
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        original_content = content
        
        # 1. Update applicable-device meta tag
        content = re.sub(r'<meta name="applicable-device" content="pc"\s*/?>', 
                         '<meta name="applicable-device" content="pc,mobile" />', 
                         content)
        
        # 2. Add viewport meta tag if missing
        if 'name="viewport"' not in content:
            content = re.sub(r'(<head[^>]*>)', r'\1\n    ' + viewport_tag, content, count=1, flags=re.IGNORECASE)
            
        # 3. Inject our mobile_opt.css before </head>
        # Calculate relative path to root for the css file
        depth = html_file.replace(base_dir, "").count(os.sep) - 1
        if depth <= 0:
            css_href = "./mobile_opt.css"
        else:
            css_href = "../" * depth + "mobile_opt.css"
            
        css_link = f'<link rel="stylesheet" type="text/css" href="{css_href}" />\n'
        
        if 'mobile_opt.css' not in content:
            content = re.sub(r'(</head>)', r'    ' + css_link + r'\1', content, count=1, flags=re.IGNORECASE)
            
        if content != original_content:
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(content)
            updated_count += 1
            
    except Exception as e:
        print(f"Error processing {html_file}: {e}")

print(f"Optimization complete. Updated {updated_count} HTML files.")
