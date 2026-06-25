import os
import re
from pathlib import Path

ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source")

def fix_logo_visibility_and_size(file_path):
    print(f"Fixing logo visibility and size for {file_path.name}...")
    content = file_path.read_text(encoding='utf-8')

    # 1. Update CSS to increase logo and slogan size, and ensure colors are correct for white background
    final_css_v6 = """
    /* --- Robust Header System V6 --- */
    .top-header {
      position: fixed !important;
      top: 0 !important;
      left: 0 !important;
      right: 0 !important;
      width: 100% !important;
      height: 80px !important; /* Increased height slightly for larger logo */
      background: rgba(255,255,255,0.98) !important;
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
      gap: 14px !important;
      flex-shrink: 0 !important;
    }
    .top-header .brand a {
      display: flex !important;
      align-items: center !important;
      text-decoration: none !important;
      font-size: 28px !important; /* Increased font size */
      font-weight: 700 !important;
      color: #111827 !important; /* Force dark color for 'In' and 'Bio' */
    }
    .top-header .brand a span { 
      color: #111827 !important; /* Ensure spans inside link are also dark */
    }
    .top-header .brand .accent { 
      color: #0d9488 !important; 
      font-style: italic !important;
    }
    .top-header .slogan, .top-header .std-slogan {
      font-size: 15px !important; /* Increased slogan size */
      color: #4b5563 !important;
      padding-left: 14px !important;
      border-left: 1px solid #e5e7eb !important;
      margin-left: 6px !important;
      white-space: nowrap !important;
      display: inline-block !important;
      font-weight: 500 !important;
    }
    .top-header-nav, .std-top-nav {
      display: flex !important;
      align-items: center !important;
      gap: 10px !important;
      margin-left: auto !important;
      margin-right: 10px !important;
    }
    .top-header-nav a, .std-top-nav a { 
      font-size: 15px !important;
      color: #374151 !important; 
      font-weight: 600 !important;
    }
    """

    # Remove previous V5 block
    content = re.sub(r'/\* --- Robust Header System V5 --- \*/.*?\}', '', content, flags=re.DOTALL)
    
    # Inject V6 CSS
    if '</style>' in content:
        content = content.replace('</style>', final_css_v6 + '\n  </style>')

    # 2. Fix the HTML structure to remove any inline white color styles
    # Replace <span style="color:#fff"> or similar with nothing to let CSS take over
    content = re.sub(r'style="color:\s*#fff[^"]*"', '', content, flags=re.I)
    content = re.sub(r'style="color:\s*white[^"]*"', '', content, flags=re.I)
    
    # Specifically fix the InSynBio spans if they have hardcoded colors
    content = content.replace('<span>In</span>', '<span>In</span>') # placeholder for identification
    
    # 3. Ensure body padding matches new header height
    content = re.sub(r'padding-top:\s*\d+px', 'padding-top: 80px', content)

    file_path.write_text(content, encoding='utf-8')

def main():
    html_files = list(ROOT.glob("*.html"))
    for fp in html_files:
        fix_logo_visibility_and_size(fp)

if __name__ == "__main__":
    main()
