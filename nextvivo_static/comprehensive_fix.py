import os
import glob
import re

base_dir = "."

print("Starting comprehensive layout and image fix...")

# Better mobile CSS - specifically handle the absolute positioning overlay layout
mobile_css = """
/* ===== InSynBio Mobile & Layout Fix ===== */

/* Force UTF-8 rendering */
@charset "utf-8";

/* 1. Make wrapper responsive on all screens */
.wrapper, .wrapper-1200, #wrapper {
    width: 100% !important;
    max-width: 100% !important;
    overflow-x: hidden !important;
    box-sizing: border-box !important;
}

/* 2. Fix absolutely positioned modules on mobile */
@media screen and (max-width: 1220px) {
    /* Unset absolute positioning on module rows and make them relative/flow */
    .customModuleRow .CModulePA {
        position: relative !important;
        height: auto !important;
        min-height: 60px;
        overflow: visible !important;
    }

    /* Make all absolute-positioned modules flow naturally */
    .ev-module-edit {
        position: relative !important;
        left: auto !important;
        top: auto !important;
        width: auto !important;
        max-width: 100% !important;
        height: auto !important;
        min-height: 30px;
        display: block !important;
        margin-bottom: 8px;
        float: none !important;
    }

    /* Row inner */
    .customModuleRowInner {
        width: 100% !important;
        max-width: 100% !important;
    }

    /* Make images responsive */
    img, .ev-pic img {
        max-width: 100% !important;
        height: auto !important;
        display: block;
    }

    /* Navigation */
    .ev-menu-nav, .nav, nav, .navigation {
        width: 100% !important;
        overflow-x: auto !important;
        white-space: nowrap;
    }

    .ev-menu-li, .nav-item, .menu-item {
        display: inline-block !important;
        float: none !important;
    }

    /* Hero / banner sections */
    .ev-base-button {
        position: relative !important;
        left: auto !important;
        top: auto !important;
        width: auto !important;
        display: inline-block !important;
        margin: 8px 0;
    }

    /* Text elements */
    h1, h2, h3, h4, .ev-text-title-1, .ev-text-title-2, .ev-text-title-3, .ev-text-title-4 {
        font-size: 1.2em !important;
        line-height: 1.4 !important;
        word-wrap: break-word !important;
        white-space: normal !important;
    }

    p, .ev-text-article-1, .ev-text-article-2 {
        font-size: 14px !important;
        line-height: 1.6 !important;
        white-space: normal !important;
    }

    /* Tables responsive */
    table {
        width: 100% !important;
        display: block;
        overflow-x: auto;
    }
}

/* 3. Modern polish (all screen sizes) */
html { scroll-behavior: smooth; }
body { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
a { transition: opacity 0.25s ease; }
a:hover { opacity: 0.75; }

/* Fix broken logo fallback */
img[src="vip_nextvivo.html"], img[src="#"] {
    display: none !important;
}
"""

# Write updated CSS
css_path = os.path.join(base_dir, "mobile_opt.css")
with open(css_path, "w", encoding="utf-8") as f:
    f.write(mobile_css)
print("Updated mobile_opt.css")

# Process all HTML files
html_files = glob.glob(f"{base_dir}/**/*.html", recursive=True)
updated_count = 0
img_fix_count = 0

for html_file in html_files:
    try:
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        original_content = content
        
        # Fix lazy-loaded images: replace src="..." data-original-src="REAL_URL"
        # with src="REAL_URL"
        def fix_img(m):
            tag = m.group(0)
            # Extract data-original-src value
            orig = re.search(r'data-original-src=["\']([^"\']+)["\']', tag)
            if orig:
                real_src = orig.group(1)
                # Replace src attribute value with the real URL
                tag = re.sub(r'src=["\'][^"\']*["\']', f'src="{real_src}"', tag)
                # Remove the lazy-loading class and data attr
                tag = tag.replace('lazy-loading', '')
                tag = re.sub(r'\s*data-original-src=["\'][^"\']*["\']', '', tag)
            return tag

        new_content = re.sub(r'<img[^>]+data-original-src=[^>]+>', fix_img, content)
        if new_content != content:
            img_fix_count += 1
            content = new_content
            
        if content != original_content:
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(content)
            updated_count += 1
            
    except Exception as e:
        print(f"Error: {html_file}: {e}")

print(f"Fixed lazy images in {img_fix_count} files.")
print(f"Total updated: {updated_count} HTML files.")
