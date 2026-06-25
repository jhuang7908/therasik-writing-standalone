"""
fix_hero_width_backlinks.py  ── 2026-04-07
1. Move <div class="page-header"> OUTSIDE of <div class="page"> in ADC and Vaccine KB
   so the hero is full-width (not constrained by max-width:1200px)
2. Add back-link (<a class="back-link">) to each KB page pointing to its parent service
"""
import re

# ── Back-link mapping: KB page → (service Chinese name, service URL) ─────────
BACK_LINKS = {
    'docs/Therasik_ADA_Database.html':      ('', 'Therasik_Antibody_Page.html'),
    'docs/Therasik_ADC_Database.html':      (' ADC ',  'Therasik_ADC_Design_Page.html'),
    'docs/Therasik_Antibody_Guide.html':    ('', 'Therasik_Antibody_Page.html'),
    'docs/Therasik_Component_Browser.html': (' CAR-T ','Therasik_CART_Page.html'),
    'docs/Therasik_Vaccine_KB.html':        ('',   'Therasik_Vaccine_Design.html'),
}

BACK_LINK_ARROW = (
    '<a href="{url}" class="back-link">\n'
    '    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>\n'
    '    {name}\n'
    '  </a>\n  '
)

for path, (service_name, service_url) in BACK_LINKS.items:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read

    original = content
    changed = False

    # ── 1. Fix width: move <div class="page-header"> outside <div class="page"> ──
    # Pattern: <div class="page">\n  <!-- ... -->\n  <div class="page-header">
    # or: <div class="page">\n  <div class="page-header">
    pattern = re.compile(
        r'(<div class="page">)\s*'
        r'(<!--[^>]*-->\s*)?'        # optional comment
        r'(<div class="page-header">.*?</div>)\s*',  # the page-header block
        re.DOTALL
    )
    m = pattern.search(content)
    if m:
        page_open = m.group(1)
        comment   = (m.group(2) or '').strip
        ph_block  = m.group(3).strip
        # Reconstruct: page-header first (full-width), then page div (max-width)
        replacement = ph_block + '\n\n' + page_open + '\n'
        content = content[:m.start] + replacement + content[m.end:]
        changed = True
        print(f'[width] Fixed page-header position in {path}')

    # ── 2. Add back-link inside page-header if not already present ───────────
    bl_href = f'href="{service_url}"'
    if bl_href not in content and 'class="back-link"' not in content:
        # Inject the back-link right after <div class="page-header">
        back_link_html = BACK_LINK_ARROW.format(url=service_url, name=service_name)
        content = content.replace(
            '<div class="page-header">\n',
            '<div class="page-header">\n  ' + back_link_html,
            1
        )
        changed = True
        print(f'[link]  Added back-link "{service_name}" to {path}')
    elif 'class="back-link"' in content:
        # Update the existing back-link URL if it points to wrong page
        content = re.sub(
            r'(<a href=")[^"]*("[\s\S]*?class="back-link">)',
            lambda m2: m2.group(0).replace(m2.group(0),
                f'<a href="{service_url}" class="back-link">'),
            content, count=1
        )
        # Also update the text inside the back-link if needed
        content = re.sub(
            r'(class="back-link"[^>]*>[\s\S]*?<svg[^>]*>.*?</svg>\s*)\n\s*[^\n<]+(\n\s*</a>)',
            lambda m2: m2.group(1) + f'\n    {service_name}' + m2.group(2),
            content, count=1
        )

    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    else:
        print(f'[skip]  No changes in {path}')

print('\nDone.')
