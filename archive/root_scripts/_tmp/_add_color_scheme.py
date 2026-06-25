"""
Add color-scheme: light to all InSynBio pages to prevent dark mode override.
"""
from pathlib import Path

SRC = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source")

OLD = '  <meta name="viewport" content="width=device-width, initial-scale=1.0">'
NEW = ('  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
       '  <meta name="color-scheme" content="light only">\n'
       '  <style>:root { color-scheme: light only; }</style>')

fixed = 0
for f in sorted(SRC.glob("*.html")):
    content = f.read_text(encoding="utf-8")
    if 'color-scheme' in content:
        continue  # Already has it
    if OLD not in content:
        # Try without indentation
        alt = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        if alt in content:
            content = content.replace(alt,
                alt + '\n  <meta name="color-scheme" content="light only">\n  <style>:root { color-scheme: light only; }</style>')
            f.write_text(content, encoding="utf-8")
            fixed += 1
            print(f"  Fixed: {f.name}")
        continue
    content = content.replace(OLD, NEW)
    f.write_text(content, encoding="utf-8")
    fixed += 1
    print(f"  Fixed: {f.name}")

print(f"\nDone. {fixed} files updated.")
