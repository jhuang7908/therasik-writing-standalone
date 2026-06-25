"""
Complete header CSS rewrite for all InSynBio pages.
Removes 6+ conflicting CSS blocks accumulated from previous fix scripts
and replaces them with a single, clean, conflict-free header CSS.
"""
import re
from pathlib import Path

SRC = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source")

# ── The single clean header CSS block ──────────────────────────────────────────
CLEAN_HEADER_CSS = """
    /* ===== HEADER (clean single block) ===== */
    .top-header {
      position: fixed;
      top: 0; left: 0; right: 0;
      width: 100%;
      height: 64px;
      background: rgba(255,255,255,0.98);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid rgba(13,148,136,0.1);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 28px;
      box-sizing: border-box;
      z-index: 9999;
      flex-wrap: nowrap;
    }
    .top-header .brand { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
    .top-header .brand a {
      text-decoration: none; color: #111827;
      display: flex; align-items: center; gap: 3px;
      font-size: 18px; font-weight: 700;
      white-space: nowrap; flex-shrink: 0;
    }
    .top-header .brand a span { color: #111827; }
    .top-header .brand .accent { color: #0d9488; font-style: italic; font-weight: 700; }
    .top-header .slogan, .top-header .std-slogan {
      font-size: 13px; color: #6b7280;
      padding-left: 12px; border-left: 1px solid #e5e7eb; margin-left: 4px;
      white-space: nowrap; display: inline-block; font-weight: 500; flex-shrink: 0;
    }
    .mobile-menu-btn, .std-mobile-btn {
      display: none; background: none;
      border: 1px solid #e5e7eb; border-radius: 8px;
      padding: 6px 8px; cursor: pointer; color: #111827; line-height: 0;
    }
    .nav-close-btn, .std-nav-close { display: none; }
    .top-header-nav, .std-top-nav {
      display: flex; align-items: center; gap: 4px; margin-left: auto;
    }
    .top-header-nav a, .std-top-nav a {
      padding: 7px 13px; font-size: 14px; color: #4b5563;
      text-decoration: none; border-radius: 20px;
      transition: all 0.2s ease; font-weight: 600;
    }
    .top-header-nav a:hover, .std-top-nav a:hover { color: #0d9488; background: rgba(13,148,136,0.06); }
    .top-header-nav a.active, .std-top-nav a.active { background: #0d9488; color: #fff; }
    .nav-dropdown, .std-nav-dd { position: relative; }
    .nav-dropdown > a::after, .std-nav-dd > a::after { content: ' ▾'; font-size: 10px; opacity: 0.6; margin-left: 2px; }
    .nav-dropdown .dropdown-menu, .std-nav-dd .std-dd-menu {
      position: absolute; top: 100%; left: 50%;
      transform: translateX(-50%) translateY(10px);
      min-width: 220px; max-height: 80vh; overflow-y: auto;
      padding: 8px; background: #fff;
      border: 1px solid rgba(0,0,0,0.06); border-radius: 12px;
      box-shadow: 0 10px 40px -10px rgba(0,0,0,0.12);
      opacity: 0; visibility: hidden;
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
      z-index: 100; margin-top: 8px;
    }
    .nav-dropdown:hover .dropdown-menu, .nav-dropdown:focus-within .dropdown-menu,
    .std-nav-dd:hover .std-dd-menu, .std-nav-dd:focus-within .std-dd-menu {
      opacity: 1; visibility: visible; transform: translateX(-50%) translateY(0);
    }
    .nav-dropdown .dropdown-menu a, .std-nav-dd .std-dd-menu a {
      display: block; padding: 12px 16px; color: #111827;
      text-decoration: none; line-height: 1.4; border-radius: 8px; text-align: left;
    }
    .nav-dropdown .dropdown-menu a:hover, .std-nav-dd .std-dd-menu a:hover { background: #f9fafb; }
    .nav-dropdown .dropdown-menu a .menu-title, .std-nav-dd .std-dd-menu a .menu-title {
      display: block; font-weight: 600; font-size: 14px; color: #111827; margin-bottom: 2px;
    }
    .nav-dropdown .dropdown-menu a:hover .menu-title, .std-nav-dd .std-dd-menu a:hover .menu-title { color: #0d9488; }
    .nav-dropdown .dropdown-menu a .menu-desc, .std-nav-dd .std-dd-menu a .menu-desc {
      display: block; font-size: 12px; color: #6b7280; font-weight: 400; line-height: 1.4;
    }
    /* ── Mobile nav ────────────────────────────────── */
    @media (max-width: 768px) {
      body { padding-top: 64px; }
      .top-header { padding: 0 20px; }
      .top-header .slogan, .top-header .std-slogan { display: none; }
      .mobile-menu-btn, .std-mobile-btn {
        display: block;
        margin-left: auto;
        color: #111827;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 6px 10px;
        cursor: pointer;
        background: none;
      }
      .top-header-nav, .std-top-nav {
        position: fixed;
        top: 0; left: 0;
        width: 100vw; height: 100vh;
        background: #fff;
        flex-direction: column;
        justify-content: center; align-items: center;
        gap: 8px;
        margin: 0;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.25s ease;
        z-index: 10000;
      }
      .top-header-nav.open, .std-top-nav.open {
        opacity: 1;
        pointer-events: auto;
      }
      .top-header-nav a, .std-top-nav a {
        font-size: 18px; padding: 10px 24px; color: #111827;
      }
      .top-header-nav a:hover, .std-top-nav a:hover { color: #0d9488; background: rgba(13,148,136,0.06); }
      .top-header-nav a.active, .std-top-nav a.active { background: #0d9488; color: #fff; }
      .nav-close-btn, .std-nav-close {
        display: block; position: absolute; top: 20px; right: 20px;
        background: none; border: none; font-size: 32px; color: #111827; cursor: pointer;
        line-height: 1; padding: 4px 8px;
      }
      .nav-dropdown .dropdown-menu, .std-nav-dd .std-dd-menu { display: none; }
      .nav-dropdown > a::after, .std-nav-dd > a::after { display: none; }
    }
    /* ── Overflow protection ───────────────────────── */
    html, body { max-width: 100%; overflow-x: hidden; }
    table { display: block; width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
    thead, tbody, tr { width: 100%; }
"""

# ── Patterns to strip from HTML pages ─────────────────────────────────────────
# 1. The original duplicate header CSS lines (29-52 range equivalents)
OLD_HEADER_STUBS = [
    # Original stub from first version
    r'    \.top-header \.brand a \{ text-decoration: none; color: #111827;[^\n]+\}\n',
    r'    \.top-header \.brand \.accent \{[^\n]+\}\n',
    r'    \.mobile-menu-btn \{ display: none;[^\n]+\}\n',
    r'    \.nav-close-btn \{ display: none; \}\n',
    r'    /\* Nav \*/\n    \n',
    r'    \.top-header-nav a \{ padding: 7px[^\n]+\}\n',
    r'    \.top-header-nav a:hover \{[^\n]+\}\n',
    r'    \.top-header-nav a\.active \{[^\n]+\}\n',
    r'    \n    \.nav-dropdown \{ position: relative; \}\n',
    r'    \.nav-dropdown > a::after \{[^\n]+\}\n',
    r'    \.nav-dropdown \.dropdown-menu \{ position: absolute;[^\n]+\}\n',
    r'    \.nav-dropdown:hover \.dropdown-menu,[^\n]+\}\n',
    r'    \.nav-dropdown \.dropdown-menu a \{ display: block; padding: 12px[^\n]+\}\n',
    r'    \.nav-dropdown \.dropdown-menu a:hover \{[^\n]+\}\n',
    r'    \.nav-dropdown \.dropdown-menu a \.menu-title \{[^\n]+\}\n',
    r'    \.nav-dropdown \.dropdown-menu a:hover \.menu-title \{[^\n]+\}\n',
    r'    \.nav-dropdown \.dropdown-menu a \.menu-desc \{[^\n]+\}\n',
]

# 2. The large accumulated junk block
# It starts with the first injected @media(max-width:768px) block for .std-mobile-btn
JUNK_PATTERN = re.compile(
    r'\n\s+@media \(max-width: 768px\) \{[^}]*\.mobile-menu-btn, \.std-mobile-btn \{ display: block !important.*?'
    r'(?=\n\s+/\* Hero \*/|\n</style>|\Z)',
    re.DOTALL
)

# Simpler approach: find the block from the first injected mobile CSS to end of style
# Marker: the first instance of "display: block !important" inside a 768px media query 
FULL_JUNK_PATTERN = re.compile(
    r'(\n    /\* Header \*/\n.*?)(    /\* Hero \*/)',
    re.DOTALL
)


def rebuild_header(content: str) -> str:
    """Replace the messy header CSS section with the clean version."""
    # Strategy: find everything between '/* Header */' and '/* Hero */'
    # and replace it with the clean header CSS
    
    header_start = content.find('    /* Header */')
    hero_marker = content.find('    /* Hero */')
    
    if header_start == -1 or hero_marker == -1:
        # Fallback: look for the specific junk start marker
        # Find the first occurrence of the injected mobile CSS
        junk_start = content.find('\n    @media (max-width: 768px) {\n      \n      .mobile-menu-btn, .std-mobile-btn { display: block !important; }')
        if junk_start == -1:
            # Try another marker
            junk_start = content.find('/* Global responsive table fix */')
            if junk_start == -1:
                return content  # Can't find junk, skip
        
        style_end = content.rfind('  </style>')
        if style_end == -1:
            return content
        
        # Remove junk from junk_start to style_end
        content = content[:junk_start] + '\n' + CLEAN_HEADER_CSS + '\n  </style>' + content[style_end + len('  </style>'):]
        return content
    
    # Replace the header section
    before_header = content[:header_start]
    after_hero = content[hero_marker:]
    
    content = before_header + CLEAN_HEADER_CSS + '\n    ' + after_hero
    return content


def process_file(path: Path) -> bool:
    """Process a single HTML file. Returns True if modified."""
    content = path.read_text(encoding='utf-8')
    original = content
    
    new_content = rebuild_header(content)
    
    if new_content != original:
        path.write_text(new_content, encoding='utf-8')
        return True
    return False


files_fixed = 0
files_skipped = 0

for html_file in sorted(SRC.glob('*.html')):
    # Skip files that don't have the header system
    content = html_file.read_text(encoding='utf-8')
    if 'top-header' not in content and 'std-mobile-btn' not in content:
        continue
    
    if process_file(html_file):
        files_fixed += 1
        print(f"  Rebuilt: {html_file.name}")
    else:
        files_skipped += 1
        # print(f"  Skipped: {html_file.name}")

print(f"\nDone. Rebuilt {files_fixed} files, skipped {files_skipped}.")
