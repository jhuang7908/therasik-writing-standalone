"""
add_backlinks.py  ── 2026-04-07
Add <a class="back-link"> HTML elements to KB pages that have the CSS but not the element.
Also fix Antibody Guide's extra margin-top on .page-header.
"""
import re

PAGES = {
    'docs/Therasik_ADA_Database.html':      ('', 'Therasik_Antibody_Page.html'),
    'docs/Therasik_ADC_Database.html':      (' ADC ',  'Therasik_ADC_Design_Page.html'),
    'docs/Therasik_Antibody_Guide.html':    ('', 'Therasik_Antibody_Page.html'),
    'docs/Therasik_Component_Browser.html': (' CAR-T ','Therasik_CART_Page.html'),
    'docs/Therasik_Vaccine_KB.html':        ('',   'Therasik_Vaccine_Design.html'),
}

BACK_LINK_SVG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>'

for path, (service_name, service_url) in PAGES.items:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read
    original = content

    # Check if <a class="back-link" is in the HTML body (after </style>)
    body_start = content.find('</style>')
    body_part = content[body_start:] if body_start != -1 else content
    has_back_link_elem = 'class="back-link"' in body_part

    if not has_back_link_elem:
        back_link_html = (
            f'<a href="{service_url}" class="back-link">\n'
            f'    {BACK_LINK_SVG}\n'
            f'    {service_name}\n'
            f'  </a>\n  '
        )
        # Insert right after <div class="page-header">\n
        if '<div class="page-header">\n' in content:
            content = content.replace(
                '<div class="page-header">\n',
                '<div class="page-header">\n  ' + back_link_html,
                1
            )
            print(f'[+link] {path}: added back-link → {service_name}')
        else:
            print(f'[WARN] {path}: no <div class="page-header"> found')
    else:
        print(f'[skip]  {path}: back-link already exists')

    # Fix Antibody Guide: remove extra margin-top:52px from .page-header
    if 'Antibody_Guide' in path:
        content = re.sub(
            r'(\.page-header\s*\{[^}]*)margin-top:\s*\d+px;?\s*',
            r'\1',
            content
        )
        content = re.sub(
            r'(\.page-header\s*\{[^}]*)margin-top:\s*\d+px;?\s*',
            r'\1',
            content
        )  # run twice for robustness
        if content != original:
            print(f'[fix]   {path}: removed margin-top from .page-header')

    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

print('\nDone.')
