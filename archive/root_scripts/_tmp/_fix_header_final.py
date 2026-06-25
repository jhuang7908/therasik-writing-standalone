import os
import re
from pathlib import Path

ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source")

def fix_header_alignment_v2(file_path):
    print(f"Refining header alignment for {file_path.name}...")
    content = file_path.read_text(encoding='utf-8')

    # 1. Clean up the messy .top-header rule from previous attempts
    # We want a clean rule that works for both PC and Mobile.
    # PC: padding 12px 32px, justify-content: space-between
    # Mobile: padding 10px 16px, justify-content: space-between
    
    clean_header_css = """
    .top-header { 
      position: fixed !important; 
      top: 0 !important; 
      left: 0 !important; 
      right: 0 !important; 
      width: 100% !important; 
      margin: 0 !important;
      padding: 12px 32px !important;
      background: rgba(255,255,255,0.95);
      backdrop-filter: blur(12px);
      border-bottom: 2px solid rgba(13,148,136,0.1);
      display: flex !important;
      align-items: center !important;
      justify-content: space-between !important;
      box-sizing: border-box !important;
      z-index: 2000 !important;
    }
    @media (max-width: 768px) {
      .top-header { padding: 10px 16px !important; }
      .std-slogan, .slogan { display: none !important; }
      .mobile-menu-btn, .std-mobile-btn { display: block !important; margin-left: auto !important; }
    }
    """
    
    # Remove all previous top-header related injections and the original rule
    content = re.sub(r'\.top-header\s*\{[^}]*\}', '', content)
    
    # Inject the new clean CSS
    if '</style>' in content:
        content = content.replace('</style>', clean_header_css + '\n  </style>')

    # 2. Ensure .top-header-nav is visible on PC
    # The previous revert might have left pointer-events: none or opacity: 0
    nav_pc_fix = """
    @media (min-width: 769px) {
      .top-header-nav, .std-top-nav {
        display: flex !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        position: static !important;
        width: auto !important;
        height: auto !important;
        background: transparent !important;
        flex-direction: row !important;
        padding: 0 !important;
      }
    }
    """
    if '</style>' in content:
        content = content.replace('</style>', nav_pc_fix + '\n  </style>')

    file_path.write_text(content, encoding='utf-8')

def main():
    html_files = []
    for f in ROOT.glob("*.html"):
        html_files.append(f)

    for fp in html_files:
        fix_header_alignment_v2(fp)

if __name__ == "__main__":
    main()
