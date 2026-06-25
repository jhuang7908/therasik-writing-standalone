"""
Build complete new website for NextVivo 
Purple theme, mobile responsive, all 48 pages.
"""
import os, re, glob, json
from html.parser import HTMLParser
from pathlib import Path

OUTPUT = Path("newsite")
OUTPUT.mkdir(exist_ok=True)
(OUTPUT / "images").mkdir(exist_ok=True)
(OUTPUT / "docs").mkdir(exist_ok=True)
(OUTPUT / "articles").mkdir(exist_ok=True)
(OUTPUT / "products").mkdir(exist_ok=True)
(OUTPUT / "support").mkdir(exist_ok=True)
(OUTPUT / "news").mkdir(exist_ok=True)

# Copy images and PDFs
import shutil
for img in glob.glob("images/*"):
    shutil.copy2(img, OUTPUT / "images" / os.path.basename(img))
for pdf in glob.glob("dom/*.pdf"):
    shutil.copy2(pdf, OUTPUT / "docs" / os.path.basename(pdf))

# Load image_map
img_map = {}
if os.path.exists("image_map.txt"):
    for line in open("image_map.txt", encoding="utf-8"):
        line = line.strip
        if "|" in line:
            local, url = line.split("|", 1)
            # local = "images/img_001_..."
            img_map[url] = local

def url_to_local(url):
    """Convert CDN URL to local path."""
    if url in img_map:
        return img_map[url]
    # Try partial match
    for k, v in img_map.items:
        if url in k or k in url:
            return v
    return url  # fallback to original CDN URL

# Load content
content = json.load(open("site_content.json", encoding="utf-8"))

# Extract text blocks for a page, filtered
class FullExtractor(HTMLParser):
    def __init__(self):
        super.__init__
        self.skip = False
        self.blocks = []
        self.imgs = []
        self.in_tag = None
        self.current_text = []

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag in ('script', 'style', 'noscript'):
            self.skip = True
        self.in_tag = tag
        if tag == 'img':
            src = attrs_d.get('src', '')
            if src and ('aimg8' in src or src.startswith('images/')):
                self.imgs.append(src)
        if tag in ('p', 'h1', 'h2', 'h3', 'h4', 'h5', 'li', 'td', 'div', 'span'):
            if self.current_text:
                text = ' '.join(self.current_text).strip
                if text and len(text) > 2:
                    self.blocks.append(text)
            self.current_text = []

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.skip = False
        if tag in ('p', 'h1', 'h2', 'h3', 'h4', 'li', 'td'):
            text = ' '.join(self.current_text).strip
            if text and len(text) > 2:
                self.blocks.append(text)
            self.current_text = []

    def handle_data(self, data):
        if self.skip:
            return
        cleaned = data.strip
        if cleaned:
            self.current_text.append(cleaned)

def extract_page(html_file):
    p = FullExtractor
    html = open(html_file, 'r', encoding='utf-8', errors='ignore').read
    title_m = re.search(r'<title>(.*?)</title>', html, re.DOTALL)
    title = title_m.group(1).strip if title_m else ''
    title = re.sub(r'_.*', '', title).strip
    p.feed(html)
    # Deduplicate and filter nav noise
    nav_noise = {'','','','','','',
                 '','Pioneer in Translational Medicine and Precision Medicine',
                 '','',''}
    blocks = []
    seen = set
    for b in p.blocks:
        if b not in nav_noise and b not in seen and len(b.strip) > 2:
            seen.add(b)
            blocks.append(b)
    return title, blocks, p.imgs

# Shared CSS
CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
    --purple: #5C3F98;
    --purple-dark: #412c72;
    --purple-light: #ede9f8;
    --text: #333;
    --text-light: #666;
    --white: #fff;
    --border: #e5e5e5;
    --shadow: 0 2px 12px rgba(92,63,152,0.10);
}

html { scroll-behavior: smooth; }
body {
    font-family: 'Microsoft YaHei', '', 'PingFang SC', sans-serif;
    color: var(--text);
    background: var(--white);
    line-height: 1.7;
    -webkit-font-smoothing: antialiased;
}

a { text-decoration: none; color: var(--purple); }
a:hover { opacity: 0.8; }
img { max-width: 100%; height: auto; display: block; }

/* ===== HEADER ===== */
header {
    background: var(--white);
    box-shadow: var(--shadow);
    position: sticky;
    top: 0;
    z-index: 1000;
}
.header-inner {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 72px;
}
.logo-area {
    display: flex;
    align-items: center;
    gap: 12px;
}
.logo-area img {
    height: 52px;
    width: auto;
}
.logo-text {
    display: flex;
    flex-direction: column;
}
.logo-text strong {
    color: var(--purple);
    font-size: 15px;
    font-weight: 700;
    line-height: 1.3;
}
.logo-text span {
    color: #888;
    font-size: 11px;
}

/* ===== NAV ===== */
nav { display: flex; align-items: center; gap: 4px; }
.nav-item {
    position: relative;
    padding: 8px 14px;
    color: var(--text);
    font-size: 15px;
    border-radius: 6px;
    transition: all 0.2s;
    white-space: nowrap;
}
.nav-item:hover, .nav-item.active {
    color: var(--purple);
    background: var(--purple-light);
}
.nav-item.active::after {
    content: '';
    position: absolute;
    bottom: -2px;
    left: 50%;
    transform: translateX(-50%);
    width: 24px;
    height: 3px;
    background: var(--purple);
    border-radius: 2px;
}

/* Hamburger */
.hamburger {
    display: none;
    flex-direction: column;
    gap: 5px;
    cursor: pointer;
    padding: 8px;
    border: none;
    background: none;
}
.hamburger span {
    display: block;
    width: 24px;
    height: 2px;
    background: var(--purple);
    border-radius: 2px;
    transition: all 0.3s;
}
.mobile-nav {
    display: none;
    background: var(--white);
    border-top: 1px solid var(--border);
    padding: 12px 24px;
}
.mobile-nav.open { display: block; }
.mobile-nav a {
    display: block;
    padding: 12px 0;
    border-bottom: 1px solid var(--border);
    color: var(--text);
    font-size: 15px;
}

/* ===== HERO ===== */
.hero {
    position: relative;
    min-height: 480px;
    background: linear-gradient(135deg, #f5f0ff 0%, #e8f4fd 100%);
    display: flex;
    align-items: center;
    overflow: hidden;
}
.hero-bg {
    position: absolute;
    right: 0;
    top: 0;
    width: 55%;
    height: 100%;
    object-fit: cover;
    opacity: 0.85;
}
.hero-content {
    position: relative;
    z-index: 1;
    max-width: 1200px;
    margin: 0 auto;
    padding: 60px 24px;
    width: 100%;
}
.hero-tag {
    display: inline-block;
    background: var(--purple-light);
    color: var(--purple);
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 13px;
    margin-bottom: 16px;
}
.hero h1 {
    font-size: 2.4rem;
    color: var(--purple-dark);
    font-weight: 800;
    line-height: 1.25;
    max-width: 540px;
    margin-bottom: 16px;
}
.hero p {
    font-size: 1.1rem;
    color: var(--text-light);
    max-width: 480px;
    margin-bottom: 28px;
}
.btn-primary {
    display: inline-block;
    background: var(--purple);
    color: var(--white) !important;
    padding: 12px 28px;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    transition: all 0.2s;
}
.btn-primary:hover { background: var(--purple-dark); opacity: 1; transform: translateY(-1px); }
.btn-outline {
    display: inline-block;
    border: 2px solid var(--purple);
    color: var(--purple) !important;
    padding: 10px 24px;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    margin-left: 12px;
    transition: all 0.2s;
}
.btn-outline:hover { background: var(--purple-light); opacity: 1; }

/* ===== SECTIONS ===== */
.section { padding: 64px 24px; }
.section-center { text-align: center; }
.container { max-width: 1200px; margin: 0 auto; }

.section-tag {
    display: inline-block;
    color: var(--purple);
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 10px;
}
.section-title {
    font-size: 2rem;
    font-weight: 800;
    color: var(--purple-dark);
    margin-bottom: 12px;
}
.section-sub {
    color: var(--text-light);
    font-size: 1rem;
    max-width: 580px;
    margin: 0 auto 40px;
}

/* ===== CARDS ===== */
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 24px;
    margin-top: 40px;
}
.card {
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    transition: all 0.25s;
    box-shadow: var(--shadow);
}
.card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(92,63,152,0.15); }
.card img { width: 100%; height: 200px; object-fit: cover; }
.card-body { padding: 20px; }
.card-body h3 { font-size: 16px; color: var(--purple-dark); margin-bottom: 8px; font-weight: 700; }
.card-body p { font-size: 14px; color: var(--text-light); line-height: 1.6; }
.card-link { display: inline-block; color: var(--purple); font-size: 14px; margin-top: 12px; font-weight: 600; }

/* ===== LIST ITEMS ===== */
.item-list { list-style: none; }
.item-list li {
    padding: 16px 0;
    border-bottom: 1px solid var(--border);
    display: flex;
    gap: 16px;
    align-items: flex-start;
}
.item-list li:last-child { border-bottom: none; }
.item-dot {
    width: 8px;
    height: 8px;
    background: var(--purple);
    border-radius: 50%;
    margin-top: 8px;
    flex-shrink: 0;
}
.item-list .item-text h4 { font-size: 15px; color: var(--text); font-weight: 600; margin-bottom: 4px; }
.item-list .item-text p { font-size: 13px; color: var(--text-light); }

/* ===== ARTICLE ===== */
.article-content {
    max-width: 860px;
    margin: 0 auto;
}
.article-content h1, .article-content h2, .article-content h3 {
    color: var(--purple-dark);
    margin: 24px 0 12px;
    font-weight: 700;
}
.article-content h1 { font-size: 1.8rem; margin-top: 0; }
.article-content h2 { font-size: 1.4rem; }
.article-content h3 { font-size: 1.15rem; }
.article-content p { margin-bottom: 14px; color: var(--text); }
.article-content img { border-radius: 8px; margin: 20px auto; }
.pdf-download {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: var(--purple-light);
    border: 1px solid var(--purple);
    color: var(--purple);
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    margin: 20px 0;
    transition: all 0.2s;
}
.pdf-download:hover { background: var(--purple); color: var(--white); }

/* ===== STATS ===== */
.stats-bar {
    background: linear-gradient(135deg, var(--purple) 0%, var(--purple-dark) 100%);
    padding: 48px 24px;
    color: white;
}
.stats-grid {
    max-width: 1200px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 24px;
    text-align: center;
}
.stat-num { font-size: 2.5rem; font-weight: 800; }
.stat-label { font-size: 14px; opacity: 0.85; margin-top: 4px; }

/* ===== TWO COL ===== */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 48px; align-items: center; }
.two-col.reverse .col-img { order: -1; }

/* ===== FOOTER ===== */
footer {
    background: var(--purple-dark);
    color: rgba(255,255,255,0.85);
    padding: 48px 24px 24px;
}
.footer-grid {
    max-width: 1200px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1fr;
    gap: 32px;
    margin-bottom: 32px;
}
.footer-brand strong { color: white; font-size: 16px; display: block; margin-bottom: 10px; }
.footer-brand p { font-size: 13px; line-height: 1.7; }
.footer-col h4 { color: white; font-size: 14px; margin-bottom: 14px; font-weight: 700; }
.footer-col a { display: block; color: rgba(255,255,255,0.7); font-size: 13px; margin-bottom: 8px; }
.footer-col a:hover { color: white; opacity: 1; }
.footer-bottom {
    max-width: 1200px;
    margin: 0 auto;
    padding-top: 20px;
    border-top: 1px solid rgba(255,255,255,0.15);
    text-align: center;
    font-size: 12px;
    color: rgba(255,255,255,0.5);
}

/* ===== PAGE HEADER ===== */
.page-header {
    background: linear-gradient(135deg, var(--purple) 0%, var(--purple-dark) 100%);
    padding: 48px 24px;
    color: white;
}
.page-header h1 { font-size: 2rem; font-weight: 800; margin-bottom: 8px; }
.page-header p { font-size: 1rem; opacity: 0.85; }
.breadcrumb { font-size: 13px; opacity: 0.7; margin-bottom: 12px; }
.breadcrumb a { color: rgba(255,255,255,0.8); }
.breadcrumb span { margin: 0 6px; }

/* ===== SIDEBAR LAYOUT ===== */
.sidebar-layout {
    display: grid;
    grid-template-columns: 240px 1fr;
    gap: 32px;
    max-width: 1200px;
    margin: 48px auto;
    padding: 0 24px;
}
.sidebar {
    background: var(--white);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    height: fit-content;
    position: sticky;
    top: 88px;
}
.sidebar h3 {
    color: var(--purple-dark);
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 2px solid var(--purple-light);
}
.sidebar a {
    display: block;
    padding: 8px 10px;
    color: var(--text);
    font-size: 14px;
    border-radius: 6px;
    margin-bottom: 2px;
}
.sidebar a:hover, .sidebar a.active { background: var(--purple-light); color: var(--purple); }

/* ===== RESPONSIVE ===== */
@media (max-width: 1024px) {
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
    .footer-grid { grid-template-columns: 1fr 1fr; }
    .two-col { grid-template-columns: 1fr; }
    .sidebar-layout { grid-template-columns: 1fr; }
    .sidebar { position: static; }
}
@media (max-width: 768px) {
    nav { display: none; }
    .hamburger { display: flex; }
    .hero h1 { font-size: 1.7rem; }
    .hero-bg { width: 100%; opacity: 0.3; }
    .section-title { font-size: 1.5rem; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
    .card-grid { grid-template-columns: 1fr; }
    .footer-grid { grid-template-columns: 1fr; }
    .two-col.reverse .col-img { order: 0; }
    .page-header h1 { font-size: 1.5rem; }
}
@media (max-width: 480px) {
    .hero h1 { font-size: 1.4rem; }
    .stat-num { font-size: 2rem; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
}

/* Utility */
.bg-light { background: #f8f6ff; }
.text-center { text-align: center; }
.mt-8 { margin-top: 8px; }
.mt-16 { margin-top: 16px; }
.mt-24 { margin-top: 24px; }
.mt-40 { margin-top: 40px; }
.mb-8 { margin-bottom: 8px; }
.mb-16 { margin-bottom: 16px; }
.tag-badge {
    display: inline-block;
    background: var(--purple-light);
    color: var(--purple);
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    margin-right: 6px;
    margin-bottom: 4px;
}
"""

# JS for hamburger
JS = """
document.addEventListener('DOMContentLoaded', function {
    var btn = document.querySelector('.hamburger');
    var nav = document.querySelector('.mobile-nav');
    if (btn && nav) {
        btn.addEventListener('click', function {
            nav.classList.toggle('open');
        });
    }
});
"""

# Write shared CSS and JS
(OUTPUT / "style.css").write_text(CSS, encoding="utf-8")
(OUTPUT / "app.js").write_text(JS, encoding="utf-8")

# Logo image (img_016 is the logo based on its dimensions 237x67)
LOGO_SRC = "images/img_016_resize,m_fixed,w_237,h_67,limit_0"

def nav_html(active=""):
    items = [
        ("", "index.html", "home"),
        ("", "about.html", "about"),
        ("", "products/index.html", "products"),
        ("", "support/index.html", "support"),
        ("", "news/index.html", "news"),
        ("", "contact.html", "contact"),
    ]
    links = ""
    mobile_links = ""
    for label, href, key in items:
        cls = " active" if active == key else ""
        links += f'<a href="/{href}" class="nav-item{cls}">{label}</a>'
        mobile_links += f'<a href="/{href}">{label}</a>'
    return links, mobile_links

def page_wrapper(title, content_html, active="", depth=0):
    prefix = "../" * depth
    nav_links, mobile_nav_links = nav_html(active)
    # Adjust nav links for depth
    if depth > 0:
        nav_links = nav_links.replace('href="/', f'href="{prefix}')
        mobile_nav_links = mobile_nav_links.replace('href="/', f'href="{prefix}')
    logo_src = prefix + LOGO_SRC
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - </title>
<meta name="description" content=" - ">
<link rel="stylesheet" href="{prefix}style.css">
</head>
<body>
<header>
  <div class="header-inner">
    <a href="{prefix}index.html" class="logo-area">
      <img src="{logo_src}" alt=" NextVivo" onerror="this.style.display='none'">
      <div class="logo-text">
        <strong></strong>
        <span>Pioneer in Translational Medicine and Precision Medicine</span>
      </div>
    </a>
    <nav>{nav_links}</nav>
    <button class="hamburger" aria-label="">
      <span></span><span></span><span></span>
    </button>
  </div>
  <div class="mobile-nav">{mobile_nav_links}</div>
</header>

{content_html}

<footer>
  <div class="footer-grid">
    <div class="footer-brand">
      <strong></strong>
      <p><br>AI</p>
    </div>
    <div class="footer-col">
      <h4></h4>
      <a href="{prefix}products/index.html">PBMC </a>
      <a href="{prefix}products/cd34.html">CD34 </a>
      <a href="{prefix}products/services.html"></a>
      <a href="{prefix}products/platform.html"></a>
    </div>
    <div class="footer-col">
      <h4></h4>
      <a href="{prefix}support/index.html"></a>
      <a href="{prefix}support/faq.html"> FAQ</a>
      <a href="{prefix}support/disease-models.html"></a>
    </div>
    <div class="footer-col">
      <h4></h4>
      <a href="{prefix}news/index.html"></a>
      <a href="{prefix}news/reviews.html"></a>
      <a href="{prefix}news/lectures.html"></a>
      <a href="{prefix}news/company.html"></a>
    </div>
  </div>
  <div class="footer-bottom">
    © 2024   | 
  </div>
</footer>
<script src="{prefix}app.js"></script>
</body>
</html>"""

# =====================
# 1. HOMEPAGE
# =====================
_, idx_blocks, idx_imgs = extract_page("index.html")

# Find hero image (largest image ~1200x611)
hero_img = "images/img_013_resize,m_fixed,w_1200,h_611,limit_0"
banner_img = "images/img_010_resize,m_fixed,w_1199,h_330,limit_0"

home_content = f"""
<section class="hero">
  <img src="{hero_img}" alt="" class="hero-bg" loading="lazy">
  <div class="hero-content">
    <div class="hero-tag"></div>
    <h1><br></h1>
    <p>，</p>
    <a href="products/index.html" class="btn-primary"></a>
    <a href="contact.html" class="btn-outline"></a>
  </div>
</section>

<section class="stats-bar">
  <div class="stats-grid">
    <div><div class="stat-num">3+</div><div class="stat-label"></div></div>
    <div><div class="stat-num">10+</div><div class="stat-label"></div></div>
    <div><div class="stat-num">8</div><div class="stat-label"></div></div>
    <div><div class="stat-num">∞</div><div class="stat-label"></div></div>
  </div>
</section>

<section class="section">
  <div class="container">
    <div class="text-center">
      <div class="section-tag">Featured products and services</div>
      <h2 class="section-title"></h2>
    </div>
    <div class="card-grid">
      <div class="card">
        <img src="images/img_017_resize,m_fixed,w_291,h_233,limit_0" alt="PBMC" loading="lazy">
        <div class="card-body">
          <h3>PBMC</h3>
          <p>PBMC，T。</p>
          <a href="products/pbmc.html" class="card-link"> →</a>
        </div>
      </div>
      <div class="card">
        <img src="images/img_018_resize,m_fixed,w_291,h_203,limit_0" alt="AML PDX" loading="lazy">
        <div class="card-body">
          <h3>AMLPDX</h3>
          <p>PDX</p>
          <a href="products/index.html" class="card-link"> →</a>
        </div>
      </div>
      <div class="card">
        <img src="images/img_020_resize,m_fixed,w_291,h_207,limit_0" alt="" loading="lazy">
        <div class="card-body">
          <h3></h3>
          <p></p>
          <a href="products/index.html" class="card-link"> →</a>
        </div>
      </div>
      <div class="card">
        <img src="images/img_019_resize,m_fixed,w_291,h_231,limit_0" alt="" loading="lazy">
        <div class="card-body">
          <h3></h3>
          <p>SLE、RA</p>
          <a href="products/index.html" class="card-link"> →</a>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="section bg-light">
  <div class="container">
    <div class="two-col">
      <div class="col-text">
        <div class="section-tag">ABOUT US</div>
        <h2 class="section-title"></h2>
        <p>AI。：</p>
        <ul class="item-list mt-16">
          <li><span class="item-dot"></span><div class="item-text"><h4></h4><p>PD-1、CAR-T</p></div></li>
          <li><span class="item-dot"></span><div class="item-text"><h4></h4><p>HLA</p></div></li>
          <li><span class="item-dot"></span><div class="item-text"><h4>PHMC</h4><p></p></div></li>
        </ul>
        <a href="about.html" class="btn-primary mt-24" style="display:inline-block"></a>
      </div>
      <div class="col-img">
        <img src="images/img_009_resize,m_fixed,w_742,h_363,limit_0" alt="" style="border-radius:12px;" loading="lazy">
      </div>
    </div>
  </div>
</section>

<section class="section">
  <div class="container">
    <div class="text-center">
      <div class="section-tag">technical data</div>
      <h2 class="section-title"></h2>
    </div>
    <div class="card-grid mt-40">
      <div class="card">
        <div class="card-body">
          <span class="tag-badge"></span>
          <h3></h3>
          <p>FcRn/Albumin（HSA）。</p>
          <a href="news/albumin-model.html" class="card-link"> →</a>
        </div>
      </div>
      <div class="card">
        <div class="card-body">
          <span class="tag-badge"></span>
          <h3>NV-NSG Plus：</h3>
          <p>，...</p>
          <a href="news/nv-nsg-plus.html" class="card-link"> →</a>
        </div>
      </div>
      <div class="card">
        <div class="card-body">
          <span class="tag-badge"></span>
          <h3>AI""</h3>
          <p>？AI。</p>
          <a href="news/ai-digital-twin.html" class="card-link"> →</a>
        </div>
      </div>
    </div>
    <div class="text-center mt-40">
      <a href="news/index.html" class="btn-outline"></a>
    </div>
  </div>
</section>
"""

(OUTPUT / "index.html").write_text(
    page_wrapper("", home_content, "home", 0),
    encoding="utf-8"
)
print("✓ index.html")

# =====================
# 2. ABOUT PAGE
# =====================
_, about_blocks, about_imgs = extract_page("nextvivo/bk_28403983.html")
about_img = "images/img_007_resize,m_fixed,w_1130,h_582,limit_0"

about_content = f"""
<div class="page-header">
  <div class="container">
    <div class="breadcrumb"><a href="index.html"></a><span>›</span></div>
    <h1></h1>
    <p></p>
  </div>
</div>
<section class="section">
  <div class="container article-content">
    <img src="{about_img}" alt="" style="border-radius:12px; margin-bottom:32px;" loading="lazy">
    {''.join(f'<p>{b}</p>' for b in about_blocks[:40] if len(b)>10)}
  </div>
</section>
"""
(OUTPUT / "about.html").write_text(
    page_wrapper("", about_content, "about", 0),
    encoding="utf-8"
)
print("✓ about.html")

# =====================
# 3. CONTACT PAGE
# =====================
_, contact_blocks, _ = extract_page("nextvivo/bk_28403988.html")
contact_content = f"""
<div class="page-header">
  <div class="container">
    <div class="breadcrumb"><a href="index.html"></a><span>›</span></div>
    <h1></h1>
    <p>，</p>
  </div>
</div>
<section class="section">
  <div class="container">
    <div class="two-col">
      <div class="col-text article-content">
        {''.join(f'<p>{b}</p>' for b in contact_blocks[:30] if len(b)>5)}
      </div>
      <div class="col-img">
        <div style="background: var(--purple-light); border-radius:12px; padding:32px;">
          <h3 style="color:var(--purple-dark); margin-bottom:20px;"></h3>
          <p style="margin-bottom:12px;">📍 </p>
          <p style="margin-bottom:12px;">🌐 www.nextvivo.com.cn</p>
          <p style="margin-bottom:24px;">📧 </p>
          <a href="mailto:info@nextvivo.com.cn" class="btn-primary"></a>
        </div>
      </div>
    </div>
  </div>
</section>
"""
(OUTPUT / "contact.html").write_text(
    page_wrapper("", contact_content, "contact", 0),
    encoding="utf-8"
)
print("✓ contact.html")

# =====================
# 4. PRODUCTS PAGES
# =====================
product_pages = [
    ("nextvivo/item_28404007_0.html",       "products/pbmc.html",       "PBMC "),
    ("nextvivo/item_28404007_3984791.html",  "products/cd34.html",       "CD34 "),
    ("nextvivo/item_28404007_3965720.html",  "products/nsg-scf.html",    "NV-NSG-hSCF/GM-CSF/IL-3"),
    ("nextvivo/item_28404007_3965732.html",  "products/nsg-il15h.html",  "NV-NSG-hIL-15"),
    ("nextvivo/item_28404007_3965733.html",  "products/nsg-il15l.html",  "NV-NSG-hIL-15"),
    ("nextvivo/item_28404007_3965735.html",  "products/nsg-il2.html",    "NV-NSG-hIL-2"),
    ("nextvivo/item_28404007_3984792.html",  "products/pbmc2.html",      "PBMC  "),
    ("nextvivo/item_28404007_3996480.html",  "products/nsg-hla.html",    "NV-NSG hB2M/HLA A2/Tslp"),
    ("nextvivo/item_28404007_3996484.html",  "products/nsg-il6.html",    "NV-NSG IL6"),
    ("nextvivo/item_28404007_3996490.html",  "products/fcrn-albumin.html","FcRn/Albumin"),
    ("nextvivo/item_28404007_3996500.html",  "products/her2.html",       "hHER2"),
    ("nextvivo/item_28548555_0.html",        "products/services.html",   ""),
    ("nextvivo/item_28548565_0.html",        "products/background.html", ""),
    ("nextvivo/item_28548631_0.html",        "products/platform.html",   ""),
]

# Products index
product_index_cards = ""
for src_f, dest_f, label in product_pages:
    _, blocks, _ = extract_page(src_f)
    desc = next((b for b in blocks if len(b) > 20), "")[:120]
    dest_rel = dest_f.replace("products/", "")
    product_index_cards += f"""
    <div class="card">
      <div class="card-body">
        <h3>{label}</h3>
        <p>{desc}</p>
        <a href="{dest_rel}" class="card-link"> →</a>
      </div>
    </div>"""

prod_idx_content = f"""
<div class="page-header">
  <div class="container">
    <div class="breadcrumb"><a href="../index.html"></a><span>›</span></div>
    <h1></h1>
    <p></p>
  </div>
</div>
<section class="section">
  <div class="container">
    <div class="card-grid">{product_index_cards}</div>
  </div>
</section>
"""
(OUTPUT / "products" / "index.html").write_text(
    page_wrapper("", prod_idx_content, "products", 1),
    encoding="utf-8"
)
print("✓ products/index.html")

for src_f, dest_f, label in product_pages:
    _, blocks, imgs = extract_page(src_f)
    body_html = ""
    for b in blocks[:60]:
        if len(b) > 5:
            body_html += f"<p>{b}</p>\n"
    fname = dest_f.replace("products/", "")
    prod_content = f"""
<div class="page-header">
  <div class="container">
    <div class="breadcrumb"><a href="../index.html"></a><span>›</span><a href="index.html"></a><span>›</span>{label}</div>
    <h1>{label}</h1>
  </div>
</div>
<section class="section">
  <div class="container">
    <div class="sidebar-layout">
      <aside class="sidebar">
        <h3></h3>
        {''.join(f'<a href="{d.replace(chr(47)+"products/","")}" {"class=active" if d==dest_f else ""}>{l}</a>' for _,d,l in product_pages)}
      </aside>
      <div class="article-content">
        <h1>{label}</h1>
        {body_html}
        <a href="../contact.html" class="btn-primary" style="margin-top:24px;display:inline-block;"></a>
      </div>
    </div>
  </div>
</section>
"""
    (OUTPUT / dest_f).write_text(
        page_wrapper(label, prod_content, "products", 1),
        encoding="utf-8"
    )
print(f"✓ {len(product_pages)} product pages")

# =====================
# 5. SUPPORT PAGES
# =====================
support_pages = [
    ("nextvivo/vip_doc/28442644_0_0_1.html",          "support/index.html",         ""),
    ("nextvivo/vip_doc/28442644_6170035_0_1.html",    "support/faq.html",           "（FAQ）"),
    ("nextvivo/vip_doc/28442644_6170036_0_1.html",    "support/disease-models.html",""),
    ("nextvivo/vip_doc/29660496.html",                "support/faq-detail.html",    "（FAQ）"),
]
for src_f, dest_f, label in support_pages:
    _, blocks, _ = extract_page(src_f)
    body_html = ''.join(f'<p>{b}</p>' for b in blocks[:80] if len(b)>5)
    fname = dest_f
    depth = 1
    sup_content = f"""
<div class="page-header">
  <div class="container">
    <div class="breadcrumb"><a href="../index.html"></a><span>›</span>{label}</div>
    <h1>{label}</h1>
  </div>
</div>
<section class="section">
  <div class="container article-content">
    <h1>{label}</h1>
    {body_html}
  </div>
</section>
"""
    (OUTPUT / dest_f).write_text(
        page_wrapper(label, sup_content, "support", depth),
        encoding="utf-8"
    )
print(f"✓ {len(support_pages)} support pages")

# =====================
# 6. NEWS / ARTICLES
# =====================
news_pages = [
    ("nextvivo/vip_doc/28403987_0_0_1.html",          "news/index.html",       ""),
    ("nextvivo/vip_doc/28403987_6129780_0_1.html",    "news/reviews.html",     ""),
    ("nextvivo/vip_doc/28403987_6129781_0_1.html",    "news/lectures.html",    ""),
    ("nextvivo/vip_doc/28403987_6142917_0_1.html",    "news/company.html",     ""),
    ("nextvivo/vip_doc/29851781.html",                "news/albumin-model.html",""),
    ("nextvivo/vip_doc/29660551.html",                "news/nv-nsg-plus.html", "NV-NSG Plus"),
    ("nextvivo/vip_doc/29660565.html",                "news/personalized-model.html",""),
    ("nextvivo/vip_doc/29660514.html",                "news/tumor-vaccine.html",""),
    ("nextvivo/vip_doc/29660567.html",                "news/nk-drugs.html",    "PD1：NK"),
    ("nextvivo/vip_doc/29660581.html",                "news/her2-platform.html","hHER2HER2"),
    ("nextvivo/vip_doc/29660632.html",                "news/aml-pdx.html",     "AML PDX"),
    ("nextvivo/vip_doc/29660741.html",                "news/ai-digital-twin.html","AI"),
    ("nextvivo/vip_doc/29660746.html",                "news/bispecific-ab.html",""),
    ("nextvivo/vip_doc/29660749.html",                "news/ab-humanization.html",""),
    ("nextvivo/vip_doc/29660752.html",                "news/adc-axc.html",     "ADCAXC"),
    ("nextvivo/vip_doc/29660757.html",                "news/humanized-mouse-v2.html",""),
    ("nextvivo/vip_doc/29660761.html",                "news/mrna-vaccine.html",""),
    ("nextvivo/vip_doc/29660763.html",                "news/fc-engineering.html","Fc"),
    ("nextvivo/vip_doc/29660771.html",                "news/cart.html",        "CAR-T"),
    ("nextvivo/vip_doc/29660839.html",                "news/lecture-summary.html",""),
    ("nextvivo/vip_doc/29660844.html",                "news/history.html",     ""),
    ("nextvivo/vip_doc/29924722.html",                "news/lecture1.html",    ""),
    ("nextvivo/vip_doc/29924723.html",                "news/lecture2.html",    ""),
    ("nextvivo/vip_doc/29924732.html",                "news/lecture3.html",    ""),
]

# Check which articles have PDF links
pdf_map = {
    "29660496": "document_23.pdf",
    "29660551": "document_37.pdf",
    "29660514": "document_38.pdf",
    "29660565": "document_39.pdf",
    "29660567": "document_40.pdf",
    "29660581": "document_41.pdf",
    "29660632": "document_42.pdf",
    "29851781": "document_43.pdf",
}

for src_f, dest_f, label in news_pages:
    _, blocks, imgs = extract_page(src_f)
    # Check if this page has a PDF
    pdf_link = ""
    for key, pdf_file in pdf_map.items:
        if key in src_f:
            pdf_link = f'<a href="../docs/{pdf_file}" class="pdf-download" target="_blank">📄 PDF</a>'
            break
    body_html = ''.join(f'<p>{b}</p>' for b in blocks[:80] if len(b)>5)
    news_content = f"""
<div class="page-header">
  <div class="container">
    <div class="breadcrumb"><a href="../index.html"></a><span>›</span><a href="index.html"></a><span>›</span>{label}</div>
    <h1>{label}</h1>
  </div>
</div>
<section class="section">
  <div class="container article-content">
    <h1>{label}</h1>
    {pdf_link}
    {body_html}
    {pdf_link}
  </div>
</section>
"""
    (OUTPUT / dest_f).write_text(
        page_wrapper(label, news_content, "news", 1),
        encoding="utf-8"
    )

print(f"✓ {len(news_pages)} news/article pages")

# =====================
# 7. NEWS INDEX
# =====================
news_cards_html = ""
for src_f, dest_f, label in news_pages[1:]:
    _, blocks, _ = extract_page(src_f)
    desc = next((b for b in blocks if len(b)>30), "")[:120]
    fname = dest_f.replace("news/", "")
    news_cards_html += f"""
    <div class="card">
      <div class="card-body">
        <h3>{label}</h3>
        <p>{desc}</p>
        <a href="{fname}" class="card-link"> →</a>
      </div>
    </div>"""

news_idx_content = f"""
<div class="page-header">
  <div class="container">
    <div class="breadcrumb"><a href="../index.html"></a><span>›</span></div>
    <h1></h1>
    <p>、</p>
  </div>
</div>
<section class="section">
  <div class="container">
    <div class="card-grid">{news_cards_html}</div>
  </div>
</section>
"""
(OUTPUT / "news" / "index.html").write_text(
    page_wrapper("", news_idx_content, "news", 1),
    encoding="utf-8"
)
print("✓ news/index.html")

print(f"\n✅ New website built in '{OUTPUT}/' directory!")
print(f"   Total pages generated: {1+1+1+1+len(product_pages)+len(support_pages)+len(news_pages)}")
