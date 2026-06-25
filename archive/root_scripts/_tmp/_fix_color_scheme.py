"""
Fix color-scheme syntax from 'light only' to 'only light'
and add CSS override for forced dark mode on Android Chrome.
"""
from pathlib import Path

SRC = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source")

# Fix the wrong syntax
OLD_META = '<meta name="color-scheme" content="light only">'
NEW_META = '<meta name="color-scheme" content="only light">'

OLD_STYLE = '<style>:root { color-scheme: light only; }</style>'
NEW_STYLE = '''<style>
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

fixed = 0
for f in sorted(SRC.glob("*.html")):
    content = f.read_text(encoding="utf-8")
    if OLD_META not in content:
        continue
    content = content.replace(OLD_META, NEW_META)
    content = content.replace(OLD_STYLE, NEW_STYLE)
    f.write_text(content, encoding="utf-8")
    fixed += 1
    print(f"  Fixed: {f.name}")

print(f"\nDone. {fixed} files fixed.")
