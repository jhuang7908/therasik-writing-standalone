import os
import re
from pathlib import Path

ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source")

def fix_header_alignment(file_path):
    print(f"Aligning header for {file_path.name}...")
    content = file_path.read_text(encoding='utf-8')

    # 1. Update .top-header CSS to ensure it doesn't shrink and stays pinned
    # We want it to span the full viewport width regardless of body content width
    header_css_fix = """
    .top-header { 
      position: fixed !important; 
      top: 0 !important; 
      left: 0 !important; 
      right: 0 !important; 
      width: 100% !important; 
      margin: 0 !important;
      padding: 12px 32px !important;
      box-sizing: border-box !important;
      z-index: 2000 !important;
    }
    @media (max-width: 768px) {
      .top-header { padding: 10px 16px !important; }
    }
    """
    
    if '</style>' in content:
        # Check if we already have a .top-header rule in style tag to replace or just append
        if '.top-header {' in content:
            # Replace existing top-header rule with a more robust one
            content = re.sub(r'\.top-header\s*\{[^}]*\}', header_css_fix, content)
        else:
            content = content.replace('</style>', header_css_fix + '\n  </style>')

    # 2. Ensure the mobile button is always on the far right
    # The .top-header is flex with justify-content: space-between.
    # We need to make sure the brand is on the left and the button is on the right.
    # If there's a slogan, it might be pushing things.
    
    # Let's add a specific fix for the mobile button placement in the CSS
    mobile_btn_fix = """
    @media (max-width: 768px) {
      .std-mobile-btn, .mobile-menu-btn { 
        margin-left: auto !important; 
        display: block !important;
      }
      .std-slogan, .slogan {
        display: none !important; /* Hide slogan on small mobile to save space if needed, or keep it */
      }
    }
    """
    if '</style>' in content:
        content = content.replace('</style>', mobile_btn_fix + '\n  </style>')

    file_path.write_text(content, encoding='utf-8')

def main():
    html_files = []
    for f in ROOT.glob("*.html"):
        html_files.append(f)

    for fp in html_files:
        fix_header_alignment(fp)

if __name__ == "__main__":
    main()
