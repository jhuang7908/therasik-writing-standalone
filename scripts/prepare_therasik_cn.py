import os
import re

# Paths
base_path = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-clone"
files_to_update = [
    "therasik_index.html",
    "Therasik_Antibody_Page.html",
    "Therasik_CART_Page.html",
    "Therasik_Bispecific_Page.html"
]

# Standard Therasik Brand Header HTML (Chinese)
# Using Cormorant Garamond for Therasik
THERASIK_HEADER = '''
  <header class="top-header">
    <div class="brand">
      <a href="therasik_index.html">
        <svg width="34" height="28" viewBox="0 0 32 30" fill="none" xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0;">
          <path d="M16 2L2 10V22L16 28L30 22V10L16 2Z" fill="#0d9488" fill-opacity="0.1" stroke="#0d9488" stroke-width="2.5" />
          <path d="M7 14L16 19L25 14" stroke="#0d9488" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M16 19V28" stroke="#0d9488" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M7 14L7 6C7 6 10 2 16 2C22 2 25 6 25 6L25 14" stroke="#0d9488" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
          <circle cx="7" cy="6" r="2" fill="#0f766e" />
          <circle cx="25" cy="6" r="2" fill="#0f766e" />
          <circle cx="16" cy="18" r="2" fill="white" stroke="#0d9488" stroke-width="1.5" />
        </svg>
        <span><span style="color:#111827">Thera</span><span style="color:var(--primary); font-style:italic">sik</span></span>
      </a>
      <span class="slogan">AI </span>
    </div>
    <nav class="top-header-nav">
      <a href="therasik_index.html"></a>
      <a href="therasik_index.html#about"></a>
      <div class="nav-dropdown" tabindex="0">
        <a href="therasik_index.html#services"></a>
        <div class="dropdown-menu">
          <a href="Therasik_Antibody_Page.html">
            <span class="menu-title"></span>
            <span class="menu-desc"></span>
          </a>
          <a href="Therasik_CART_Page.html">
            <span class="menu-title"> CAR-T </span>
            <span class="menu-desc">ACTES </span>
          </a>
          <a href="Therasik_Bispecific_Page.html">
            <span class="menu-title"></span>
            <span class="menu-desc">Nano-Convert™ </span>
          </a>
        </div>
      </div>
      <a href="therasik_index.html#case-studies"></a>
      <a href="therasik_index.html#workflow"></a>
      <a href="therasik_index.html#faq"></a>
      <a href="therasik_index.html#contact"></a>
    </nav>
  </header>
'''

# Standard Footer for Therasik
THERASIK_FOOTER = '''
  <footer class="site-footer">
    <p>© 2026 Therasik · <a href="https://therasik.com">therasik.com</a> · <a href="mailto:contact@therasik.com">contact@therasik.com</a></p>
  </footer>
'''

# Header CSS patch for single-row and layout fix
STYLE_PATCH = '''
    .top-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 32px; background: rgba(255,255,255,0.95); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(0,0,0,0.05); flex-wrap: nowrap; gap: 12px; position: fixed; width: 100%; top: 0; z-index: 1000; height: 72px; box-sizing: border-box; }
    .top-header .brand { font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 700; font-size: 26px; letter-spacing: -0.03em; display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
    .top-header .brand a { text-decoration: none; color: inherit; display: flex; align-items: center; gap: 10px; }
    .top-header .slogan { font-size: 14px; color: var(--text-muted); padding-left: 14px; border-left: 1px solid var(--border); white-space: nowrap; font-weight: 600; letter-spacing: 0.02em; display: flex; align-items: center; height: 24px; }
    .top-header-nav { display: flex; align-items: center; gap: 4px; flex: 1; justify-content: flex-end; }
    .top-header-nav a { padding: 8px 12px; font-size: 14px; color: var(--text-muted); text-decoration: none; border-radius: 20px; transition: all 0.2s ease; font-weight: 600; white-space: nowrap; }
    .top-header-nav a:hover { color: var(--primary); background: rgba(13,148,136,0.06); }
    .top-header-nav a.active { background: var(--primary); color: #fff; box-shadow: 0 2px 8px rgba(13,148,136,0.25); }
    body { padding-top: 72px; }
    @media (max-width: 1100px) {
        .top-header .slogan { display: none; }
    }
    @media (max-width: 768px) {
        .top-header { padding: 8px 16px; height: auto; flex-wrap: wrap; }
        .top-header-nav { justify-content: center; width: 100%; overflow-x: auto; padding-top: 8px; border-top: 1px solid var(--border); }
    }
'''

def patch_file(filename):
    path = os.path.join(base_path, filename)
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update <title> and meta
    content = re.sub(r'<title>.*?</title>', f'<title>Therasik | AI </title>', content)
    
    # 2. Inject CSS patch
    if '</style>' in content:
        content = content.replace('</style>', STYLE_PATCH + '\n    </style>')

    # 3. Replace <header> block
    # Matches <header>... </header> or <header class="top-header"> ... </header>
    content = re.sub(r'<header.*?>.*?</header>', THERASIK_HEADER, content, flags=re.DOTALL)

    # 4. Replace <footer> block
    content = re.sub(r'<footer.*?>.*?</footer>', THERASIK_FOOTER, content, flags=re.DOTALL)

    # 5. Global text replacements (InSynBio -> Therasik)
    # Careful not to break paths if any, but since we are standardizing the header, it's safer.
    # Replace individual strings
    content = content.replace('InSynBio', 'Therasik')
    
    # 6. Fix internal links to point to Therasik versions
    content = content.replace('index.html', 'therasik_index.html')
    content = content.replace('InSynBio_Antibody_Developability_Assessment_Page.html', 'Therasik_Antibody_Page.html')
    content = content.replace('InSynBio_CART_Design_Page.html', 'Therasik_CART_Page.html')
    content = content.replace('InSynBio_Bispecific_Antibody_Design_Page.html', 'Therasik_Bispecific_Page.html')
    
    # Special fix for the home link in the header which we just injected
    # (The standard header already uses therasik_index.html, so this is just for safety)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Patched {filename}")

for f in files_to_update:
    patch_file(f)

# Also copy index.html to therasik_index.html if we want to keep them in sync?
# User said "therasik_index.html is the new Chinese homepage address".
