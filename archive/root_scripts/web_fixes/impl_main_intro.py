"""
impl_main_intro.py  ── 2026-04-07
Implement the plan: service-hero in RIGHT column (.main-intro),
not as a full-width banner above page-wrap.

Steps for each of the 5 service pages:
1. Remove <div class="service-hero"> HTML + its CSS
2. Add .main-intro CSS (edge-to-edge within right column via neg margins)
3. Restructure top of <main class="main">:
   wrap breadcrumb + h1 + description inside <div class="main-intro">
4. Fix heading hierarchy (restore h2→h1 where needed: ADC, Vaccine)
5. Update subtitle text to 2-sentence Chinese descriptions
"""
import re

# ══════════════════════════════════════════════════════════════════
# CANONICAL CSS
# ══════════════════════════════════════════════════════════════════
MAIN_INTRO_CSS = """
    /* ── main-intro: green hero within right column ── */
    .main-intro {
      margin: -60px -60px 40px;
      padding: 36px 60px 28px;
      background:
        repeating-linear-gradient(135deg, transparent, transparent 14px,
          rgba(13,148,136,0.055) 14px, rgba(13,148,136,0.055) 15px),
        linear-gradient(135deg, #e6faf7 0%, #d4f3ed 45%, #eaf7f3 100%);
      border-bottom: 4px solid #0d9488;
    }
    .main-intro .breadcrumb { margin-bottom: 20px; }
    .main-intro h1 {
      font-family: 'Cormorant Garamond', serif;
      font-size: 38px;
      font-weight: 700;
      color: #0d4a43;
      margin: 0 0 10px;
      letter-spacing: -0.02em;
      line-height: 1.15;
    }
    .main-intro > p {
      color: #2d6a61;
      font-size: 15px;
      line-height: 1.65;
      max-width: 640px;
      margin: 0;
    }
    @media (max-width: 900px) {
      .main-intro { margin: -32px -24px 32px; padding: 28px 24px 24px; }
      .main-intro h1 { font-size: 28px; }
    }"""


def remove_service_hero_html(content):
    """Remove the <div class="service-hero">...</div> block."""
    return re.sub(
        r'\n<div class="service-hero">.*?</div>\n',
        '\n',
        content,
        flags=re.DOTALL
    )


def remove_service_hero_css(content):
    """Remove the .service-hero CSS block (comment through last closing brace)."""
    return re.sub(
        r'\n    /\* ── service-hero: mirrors KB page-header ── \*/.*?'
        r'@media \(max-width: 768px\) \{\s*\.service-hero \{[^}]+\}\s*\.service-hero h1 \{[^}]+\}\s*\}',
        '',
        content,
        flags=re.DOTALL
    )


def add_main_intro_css(content):
    """Inject .main-intro CSS before </style>."""
    if '.main-intro' in content:
        return content  # already done
    return content.replace('  </style>', MAIN_INTRO_CSS + '\n  </style>', 1)


# ══════════════════════════════════════════════════════════════════
# PER-PAGE RESTRUCTURING
# ══════════════════════════════════════════════════════════════════

def restructure_antibody(content):
    """Antibody: breadcrumb → h1 → p.subtitle → mission-block"""
    old = (
        '<main class="main">\n'
        '      <div class="breadcrumb">\n'
        '        <a href="index.html"></a><span>/</span>'
        '<a href="index.html#services" class="active">AI </a>'
        '<span>/</span><span></span>\n'
        '      </div>\n\n'
        '      <h1></h1>\n'
        '      <p class="subtitle"> Biotech、 CRO '
        '——、、。</p>\n\n'
        '      <div class="mission-block">'
    )
    new = (
        '<main class="main">\n'
        '  <div class="main-intro">\n'
        '    <div class="breadcrumb">\n'
        '      <a href="index.html"></a><span>/</span>'
        '<a href="index.html#services" class="active">AI </a>'
        '<span>/</span><span></span>\n'
        '    </div>\n'
        '    <h1></h1>\n'
        '    <p> AI 、、，。'
        ' 1,142  ΔΔG ，、。</p>\n'
        '  </div>\n\n'
        '      <div class="mission-block">'
    )
    return content.replace(old, new, 1)


def restructure_adc(content):
    """ADC: breadcrumb(therasik_index refs) → h2#overview → p.subtitle → p(intro)"""
    old = (
        '      <div class="breadcrumb"><a href="therasik_index.html"></a>'
        ' <span>&gt;</span> <a href="therasik_index.html#services">AI </a>'
        ' <span>&gt;</span>  ADC </div>\n'
        '      \n'
        '      <h2 id="overview"> ADC </h2>\n'
        '      <p class="subtitle"> AI 。'
        '- CMC 。</p>\n'
        '      \n'
        '      <p>Therasik  ADC ，'
        '。， AI  ADC 。</p>'
    )
    new = (
        '  <div class="main-intro" id="overview">\n'
        '    <div class="breadcrumb">\n'
        '      <a href="index.html"></a><span>/</span>'
        '<a href="index.html#services" class="active">AI </a>'
        '<span>/</span><span> ADC </span>\n'
        '    </div>\n'
        '    <h1> ADC </h1>\n'
        '    <p> AI  ADC ，、- CMC 。'
        ' 100+  ADC ，-，。</p>\n'
        '  </div>\n\n'
        '      <p>Therasik  ADC ，'
        '。， AI  ADC 。</p>'
    )
    return content.replace(old, new, 1)


def restructure_cart(content):
    """CAR-T: breadcrumb(old text) → h1 → p.subtitle → mission-block"""
    old = (
        '      <div class="breadcrumb">\n'
        '        <a href="index.html"></a><span>/</span>'
        '<a href="index.html#services">← </a>'
        '<span>/</span><span> CAR-T</span>\n'
        '      </div>\n\n'
        '      <h1> CAR-T </h1>\n'
        '      <p class="subtitle">AI ：，。</p>\n\n'
        '      <div class="mission-block">'
    )
    new = (
        '  <div class="main-intro">\n'
        '    <div class="breadcrumb">\n'
        '      <a href="index.html"></a><span>/</span>'
        '<a href="index.html#services" class="active">AI </a>'
        '<span>/</span><span> CAR-T </span>\n'
        '    </div>\n'
        '    <h1> CAR-T </h1>\n'
        '    <p>ACTES  237  CAR ，、。'
        ' CAR-T、CAR-NK、CAR-M ，。</p>\n'
        '  </div>\n\n'
        '      <div class="mission-block">'
    )
    return content.replace(old, new, 1)


def restructure_bispecific(content):
    """: breadcrumb → mission-block (NO h1). Insert main-intro before mission-block."""
    old = (
        '      <div class="breadcrumb">\n'
        '        <a href="index.html"></a><span>/</span>'
        '<a href="index.html#services" class="active">AI </a>'
        '<span>/</span><span></span>\n'
        '      </div>\n'
        '      <!-- Hero / Mission -->\n'
        '      <div class="mission-block">'
    )
    new = (
        '  <div class="main-intro">\n'
        '    <div class="breadcrumb">\n'
        '      <a href="index.html"></a><span>/</span>'
        '<a href="index.html#services" class="active">AI </a>'
        '<span>/</span><span></span>\n'
        '    </div>\n'
        '    <h1></h1>\n'
        '    <p> Nano-Convert™  SmartLink™ ， CMC 。'
        ' 75+ ，，。</p>\n'
        '  </div>\n\n'
        '      <!-- Hero / Mission -->\n'
        '      <div class="mission-block">'
    )
    return content.replace(old, new, 1)


def restructure_vaccine(content):
    """: breadcrumb → mission-block → h2#platform → p.subtitle → trust-grid
    → Extract breadcrumb into main-intro, add h1, remove h2 and subtitle."""
    # Step 1: Replace breadcrumb + newline with main-intro opening
    old_bc = (
        '    <div class="breadcrumb">\n'
        '      <a href="index.html"></a><span>/</span>'
        '<a href="index.html#services" class="active">AI </a>'
        '<span>/</span><span></span>\n'
        '    </div>\n\n'
        '    <div class="mission-block">'
    )
    new_bc = (
        '  <div class="main-intro" id="platform">\n'
        '    <div class="breadcrumb">\n'
        '      <a href="index.html"></a><span>/</span>'
        '<a href="index.html#services" class="active">AI </a>'
        '<span>/</span><span></span>\n'
        '    </div>\n'
        '    <h1></h1>\n'
        '    <p>AI ，、、mRNA 。'
        ' IEDB  100 ，、。</p>\n'
        '  </div>\n\n'
        '    <div class="mission-block">'
    )
    content = content.replace(old_bc, new_bc, 1)

    # Step 2: Remove h2#platform and its subtitle (now redundant)
    old_h2 = (
        '\n    <h2 id="platform"></h2>\n'
        '    <p class="subtitle">、 mRNA 。</p>\n\n'
        '    <div class="trust-grid">'
    )
    new_h2 = '\n\n    <div class="trust-grid">'
    content = content.replace(old_h2, new_h2, 1)

    return content


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════

PAGES = [
    ("docs/Therasik_Antibody_Page.html",   restructure_antibody),
    ("docs/Therasik_ADC_Design_Page.html", restructure_adc),
    ("docs/Therasik_CART_Page.html",       restructure_cart),
    ("docs/Therasik_Bispecific_Page.html", restructure_bispecific),
    ("docs/Therasik_Vaccine_Design.html",  restructure_vaccine),
]

changed = []
for path, restructure_fn in PAGES:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read
    orig = content

    # 1. Remove service-hero HTML
    content = remove_service_hero_html(content)

    # 2. Remove service-hero CSS
    content = remove_service_hero_css(content)

    # 3. Add main-intro CSS
    content = add_main_intro_css(content)

    # 4. Restructure main top
    content = restructure_fn(content)

    # Verify
    has_mi = 'class="main-intro"' in content
    has_sh = 'class="service-hero"' in content
    h1_count = len(re.findall(r'<h1[^/]', content[content.find('<body'):]))

    if has_sh:
        print(f"  ✗ service-hero NOT removed in {path}")
    if not has_mi:
        print(f"  ✗ main-intro NOT added in {path}")

    if content != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        changed.append(path)
        print(f"✓ {path.replace('docs/','')}: hero={has_mi} sh_removed={not has_sh} h1={h1_count}")
    else:
        print(f"✗ NO CHANGE: {path}")

print(f"\n{len(changed)}/5 files updated.")
