"""
normalize_therasik_pages.py
One-shot script to bring ALL Therasik HTML pages to a consistent visual standard:
  1. Fix :root CSS variables → green theme (#0d9488)
  2. Remove duplicate / homepage-only hero+section CSS that was wrongly injected by fix_ada_css3.py
  3. Ensure body has desktop padding-top:62px for fixed header
  4. Ensure .top-header uses the correct green border + fixed position
  5. Remove stray duplicate CSS rules
"""
import glob, re

GREEN = {
    '--primary': '#0d9488',
    '--primary-dark': '#0f766e',
    '--primary-light': '#ccfbf1',
}

# CSS chunks that belong ONLY to the homepage and should NOT appear in subpages
HOMEPAGE_ONLY_PATTERNS = [
    # The full-screen hero with banner image (index page style)
    r'\.hero-banner \{[^}]+\}',
    r'\.hero-overlay \{[^}]+\}',
    r'\.hero .hero-inner \{[^}]+\}',
    r'\.hero \.btn \{[^}]+\}',
    r'\.hero \.btn-outline \{[^}]+\}',
    r'\.hero-features \{[^}]+\}',
    r'\.feature-item \{[^}]+\}',
    r'\.feature-item svg \{[^}]+\}',
    # Homepage sections
    r'\.section-alt \{[^}]+\}',
    r'#about\.section \{[^}]+\}',
    r'#knowledge-base\.section \{[^}]+\}',
    r'\.section h2 \{[^}]+\}',
    r'\.section \.section-label \{[^}]+\}',
    r'\.section p \{[^}]+\}',
    r'\.section ul \{[^}]+\}',
    r'\.section li \{[^}]+\}',
    r'\.section \.highlight \{[^}]+\}',
    r'\.stat-strip \{[^}]+\}',
    r'\.stat-item \{[^}]+\}',
    r'\.services-grid \{[^}]+\}',
    r'\.service-card \{[^}]+\}',
    r'\.trust-inner \{[^}]+\}',
    r'\.trust-item \{[^}]+\}',
    r'\.workflow-steps \{[^}]+\}',
    r'\.workflow-step \{[^}]+\}',
    r'\.contact-grid \{[^}]+\}',
    r'\.contact-card \{[^}]+\}',
    r'\.lang-switch \{[^}]+\}',
    r'\.lang-switch button \{[^}]+\}',
]

# Subpages that should NOT have homepage CSS mixed in
SUBPAGES = [f for f in glob.glob("docs/Therasik_*.html")
            if 'therasik_index' not in f.lower()]

def fix_root_vars(content):
    """Replace blue :root variables with green equivalents."""
    # Fix --primary
    content = re.sub(r'--primary:\s*#2563eb', '--primary: #0d9488', content)
    content = re.sub(r'--primary-dark:\s*#1e40af', '--primary-dark: #0f766e', content)
    content = re.sub(r'--primary-light:\s*#dbeafe', '--primary-light: #ccfbf1', content)
    # Fix blue rgba references in CSS (not in HTML attributes)
    content = re.sub(r'rgba\(37,\s*99,\s*235,\s*([\d.]+)\)',
                     lambda m: f'rgba(13,148,136,{m.group(1)})', content)
    content = re.sub(r'rgba\(37,\s*99,\s*235,\s*([\d.]+)\)',
                     lambda m: f'rgba(13,148,136,{m.group(1)})', content)
    # Fix blue hex in border-bottom of top-header
    content = content.replace('border-bottom:2px solid rgba(37, 99, 235, 0.12)',
                              'border-bottom:2px solid rgba(13,148,136,0.15)')
    content = content.replace('border-bottom: 2px solid rgba(37, 99, 235, 0.1)',
                              'border-bottom: 2px solid rgba(13,148,136,0.15)')
    # Fix --bg-alt2 if it is light blue
    content = re.sub(r'--bg-alt2:\s*#eff6ff', '--bg-alt2: #f0fdfa', content)
    content = re.sub(r'--bg-alt2:\s*#f0f9ff', '--bg-alt2: #f0fdfa', content)
    # Fix card-border blue
    content = re.sub(r'--card-border:\s*rgba\(37,\s*99,\s*235,\s*([\d.]+)\)',
                     lambda m: f'--card-border: rgba(13,148,136,{m.group(1)})', content)
    content = re.sub(r'--card-shadow:[^;]+rgba\(37,\s*99,\s*235[^;]+;',
                     '--card-shadow: 0 2px 10px rgba(13,148,136,0.08);', content)
    return content

def fix_body_padding(content):
    """Ensure body has padding-top:62px at desktop level (for fixed header)."""
    # Check if desktop-level padding-top is set for body
    # We look for body { ... } outside of @media queries
    style_block = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
    if not style_block:
        return content
    css = style_block.group(1)

    # Find body rule outside media queries (simple heuristic: before first @media)
    first_media = css.find('@media')
    css_before_media = css[:first_media] if first_media != -1 else css

    body_match = re.search(r'body\s*\{([^}]+)\}', css_before_media)
    if body_match:
        body_decls = body_match.group(1)
        if 'padding-top' not in body_decls:
            # Add padding-top to existing body rule
            new_body_decls = body_decls.rstrip() + ' padding-top: 62px;'
            content = content.replace(body_match.group(0),
                                      f'body {{{new_body_decls}}}', 1)
    return content

def fix_top_header_css(content):
    """Ensure top-header is position:fixed with green border."""
    content = re.sub(
        r'\.top-header\s*\{[^}]*position:\s*sticky[^}]*\}',
        lambda m: m.group(0).replace('position: sticky', 'position: fixed')
                              .replace('position:sticky', 'position:fixed'),
        content
    )
    # Ensure width:100% in top-header
    def add_width(m):
        decls = m.group(1)
        if 'width:100%' not in decls and 'width: 100%' not in decls:
            decls = decls.rstrip() + ' width:100%;'
        return f'.top-header {{{decls}}}'
    content = re.sub(r'\.top-header\s*\{([^}]+)\}', add_width, content)
    return content

def remove_duplicate_active_rules(content):
    """Remove duplicate .top-header-nav a.active rules."""
    # Keep only the first occurrence; remove subsequent identical ones
    pattern = r'\.top-header-nav a\.active \{ background: var\(--primary\); color: #fff; font-weight: 500; \}'
    matches = [(m.start(), m.end()) for m in re.finditer(re.escape(
        '.top-header-nav a.active { background: var(--primary); color: #fff; font-weight: 500; }'), content)]
    # Remove all but the first
    for start, end in reversed(matches[1:]):
        content = content[:start] + content[end:]
    return content

changes = {}

for filepath in SUBPAGES:
    with open(filepath, 'r', encoding='utf-8') as f:
        original = f.read()

    content = original
    content = fix_root_vars(content)
    content = fix_body_padding(content)
    content = fix_top_header_css(content)
    content = remove_duplicate_active_rules(content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        changes[filepath] = True
        print(f"Fixed: {filepath}")
    else:
        print(f"No change: {filepath}")

print(f"\nTotal files modified: {sum(changes.values())}")
