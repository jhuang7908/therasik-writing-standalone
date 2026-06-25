import os
import re
from pathlib import Path

ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source")

def fix_header_structure_and_style(file_path):
    print(f"Fixing header for {file_path.name}...")
    content = file_path.read_text(encoding='utf-8')

    # 1. Fix HTML Structure: Move slogan inside brand div if it's a sibling
    # We want: <div class="brand"><a...>...</a><span class="slogan">...</span></div>
    # Current: <div class="brand"><a...>...</a></div> <span class="slogan">...</span>
    
    # Capture brand div contents and slogan contents
    struct_pattern = re.compile(r'<div class="brand">(.*?)</div>\s*<span class="(std-)?slogan">(.*?)</span>', re.DOTALL)
    if struct_pattern.search(content):
        content = struct_pattern.sub(r'<div class="brand">\1<span class="\2slogan">\3</span></div>', content)

    # 2. Clean up all top-header related CSS rules
    final_css = """
    /* --- Robust Header System V2 --- */
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
    .top-header .brand {
      display: flex !important;
      align-items: center !important;
      gap: 12px !important;
      flex-shrink: 0 !important;
    }
    .top-header .brand a {
      display: flex !important;
      align-items: center !important;
      text-decoration: none !important;
    }
    .top-header .slogan, .top-header .std-slogan {
      font-size: 13px !important;
      color: #6b7280 !important;
      padding-left: 12px !important;
      border-left: 1px solid #e5e7eb !important;
      margin-left: 4px !important;
      white-space: nowrap !important;
      display: inline-block !important;
      font-weight: 500 !important;
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
    .mobile-menu-btn, .std-mobile-btn {
      display: none !important;
    }

    @media (max-width: 768px) {
      .top-header {
        height: 64px !important;
        padding: 0 16px !important;
      }
      .top-header .slogan, .top-header .std-slogan {
        display: none !important;
      }
      .mobile-menu-btn, .std-mobile-btn {
        display: block !important;
        margin-left: auto !important;
        background: none !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 8px !important;
        padding: 6px 10px !important;
        cursor: pointer !important;
      }
      .top-header-nav, .std-top-nav {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        background: #fff !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        gap: 16px !important;
        margin: 0 !important;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.25s ease;
        z-index: 10000 !important;
      }
      .top-header-nav.open, .std-top-nav.open {
        opacity: 1 !important;
        pointer-events: auto !important;
      }
      .nav-close-btn, .std-nav-close {
        display: block !important;
        position: absolute !important;
        top: 20px !important;
        right: 20px !important;
        font-size: 32px !important;
        background: none !important;
        border: none !important;
        cursor: pointer !important;
      }
    }
    """

    # Clean up existing rules
    content = re.sub(r'\.top-header\s*\{[^}]*\}', '', content)
    content = re.sub(r'\.top-header\s*\.brand\s*\{[^}]*\}', '', content)
    content = re.sub(r'\.top-header\s*\.slogan\s*\{[^}]*\}', '', content)
    content = re.sub(r'\.std-slogan\s*\{[^}]*\}', '', content)
    content = re.sub(r'\.top-header-nav\s*\{[^}]*\}', '', content)
    content = re.sub(r'\.std-top-nav\s*\{[^}]*\}', '', content)
    
    # Inject new CSS
    if '</style>' in content:
        content = content.replace('</style>', final_css + '\n  </style>')

    # Ensure body padding
    content = re.sub(r'padding-top:\s*\d+px', 'padding-top: 72px', content)

    file_path.write_text(content, encoding='utf-8')

def main():
    html_files = list(ROOT.glob("*.html"))
    for fp in html_files:
        fix_header_structure_and_style(fp)

if __name__ == "__main__":
    main()
