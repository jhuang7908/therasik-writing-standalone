"""
add_service_hero.py  ── 2026-04-07
Add a light-green patterned .service-hero section to all 5 AI service pages.
Exactly mirrors the KB pages' .page-header style (gradient + diagonal stripe + accent bar).
Also demotes the first body <h1> to <h2> (page title is now in service-hero).
"""

# ── Canonical CSS block (identical to KB .page-header) ────────────────────────
SERVICE_HERO_CSS = """
    /* ── service-hero: mirrors KB page-header ── */
    .service-hero {
      background:
        repeating-linear-gradient(135deg, transparent, transparent 14px,
          rgba(13,148,136,0.055) 14px, rgba(13,148,136,0.055) 15px),
        linear-gradient(135deg, #e6faf7 0%, #d4f3ed 45%, #eaf7f3 100%);
      border-top: 4px solid #0d9488;
      border-bottom: 1px solid rgba(13,148,136,0.18);
      padding: 36px 40px 28px;
    }
    .service-hero h1 {
      font-family: 'Cormorant Garamond', serif;
      font-size: 38px;
      font-weight: 700;
      margin: 0 0 10px;
      letter-spacing: -0.02em;
      color: #0d4a43;
    }
    .service-hero p {
      color: #2d6a61;
      font-size: 15px;
      max-width: 720px;
      line-height: 1.65;
      margin: 0;
    }
    .service-hero .back-link {
      font-size: 13px; color: #0f766e; text-decoration: none;
      font-weight: 600; display: inline-flex; align-items: center;
      gap: 5px; margin-bottom: 14px; opacity: 0.85;
    }
    .service-hero .back-link:hover { opacity: 1; color: #0d9488; }
    @media (max-width: 768px) {
      .service-hero { padding: 24px 20px 20px; }
      .service-hero h1 { font-size: 26px; }
    }"""

BACK_LINK_SVG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>'

def service_hero_html(title, description):
    return f"""
<div class="service-hero">
  <a href="index.html#services" class="back-link">
    {BACK_LINK_SVG}
    AI 
  </a>
  <h1>{title}</h1>
  <p>{description}</p>
</div>
"""

# ── Per-page configuration ────────────────────────────────────────────────────
PAGES = [
    {
        "path": "docs/Therasik_Antibody_Page.html",
        "title": "",
        "desc": " AI 、、， IND 。 1,142  ΔΔG ，、。",
        # First h1 in body has no id attr: <h1>
        "h1_old": "<h1>",
        "h1_new": "<h2>",
        "h1_close_old": "</h1>",
        "h1_close_new": "</h2>",
    },
    {
        "path": "docs/Therasik_ADC_Design_Page.html",
        "title": " ADC ",
        "desc": " AI （ADC），、、- CMC 。 100+  ADC ，-，。",
        # First h1: <h1 id="overview">
        "h1_old": '<h1 id="overview">',
        "h1_new": '<h2 id="overview">',
        "h1_close_old": "</h1>",
        "h1_close_new": "</h2>",
    },
    {
        "path": "docs/Therasik_CART_Page.html",
        "title": " CAR-T ",
        "desc": "ACTES  CAR-T ， 237  CAR ，、、。 CAR-T、CAR-NK、CAR-M ，。",
        "h1_old": "<h1>",
        "h1_new": "<h2>",
        "h1_close_old": "</h1>",
        "h1_close_new": "</h2>",
    },
    {
        "path": "docs/Therasik_Bispecific_Page.html",
        "title": "",
        "desc": " Nano-Convert™  SmartLink™ ，、CMC 。 75+ ，，。",
        "h1_old": "<h1>",
        "h1_new": "<h2>",
        "h1_close_old": "</h1>",
        "h1_close_new": "</h2>",
    },
    {
        "path": "docs/Therasik_Vaccine_Design.html",
        "title": "",
        "desc": "AI ，、、mRNA 。 IEDB  100 ，、 in silico 。",
        "h1_old": '<h1 id="platform">',
        "h1_new": '<h2 id="platform">',
        "h1_close_old": "</h1>",
        "h1_close_new": "</h2>",
    },
]

import re

changed = []
for cfg in PAGES:
    path = cfg["path"]
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read
    orig = content

    # ── 1. Skip if service-hero already added ─────────────────────────────────
    if 'class="service-hero"' in content:
        print(f"– Already has service-hero: {path}")
        continue

    # ── 2. Inject CSS before </style> (first occurrence) ─────────────────────
    content = content.replace('  </style>', SERVICE_HERO_CSS + '\n  </style>', 1)

    # ── 3. Inject HTML after </header> using regex ───────────────────────────
    hero_html = service_hero_html(cfg["title"], cfg["desc"])
    # Match </header> followed by any whitespace, then <div class="page-wrap">
    content = re.sub(
        r'(</header>)\s*(<div class="page-wrap">)',
        r'\1\n' + hero_html + r'\n\2',
        content,
        count=1
    )

    # ── 4. Demote first body h1 → h2 (only the FIRST occurrence) ─────────────
    # Find body start, then replace only the first h1 after it
    body_idx = content.find('<body')
    if body_idx >= 0:
        before_body = content[:body_idx]
        after_body = content[body_idx:]
        # Replace first matching h1 open tag
        after_body = after_body.replace(cfg["h1_old"], cfg["h1_new"], 1)
        # Replace next matching h1 close tag (after the open tag)
        # Find position of the h2 we just created, then find the first </h1> after it
        h2_pos = after_body.find(cfg["h1_new"])
        if h2_pos >= 0:
            after_h2 = after_body[h2_pos:]
            after_h2 = after_h2.replace(cfg["h1_close_old"], cfg["h1_close_new"], 1)
            after_body = after_body[:h2_pos] + after_h2
        content = before_body + after_body

    if content != orig and 'class="service-hero"' in content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        changed.append(path)
        print(f"✓ Updated: {path}")
    else:
        print(f"✗ FAILED (check injection point): {path}")
        # Debug: show context
        idx = content.find('</header>')
        print(f"  </header> at char {idx}, followed by: {content[idx:idx+60]!r}")

print(f"\n{len(changed)}/5 files updated.")
