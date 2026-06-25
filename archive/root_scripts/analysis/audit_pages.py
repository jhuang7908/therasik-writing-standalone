import re

pages = {
    'index': 'docs/therasik_index.html',
    'ADA': 'docs/Therasik_ADA_Database.html',
    'ADC': 'docs/Therasik_ADC_Database.html',
    'AntibodyGuide': 'docs/Therasik_Antibody_Guide.html',
    'ComponentBrowser': 'docs/Therasik_Component_Browser.html',
    'VaccineKB': 'docs/Therasik_Vaccine_KB.html',
    'CART': 'docs/Therasik_CART_Page.html',
    'ADCDesign': 'docs/Therasik_ADC_Design_Page.html',
}

for name, path in pages.items():
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    # Extract :root primary
    root = re.search(r'--primary:\s*([^;]+);', c)
    primary = root.group(1).strip() if root else '?'

    # Extract body padding-top (outside media query)
    body_before_media = c[:c.find('@media')] if '@media' in c else c
    body_pt = re.search(r'body\s*\{[^}]*padding-top:\s*([^;]+);', body_before_media)
    pt = body_pt.group(1).strip() if body_pt else 'MISSING'

    # Check top-header position
    th_fixed = 'position: fixed' in c or 'position:fixed' in c
    th_sticky = 'position: sticky' in c or 'position:sticky' in c
    th_pos = 'fixed' if th_fixed else ('sticky' if th_sticky else 'other')

    # Check hero type in HTML body
    hero_banner = '<div class="hero-banner">' in c
    page_header = '<div class="page-header">' in c
    hero_section = '<section class="hero">' in c

    # Check hero background CSS
    hero_css = re.search(r'\.hero \{([^}]+)\}', c)
    ph_css = re.search(r'\.page-header\{([^}]+)\}', c)
    if hero_css:
        bg_m = re.search(r'background:\s*([^;]+);', hero_css.group(1))
        hero_bg = bg_m.group(1).strip()[:70] if bg_m else 'none/default'
    else:
        hero_bg = 'N/A'
    if ph_css:
        bg_m2 = re.search(r'background:\s*([^;]+);', ph_css.group(1))
        ph_bg = bg_m2.group(1).strip()[:70] if bg_m2 else 'none/default'
    else:
        ph_bg = 'N/A'

    # Check brand font-size
    brand_m = re.search(r'\.top-header \.brand\s*\{([^}]+)\}', c)
    if not brand_m:
        brand_m = re.search(r'\.brand\s*\{([^}]+)\}', c)
    bfs_m = re.search(r'font-size:\s*([^;]+);', brand_m.group(1)) if brand_m else None
    bfs = bfs_m.group(1).strip() if bfs_m else '?'

    # Check slogan style
    slogan_m = re.search(r'\.slogan\s*\{([^}]+)\}', c)
    if not slogan_m:
        slogan_m = re.search(r'\.top-header \.slogan\s*\{([^}]+)\}', c)
    slogan_display = ''
    if slogan_m:
        disp_m = re.search(r'display:\s*([^;]+);', slogan_m.group(1))
        slogan_display = disp_m.group(1).strip() if disp_m else '?'

    print(f'--- {name} ---')
    print(f'  --primary:    {primary}')
    print(f'  body pad-top: {pt}')
    print(f'  header:       {th_pos}')
    print(f'  HTML hero:    hero-section={hero_section}, hero-banner={hero_banner}, page-header={page_header}')
    print(f'  .hero bg:     {hero_bg}')
    print(f'  .page-header: {ph_bg}')
    print(f'  brand fs:     {bfs}')
    print(f'  slogan disp:  {slogan_display}')
    print()
