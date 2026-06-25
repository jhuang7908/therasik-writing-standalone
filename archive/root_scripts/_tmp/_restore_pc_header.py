"""
1. Restore PC header: height 72px, logo 22px, body padding-top 72px
2. Remove forced color-scheme light override (user accepts dark mode on mobile)
"""
from pathlib import Path
import re

SRC = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source")

# ── Remove color-scheme override ─────────────────────────────────
OLD_COLOR_BLOCK = '''  <meta name="color-scheme" content="only light">
  <style>
  :root { color-scheme: only light; }
  /* Block Android Chrome forced dark mode */
  html { background: #ffffff !important; }
  body { background: #ffffff !important; color: #111827 !important; }
  @media (prefers-color-scheme: dark) {
    html, body { background: #ffffff !important; color: #111827 !important; }
    .top-header { background: rgba(255,255,255,0.98) !important; }
    .top-header .brand a, .top-header .brand a span { color: #111827 !important; }
    .top-header-nav a, .std-top-nav a { color: #4b5563 !important; }
  }
</style>'''

# ── CSS fixes for header size ─────────────────────────────────────
FIXES = [
    # height 64px → 72px
    ('height: 64px;\n      background:', 'height: 72px;\n      background:'),
    # padding 0 28px → 0 32px
    ('padding: 0 28px;\n      box-sizing:', 'padding: 0 32px;\n      box-sizing:'),
    # font-size 18px → 22px for brand
    ('font-size: 18px; font-weight: 700;\n      white-space: nowrap; flex-shrink: 0;\n    }',
     'font-size: 22px; font-weight: 700;\n      white-space: nowrap; flex-shrink: 0;\n      font-family: \'Space Grotesk\', \'Inter\', sans-serif;\n    }'),
    # slogan font 13px → 14px
    ('font-size: 13px; color: #6b7280;\n      padding-left: 12px; border-left: 1px solid #e5e7eb; margin-left: 4px;',
     'font-size: 14px; color: #6b7280;\n      padding-left: 14px; border-left: 1px solid #e5e7eb; margin-left: 6px;'),
    # body padding-top 64px → 72px (in the mobile media query too)
    ('body { padding-top: 64px; overflow-x: hidden; }',
     'body { padding-top: 72px; overflow-x: hidden; }'),
    # body padding-top in global rule
    ('padding-top: 64px; overflow-x: hidden; }',
     'padding-top: 72px; overflow-x: hidden; }'),
]

fixed = 0
for f in sorted(SRC.glob("*.html")):
    if f.name == "index.html":
        continue  # Already done manually
    content = f.read_text(encoding="utf-8")
    original = content

    # Remove color-scheme block
    content = content.replace(OLD_COLOR_BLOCK, "")

    # Apply header size fixes
    for old, new in FIXES:
        content = content.replace(old, new)

    if content != original:
        f.write_text(content, encoding="utf-8")
        fixed += 1
        print(f"  Fixed: {f.name}")

print(f"\nDone. {fixed} files updated.")
