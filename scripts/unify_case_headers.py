"""
 6 ：
1.  CSS + HTML 
2. 3  Hero / 
"""
import re, pathlib

WEB = pathlib.Path(r"d:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source")

# ───  CSS ──────────────────────────────────────────────────────────────
HEADER_CSS = """    /* ───  ─── */
    .top-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 32px; background: rgba(255,255,255,0.95); backdrop-filter: blur(12px); border-bottom: 2px solid rgba(13,148,136,0.1); position: fixed; width: 100%; top: 0; z-index: 2000; gap: 12px; flex-wrap: wrap; }
    .top-header .brand { font-family: 'Cormorant Garamond', Georgia, serif; font-weight: 700; font-size: 26px; letter-spacing: -0.03em; display: flex; align-items: center; flex-wrap: nowrap; min-width: max-content; white-space: nowrap; }
    .top-header .brand a { text-decoration: none; color: #111827; display: flex; align-items: center; gap: 10px; white-space: nowrap; flex-shrink: 0; }
    .top-header .brand .accent { color: var(--primary); font-style: italic; font-weight: 700; }
    .top-header .slogan { font-size: 14px; color: var(--text-muted); padding-left: 14px; border-left: 1px solid var(--border); margin-left: 14px; font-weight: 600; white-space: nowrap; display: inline-flex; align-items: center; flex-shrink: 0; }
    .mobile-menu-btn { display: none; background: none; border: 1px solid var(--border); border-radius: 8px; padding: 6px 8px; cursor: pointer; color: var(--text); line-height: 0; }
    .nav-close-btn { display: none; }
    .top-header-nav { display: flex; align-items: center; gap: 6px; flex: 1; justify-content: center; }
    .top-header-nav a { padding: 8px 16px; font-size: 15px; color: var(--text-muted); text-decoration: none; border-radius: 20px; transition: all 0.2s ease; font-weight: 600; }
    .top-header-nav a:hover { color: var(--primary); background: rgba(13,148,136,0.06); }
    .nav-dropdown { position: relative; }
    .nav-dropdown > a::after { content: ' ▾'; font-size: 10px; opacity: 0.6; margin-left: 4px; }
    .nav-dropdown .dropdown-menu { position: absolute; top: 100%; left: 50%; transform: translateX(-50%) translateY(10px); min-width: 220px; padding: 8px; background: #fff; border: 1px solid rgba(0,0,0,0.06); border-radius: 12px; box-shadow: 0 10px 40px -10px rgba(0,0,0,0.12); opacity: 0; visibility: hidden; transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1); z-index: 100; margin-top: 8px; }
    .nav-dropdown:hover .dropdown-menu, .nav-dropdown:focus-within .dropdown-menu { opacity: 1; visibility: visible; transform: translateX(-50%) translateY(0); }
    .nav-dropdown .dropdown-menu a { display: block; padding: 12px 16px; color: var(--text); text-decoration: none; line-height: 1.4; border-radius: 8px; text-align: left; }
    .nav-dropdown .dropdown-menu a:hover { background: #f8fafc; }
    .nav-dropdown .dropdown-menu a .menu-title { display: block; font-weight: 600; font-size: 14px; color: var(--text); margin-bottom: 2px; }
    .nav-dropdown .dropdown-menu a:hover .menu-title { color: var(--primary); }
    .nav-dropdown .dropdown-menu a .menu-desc { display: block; font-size: 12px; color: var(--text-muted); font-weight: 400; line-height: 1.4; }
    .header-right { display: flex; align-items: center; gap: 16px; }
    @media (max-width: 768px) {
      .mobile-menu-btn { display: block; }
      .top-header { padding: 10px 16px; flex-wrap: nowrap; }
      .top-header-nav { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: #fff; flex-direction: column; justify-content: center; align-items: center; gap: 4px; z-index: 9999; opacity: 0; pointer-events: none; transition: opacity 0.25s; padding: 24px; overflow-y: auto; }
      .top-header-nav.open { opacity: 1; pointer-events: auto; }
      .top-header-nav a { font-size: 18px; padding: 12px 24px; }
      .nav-close-btn { display: block; position: absolute; top: 16px; right: 20px; background: none; border: none; font-size: 32px; color: var(--text); cursor: pointer; line-height: 1; padding: 4px 8px; }
      .header-right { display: none; }
    }"""

# ───  HTML ─────────────────────────────────────────────────────────────
HEADER_HTML = """  <header class="top-header">
    <div class="brand">
      <a href="index.html">
        <span style="color:#111827">Thera</span> <span class="accent">sik</span>
      </a>
      <span class="slogan">AI </span>
    </div>
    <button class="mobile-menu-btn" aria-label="" onclick="document.querySelector('.top-header-nav').classList.add('open')">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
    </button>
    <nav class="top-header-nav">
      <button class="nav-close-btn" aria-label="" onclick="this.parentElement.classList.remove('open')">&times;</button>
      <a href="index.html"></a>
      <div class="nav-dropdown" tabindex="0">
        <a href="index.html#services">AI </a>
        <div class="dropdown-menu">
          <a href="Therasik_Antibody_Page.html"><span class="menu-title"></span><span class="menu-desc">、、</span></a>
          <a href="Therasik_ADC_Design_Page.html"><span class="menu-title"> ADC </span><span class="menu-desc">--</span></a>
          <a href="Therasik_CART_Page.html"><span class="menu-title"> CAR-T </span><span class="menu-desc"></span></a>
          <a href="Therasik_Bispecific_Page.html"><span class="menu-title"></span><span class="menu-desc"> · CMC  · </span></a>
          <a href="Therasik_Vaccine_Design.html"><span class="menu-title"></span><span class="menu-desc"> ·  · mRNA</span></a>
        </div>
      </div>
      <div class="nav-dropdown" tabindex="0">
        <a href="index.html#knowledge-base"></a>
        <div class="dropdown-menu">
          <a href="Therasik_Antibody_Guide.html"><span class="menu-title"></span><span class="menu-desc"></span></a>
          <a href="Therasik_ADA_Database.html"><span class="menu-title">ADA </span><span class="menu-desc">138 </span></a>
          <a href="Therasik_ADC_Database.html"><span class="menu-title">ADC </span><span class="menu-desc">100  ADC </span></a>
          <a href="Therasik_Component_Browser.html"><span class="menu-title">CAR </span><span class="menu-desc">237  CAR-T </span></a>
          <a href="Therasik_Vaccine_KB.html"><span class="menu-title"></span><span class="menu-desc"></span></a>
        </div>
      </div>
      <div class="nav-dropdown" tabindex="0">
        <a href="index.html#case-studies"></a>
        <div class="dropdown-menu">
          <a href="case_mumab4d5_humanization_zh.html"><span class="menu-title">muMAb4D5 </span><span class="menu-desc">CDR  + </span></a>
          <a href="case_mumab4d5_cmc_zh.html"><span class="menu-title">muMAb4D5 CMC </span><span class="menu-desc">15 ，</span></a>
          <a href="case_mumab4d5_vhh_zh.html"><span class="menu-title">VH → HER2 VHH </span><span class="menu-desc"></span></a>
          <a href="case_vgrw_sr_r2_affinity_maturation.html"><span class="menu-title">VHH </span><span class="menu-desc"> −3.32 kcal/mol</span></a>
          <a href="case_bispecific_vhh_expression_optimization.html"><span class="menu-title"> VHH </span><span class="menu-desc">pI  +  IC90  4.8 </span></a>
          <a href="case_malaria_carm_design.html"><span class="menu-title">CAR-M </span><span class="menu-desc">CIDRα1  CAR-</span></a>
        </div>
      </div>
      <a href="Therasik_OurTech.html"></a>
      <div class="nav-dropdown" tabindex="0">
        <a href="index.html#about"></a>
        <div class="dropdown-menu">
          <a href="index.html#about"><span class="menu-title"></span><span class="menu-desc"></span></a>
          <a href="index.html#workflow"><span class="menu-title"></span><span class="menu-desc"></span></a>
        </div>
      </div>
      <a href="index.html#contact"></a>
    </nav>
    <div class="header-right"></div>
  </header>"""

# ───  →  Hero  ──────────────────────────────────────────────────
# : (,  badge,  badge,  h1,  h1,  subtitle,  subtitle)
#  exact string replace，
HERO_ZH = {
    "case_vgrw_sr_r2_affinity_maturation.html": {
        "html_lang": ('lang="en"', 'lang="zh-CN"'),
        "title": (
            "Case Study: Virtual Affinity Maturation of VGRW-SR-R2 | Therasik",
            "：VGRW-SR-R2 VHH  | Therasik"
        ),
        "badge": (
            "Case Study · Virtual Affinity Maturation · ISB-VAM-2026-004",
            " ·  · ISB-VAM-2026-004"
        ),
        "h1": (
            "VGRW-SR-R2 <em>Anti-HER2 VHH</em><br>Virtual Affinity Maturation",
            "VGRW-SR-R2 <em> HER2 VHH</em><br>"
        ),
        "subtitle": (
            "Exhaustive interface scanning of humanized anti-HER2 nanobody VGRW-SR-R2 — 247 mutations evaluated across 5 independent dimensions, uncovering an epistatic double mutant that outperforms wild type while preserving full backbone integrity.",
            " HER2  VGRW-SR-R2 —— 5  247 ，，。"
        ),
        "stat_labels": [
            ("Mutations Screened", ""),
            ("Filter Dimensions", ""),
            ("Best ΔΔG (kcal/mol)", " ΔΔG (kcal/mol)"),
            ("Epistatic Synergy", ""),
            ("Multi-validated", ""),
            ("Better than WT", ""),
            ("Strong positive", ""),
        ],
    },
    "case_bispecific_vhh_expression_optimization.html": {
        "html_lang": ('lang="en"', 'lang="zh-CN"'),
        "title": (
            "Case Study: Bispecific VHH Expression Optimization | Therasik",
            "： VHH  | Therasik"
        ),
        "badge": (
            "Case Study &nbsp;·&nbsp; Bispecific VHH Engineering",
            " ·  VHH "
        ),
        "h1": (
            "Engineering a <em>High-Expression</em><br>Bispecific Coronavirus Nanobody",
            "<em></em><br>"
        ),
        "subtitle": (
            "Diagnosing pI-driven ER retention and rescuing yeast secretion via arm selection and charged-linker engineering.",
            " pI ，。"
        ),
        "stat_labels": [
            ("pI Reduction", "pI "),
            ("Net Charge Units", ""),
            ("Cross-CoV Activity ↑", " ↑"),
        ],
    },
    "case_malaria_carm_design.html": {
        "html_lang": ('lang="en"', 'lang="zh-CN"'),
        "title": (
            "Case Study: Anti-CIDRα1 Dual-Binder CAR-Macrophage for High-Parasitemia P. falciparum Malaria | Therasik",
            "： CIDRα1  CAR- | Therasik"
        ),
        "badge": (
            "Case Study &nbsp;·&nbsp; CAR-M Design",
            " · CAR-"
        ),
        "h1": (
            "Anti-CIDRα1 Dual-Binder<br><em>CAR-Macrophage</em> for High-Parasitemia<br><em>P. falciparum</em> Malaria",
            " CIDRα1 <br><em>CAR-</em><br><em></em>"
        ),
        "subtitle": (
            "A rationally designed CAR-M construct with every decision backed by the ACTES 11-layer decision cascade.",
            " ACTES 11  CAR-M 。"
        ),
        "stat_labels": [
            ("CIDRα1 Subclasses Covered", " CIDRα1 "),
            ("Macrophage-Native Signal", ""),
            ("Animal Model Strategy", ""),
            ("Design Layers", ""),
        ],
    },
}


def replace_header_css(html: str) -> str:
    """ </style>  CSS， .top-header / .nav-dropdown """
    #  CSS（/）
    # ： style  /* ─── HEADER */ 
    # ：， CSS （cascade ）
    #  CSS
    if "/* ───  ─── */" in html:
        return html
    #  </style> 
    return html.replace("</style>", HEADER_CSS + "\n  </style>", 1)


def replace_header_html(html: str) -> str:
    """ header HTML  <header class="top-header">...</header>"""
    pattern = re.compile(
        r'<header\s+class="top-header"[^>]*>.*?</header>',
        re.DOTALL
    )
    if pattern.search(html):
        return pattern.sub(HEADER_HTML, html)
    #  <header>  <nav class="top-header-nav">（ nav ）
    #  <body> 
    return html.replace("<body>", "<body>\n" + HEADER_HTML, 1)


def apply_hero_zh(fname: str, html: str) -> str:
    """ Hero """
    spec = HERO_ZH.get(fname)
    if not spec:
        return html
    for key, val in spec.items():
        if key == "stat_labels":
            for old_lbl, new_lbl in val:
                html = html.replace(old_lbl, new_lbl)
        else:
            old, new = val
            html = html.replace(old, new)
    return html


# ───  4  ──────────────────────────────────────────────────
targets = [
    "case_mumab4d5_vhh_zh.html",
    "case_vgrw_sr_r2_affinity_maturation.html",
    "case_bispecific_vhh_expression_optimization.html",
    "case_malaria_carm_design.html",
]

for fname in targets:
    p = WEB / fname
    html = p.read_text(encoding="utf-8")

    # 1.  HTML
    html = replace_header_html(html)

    # 2.  CSS
    html = replace_header_css(html)

    # 3.  →  Hero（）
    html = apply_hero_zh(fname, html)

    p.write_text(html, encoding="utf-8")
    print(f"✓ {fname}")

# ───  index.html： VH/VL  ─────────────────────────────
for homepage in ["index.html", "therasik_index.html"]:
    p = WEB / homepage
    html = p.read_text(encoding="utf-8")

    #  case_bispecific_vhvl_pairing  <a> （）
    html = re.sub(
        r'\s*<a href="case_bispecific_vhvl_pairing\.html"[^>]*>.*?</a>',
        '',
        html,
        flags=re.DOTALL
    )

    #  CMC （ case_mumab4d5_cmc.html  case_mumab4d5_cmc_zh.html）
    html = html.replace(
        'href="case_mumab4d5_cmc.html"',
        'href="case_mumab4d5_cmc_zh.html"'
    )

    p.write_text(html, encoding="utf-8")
    print(f"✓ {homepage}")

print("\n")
