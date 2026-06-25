"""
standardize_kb_pages.py  ── 2026-04-07
Make ALL Therasik knowledge-base sub-pages visually identical:
  • header: fixed, green border, Cormorant brand 26px, slogan inline-flex
  • page hero: <div class="page-header"> with soft green gradient
  • body padding-top: 62px (matches 62px fixed header height)
  • remove leftover homepage-only hero CSS from ADA Database
"""
import re, glob

# ── Standard CSS blocks to inject/replace ─────────────────────────────────────

BRAND_SLOGAN_CSS = """
    /* ── Brand & Slogan ── */
    .top-header .brand { font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 700; font-size: 26px; letter-spacing: -0.03em; display: flex; align-items: center; flex-wrap: nowrap; min-width: max-content; white-space: nowrap; }
    .top-header .brand a { text-decoration: none; color: #111827; display: flex; align-items: center; gap: 10px; white-space: nowrap; flex-shrink: 0; }
    .top-header .brand .accent { color: var(--primary); font-style: italic; font-weight: 700; }
    .top-header .slogan { font-size: 14px; color: var(--text-muted); padding-left: 14px; border-left: 1px solid var(--border); margin-left: 14px; font-weight: 600; white-space: nowrap; display: inline-flex; align-items: center; flex-shrink: 0; }
"""

PAGE_HEADER_CSS = """
    /* ── Page Header (knowledge-base hero) ── */
    .page-header { background: linear-gradient(135deg, #f0fdfa 0%, #e8f6f3 60%, #f5f5f0 100%); border-bottom: 1px solid rgba(13,148,136,0.12); padding: 40px 40px 32px; }
    .page-header h1 { font-family: 'Cormorant Garamond', serif; font-size: 38px; font-weight: 700; margin: 0 0 10px; letter-spacing: -0.02em; color: #111827; }
    .page-header p { color: #6b7280; font-size: 15px; max-width: 720px; line-height: 1.65; margin: 0 0 16px; }
    .back-link { font-size: 14px; color: var(--primary); text-decoration: none; font-weight: 500; display: inline-flex; align-items: center; gap: 6px; margin-bottom: 16px; }
    .back-link:hover { color: var(--primary-dark); }
    @media (max-width: 768px) {
      .page-header { padding: 28px 20px 24px; }
      .page-header h1 { font-size: 28px; }
    }
"""

# ADA database has these meta chips below the description — keep their CSS
ADA_META_CHIP_CSS = """
    .hero-meta { display: flex; gap: 16px; margin-top: 16px; flex-wrap: wrap; }
    .meta-chip { background: rgba(255,255,255,0.85); border: 1px solid rgba(13,148,136,0.18); border-radius: 20px; padding: 5px 14px; font-size: 12px; color: var(--text-muted); }
    .meta-chip b { color: var(--primary-dark); }
"""

# ── Knowledge-base subpages (NOT index, NOT service pages) ───────────────────
KB_PAGES = [
    'docs/Therasik_ADA_Database.html',
    'docs/Therasik_ADC_Database.html',
    'docs/Therasik_Antibody_Guide.html',
    'docs/Therasik_Component_Browser.html',
    'docs/Therasik_Vaccine_KB.html',
]

def ensure_brand_slogan_css(content):
    """
    If the page already has .top-header .brand { ... } with font-size, leave it.
    Otherwise inject/replace with the standard block.
    """
    # Check if correct brand CSS already exists
    has_brand = bool(re.search(
        r'\.top-header \.brand\s*\{[^}]*font-size:\s*26px', content))
    has_slogan = bool(re.search(
        r'\.top-header \.slogan\s*\{[^}]*display:\s*inline-flex', content))
    has_plain_brand = bool(re.search(
        r'\.brand\s*\{[^}]*font-size:\s*26px', content))

    if has_brand and has_slogan:
        return content  # already correct

    # Remove any stale .brand / .slogan rules (not scoped to .top-header)
    content = re.sub(r'\n    \.brand\s*\{[^}]+\}', '', content)
    content = re.sub(r'\n    \.slogan\s*\{[^}]+\}', '', content)

    # Inject after the top-header block
    inject_after = re.search(r'(\.top-header\s*\{[^}]+\})', content)
    if inject_after:
        pos = inject_after.end()
        content = content[:pos] + BRAND_SLOGAN_CSS + content[pos:]
    return content

def ensure_page_header_css(content, is_ada=False):
    """
    Add or update .page-header CSS to have the standard green gradient.
    """
    # Check if background is already set on .page-header
    has_bg = bool(re.search(
        r'\.page-header\s*\{[^}]*background:\s*linear-gradient', content))

    if has_bg and not is_ada:
        # Ensure the background is the standard one (update if different)
        content = re.sub(
            r'(\.page-header\s*\{[^}]*)background:\s*[^;]+;',
            r'\1background: linear-gradient(135deg, #f0fdfa 0%, #e8f6f3 60%, #f5f5f0 100%);',
            content
        )
        return content

    # Remove existing .page-header CSS so we can replace cleanly
    content = re.sub(r'\n    /\* ── Page Header[^*]*\*/\n.*?(?=\n    /\*|\Z)',
                     '', content, flags=re.DOTALL)
    # Also remove inline .page-header if it just has margin
    content = re.sub(r'\n  \.page-header \{ margin-bottom:[^}]+\}', '', content)
    content = re.sub(r'\n    \.page-header \{ margin-bottom:[^}]+\}', '', content)

    # Inject before </style>
    css_to_inject = PAGE_HEADER_CSS
    if is_ada:
        css_to_inject += ADA_META_CHIP_CSS
    content = content.replace('</style>', css_to_inject + '\n  </style>', 1)
    return content

def fix_body_padding(content, target_px=62):
    """Set body padding-top at desktop level (outside @media)."""
    style_block = re.search(r'(<style>)(.*?)(</style>)', content, re.DOTALL)
    if not style_block:
        return content

    css = style_block.group(2)
    first_media = css.find('@media')
    css_pre = css[:first_media] if first_media != -1 else css

    body_m = re.search(r'(body\s*\{)([^}]+)(\})', css_pre)
    if body_m:
        decls = body_m.group(2)
        if 'padding-top' in decls:
            # Replace existing padding-top value
            new_decls = re.sub(r'padding-top:\s*[^;]+;',
                               f'padding-top: {target_px}px;', decls)
        else:
            new_decls = decls.rstrip() + f' padding-top: {target_px}px;'
        old_rule = body_m.group(0)
        new_rule = body_m.group(1) + new_decls + body_m.group(3)
        content = content.replace(old_rule, new_rule, 1)
    return content

def convert_ada_hero_to_page_header(content):
    """
    ADA Database uses <section class="hero"> instead of <div class="page-header">.
    Convert it and strip the homepage-only .hero CSS.
    """
    # Convert HTML element
    content = content.replace('<section class="hero">', '<div class="page-header">', 1)
    # Find the closing </section> that matches (after .hero content, before .controls)
    # ADA hero ends before <div class="controls">
    content = re.sub(
        r'</section>\s*\n\s*<!-- ── Controls',
        '</div>\n\n<!-- ── Controls',
        content, count=1
    )
    # Remove large homepage-only hero CSS that was wrongly injected
    # Pattern: the injected block starts with .hero { position: relative; min-height
    content = re.sub(
        r'\n    \.hero \{ position: relative; min-height:[^}]+\}',
        '', content
    )
    content = re.sub(
        r'\n    \.hero-banner \{[^}]+\}',
        '', content
    )
    content = re.sub(
        r'\n    \.hero-banner img \{[^}]+\}',
        '', content
    )
    content = re.sub(
        r'\n    \.hero-overlay \{[^}]+\}',
        '', content
    )
    content = re.sub(
        r'\n    \.hero \.hero-inner \{[^}]+\}',
        '', content
    )
    content = re.sub(
        r'\n    \.hero h1 \{ font-family.*?color: #ffffff[^}]+\}',
        '', content
    )
    content = re.sub(
        r'\n    \.hero \.tagline \{[^}]+\}',
        '', content
    )
    content = re.sub(
        r'\n    \.hero \.cta-row \{[^}]+\}',
        '', content
    )
    content = re.sub(
        r'\n    \.hero \.btn \{[^}]+\}',
        '', content
    )
    content = re.sub(
        r'\n    \.hero \.btn-outline \{[^}]+\}',
        '', content
    )
    content = re.sub(
        r'\n    \.hero-features \{[^}]+\}',
        '', content
    )
    content = re.sub(
        r'\n    \.feature-item \{[^}]+\}',
        '', content
    )
    content = re.sub(
        r'\n    \.feature-item svg \{[^}]+\}',
        '', content
    )
    # Remove the old .hero rule that had background gradient + margin-top:58px
    content = re.sub(
        r'\n    /\* ── Hero ── \*/\n    \.hero \{[^}]+\}',
        '', content
    )
    content = re.sub(
        r'\n    \.hero h1 \{[^}]+\}',
        '', content
    )
    content = re.sub(
        r'\n    \.hero p \{[^}]+\}',
        '', content
    )
    return content


# ── Process each KB page ──────────────────────────────────────────────────────
for path in KB_PAGES:
    with open(path, 'r', encoding='utf-8') as f:
        original = f.read()

    content = original
    is_ada = 'ADA_Database' in path

    if is_ada:
        content = convert_ada_hero_to_page_header(content)

    content = ensure_brand_slogan_css(content)
    content = ensure_page_header_css(content, is_ada=is_ada)
    content = fix_body_padding(content, target_px=62)

    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'✓ Updated: {path}')
    else:
        print(f'– No change: {path}')

print('\nDone.')
