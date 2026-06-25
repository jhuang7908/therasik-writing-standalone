"""
Fix script:
1. Add Immunogenicity to Services dropdown on all pages that are missing it
2. Fix compare-grid mobile stacking in case_bispecific_vhvl_pairing.html
3. Add overflow-x scroll wrapper for SVG charts on mobile
"""
import os, re

BASE = "D:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source"

IMMUNO_LINK = """          <a href="immunogenicity_study.html">
            <span class="menu-title">Immunogenicity</span>
            <span class="menu-desc">ADA Prediction &amp; Reference DB</span>
          </a>"""

# The pattern to find the end of the Services dropdown (right after Bispecific)
# All affected pages end the dropdown the same way
OLD_BISPECIFIC_END = """          <a href="InSynBio_Bispecific_Antibody_Design_Page.html">
            <span class="menu-title">Bispecific</span>
            <span class="menu-desc">Multispecific Engineering</span>
          </a>
        </div>"""

NEW_BISPECIFIC_END = """          <a href="InSynBio_Bispecific_Antibody_Design_Page.html">
            <span class="menu-title">Bispecific</span>
            <span class="menu-desc">Multispecific Engineering</span>
          </a>
          <a href="immunogenicity_study.html">
            <span class="menu-title">Immunogenicity</span>
            <span class="menu-desc">ADA Prediction &amp; Reference DB</span>
          </a>
        </div>"""

PAGES_NEED_IMMUNO = [
    "InSynBio_Antibody_Developability_Assessment_Page.html",
    "case_mumab4d5_humanization_en.html",
    "case_bispecific_vhh_expression_optimization.html",
    "case_vgrw_sr_r2_affinity_maturation.html",
    "case_mumab4d5_vhh_en.html",
    "case_mumab4d5_cmc.html",
    "case_malaria_carm_design.html",
]

# ── 1. Add Immunogenicity to Services dropdown ────────────────────────────
for page in PAGES_NEED_IMMUNO:
    path = os.path.join(BASE, page)
    if not os.path.exists(path):
        print(f"SKIP (not found): {page}")
        continue
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if "immunogenicity_study.html" in content and "menu-title" in content:
        print(f"ALREADY has immuno: {page}")
        continue
    if OLD_BISPECIFIC_END in content:
        content = content.replace(OLD_BISPECIFIC_END, NEW_BISPECIFIC_END, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"FIXED immuno nav: {page}")
    else:
        print(f"PATTERN NOT FOUND: {page}")

print()

# ── 2. Mobile fixes for case_bispecific_vhvl_pairing.html ─────────────────
VPSA_PAGE = os.path.join(BASE, "case_bispecific_vhvl_pairing.html")
with open(VPSA_PAGE, encoding="utf-8") as f:
    vpsa = f.read()

# Add mobile CSS after existing @media block
OLD_MOBILE_CSS = """    @media (max-width: 768px) {
      .case-hero h1 { font-size: 32px; }
      .compare-grid { grid-template-columns: 1fr; }
      .top-header-nav { display: none; }
    }"""

NEW_MOBILE_CSS = """    @media (max-width: 768px) {
      .case-hero h1 { font-size: 32px; }
      .compare-grid { grid-template-columns: 1fr; }
      .top-header-nav { display: none; }
      .qa-grid { grid-template-columns: 1fr; }
      .flow { flex-direction: column; align-items: stretch; }
      .flow-arrow { transform: rotate(90deg); text-align: center; }
      .hero-stats { flex-direction: column; gap: 8px; }
      .hero-stat { border-right: none; border-bottom: 1px solid rgba(255,255,255,0.12); padding: 10px 14px; }
      .hero-stat:last-child { border-bottom: none; }
      h2.section-title { font-size: 26px; }
    }
    @media (max-width: 520px) {
      .case-hero h1 { font-size: 26px; }
      .case-hero .subtitle { font-size: 14px; }
      section.section { padding: 32px 0; }
    }"""

if OLD_MOBILE_CSS in vpsa:
    vpsa = vpsa.replace(OLD_MOBILE_CSS, NEW_MOBILE_CSS)
    print("FIXED: VPSA page mobile CSS")
else:
    print("VPSA mobile CSS pattern not found - skipping")

# Fix SVG charts: wrap them in scrollable container
# Find SVG chart divs and add min-width+overflow wrapper
# Pattern: style="background:#f9fafb;...border-radius:14px;..."  containing <svg
SVG_STYLE_OLD = 'style="width:100%;max-width:620px;display:block;font-family:Inter,sans-serif;"'
SVG_STYLE_NEW = 'style="width:100%;min-width:460px;display:block;font-family:Inter,sans-serif;"'
if SVG_STYLE_OLD in vpsa:
    vpsa = vpsa.replace(SVG_STYLE_OLD, SVG_STYLE_NEW)
    print("FIXED: VPSA SVG min-width")

# Add overflow-x auto to SVG chart containers in VPSA page
OLD_SVG_DIV = '    <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:14px;padding:24px 28px;margin:24px 0;">'
NEW_SVG_DIV = '    <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:14px;padding:24px 28px;margin:24px 0;overflow-x:auto;-webkit-overflow-scrolling:touch;">'
if OLD_SVG_DIV in vpsa:
    vpsa = vpsa.replace(OLD_SVG_DIV, NEW_SVG_DIV)
    print("FIXED: VPSA SVG container overflow-x")

with open(VPSA_PAGE, "w", encoding="utf-8") as f:
    f.write(vpsa)
print()

# ── 3. Fix SVG chart containers on service pages ──────────────────────────
SERVICE_PAGES = [
    "InSynBio_Antibody_Developability_Assessment_Page.html",
    "InSynBio_Bispecific_Antibody_Design_Page.html",
    "InSynBio_CART_Design_Page.html",
    "immunogenicity_study.html",
]

# Pattern: SVG with viewBox inside a chart wrapper without overflow-x
SVG_CHART_OLD = 'style="width:100%;max-width:'
SVG_SCROLL_WRAPPER_START = '<div style="overflow-x:auto;-webkit-overflow-scrolling:touch;">'
SVG_SCROLL_WRAPPER_END = '</div>'

for page in SERVICE_PAGES:
    path = os.path.join(BASE, page)
    if not os.path.exists(path):
        continue
    with open(path, encoding="utf-8") as f:
        content = f.read()

    # Add min-width to SVG elements that don't have it yet
    # Replace max-width only SVG sizing with min-width added
    count = 0
    # Make SVG chart divs scrollable: find <svg viewBox with style width:100%
    new_content = re.sub(
        r'(<svg\s+viewBox="[^"]+"\s+xmlns="[^"]+"\s+style=")(width:100%;max-width:(\d+)px;)',
        lambda m: m.group(1) + f'width:100%;min-width:{min(int(m.group(3)), 480)}px;max-width:{m.group(3)}px;',
        content
    )
    if new_content != content:
        count = content.count('width:100%;max-width:') - new_content.count('width:100%;max-width:')
        count = new_content.count('min-width:')
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"FIXED SVG min-width in {page}")
    else:
        print(f"No SVG changes in {page}")

print()
print("All fixes complete.")
