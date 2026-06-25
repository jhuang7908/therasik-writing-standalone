import os
import re
from pathlib import Path

ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source")

def fix_index_header_to_dark(file_path):
    print(f"Applying dark header fix to {file_path.name}...")
    content = file_path.read_text(encoding='utf-8')

    # 1. Update CSS for index.html to have a dark header like Therasik
    dark_header_css = """
    /* --- Dark Header for Homepage --- */
    .top-header {
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      right: 0 !important;
      width: 100% !important;
      height: 72px !important;
      background: #111827 !important; /* Dark background */
      border-bottom: 1px solid rgba(255,255,255,0.1) !important;
      display: flex !important;
      align-items: center !important;
      justify-content: space-between !important;
      padding: 0 32px !important;
      box-sizing: border-box !important;
      z-index: 9999 !important;
      flex-wrap: nowrap !important;
    }
    .top-header .brand a span { color: #fff !important; } /* White text for logo */
    .top-header .brand .accent { color: var(--primary) !important; }
    .top-header .slogan, .top-header .std-slogan {
      color: rgba(255,255,255,0.7) !important;
      border-left: 1px solid rgba(255,255,255,0.2) !important;
    }
    .top-header-nav a, .std-top-nav a {
      color: rgba(255,255,255,0.8) !important;
    }
    .top-header-nav a:hover, .std-top-nav a:hover {
      color: #fff !important;
      background: rgba(255,255,255,0.1) !important;
    }
    .top-header-nav a.active, .std-top-nav a.active {
      background: var(--primary) !important;
      color: #fff !important;
    }
    .nav-dropdown > a::after { color: rgba(255,255,255,0.5) !important; }

    @media (max-width: 768px) {
      .top-header { height: 64px !important; padding: 0 16px !important; }
      .mobile-menu-btn, .std-mobile-btn { 
        color: #fff !important; 
        border-color: rgba(255,255,255,0.3) !important;
        margin-left: auto !important;
        display: block !important;
      }
      .top-header-nav, .std-top-nav { background: #111827 !important; }
      .top-header-nav a, .std-top-nav a { color: #fff !important; }
    }
    """

    # Remove the previous "Robust Header System" block
    content = re.sub(r'/\* --- Robust Header System V[23] --- \*/.*?\}', '', content, flags=re.DOTALL)
    
    # Inject the new dark header CSS
    if '</style>' in content:
        content = content.replace('</style>', dark_header_css + '\n  </style>')

    # 2. Fix the HTML for the brand to ensure white text is used
    # Change <span style="color:#111827">In</span> to use white or remove hardcoded color
    content = content.replace('color:#111827', 'color:inherit')

    file_path.write_text(content, encoding='utf-8')

def fix_other_pages_header(file_path):
    # For other pages, keep the white header but ensure it's robust and single-line
    print(f"Applying robust white header to {file_path.name}...")
    content = file_path.read_text(encoding='utf-8')

    white_header_css = """
    /* --- Robust White Header for Subpages --- */
    .top-header {
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      right: 0 !important;
      width: 100% !important;
      height: 72px !important;
      background: rgba(255,255,255,0.97) !important;
      backdrop-filter: blur(12px) !important;
      border-bottom: 1px solid rgba(13,148,136,0.1) !important;
      display: flex !important;
      align-items: center !important;
      justify-content: space-between !important;
      padding: 0 32px !important;
      box-sizing: border-box !important;
      z-index: 9999 !important;
      flex-wrap: nowrap !important;
    }
    .top-header-nav, .std-top-nav {
      display: flex !important;
      align-items: center !important;
      gap: 6px !important;
      margin-left: auto !important;
      margin-right: 10px !important;
      flex-direction: row !important;
      position: static !important;
      width: auto !important;
      height: auto !important;
      background: transparent !important;
      opacity: 1 !important;
      pointer-events: auto !important;
    }
    @media (max-width: 768px) {
      .top-header { height: 64px !important; padding: 0 16px !important; }
      .mobile-menu-btn, .std-mobile-btn { margin-left: auto !important; display: block !important; }
      .top-header .slogan, .top-header .std-slogan { display: none !important; }
      .top-header-nav, .std-top-nav {
        position: fixed !important; top: 0 !important; left: 0 !important;
        width: 100vw !important; height: 100vh !important;
        background: #fff !important; flex-direction: column !important;
        justify-content: center !important; align-items: center !important;
        opacity: 0; pointer-events: none; transition: opacity 0.25s ease;
      }
      .top-header-nav.open, .std-top-nav.open { opacity: 1 !important; pointer-events: auto !important; }
    }
    """
    
    content = re.sub(r'/\* --- Robust Header System V[23] --- \*/.*?\}', '', content, flags=re.DOTALL)
    if '</style>' in content:
        content = content.replace('</style>', white_header_css + '\n  </style>')

    file_path.write_text(content, encoding='utf-8')

def main():
    # Fix index.html with dark header
    index_path = ROOT / "index.html"
    if index_path.exists():
        fix_index_header_to_dark(index_path)
    
    # Fix all other pages with robust white header
    for fp in ROOT.glob("*.html"):
        if fp.name != "index.html":
            fix_other_pages_header(fp)

if __name__ == "__main__":
    main()
