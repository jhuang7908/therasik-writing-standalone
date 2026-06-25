"""
fix_nav_service.py  ── 2026-04-07
1. Rename "" nav label  →  "AI "
2. Fix order: ""  →  ""  (everywhere)
3. Fix menu-desc: remove "", replace with ""
4. Update homepage section label / heading / service card description
5. Fix back-links on KB pages
"""
import glob, re

# All HTML files that carry the shared nav
files = (
    glob.glob("docs/Therasik_*.html")
    + ["docs/therasik_index.html"]
)

REPLACEMENTS = [
    # ── 1. Nav trigger:  → AI  ─────────────────────────────────────
    (
        '></a>',
        '>AI </a>',
        True   # replace all occurrences in file
    ),
    # ── 2. Menu title ──────────────────────────────────────────────────────────
    (
        '',
        '',
        True
    ),
    # ── 3. Menu desc:  removed ─────────────────────────────────────────
    (
        '、、',
        '、、',
        True
    ),
]

# ── Homepage-only replacements ─────────────────────────────────────────────────
HOME_REPLACEMENTS = [
    # Section label
    (
        '<span class="section-label lang-zh"></span>',
        '<span class="section-label lang-zh">AI </span>',
    ),
    # Section heading
    (
        '<h2 style="margin-bottom:6px"></h2>',
        '<h2 style="margin-bottom:6px">AI </h2>',
    ),
    # Service card description (antibody card) — remove 
    (
        '、、、、、。',
        '、、、、。',
    ),
    # Section-level subtitle
    (
        ' in silico 、。',
        ' AI 、。',
    ),
]

changed = []

for path in files:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read
    orig = content

    # Global replacements
    for old, new, _ in REPLACEMENTS:
        content = content.replace(old, new)

    # Homepage-only
    if 'therasik_index.html' in path.lower:
        for old, new in HOME_REPLACEMENTS:
            content = content.replace(old, new)

    if content != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        changed.append(path)

print(f"Changed {len(changed)} files:")
for p in changed:
    print(f"  ✓ {p}")
