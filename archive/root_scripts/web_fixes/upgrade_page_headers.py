"""
upgrade_page_headers.py  ── 2026-04-07
Upgrade all KB page-header heroes to a richer, more professional style:
  • Deeper teal-green gradient (not near-white)
  • 4px green accent bar at the very top
  • Slightly larger padding
  • Better h1/p color contrast
  • Consistent across all 5 KB pages
"""
import re, glob

KB_PAGES = [
    'docs/Therasik_ADA_Database.html',
    'docs/Therasik_ADC_Database.html',
    'docs/Therasik_Antibody_Guide.html',
    'docs/Therasik_Component_Browser.html',
    'docs/Therasik_Vaccine_KB.html',
]

# New page-header CSS — deeper, richer, still light enough for readability
NEW_PH_CSS = (
    '.page-header { '
    'background: linear-gradient(135deg, #e6faf7 0%, #d4f3ed 45%, #eaf7f3 100%); '
    'border-top: 4px solid #0d9488; '
    'border-bottom: 1px solid rgba(13,148,136,0.18); '
    'padding: 36px 40px 28px; '
    '}'
)
NEW_PH_H1 = (
    '.page-header h1 { '
    'font-family: \'Cormorant Garamond\', serif; '
    'font-size: 38px; font-weight: 700; '
    'margin: 0 0 10px; letter-spacing: -0.02em; '
    'color: #0d4a43; '          # deep teal instead of near-black
    '}'
)
NEW_PH_P = (
    '.page-header p { '
    'color: #2d6a61; '          # teal-muted, readable on green bg
    'font-size: 15px; max-width: 720px; line-height: 1.65; margin: 0 0 16px; '
    '}'
)
NEW_BACKLINK = (
    '.back-link { '
    'font-size: 13px; color: #0f766e; text-decoration: none; font-weight: 600; '
    'display: inline-flex; align-items: center; gap: 5px; margin-bottom: 14px; '
    'opacity: 0.85; '
    '}'
    '\n    .back-link:hover { opacity: 1; color: #0d9488; }'
)

# Mobile override
MOBILE_CSS = (
    '@media (max-width: 768px) { '
    '.page-header { padding: 24px 20px 20px; } '
    '.page-header h1 { font-size: 26px; } '
    '}'
)

FULL_CSS = f"""
    /* ── Page Header (knowledge-base hero) ── */
    {NEW_PH_CSS}
    {NEW_PH_H1}
    {NEW_PH_P}
    {NEW_BACKLINK}
    {MOBILE_CSS}
"""

# Pattern to replace the old injected block
OLD_PATTERN = re.compile(
    r'/\* ── Page Header \(knowledge-base hero\) ── \*/\n'
    r'.*?'
    r'@media \(max-width: 768px\) \{'
    r'\s*\.page-header \{[^}]+\}'
    r'\s*\.page-header h1 \{[^}]+\}'
    r'\s*\}',
    re.DOTALL
)

for path in KB_PAGES:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content

    # Replace the injected page-header CSS block
    if '/* ── Page Header (knowledge-base hero) ── */' in content:
        content = OLD_PATTERN.sub(FULL_CSS.strip(), content)
    else:
        # Just replace the individual rules
        content = re.sub(
            r'\.page-header\s*\{\s*background:\s*linear-gradient[^}]+\}',
            NEW_PH_CSS, content
        )
        content = re.sub(
            r'\.page-header h1\s*\{[^}]+color:\s*#111827[^}]+\}',
            NEW_PH_H1, content
        )
        content = re.sub(
            r'\.page-header p\s*\{[^}]+color:\s*#6b7280[^}]+\}',
            NEW_PH_P, content
        )

    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'✓ {path}')
    else:
        print(f'– no change: {path}')

print('\nDone.')
