import os
import re
from pathlib import Path

ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source")

def fix_header_final_v5(file_path):
    print(f"Reverting PC header and fixing mobile alignment for {file_path.name}...")
    content = file_path.read_text(encoding='utf-8')

    # 1. Robust Header System V5 - White background for PC, optimized for Mobile
    final_css = """
    /* --- Robust Header System V5 --- */
    .top-header {
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      right: 0 !important;
      width: 100% !important;
      height: 72px !important;
      background: rgba(255,255,255,0.98) !important; /* Reverted to White */
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
      color: #111827 !important; /* Logo text back to Dark */
    }
    .top-header .brand .accent { color: #0d9488 !important; }
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
    .top-header-nav a, .std-top-nav a { color: #4b5563 !important; }
    .top-header-nav a:hover, .std-top-nav a:hover { color: #0d9488 !important; }
    .mobile-menu-btn, .std-mobile-btn {
      display: none !important;
    }

    @media (max-width: 768px) {
      .top-header {
        height: 64px !important;
        padding: 0 24px !important; /* Match Hero padding */
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
        color: #111827 !important;
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
      .top-header-nav a, .std-top-nav a { font-size: 18px !important; color: #111827 !important; }
    }
    
    html, body {
      max-width: 100% !important;
      overflow-x: hidden !important;
      position: relative !important;
    }
    """

    # Remove all previous header injections
    content = re.sub(r'/\* --- Robust Header System.*?\}', '', content, flags=re.DOTALL)
    content = re.sub(r'/\* --- Dark Header for Homepage.*?\}', '', content, flags=re.DOTALL)
    
    # Inject the new V5 CSS
    if '</style>' in content:
        content = content.replace('</style>', final_css + '\n  </style>')

    # Ensure body padding
    content = re.sub(r'padding-top:\s*\d+px', 'padding-top: 72px', content)

    file_path.write_text(content, encoding='utf-8')

def main():
    html_files = list(ROOT.glob("*.html"))
    for fp in html_files:
        fix_header_final_v5(fp)

if __name__ == "__main__":
    main()
