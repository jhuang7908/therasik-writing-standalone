"""
rename_knowledge_base.py  ── 2026-04-07
Replace "" with "" in:
  - top navigation dropdown label
  - section headings on homepage
  - page meta descriptions where relevant
  BUT keep individual page names intact (e.g. "" stays as-is)
"""
import glob, re

all_html = glob.glob("docs/Therasik_*.html") + ["docs/therasik_index.html"]

for path in all_html:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read
    original = content

    # ── Nav dropdown trigger link (the label that shows in the nav bar) ──
    # Change: <a href="...#knowledge-base"></a>
    # Keep:   <span class="menu-title"></span>  (individual page names)
    content = re.sub(
        r'(<a href="[^"]*#knowledge-base"[^>]*>)\s*\s*(</a>)',
        r'\1\2',
        content
    )
    # Also the non-anchor version: >< in nav (not inside menu-title span)
    content = re.sub(
        r'(<a href="[^"]*knowledge-base[^"]*"[^>]*>)\s*\s*(</a>)',
        r'\1\2',
        content
    )

    # ── Homepage section heading ──
    content = re.sub(
        r'(<h2[^>]*>)\s*\s*(</h2>)',
        r'\1\2',
        content
    )
    content = re.sub(
        r'(<span[^>]*section-label[^>]*>)\s*\s*(</span>)',
        r'\1\2',
        content
    )

    # ── Active nav text in standalone <a> tags (not inside menu-title) ──
    # Pattern: >< that is the direct nav link text, not a page title
    # Use negative lookbehind to avoid changing "", "ADA" etc.
    # We target only standalone "" as nav link text
    content = re.sub(
        r'(?<![^\s>])(?=\s*</a>)',
        '',
        content
    )

    if content != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✓ {path}")
    else:
        print(f"– {path}")

print("\nDone.")
