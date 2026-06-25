import re

pages = [
    'docs/Therasik_ADA_Database.html',
    'docs/Therasik_ADC_Database.html',
    'docs/Therasik_Vaccine_KB.html',
    'docs/Therasik_Antibody_Guide.html',
    'docs/Therasik_Component_Browser.html',
]

for f in pages:
    with open(f, 'r', encoding='utf-8') as fh:
        c = fh.read()

    name = f.split('/')[-1].replace('.html', '')
    
    # Check HTML element type
    has_ph_div = 'class="page-header"' in c
    has_hero_sec = 'class="hero"' in c

    # Find page-header CSS with background
    ph_bg = re.search(r'\.page-header\s*\{([^}]+)\}', c)
    bg_val = ''
    if ph_bg:
        bg_m = re.search(r'background:\s*([^;]+);', ph_bg.group(1))
        bg_val = bg_m.group(1).strip()[:60] if bg_m else 'no background'

    # Check brand css
    brand_css = re.search(r'\.top-header \.brand\s*\{([^}]+)\}', c)
    slogan_css = re.search(r'\.top-header \.slogan\s*\{([^}]+)\}', c)
    has_brand = bool(brand_css)
    has_slogan = bool(slogan_css)

    # Body padding
    body_before_media = c[:c.find('@media')] if '@media' in c else c
    body_pt = re.search(r'body\s*\{[^}]*padding-top:\s*([^;]+);', body_before_media)
    pt = body_pt.group(1).strip() if body_pt else 'MISSING'

    print(f'{name}:')
    print(f'  HTML:   page-header div={has_ph_div}, hero-section={has_hero_sec}')
    print(f'  PH bg:  "{bg_val}"')
    print(f'  brand:  {has_brand}, slogan: {has_slogan}')
    print(f'  body pad-top: {pt}')
    print()
