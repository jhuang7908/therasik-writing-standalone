"""
normalize_service_pages.py  ── 2026-04-07
Fix CSS inconsistencies across the 5 AI service pages:
1. Normalize --text-muted to #6b7280 (all pages)
2. Normalize --text to #111827 (all pages)
3. Fix .trust-card blue tint (#f5f8ff) → green tint (#f0fdf9) on //
4. Add .breadcrumb CSS to ADC page
5. Fix Antibody page h1 / title / meta from old "" to ""
"""
import re

PAGES = [
    "docs/Therasik_Antibody_Page.html",
    "docs/Therasik_ADC_Design_Page.html",
    "docs/Therasik_CART_Page.html",
    "docs/Therasik_Bispecific_Page.html",
    "docs/Therasik_Vaccine_Design.html",
]

# ── 1. Canonical CSS variable values ──────────────────────────────────────────
VAR_FIXES = [
    ('--text-muted: #4b5563', '--text-muted: #6b7280'),
    ('--text: #111827',       '--text: #111827'),   # already correct on 3 pages
    ('--text: #1f2937',       '--text: #111827'),   # fix ADC/CAR-T
]

# ── 2. Trust-card: blue tint → green tint ─────────────────────────────────────
TRUST_CARD_FIX = (
    'linear-gradient(160deg, #fff 0%, #f5f8ff 100%)',
    'linear-gradient(160deg, #fff 0%, #f0fdf9 100%)',
)

# ── 3. ADC breadcrumb CSS (inject after .subtitle rule) ──────────────────────
ADC_BREADCRUMB_CSS = """
    .breadcrumb { font-size: 14px; color: #6b7280; margin-bottom: 32px; font-weight: 500; }
    .breadcrumb a { color: #6b7280; text-decoration: none; }
    .breadcrumb a:hover { color: var(--primary); }
    .breadcrumb span { margin: 0 6px; }"""

# ── 4. Antibody page title fixes ──────────────────────────────────────────────
AB_FIXES = [
    (' | Therasik', ' | Therasik'),
    (' |',          ' |'),
    ('><',          '><'),
    ('content="Therasik ',
     'content="Therasik '),
    # h1 in body
    ('<h1></h1>',   '<h1></h1>'),
    # h1 with id attributes
    ('<h1 id="platform"></h1>',
     '<h1 id="platform"></h1>'),
]

changed = []

for path in PAGES:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read
    orig = content

    # 1. Normalize CSS variables
    for old, new in VAR_FIXES:
        content = content.replace(old, new)

    # 2. Fix trust-card blue tint → green tint
    content = content.replace(TRUST_CARD_FIX[0], TRUST_CARD_FIX[1])

    # 3. ADC: add breadcrumb CSS
    if 'ADC_Design_Page' in path and '.breadcrumb' not in content:
        # inject after .subtitle CSS rule
        content = content.replace(
            '.subtitle { font-size: 20px;',
            ADC_BREADCRUMB_CSS + '\n    .subtitle { font-size: 20px;'
        )
        if '.breadcrumb' not in content:
            # fallback: inject just before </style>
            content = content.replace(
                '  </style>',
                ADC_BREADCRUMB_CSS + '\n  </style>',
                1
            )

    # 4. Antibody page title/meta/h1
    if 'Antibody_Page' in path:
        for old, new in AB_FIXES:
            content = content.replace(old, new)

    if content != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        changed.append(path)
        print(f"✓ Fixed: {path}")
    else:
        print(f"– Unchanged: {path}")

print(f"\n{len(changed)} files updated.")
