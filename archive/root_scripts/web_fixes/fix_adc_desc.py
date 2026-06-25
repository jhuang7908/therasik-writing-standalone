"""Fix ADC description across all website pages:  → , add stage breakdown."""
import os

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source'
DOCS = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite\docs'

REPLACEMENTS = [
    # stat strip on homepage
    ('100+</div>\n        <div class="trust-label" style="font-size:13px; color:var(--text-muted); margin-top:4px; font-weight:600;"> ADC </div>',
     '100</div>\n        <div class="trust-label" style="font-size:13px; color:var(--text-muted); margin-top:4px; font-weight:600;"> ADC </div>'),
    # About section stat card
    ('<div style="font-size:28px;font-weight:700;color:#0d4a43;font-family:\'Cormorant Garamond\',serif;">100+</div>\n          <div style="font-size:13px;color:#2d6a61;margin-top:4px;font-weight:600;"> ADC </div>\n          <div style="font-size:12px;color:#4b5563;margin-top:6px;line-height:1.5;">、、， ADC </div>',
     '<div style="font-size:28px;font-weight:700;color:#0d4a43;font-family:\'Cormorant Garamond\',serif;">100</div>\n          <div style="font-size:13px;color:#2d6a61;margin-top:4px;font-weight:600;"> ADC </div>\n          <div style="font-size:12px;color:#4b5563;margin-top:6px;line-height:1.5;">12  + 88 ，、、</div>'),
    # Nav dropdown desc
    ('100+  ADC ，-，。',
     '100  ADC （12  + 88 ），-，。'),
    # Service section cards on homepage
    (' 100+ -- 8 。',
     ' 100  ADC -- 8 。'),
    # About section on homepage h2 section
    ('100+  ADC </strong>',
     '100  ADC </strong>'),
    # homepage about body text
    ('100+  ADC ',
     '100  ADC '),
    # ADC design page main-intro
    (' 100+  ADC ',
     ' 100  ADC （12  + 88 ）'),
    # Knowledge base section labels
    ('100+  ADC ，、。',
     '100  ADC （ + ），、。'),
    # Any remaining 100+
    ('100+  ADC', '100  ADC'),
    ('100+ Clinical ADC', '100 Clinical ADC'),
]

def process_dir(path):
    changed = []
    for fname in os.listdir(path):
        if not fname.endswith('.html'): continue
        fp = os.path.join(path, fname)
        orig = open(fp, encoding='utf-8').read
        c = orig
        for old, new in REPLACEMENTS:
            c = c.replace(old, new)
        if c != orig:
            open(fp, 'w', encoding='utf-8').write(c)
            changed.append(fname)
    return changed

w = process_dir(ROOT)
d = process_dir(DOCS)
print(f"web-source: {len(w)} files: {w}")
print(f"docs: {len(d)} files: {d}")
