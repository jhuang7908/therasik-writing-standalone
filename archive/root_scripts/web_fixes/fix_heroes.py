import os
import re

def fix_html(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Replace CSS
    css_old = r"""    \.hero \{ background:linear-gradient.*?\}
    \.hero-inner \{ max-width:.*?\}
    \.eyebrow \{.*?\}
    h1 \{ font-family:'Cormorant Garamond'.*?\}
    \.subtitle \{.*?\}
    \.hero-stats \{.*?\}
    \.hero-stat \{.*?\}
    \.hero-stat strong \{.*?\}
    \.hero-stat span \{.*?\}"""
    
    css_new = """    .case-hero { background: url('images/hero-bg.svg') center/cover no-repeat, linear-gradient(135deg, #0d4a44 0%, #0d7a70 55%, #0d9488 100%); padding: 72px 24px 60px; text-align: center; }
    .hero-inner { max-width: 1000px; margin: 0 auto; }
    .hero-badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2); color: #a7f3d0; font-size: 13px; font-weight: 600; padding: 6px 16px; border-radius: 20px; margin-bottom: 20px; }
    .case-hero h1 { font-family: 'Cormorant Garamond', serif; font-size: clamp(32px,5vw,52px); color: #fff; line-height: 1.15; margin-bottom: 14px; font-weight: 700; }
    .subtitle { font-size: 17px; color: #a7f3d0; max-width: 700px; margin: 0 auto 32px; line-height: 1.6; }
    .hero-stats { display: flex; justify-content: center; flex-wrap: nowrap; background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); border-radius: 16px; padding: 18px 8px; max-width: 940px; margin: 0 auto; overflow-x: auto; }
    .hero-stat { flex: 1; min-width: 0; padding: 6px 10px; border-right: 1px solid rgba(255,255,255,0.12); text-align: center; }
    .hero-stat:last-child { border-right: none; }
    .hero-stat .val { font-size: clamp(18px,2.2vw,26px); font-weight: 800; color: #fff; line-height: 1; margin-bottom: 3px; white-space: nowrap; }
    .hero-stat .lbl { font-size: 9.5px; color: #6ee7b7; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; line-height: 1.3; margin-bottom: 5px; }"""
    
    content = re.sub(css_old, css_new, content, flags=re.DOTALL)
    
    # 2. Replace HTML
    content = content.replace('<section class="hero">', '<section class="case-hero">')
    content = content.replace('<span class="eyebrow">', '<div class="hero-badge">')
    content = content.replace('</span>\n      <h1>', '</div>\n      <h1>')
    
    # Fix stats
    content = re.sub(r'<div class="hero-stat"><strong>(.*?)</strong><span>(.*?)</span></div>', r'<div class="hero-stat"><div class="val">\1</div><div class="lbl">\2</div></div>', content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

files = [
    'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/docs/case_pdl1_epitope_analysis.html',
    'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/docs/case_ab278_fentanyl_affinity_maturation.html',
    'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/docs/case_cdr_denovo_redesign.html'
]

for f in files:
    fix_html(f)
    print(f"Fixed {f}")
