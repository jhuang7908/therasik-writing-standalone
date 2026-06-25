import re

path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

badge_map = {
    'Glucuronide-MMAE':           ('Enzyme-Cleavable',    'badge-linker'),
    'Pyrophosphate-diester':      ('Enzyme-Cleavable',    'badge-linker'),
    'Legumain-cleavable':         ('Enzyme-Cleavable',    'badge-linker'),
    'beta-galactoside-cleavable': ('Enzyme-Cleavable',    'badge-linker'),
    'Sulfatase-cleavable':        ('Enzyme-Cleavable',    'badge-linker'),
    'Phosphatase-cleavable':      ('Enzyme-Cleavable',    'badge-linker'),
    'Hydrazone-disulfide':        ('pH-Sensitive',        'badge-approved'),
    'Thioether-cleavable':        ('Disulfide/Reducible', 'badge-payload'),
    'Mal-PEG4-NHS':               ('Non-Cleavable',       'badge-phase3'),
    'SMPEG24':                    ('Non-Cleavable',       'badge-phase3'),
    'Sulfo-SMCC':                 ('Non-Cleavable',       'badge-phase3'),
    'mc-val-cit-PABC':            ('Protease (CatB)',     'badge-linker'),
    'GGFG':                       ('Protease (CatB/L)',   'badge-linker'),
    'VA-PABC':                    ('Protease (CatB)',     'badge-linker'),
    'PEG4-vc-PABC':               ('Protease (CatB)',     'badge-linker'),
    'PEG8-vc-PABC':               ('Protease (CatB)',     'badge-linker'),
    'Mal-PEG2-V-Cit-PAB':        ('Protease (CatB)',     'badge-linker'),
    'Fmoc-vc-PABC':               ('Protease (CatB)',     'badge-linker'),
    'Dde-vc-PABC':                ('Protease (CatB)',     'badge-linker'),
    'Peptide-MMAF':               ('Protease (CatB)',     'badge-linker'),
    'Val-Cit-PAB-OH':             ('Protease (CatB)',     'badge-linker'),
    'mc-Val-Cit-PAB-PNP':         ('Protease (CatB)',     'badge-linker'),
}

fixed = 0
for linker_name, (badge_text, badge_class) in badge_map.items():
    old_title_pattern = '<div class="card-title">' + linker_name + '</div>'
    pos = content.find(old_title_pattern)
    if pos < 0:
        print('NOT FOUND: ' + linker_name)
        continue
    search_window = content[pos:pos+400]
    new_badge = '<span class="badge ' + badge_class + '">' + badge_text + '</span>'
    new_window = re.sub(
        r'<span class="badge [^"]+">Cleavable</span>',
        new_badge,
        search_window,
        count=1
    )
    content = content[:pos] + new_window + content[pos+400:]
    print('Fixed: ' + linker_name + ' -> ' + badge_text)
    fixed += 1

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Total fixed: ' + str(fixed))
