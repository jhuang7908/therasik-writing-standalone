"""
Strategy: Download ALL CDN assets, rebuild HTML using original structure + local assets.
This gives ~100% visual fidelity to the original website.
"""
import urllib.request
import os
import re
import glob
import shutil
from pathlib import Path

OUTPUT = Path("faithful_site")
OUTPUT.mkdir(exist_ok=True)
for d in ["css", "js", "images", "docs", "self_define", "nextvivo/vip_doc"]:
    (OUTPUT / d).mkdir(parents=True, exist_ok=True)

HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': 'http://www.nextvivo.com.cn/'}

def download(url, dest):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        r = urllib.request.urlopen(req, timeout=10)
        data = r.read()
        open(dest, 'wb').write(data)
        print(f"  OK  {os.path.basename(dest)} ({len(data)//1024}KB)")
        return True
    except Exception as e:
        print(f"  FAIL {url[:60]}: {e}")
        return False

print("=== Downloading CDN CSS files ===")
css_files = [
    ('http://s.dlssyht.cn/css/VNew/base.min.css',               'css/base.min.css'),
    ('http://s.dlssyht.cn/css/VNew/web_frame.css',              'css/web_frame.css'),
    ('http://s.dlssyht.cn/css/VNew/inner_frame.min.css',        'css/inner_frame.min.css'),
    ('http://s.dlssyht.cn/css/VNew/animate.min.css',            'css/animate.min.css'),
    ('http://s.dlssyht.cn/templates/others43/css/skincolor.css','css/skincolor.css'),
    ('http://s.dlssyht.cn/templates/others43/css/webskin.css',  'css/webskin.css'),
    ('http://s.dlssyht.cn/css/VNew/web_style/base_module_style.min.css', 'css/base_module_style.min.css'),
    ('http://s.dlssyht.cn/css/VNew/icon_text/iconfont.min.css', 'css/iconfont.min.css'),
    ('http://s.dlssyht.cn/js/ev_popup/skin/skin.min.css',       'css/skin.min.css'),
    ('http://s.dlssyht.cn/plugins/public/js/lightGallery/css/lightgallery.min.css', 'css/lightgallery.min.css'),
    ('http://s.dlssyht.cn/plugins/public/js/photoSphereViewer/index.min.css', 'css/photosphere.min.css'),
    ('http://s.dlssyht.cn/plugins/public/js/imageViewer/viewer.min.css', 'css/viewer.min.css'),
]
for url, dest in css_files:
    download(url, str(OUTPUT / dest))

print("\n=== Downloading CDN JS files ===")
js_files = [
    ('http://s.dlssyht.cn/plugins/public/js/cookies.js',       'js/cookies.js'),
    ('http://s.dlssyht.cn/plugins/public/js/jquery-1.7.1.min.js', 'js/jquery.min.js'),
    ('http://s.dlssyht.cn/Language/Zh-cn/Language.js?0415',    'js/Language.js'),
    ('http://s.dlssyht.cn/js/VNew/public.js?0415',             'js/public.js'),
    ('http://s.dlssyht.cn/plugins/public/js/base64.min.js',    'js/base64.min.js'),
    ('http://s.dlssyht.cn/js/ev_popup/ev_popup.min.js?0415',   'js/ev_popup.min.js'),
    ('http://s.dlssyht.cn/js/VNew/tj/jquery.scrollify.min.js?0415', 'js/scrollify.min.js'),
    ('http://s.dlssyht.cn/js/VNew/tj/public_fun.js?0415',      'js/public_fun.js'),
    ('http://s.dlssyht.cn/plugins/public/js/lightGallery/js/lightgallery-all.min.js?0415', 'js/lightgallery.min.js'),
    ('http://s.dlssyht.cn/plugins/public/js/imageViewer/viewer.min.js?0415', 'js/viewer.min.js'),
]
for url, dest in js_files:
    download(url, str(OUTPUT / dest))

print("\n=== Copying local images and PDFs ===")
for img in glob.glob("images/*"):
    shutil.copy2(img, str(OUTPUT / "images" / os.path.basename(img)))
for pdf in glob.glob("dom/*.pdf"):
    shutil.copy2(pdf, str(OUTPUT / "docs" / os.path.basename(pdf)))
# Copy self_define CSS (custom per-page styles)
for css in glob.glob("self_define/*.css"):
    shutil.copy2(css, str(OUTPUT / "self_define" / os.path.basename(css)))
print(f"  Copied {len(glob.glob('images/*'))} images, {len(glob.glob('dom/*.pdf'))} PDFs")

print("\nDone. Now processing HTML files...")
