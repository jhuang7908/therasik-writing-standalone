"""
update_nav_about.py — 2026-04-07
1. Replace the 4 bare nav links ( /  /  / ) with:
   -  dropdown (7 cases)
   -  dropdown (, , )
   - standalone   ( moved inside )
2. Expand the #about section in therasik_index.html
"""
import re, os

# ══════════════════════════════════════════════════════════════════
# NEW NAV BLOCK (for pages where main indent is 6 spaces = standard)
# ══════════════════════════════════════════════════════════════════
NEW_NAV_6 = '''\n      <div class="nav-dropdown" tabindex="0">
        <a href="index.html#case-studies"></a>
        <div class="dropdown-menu">
          <a href="case_mumab4d5_humanization_zh.html">
            <span class="menu-title">muMAb4D5 </span>
            <span class="menu-desc">CDR  + </span>
          </a>
          <a href="case_mumab4d5_cmc_zh.html">
            <span class="menu-title">muMAb4D5 CMC </span>
            <span class="menu-desc">15 ，</span>
          </a>
          <a href="case_mumab4d5_vhh_zh.html">
            <span class="menu-title">VH → HER2 VHH </span>
            <span class="menu-desc"></span>
          </a>
          <a href="case_vgrw_sr_r2_affinity_maturation.html">
            <span class="menu-title">VHH </span>
            <span class="menu-desc"> −3.32 kcal/mol</span>
          </a>
          <a href="case_bispecific_vhh_expression_optimization.html">
            <span class="menu-title"> VHH </span>
            <span class="menu-desc">pI  +  IC90  4.8 </span>
          </a>
          <a href="case_bispecific_vhvl_pairing.html">
            <span class="menu-title"> VH/VL </span>
            <span class="menu-desc">-</span>
          </a>
          <a href="case_malaria_carm_design.html">
            <span class="menu-title">CAR-M </span>
            <span class="menu-desc">CIDRα1  CAR-</span>
          </a>
        </div>
      </div>
      <div class="nav-dropdown" tabindex="0">
        <a href="index.html#about"></a>
        <div class="dropdown-menu">
          <a href="Therasik_OurTech.html">
            <span class="menu-title"></span>
            <span class="menu-desc">AbEngineCore </span>
          </a>
          <a href="index.html#about">
            <span class="menu-title"></span>
            <span class="menu-desc"> AI </span>
          </a>
          <a href="index.html#workflow">
            <span class="menu-title"></span>
            <span class="menu-desc"></span>
          </a>
        </div>
      </div>
      <a href="index.html#contact"></a>'''

# Variant for Component Browser (4-space indent)
NEW_NAV_4 = '''\n    <div class="nav-dropdown" tabindex="0">
      <a href="index.html#case-studies"></a>
      <div class="dropdown-menu">
        <a href="case_mumab4d5_humanization_zh.html">
          <span class="menu-title">muMAb4D5 </span>
          <span class="menu-desc">CDR  + </span>
        </a>
        <a href="case_mumab4d5_cmc_zh.html">
          <span class="menu-title">muMAb4D5 CMC </span>
          <span class="menu-desc">15 ，</span>
        </a>
        <a href="case_mumab4d5_vhh_zh.html">
          <span class="menu-title">VH → HER2 VHH </span>
          <span class="menu-desc"></span>
        </a>
        <a href="case_vgrw_sr_r2_affinity_maturation.html">
          <span class="menu-title">VHH </span>
          <span class="menu-desc"> −3.32 kcal/mol</span>
        </a>
        <a href="case_bispecific_vhh_expression_optimization.html">
          <span class="menu-title"> VHH </span>
          <span class="menu-desc">pI  +  IC90  4.8 </span>
        </a>
        <a href="case_bispecific_vhvl_pairing.html">
          <span class="menu-title"> VH/VL </span>
          <span class="menu-desc">-</span>
        </a>
        <a href="case_malaria_carm_design.html">
          <span class="menu-title">CAR-M </span>
          <span class="menu-desc">CIDRα1  CAR-</span>
        </a>
      </div>
    </div>
    <div class="nav-dropdown" tabindex="0">
      <a href="index.html#about"></a>
      <div class="dropdown-menu">
        <a href="Therasik_OurTech.html">
          <span class="menu-title"></span>
          <span class="menu-desc">AbEngineCore </span>
        </a>
        <a href="index.html#about">
          <span class="menu-title"></span>
          <span class="menu-desc"> AI </span>
        </a>
        <a href="index.html#workflow">
          <span class="menu-title"></span>
          <span class="menu-desc"></span>
        </a>
      </div>
    </div>
    <a href="index.html#contact"></a>'''

# Index page variant (Therasik_OurTech in same dir)
# same as 6-space but no change needed for links

PATTERN_6 = re.compile(
    r'\n      <a href="[^"]*#case-studies"></a>'
    r'\n      <a href="[^"]*#about"></a>'
    r'\n      <a href="[^"]*#workflow"></a>'
    r'\n      <a href="[^"]*#contact"></a>'
)

PATTERN_4 = re.compile(
    r'\n    <a href="[^"]*#case-studies"></a>'
    r'\n    <a href="[^"]*#about"></a>'
    r'\n    <a href="[^"]*#workflow"></a>'
    r'\n    <a href="[^"]*#contact"></a>'
)

# ══════════════════════════════════════════════════════════════════
# EXPANDED #about SECTION (for therasik_index.html)
# ══════════════════════════════════════════════════════════════════
OLD_ABOUT = '''  <section id="about" class="section">
    <div class="section-inner">
      <span class="section-label lang-zh"></span>
      <h2 style="margin-bottom:16px"> AI </h2>
      <p>Therasik  AI 。，<strong></strong>。 <strong>1,142 </strong>、<strong>138  (ADA) </strong> <strong>100+  ADC </strong>。。</p>
      <div class="highlight">
        <p><strong>：</strong> AlphaFold2、ABodyBuilder2  HADDOCK3； ProteinMPNN  RFdiffusion。，。</p>
      </div>
    </div>
  </section>'''

NEW_ABOUT = '''  <section id="about" class="section">
    <div class="section-inner">
      <span class="section-label lang-zh"></span>
      <h2 style="margin-bottom:16px"> AI </h2>
      <p style="font-size:17px;line-height:1.75;color:var(--text);max-width:760px;margin-bottom:24px;">Therasik  AI ， Biotech、 CRO 。，<strong></strong>，<strong></strong>——、。</p>

      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin:24px 0 32px;">
        <div style="background:linear-gradient(135deg,#e6faf7,#d4f3ed);border-radius:12px;padding:20px 18px;border-left:3px solid #0d9488;">
          <div style="font-size:28px;font-weight:700;color:#0d4a43;font-family:'Cormorant Garamond',serif;">1,142</div>
          <div style="font-size:13px;color:#2d6a61;margin-top:4px;font-weight:500;"></div>
          <div style="font-size:12px;color:#4b5563;margin-top:6px;line-height:1.5;"> VH/VL、VHH ，</div>
        </div>
        <div style="background:linear-gradient(135deg,#e6faf7,#d4f3ed);border-radius:12px;padding:20px 18px;border-left:3px solid #0d9488;">
          <div style="font-size:28px;font-weight:700;color:#0d4a43;font-family:'Cormorant Garamond',serif;">138</div>
          <div style="font-size:13px;color:#2d6a61;margin-top:4px;font-weight:500;"> ADA </div>
          <div style="font-size:12px;color:#4b5563;margin-top:6px;line-height:1.5;"> PMID / FDA ，</div>
        </div>
        <div style="background:linear-gradient(135deg,#e6faf7,#d4f3ed);border-radius:12px;padding:20px 18px;border-left:3px solid #0d9488;">
          <div style="font-size:28px;font-weight:700;color:#0d4a43;font-family:'Cormorant Garamond',serif;">100+</div>
          <div style="font-size:13px;color:#2d6a61;margin-top:4px;font-weight:500;"> ADC </div>
          <div style="font-size:12px;color:#4b5563;margin-top:6px;line-height:1.5;">、、， ADC </div>
        </div>
      </div>

      <h3 style="font-size:18px;color:var(--text);margin:0 0 12px;"> CRO / AI </h3>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:28px;">
        <div style="display:flex;gap:12px;align-items:flex-start;">
          <span style="width:20px;height:20px;border-radius:50%;background:#0d9488;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:2px;">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
          </span>
          <div>
            <strong style="font-size:14px;display:block;margin-bottom:2px;">，</strong>
            <span style="font-size:13px;color:var(--text-muted);"> FDA/EMA ，。</span>
          </div>
        </div>
        <div style="display:flex;gap:12px;align-items:flex-start;">
          <span style="width:20px;height:20px;border-radius:50%;background:#0d9488;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:2px;">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
          </span>
          <div>
            <strong style="font-size:14px;display:block;margin-bottom:2px;">，</strong>
            <span style="font-size:13px;color:var(--text-muted);">，，。</span>
          </div>
        </div>
        <div style="display:flex;gap:12px;align-items:flex-start;">
          <span style="width:20px;height:20px;border-radius:50%;background:#0d9488;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:2px;">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
          </span>
          <div>
            <strong style="font-size:14px;display:block;margin-bottom:2px;"> AI </strong>
            <span style="font-size:13px;color:var(--text-muted);"> AlphaFold2、HADDOCK3、ProteinMPNN  8+ ，，。</span>
          </div>
        </div>
        <div style="display:flex;gap:12px;align-items:flex-start;">
          <span style="width:20px;height:20px;border-radius:50%;background:#0d9488;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:2px;">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
          </span>
          <div>
            <strong style="font-size:14px;display:block;margin-bottom:2px;">、</strong>
            <span style="font-size:13px;color:var(--text-muted);"> NDA 。。</span>
          </div>
        </div>
      </div>

      <div class="highlight" style="display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap;">
        <div style="flex:1;min-width:280px;">
          <p style="margin:0 0 6px;"><strong>：</strong> AlphaFold2、ABodyBuilder2  HADDOCK3； ProteinMPNN  RFdiffusion； ThermoMPNN； IEDB / 27  HLA-DR ；EvoEF2 + PRODIGY  ΔΔG 。</p>
        </div>
        <a href="Therasik_OurTech.html" style="display:inline-flex;align-items:center;gap:6px;padding:10px 18px;background:#0d9488;color:#fff;border-radius:8px;font-size:14px;font-weight:600;text-decoration:none;flex-shrink:0;align-self:center;">
           →
        </a>
      </div>
    </div>
  </section>'''


# ══════════════════════════════════════════════════════════════════
# PROCESS FILES
# ══════════════════════════════════════════════════════════════════

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source'
changed = []
skipped = []

for fname in sorted(os.listdir(ROOT)):
    if not fname.endswith('.html'):
        continue
    path = os.path.join(ROOT, fname)
    orig = open(path, encoding='utf-8').read
    c = orig

    # Nav replacement
    if PATTERN_4.search(c):
        c = PATTERN_4.sub(NEW_NAV_4, c)
    elif PATTERN_6.search(c):
        c = PATTERN_6.sub(NEW_NAV_6, c)
    else:
        skipped.append(fname)

    # About section expansion (only on therasik_index.html)
    if fname == 'therasik_index.html' and OLD_ABOUT in c:
        c = c.replace(OLD_ABOUT, NEW_ABOUT, 1)

    if c != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(c)
        changed.append(fname)
        has_dropdown = 'case_mumab4d5_humanization' in c
        print(f"✓ {fname} (dropdown={'yes' if has_dropdown else 'NO'})")
    else:
        pass  # unchanged / not matched

print(f"\n{len(changed)} files updated.")
if skipped:
    print(f"No match (skipped): {', '.join(skipped)}")
