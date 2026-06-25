"""
update_about3.py — 2026-04-07
1. Fix Therasik name: sik = seek (not Kinetics)
2. Team cards: remove specialties, just clean university names
3. Nav: move  to standalone main-nav
         dropdown →  + 
"""
import os, re

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source'
DOCS = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\docs'

# ══════════════════════════════════════════════════════════════════
# 1.  Fix Therasik name in #about section (index pages only)
# ══════════════════════════════════════════════════════════════════
OLD_MEANING = (
    '"Therasik"  <strong>Thera</strong>（Therapeutic，） '
    '<strong>sik</strong>（Science · Intelligence · Kinetics，··）——\n'
    '         AI 。'
)
NEW_MEANING = (
    '"Therasik"  <strong>Thera</strong>（Therapeutic，） '
    '<strong>sik</strong>（Seek，）——\n'
    '         AI 。'
)

# ── Team cards: remove the two specialty lines in each card ──────
# Columbia
OLD_CU = '''\
            <div style="font-weight:700;font-size:14px;color:#0d4a43;margin-bottom:4px;"></div>
            <div style="font-size:12px;color:var(--text-muted);line-height:1.5;">Columbia University<br><br></div>'''
NEW_CU = '''\
            <div style="font-weight:700;font-size:14px;color:#0d4a43;margin-bottom:4px;"></div>
            <div style="font-size:12px;color:var(--text-muted);line-height:1.5;">Columbia University</div>'''

# CAS
OLD_CAS = '''\
            <div style="font-weight:700;font-size:14px;color:#0d4a43;margin-bottom:4px;"></div>
            <div style="font-size:12px;color:var(--text-muted);line-height:1.5;">Chinese Academy of Sciences<br><br></div>'''
NEW_CAS = '''\
            <div style="font-weight:700;font-size:14px;color:#0d4a43;margin-bottom:4px;"></div>
            <div style="font-size:12px;color:var(--text-muted);line-height:1.5;">Chinese Academy of Sciences</div>'''

# Tsinghua
OLD_THU = '''\
            <div style="font-weight:700;font-size:14px;color:#0d4a43;margin-bottom:4px;"></div>
            <div style="font-size:12px;color:var(--text-muted);line-height:1.5;">Tsinghua University<br><br></div>'''
NEW_THU = '''\
            <div style="font-weight:700;font-size:14px;color:#0d4a43;margin-bottom:4px;"></div>
            <div style="font-size:12px;color:var(--text-muted);line-height:1.5;">Tsinghua University</div>'''

# ══════════════════════════════════════════════════════════════════
# 2.  Nav:  → standalone;  →  + 
#     Current (6-space):
#       [▾: , ]
#       <a href="index.html#workflow"></a>
#       <a href="index.html#contact"></a>
#     New:
#       <a href="Therasik_OurTech.html"></a>
#       [▾: , ]
#       <a href="index.html#contact"></a>
# ══════════════════════════════════════════════════════════════════
OLD_NAV_6 = '''\
      <div class="nav-dropdown" tabindex="0">
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

NEW_NAV_6 = '''\
      <a href="Therasik_OurTech.html"></a>
      <div class="nav-dropdown" tabindex="0">
        <a href="index.html#about"></a>
        <div class="dropdown-menu">
          <a href="index.html#about">
            <span class="menu-title"></span>
            <span class="menu-desc"></span>
          </a>
          <a href="index.html#workflow">
            <span class="menu-title"></span>
            <span class="menu-desc"></span>
          </a>
        </div>
      </div>
      <a href="index.html#contact"></a>'''

# 4-space variant
OLD_NAV_4 = '''\
    <div class="nav-dropdown" tabindex="0">
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

NEW_NAV_4 = '''\
    <a href="Therasik_OurTech.html"></a>
    <div class="nav-dropdown" tabindex="0">
      <a href="index.html#about"></a>
      <div class="dropdown-menu">
        <a href="index.html#about">
          <span class="menu-title"></span>
          <span class="menu-desc"></span>
        </a>
        <a href="index.html#workflow">
          <span class="menu-title"></span>
          <span class="menu-desc"></span>
        </a>
      </div>
    </div>
    <a href="index.html#contact"></a>'''


def process_dir(root, label):
    changed = []
    for fname in sorted(os.listdir(root)):
        if not fname.endswith('.html'):
            continue
        path = os.path.join(root, fname)
        orig = open(path, encoding='utf-8').read
        c = orig

        # About section fixes (index pages only)
        if fname in ('therasik_index.html', 'index.html'):
            c = c.replace(OLD_MEANING, NEW_MEANING)
            c = c.replace(OLD_CU, NEW_CU)
            c = c.replace(OLD_CAS, NEW_CAS)
            c = c.replace(OLD_THU, NEW_THU)

        # Nav restructure (all pages)
        c = c.replace(OLD_NAV_6, NEW_NAV_6)
        c = c.replace(OLD_NAV_4, NEW_NAV_4)

        if c != orig:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(c)
            changed.append(fname)

    print(f'\n{label}: {len(changed)} files updated')
    for f in changed:
        print(f'  ✓ {f}')
    return changed

process_dir(ROOT, 'web-source')
process_dir(DOCS, 'docs')
