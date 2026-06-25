import os
import re
from pathlib import Path

ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source")

def fix_html(file_path):
    print(f"Processing {file_path.name}...")
    content = file_path.read_text(encoding='utf-8')

    # 1. Add overflow-x: hidden to body
    if 'body {' in content:
        content = re.sub(r'(body\s*\{[^}]*)}', r'\1; overflow-x: hidden; }', content)
    elif 'body{' in content:
        content = re.sub(r'(body\{[^}]*)}', r'\1; overflow-x: hidden; }', content)

    # 2. Fix .top-header to be truly fixed and viewport-width
    # Look for .top-header { ... }
    header_pattern = re.compile(r'(\.top-header\s*\{[^}]*position:\s*fixed;[^}]*)\}')
    if header_pattern.search(content):
        content = header_pattern.sub(r'\1 left: 0; right: 0; width: auto; z-index: 2000; }', content)

    # 3. Standardize mobile nav overlay for all pages
    # We need to ensure the mobile menu button and the nav container are handled.
    # Some pages use .std- prefixes, some don't.
    
    mobile_css = """
    @media (max-width: 768px) {
      .top-header { padding: 10px 16px !important; flex-wrap: nowrap !important; }
      .mobile-menu-btn, .std-mobile-btn { display: block !important; }
      .top-header-nav, .std-top-nav { 
        position: fixed !important; top: 0 !important; left: 0 !important; 
        width: 100vw !important; height: 100vh !important; 
        background: #fff !important; flex-direction: column !important; 
        justify-content: center !important; align-items: center !important; 
        gap: 8px !important; z-index: 9999 !important; 
        opacity: 0; pointer-events: none; transition: opacity 0.25s; 
        padding: 24px !important; overflow-y: auto !important; 
        display: flex !important;
      }
      .top-header-nav.open, .std-top-nav.open { opacity: 1 !important; pointer-events: auto !important; }
      .top-header-nav a, .std-top-nav a { font-size: 18px !important; padding: 12px 24px !important; }
      .nav-close-btn, .std-nav-close { display: block !important; position: absolute !important; top: 16px !important; right: 20px !important; background: none !important; border: none !important; font-size: 32px !important; color: #111827 !important; cursor: pointer !important; }
      .nav-dropdown .dropdown-menu, .std-nav-dd .std-dd-menu { position: static !important; transform: none !important; opacity: 1 !important; visibility: visible !important; box-shadow: none !important; border: none !important; padding: 0 !important; width: 100% !important; text-align: center !important; }
      .nav-dropdown > a::after, .std-nav-dd > a::after { display: none !important; }
    }
    """
    
    # Inject mobile CSS before the closing </style> tag
    if '</style>' in content:
        content = content.replace('</style>', mobile_css + '\n  </style>')

    file_path.write_text(content, encoding='utf-8')

def main():
    html_files = [
        "index.html",
        "ada_database.html",
        "adc_database.html",
        "antibody-guide.html",
        "component-browser.html",
        "vaccine_kb_data.html",
        "InSynBio_OurTech.html",
        "InSynBio_Antibody_Developability_Assessment_Page.html",
        "InSynBio_ADC_Design_Page.html",
        "InSynBio_Bispecific_Antibody_Design_Page.html",
        "InSynBio_CART_Design_Page.html",
        "vaccine_design.html"
    ]
    
    # Also include all case studies
    for f in ROOT.glob("case_*.html"):
        html_files.append(f.name)

    for filename in set(html_files):
        fp = ROOT / filename
        if fp.exists():
            fix_html(fp)

if __name__ == "__main__":
    main()
