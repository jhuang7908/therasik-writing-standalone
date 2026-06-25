"""
update_about_nav2.py — 2026-04-07
1. Rename bispecific dropdown item:  → 
2. Restructure  dropdown: remove , keep  + 
3. Add  back as standalone main-nav item before 
4. Expand #about section with team background, mission, Therasik meaning
"""
import re, os

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source'
DOCS = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\docs'

# ══════════════════════════════════════════════════════════════════
# 1. Rename bispecific in dropdown (both indent levels)
# ══════════════════════════════════════════════════════════════════
OLD_BI_6 = '''            <span class="menu-title"></span>
            <span class="menu-desc"></span>'''
NEW_BI_6 = '''            <span class="menu-title"></span>
            <span class="menu-desc"> · CMC  · </span>'''

OLD_BI_4 = '''          <span class="menu-title"></span>
          <span class="menu-desc"></span>'''
NEW_BI_4 = '''          <span class="menu-title"></span>
          <span class="menu-desc"> · CMC  · </span>'''

# ══════════════════════════════════════════════════════════════════
# 2+3. Fix  dropdown + restore  to main nav
#      Pattern covers both indent levels (6-space standard)
# ══════════════════════════════════════════════════════════════════
# OLD:  dropdown with 3 items (, , ) + 
OLD_ABOUT_DROPDOWN_6 = '''      <div class="nav-dropdown" tabindex="0">
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

NEW_ABOUT_DROPDOWN_6 = '''      <div class="nav-dropdown" tabindex="0">
        <a href="index.html#about"></a>
        <div class="dropdown-menu">
          <a href="index.html#about">
            <span class="menu-title"></span>
            <span class="menu-desc"></span>
          </a>
          <a href="Therasik_OurTech.html">
            <span class="menu-title"></span>
            <span class="menu-desc">AbEngineCore </span>
          </a>
        </div>
      </div>
      <a href="index.html#workflow"></a>
      <a href="index.html#contact"></a>'''

# 4-space variant (Component Browser)
OLD_ABOUT_DROPDOWN_4 = '''    <div class="nav-dropdown" tabindex="0">
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

NEW_ABOUT_DROPDOWN_4 = '''    <div class="nav-dropdown" tabindex="0">
      <a href="index.html#about"></a>
      <div class="dropdown-menu">
        <a href="index.html#about">
          <span class="menu-title"></span>
          <span class="menu-desc"></span>
        </a>
        <a href="Therasik_OurTech.html">
          <span class="menu-title"></span>
          <span class="menu-desc">AbEngineCore </span>
        </a>
      </div>
    </div>
    <a href="index.html#workflow"></a>
    <a href="index.html#contact"></a>'''

# ══════════════════════════════════════════════════════════════════
# 4. Expanded #about section for therasik_index.html
# ══════════════════════════════════════════════════════════════════
OLD_ABOUT_SECTION_START = '  <section id="about" class="section">'
OLD_ABOUT_SECTION_END   = '  </section>'

CHECKMARK_SVG = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>'

NEW_ABOUT_SECTION = '''  <section id="about" class="section">
    <div class="section-inner">
      <span class="section-label lang-zh"></span>
      <h2 style="margin-bottom:8px">Therasik — AI </h2>
      <p style="font-size:15px;color:var(--text-muted);margin:0 0 28px;max-width:680px;line-height:1.6;">
        "Therasik"  <strong>Thera</strong>（Therapeutic，） <strong>sik</strong>（Science · Intelligence · Kinetics，··）——
         AI 。
      </p>

      <!--  -->
      <div style="background:linear-gradient(135deg,#e6faf7 0%,#f0fdf9 100%);border:1px solid rgba(13,148,136,0.15);border-radius:14px;padding:24px 28px;margin-bottom:28px;">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#0d9488;margin-bottom:14px;"></div>
        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;">
          <div style="text-align:center;padding:16px 12px;background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
            <div style="font-size:22px;margin-bottom:6px;">🎓</div>
            <div style="font-weight:700;font-size:14px;color:#0d4a43;margin-bottom:4px;"></div>
            <div style="font-size:12px;color:var(--text-muted);line-height:1.5;">Columbia University<br><br></div>
          </div>
          <div style="text-align:center;padding:16px 12px;background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
            <div style="font-size:22px;margin-bottom:6px;">🔬</div>
            <div style="font-weight:700;font-size:14px;color:#0d4a43;margin-bottom:4px;"></div>
            <div style="font-size:12px;color:var(--text-muted);line-height:1.5;">Chinese Academy of Sciences<br><br></div>
          </div>
          <div style="text-align:center;padding:16px 12px;background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
            <div style="font-size:22px;margin-bottom:6px;">💡</div>
            <div style="font-weight:700;font-size:14px;color:#0d4a43;margin-bottom:4px;"></div>
            <div style="font-size:12px;color:var(--text-muted);line-height:1.5;">Tsinghua University<br><br></div>
          </div>
        </div>
      </div>

      <!--  -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:28px;">
        <div style="border-left:3px solid #0d9488;padding-left:18px;">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#0d9488;margin-bottom:8px;"></div>
          <p style="margin:0;font-size:14px;line-height:1.7;color:var(--text);"> AI ，、。</p>
        </div>
        <div style="border-left:3px solid #0d9488;padding-left:18px;">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#0d9488;margin-bottom:8px;"></div>
          <p style="margin:0;font-size:14px;line-height:1.7;color:var(--text);"> Biotech  CRO —— IND-enabling ，。</p>
        </div>
      </div>

      <!--  -->
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:28px;">
        <div style="background:linear-gradient(135deg,#e6faf7,#d4f3ed);border-radius:12px;padding:20px 18px;border-left:3px solid #0d9488;">
          <div style="font-size:28px;font-weight:700;color:#0d4a43;font-family:\'Cormorant Garamond\',serif;">1,142</div>
          <div style="font-size:13px;color:#2d6a61;margin-top:4px;font-weight:600;"></div>
          <div style="font-size:12px;color:#4b5563;margin-top:6px;line-height:1.5;"> VH/VL、VHH ，</div>
        </div>
        <div style="background:linear-gradient(135deg,#e6faf7,#d4f3ed);border-radius:12px;padding:20px 18px;border-left:3px solid #0d9488;">
          <div style="font-size:28px;font-weight:700;color:#0d4a43;font-family:\'Cormorant Garamond\',serif;">138</div>
          <div style="font-size:13px;color:#2d6a61;margin-top:4px;font-weight:600;"> ADA </div>
          <div style="font-size:12px;color:#4b5563;margin-top:6px;line-height:1.5;"> PMID / FDA ，</div>
        </div>
        <div style="background:linear-gradient(135deg,#e6faf7,#d4f3ed);border-radius:12px;padding:20px 18px;border-left:3px solid #0d9488;">
          <div style="font-size:28px;font-weight:700;color:#0d4a43;font-family:\'Cormorant Garamond\',serif;">100+</div>
          <div style="font-size:13px;color:#2d6a61;margin-top:4px;font-weight:600;"> ADC </div>
          <div style="font-size:12px;color:#4b5563;margin-top:6px;line-height:1.5;">、、， ADC </div>
        </div>
      </div>

      <!--  -->
      <h3 style="font-size:16px;color:var(--text);margin:0 0 14px;font-weight:600;"> AI  CRO </h3>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:28px;">
        <div style="display:flex;gap:12px;align-items:flex-start;">
          <span style="width:20px;height:20px;border-radius:50%;background:#0d9488;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:2px;">''' + CHECKMARK_SVG + '''</span>
          <div>
            <strong style="font-size:14px;display:block;margin-bottom:2px;">，</strong>
            <span style="font-size:13px;color:var(--text-muted);"> FDA/EMA ，。</span>
          </div>
        </div>
        <div style="display:flex;gap:12px;align-items:flex-start;">
          <span style="width:20px;height:20px;border-radius:50%;background:#0d9488;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:2px;">''' + CHECKMARK_SVG + '''</span>
          <div>
            <strong style="font-size:14px;display:block;margin-bottom:2px;">，</strong>
            <span style="font-size:13px;color:var(--text-muted);">，3–5 。</span>
          </div>
        </div>
        <div style="display:flex;gap:12px;align-items:flex-start;">
          <span style="width:20px;height:20px;border-radius:50%;background:#0d9488;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:2px;">''' + CHECKMARK_SVG + '''</span>
          <div>
            <strong style="font-size:14px;display:block;margin-bottom:2px;"> AI </strong>
            <span style="font-size:13px;color:var(--text-muted);">AlphaFold2、HADDOCK3、ProteinMPNN  8+ ，。</span>
          </div>
        </div>
        <div style="display:flex;gap:12px;align-items:flex-start;">
          <span style="width:20px;height:20px;border-radius:50%;background:#0d9488;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:2px;">''' + CHECKMARK_SVG + '''</span>
          <div>
            <strong style="font-size:14px;display:block;margin-bottom:2px;">，NDA </strong>
            <span style="font-size:13px;color:var(--text-muted);"> NDA ，。</span>
          </div>
        </div>
      </div>

      <div class="highlight" style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;">
        <p style="margin:0;flex:1;min-width:260px;font-size:14px;line-height:1.7;">
          <strong>：</strong>AlphaFold2 · ABodyBuilder2 · HADDOCK3 · ProteinMPNN · RFdiffusion · ThermoMPNN · IEDB · EvoEF2 · PRODIGY —  ΔΔG ，。
        </p>
        <a href="Therasik_OurTech.html" style="display:inline-flex;align-items:center;gap:6px;padding:10px 18px;background:#0d9488;color:#fff;border-radius:8px;font-size:14px;font-weight:600;text-decoration:none;flex-shrink:0;white-space:nowrap;">
           →
        </a>
      </div>
    </div>
  </section>'''


def replace_about_section(content):
    """Replace the entire #about section."""
    # Find start
    start = content.find('  <section id="about" class="section">')
    if start < 0:
        return content
    # Find its closing </section>
    end = content.find('  </section>', start)
    if end < 0:
        return content
    end += len('  </section>')
    return content[:start] + NEW_ABOUT_SECTION + content[end:]


# ══════════════════════════════════════════════════════════════════
# PROCESS
# ══════════════════════════════════════════════════════════════════
def process_dir(root):
    changed = []
    for fname in sorted(os.listdir(root)):
        if not fname.endswith('.html'):
            continue
        path = os.path.join(root, fname)
        orig = open(path, encoding='utf-8').read
        c = orig

        # 1. Rename bispecific
        c = c.replace(OLD_BI_6, NEW_BI_6)
        c = c.replace(OLD_BI_4, NEW_BI_4)

        # 2+3. Fix  dropdown + restore 
        c = c.replace(OLD_ABOUT_DROPDOWN_6, NEW_ABOUT_DROPDOWN_6)
        c = c.replace(OLD_ABOUT_DROPDOWN_4, NEW_ABOUT_DROPDOWN_4)

        # 4. Expand about section (index only)
        if fname in ('therasik_index.html', 'index.html'):
            c = replace_about_section(c)

        if c != orig:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(c)
            changed.append(fname)

    return changed

changed_web = process_dir(ROOT)
changed_docs = process_dir(DOCS)

print(f"web-source: {len(changed_web)} files")
for f in changed_web: print(f'  ✓ {f}')
print(f"\ndocs: {len(changed_docs)} files")
for f in changed_docs: print(f'  ✓ {f}')
