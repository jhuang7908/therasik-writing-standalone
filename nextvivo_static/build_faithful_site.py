"""
Rebuild faithful HTML pages - replace all CDN links with local ones,
fix encoding, fix images, remove expired banner.
"""
import os
import re
import glob
import shutil
from pathlib import Path

OUTPUT = Path("faithful_site")

# CDN URL → local path mapping
CDN_MAP = {
    # CSS
    'http://s.dlssyht.cn/css/VNew/base.min.css':                   'css/base.min.css',
    'https://s.dlssyht.cn/css/VNew/base.min.css':                  'css/base.min.css',
    '//s.dlssyht.cn/css/VNew/base.min.css':                        'css/base.min.css',
    'http://s.dlssyht.cn/css/VNew/web_frame.css':                  'css/web_frame.css',
    'https://s.dlssyht.cn/css/VNew/web_frame.css':                 'css/web_frame.css',
    '//s.dlssyht.cn/css/VNew/web_frame.css':                       'css/web_frame.css',
    'http://s.dlssyht.cn/css/VNew/inner_frame.min.css':            'css/inner_frame.min.css',
    'https://s.dlssyht.cn/css/VNew/inner_frame.min.css':           'css/inner_frame.min.css',
    '//s.dlssyht.cn/css/VNew/inner_frame.min.css':                 'css/inner_frame.min.css',
    'http://s.dlssyht.cn/css/VNew/animate.min.css':                'css/animate.min.css',
    'https://s.dlssyht.cn/css/VNew/animate.min.css':               'css/animate.min.css',
    '//s.dlssyht.cn/css/VNew/animate.min.css':                     'css/animate.min.css',
    'http://s.dlssyht.cn/templates/others43/css/skincolor.css':    'css/skincolor.css',
    'https://s.dlssyht.cn/templates/others43/css/skincolor.css':   'css/skincolor.css',
    '//s.dlssyht.cn/templates/others43/css/skincolor.css':         'css/skincolor.css',
    'http://s.dlssyht.cn/templates/others43/css/webskin.css':      'css/webskin.css',
    'https://s.dlssyht.cn/templates/others43/css/webskin.css':     'css/webskin.css',
    '//s.dlssyht.cn/templates/others43/css/webskin.css':           'css/webskin.css',
    'http://s.dlssyht.cn/css/VNew/web_style/base_module_style.min.css': 'css/base_module_style.min.css',
    'https://s.dlssyht.cn/css/VNew/web_style/base_module_style.min.css': 'css/base_module_style.min.css',
    '//s.dlssyht.cn/css/VNew/web_style/base_module_style.min.css': 'css/base_module_style.min.css',
    'http://s.dlssyht.cn/css/VNew/icon_text/iconfont.min.css':     'css/iconfont.min.css',
    'https://s.dlssyht.cn/css/VNew/icon_text/iconfont.min.css':    'css/iconfont.min.css',
    '//s.dlssyht.cn/css/VNew/icon_text/iconfont.min.css':          'css/iconfont.min.css',
    'http://s.dlssyht.cn/js/ev_popup/skin/skin.min.css':           'css/skin.min.css',
    'https://s.dlssyht.cn/js/ev_popup/skin/skin.min.css':          'css/skin.min.css',
    '//s.dlssyht.cn/js/ev_popup/skin/skin.min.css':                'css/skin.min.css',
    'http://s.dlssyht.cn/plugins/public/js/lightGallery/css/lightgallery.min.css': 'css/lightgallery.min.css',
    'https://s.dlssyht.cn/plugins/public/js/lightGallery/css/lightgallery.min.css': 'css/lightgallery.min.css',
    '//s.dlssyht.cn/plugins/public/js/lightGallery/css/lightgallery.min.css': 'css/lightgallery.min.css',
    'http://s.dlssyht.cn/plugins/public/js/photoSphereViewer/index.min.css': 'css/photosphere.min.css',
    '//s.dlssyht.cn/plugins/public/js/photoSphereViewer/index.min.css': 'css/photosphere.min.css',
    'http://s.dlssyht.cn/plugins/public/js/imageViewer/viewer.min.css': 'css/viewer.min.css',
    '//s.dlssyht.cn/plugins/public/js/imageViewer/viewer.min.css':  'css/viewer.min.css',
    # JS
    'http://s.dlssyht.cn/plugins/public/js/cookies.js':            'js/cookies.js',
    '//s.dlssyht.cn/plugins/public/js/cookies.js':                 'js/cookies.js',
    'http://s.dlssyht.cn/plugins/public/js/jquery-1.7.1.min.js':   'js/jquery.min.js',
    '//s.dlssyht.cn/plugins/public/js/jquery-1.7.1.min.js':        'js/jquery.min.js',
    'http://s.dlssyht.cn/Language/Zh-cn/Language.js?0415':         'js/Language.js',
    'https://s.dlssyht.cn/Language/Zh-cn/Language.js?0415':        'js/Language.js',
    '//s.dlssyht.cn/Language/Zh-cn/Language.js?0415':              'js/Language.js',
    'http://s.dlssyht.cn/js/VNew/public.js?0415':                  'js/public.js',
    '//s.dlssyht.cn/js/VNew/public.js?0415':                       'js/public.js',
    'http://s.dlssyht.cn/plugins/public/js/base64.min.js':         'js/base64.min.js',
    '//s.dlssyht.cn/plugins/public/js/base64.min.js':              'js/base64.min.js',
    'http://s.dlssyht.cn/js/ev_popup/ev_popup.min.js?0415':        'js/ev_popup.min.js',
    '//s.dlssyht.cn/js/ev_popup/ev_popup.min.js?0415':             'js/ev_popup.min.js',
    'http://s.dlssyht.cn/js/VNew/tj/jquery.scrollify.min.js?0415': 'js/scrollify.min.js',
    '//s.dlssyht.cn/js/VNew/tj/jquery.scrollify.min.js?0415':      'js/scrollify.min.js',
    'http://s.dlssyht.cn/js/VNew/tj/public_fun.js?0415':           'js/public_fun.js',
    '//s.dlssyht.cn/js/VNew/tj/public_fun.js?0415':                'js/public_fun.js',
    'http://s.dlssyht.cn/plugins/public/js/lightGallery/js/lightgallery-all.min.js?0415': 'js/lightgallery.min.js',
    '//s.dlssyht.cn/plugins/public/js/lightGallery/js/lightgallery-all.min.js?0415': 'js/lightgallery.min.js',
    'http://s.dlssyht.cn/plugins/public/js/imageViewer/viewer.min.js?0415': 'js/viewer.min.js',
    '//s.dlssyht.cn/plugins/public/js/imageViewer/viewer.min.js?0415': 'js/viewer.min.js',
}

# Expired banner pattern
BANNER_PAT = re.compile(
    r'<div[^>]*id="evMo_SVNeT"[^>]*>[\s\S]*?[\s\S]*?</div>\s*</div>\s*</div>',
    re.IGNORECASE
)

# Lazy image fix
def fix_lazy_img(m):
    tag = m.group(0)
    orig = re.search(r'data-original-src=["\']([^"\']+)["\']', tag)
    if orig:
        real_src = orig.group(1)
        # map to local if possible
        local = img_url_to_local(real_src)
        tag = re.sub(r'src=["\'][^"\']*["\']', f'src="{local}"', tag)
        tag = tag.replace('lazy-loading', '')
        tag = re.sub(r'\s*data-original-src=["\'][^"\']*["\']', '', tag)
    return tag

# Load image map
img_map = {}
if os.path.exists("image_map.txt"):
    for line in open("image_map.txt", encoding="utf-8"):
        if "|" in line:
            local, url = line.strip.split("|", 1)
            img_map[url] = local

def img_url_to_local(url):
    if url in img_map:
        return img_map[url]
    for k, v in img_map.items:
        if url in k:
            return v
    return url


def process_html(src_file, dest_file, depth=0):
    prefix = "../" * depth

    with open(src_file, 'r', encoding='utf-8', errors='ignore') as f:
        html = f.read

    # 1. Remove expired banner
    html = BANNER_PAT.sub('', html)
    html = re.sub(r'，，543567413', '', html)

    # 2. Fix lazy images
    html = re.sub(r'<img[^>]+data-original-src=[^>]+>', fix_lazy_img, html)

    # 3. Replace CDN URLs with local paths
    for cdn_url, local_path in CDN_MAP.items:
        local_with_prefix = prefix + local_path
        html = html.replace(f'"{cdn_url}"', f'"{local_with_prefix}"')
        html = html.replace(f"'{cdn_url}'", f"'{local_with_prefix}'")

    # 4. Also fix self_define CSS references (relative - should work as-is for root pages,
    #    but need prefix adjustment for subpages)
    if depth > 0:
        html = re.sub(
            r'(href=["\'])self_define/',
            rf'\1{prefix}self_define/',
            html
        )
        # Fix dom/ PDF links
        html = re.sub(
            r'(href=["\'])dom/',
            rf'\1{prefix}docs/',
            html
        )
        # Fix relative image paths in nextvivo/ subpages
        html = re.sub(
            r'(src=["\'])images/',
            rf'\1{prefix}images/',
            html
        )
    else:
        html = re.sub(r'(href=["\'])dom/', r'\1docs/', html)

    # 5. Fix PDF link filenames (document_XX.pdf)
    html = re.sub(
        r'(href=["\'])(?:\.\.\/)?docs\/document_(\d+)\.pdf(["\'])',
        rf'\1{prefix}docs/document_\2.pdf\3',
        html
    )

    # 6. Add charset and viewport
    if '<meta charset' not in html:
        html = re.sub(r'(<head[^>]*>)', r'\1\n<meta charset="utf-8">', html, count=1, flags=re.IGNORECASE)
    if 'name="viewport"' not in html:
        html = re.sub(r'(<meta charset[^>]*>)', r'\1\n<meta name="viewport" content="width=device-width, initial-scale=1.0">', html, count=1, flags=re.IGNORECASE)

    # 7. Add mobile horizontal scroll fix (minimal, doesn't break layout)
    mobile_fix = """
<style>
html { overflow-x: hidden; }
body { overflow-x: hidden; }
@media (max-width: 1220px) {
  #wrapper, .wrapper-1200 { overflow-x: auto !important; min-width: 1200px; }
  body { overflow-x: auto; }
}
</style>"""
    if 'mobile_fix' not in html:
        html = re.sub(r'(</head>)', mobile_fix + r'\1', html, count=1, flags=re.IGNORECASE)

    os.makedirs(os.path.dirname(dest_file) if os.path.dirname(dest_file) else '.', exist_ok=True)
    with open(dest_file, 'w', encoding='utf-8') as f:
        f.write(html)


# Process all HTML files
html_files = [
    ("index.html",                                           str(OUTPUT/"index.html"),                           0),
    ("vip_nextvivo.html",                                    str(OUTPUT/"vip_nextvivo.html"),                    0),
    ("nextvivo/bk_28403983.html",                           str(OUTPUT/"nextvivo/bk_28403983.html"),            1),
    ("nextvivo/bk_28403988.html",                           str(OUTPUT/"nextvivo/bk_28403988.html"),            1),
    ("nextvivo/item_28404007_0.html",                       str(OUTPUT/"nextvivo/item_28404007_0.html"),        1),
    ("nextvivo/item_28404007_3965720.html",                 str(OUTPUT/"nextvivo/item_28404007_3965720.html"),  1),
    ("nextvivo/item_28404007_3965732.html",                 str(OUTPUT/"nextvivo/item_28404007_3965732.html"),  1),
    ("nextvivo/item_28404007_3965733.html",                 str(OUTPUT/"nextvivo/item_28404007_3965733.html"),  1),
    ("nextvivo/item_28404007_3965735.html",                 str(OUTPUT/"nextvivo/item_28404007_3965735.html"),  1),
    ("nextvivo/item_28404007_3984791.html",                 str(OUTPUT/"nextvivo/item_28404007_3984791.html"),  1),
    ("nextvivo/item_28404007_3984792.html",                 str(OUTPUT/"nextvivo/item_28404007_3984792.html"),  1),
    ("nextvivo/item_28404007_3996480.html",                 str(OUTPUT/"nextvivo/item_28404007_3996480.html"),  1),
    ("nextvivo/item_28404007_3996484.html",                 str(OUTPUT/"nextvivo/item_28404007_3996484.html"),  1),
    ("nextvivo/item_28404007_3996490.html",                 str(OUTPUT/"nextvivo/item_28404007_3996490.html"),  1),
    ("nextvivo/item_28404007_3996500.html",                 str(OUTPUT/"nextvivo/item_28404007_3996500.html"),  1),
    ("nextvivo/item_28548555_0.html",                       str(OUTPUT/"nextvivo/item_28548555_0.html"),        1),
    ("nextvivo/item_28548565_0.html",                       str(OUTPUT/"nextvivo/item_28548565_0.html"),        1),
    ("nextvivo/item_28548631_0.html",                       str(OUTPUT/"nextvivo/item_28548631_0.html"),        1),
]
# Add all vip_doc pages
for f in glob.glob("nextvivo/vip_doc/*.html"):
    fname = os.path.basename(f)
    html_files.append((f, str(OUTPUT/f"nextvivo/vip_doc/{fname}"), 2))

for src, dest, depth in html_files:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    process_html(src, dest, depth)

print(f"Processed {len(html_files)} HTML files")

# Copy self_define CSS (custom theme CSS - already local)
sd_out = OUTPUT / "self_define"
sd_out.mkdir(exist_ok=True)
for css in glob.glob("self_define/*.css"):
    shutil.copy2(css, str(sd_out / os.path.basename(css)))
print(f"Copied {len(glob.glob('self_define/*.css'))} self_define CSS files")
print(f"\n✅ Faithful site built in '{OUTPUT}/' directory!")
