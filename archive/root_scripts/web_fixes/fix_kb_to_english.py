"""
Standardize all KB pages to English-first UI labels.
Applies to: ADA, ADC, Component Browser, Vaccine, Antibody Guide
"""
import os

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite'

# ── per-file replacements ────────────────────────────────────────────────────
FIXES = {
    # ADA Database - remaining Chinese labels
    'Therasik_ADA_Database.html': [
        # filter option labels
        ('', 'All Origins'),
        ('', 'All Diseases'),
        ('s', 'All Routes'),
        ('', 'All Routes'),
        # TH header
        ('><', '>Antibody Evaluator<'),
        # .dk evidence label still in Chinese
        ('', 'Evidence Excerpt'),
        # Any remaining Chinese labels from panel
        ('ADA ', 'ADA Incidence'),
        ('', 'Evidence Tier'),
        ('ADA ', 'ADA Display Value'),
        ('', 'Source URL'),
        ('', 'Indication'),
        ('', 'Disease Class'),
        ('', 'Route'),
        ('', 'Half-life'),
        ('', 'Dose'),
        ('', 'Frequency'),
        ('', 'Approval Year'),
        ('', 'Assay Platform'),
        ('MTX ', 'MTX Co-med'),
        ('', 'Immunosuppressant Context'),
        ('', 'Clinical Flags'),
        ('', 'Fc Isotype'),
        ('', 'Effector Status'),
        ('Fc  / ', 'Fc Notes / Design'),
        ('', 'Net immunogenic clusters'),
        ('', 'Total clusters'),
        ('', 'High-binding'),
        ('', 'Medium-binding'),
        ('', 'Tolerated (silent)'),
        ('TCIA ', 'TCIA Score'),
        ('TCIA ', 'TCIA Risk Level'),
        ('（VH+VL ）', 'Hydrophilic surface fraction (VH+VL avg)'),
        (' =  = ； =  = ',
         'Higher = more hydrophilic surface = lower aggregation risk; lower = more hydrophobic patches = higher risk'),
        ('VH ', 'VH hydrophilic fraction'),
        ('VL ', 'VL hydrophilic fraction'),
        ('', 'Surface patches (n)'),
        ('', 'Surface risk'),
        ('（max9）', 'Hydrophobic patch (max9)'),
        (' pI', 'pI (isoelectric point)'),
        ('GRAVY', 'GRAVY (hydrophobicity)'),
        ('', 'Instability index'),
        ('（pH 7）', 'Net charge @ pH 7'),
        ('ADA V2 ', 'ADA V2 Score'),
        ('ADA V2 ', 'ADA V2 Risk'),
        ('', 'Deamidation sites'),
        ('', 'Isomerization sites'),
        ('', 'Aggregation motifs'),
        ('CMC ', 'CMC flags'),
        ('VH ', 'VH Germline'),
        ('VH ', 'VH Identity'),
        ('VH ', 'VH Family'),
        ('VL ', 'VL Germline'),
        ('VL ', 'VL Identity'),
        ('VL ', 'VL Family'),
        ('VH-VL ', 'VH-VL Angle'),
        ('', 'Interface pairs'),
        ('', 'Format'),
        ("d.half_life+' '", "d.half_life+' days'"),
        ('', 'Concomitant immunosuppressant'),
        ('Checkpoint ', 'Checkpoint inhibitor'),
        ('', 'Immune-depleting regimen'),
        ('', 'Oncology indication'),
        (' ▾', 'Expand ▾'),
        (' ▴', 'Collapse ▴'),
        (' <small></small>',
         'Net immunogenic clusters <small>(excl. tolerated)</small>'),
    ],
    # ADC Database - filter options
    'Therasik_ADC_Database.html': [
        ('><', '>Approved<'),
        ('> 3 <', '>Phase 3<'),
        ('> 2 <', '>Phase 2<'),
        ('> 1 <', '>Phase 1<'),
        ('><', '>Discontinued<'),
        ('><', '>Solid Tumor<'),
        # also check for option value= variants
        ('value=""', 'value="approved"'),
        ('value=" 3 "', 'value="phase3"'),
        ('value=" 2 "', 'value="phase2"'),
        ('value=" 1 "', 'value="phase1"'),
        ('value=""', 'value="discontinued"'),
    ],
    # CAR Component Browser
    'Therasik_Component_Browser.html': [
        ('><', '>All Categories<'),
        ('><', '>All Tiers<'),
        ('T1 — ', 'T1 — Approved'),
        ('T2 — ', 'T2 — Clinical Trial'),
        ('T3 — ', 'T3 — Preclinical'),
        ('><', '>All Cell Types<'),
        ('value=""', 'value=""'),
        ('value=""', 'value=""'),
        ('value=""', 'value=""'),
    ],
    # Antibody Guide
    'Therasik_Antibody_Guide.html': [
        ('><', '>All Categories<'),
        ('><', '>All Evidence Levels<'),
        ('T1 — ', 'T1 — Approved'),
        ('T2 — ', 'T2 — Clinical Trial'),
        ('T3 —  / ', 'T3 — Preclinical'),
        ('value=""', 'value=""'),
        ('value=""', 'value=""'),
    ],
}

SOURCE_DIRS = [
    os.path.join(ROOT, 'therasik-web-source'),
    os.path.join(ROOT, 'docs'),
]

for fname, fixes in FIXES.items:
    for sdir in SOURCE_DIRS:
        fpath = os.path.join(sdir, fname)
        if not os.path.exists(fpath):
            continue
        txt = open(fpath, encoding='utf-8').read
        n = 0
        for old, new in fixes:
            if old in txt:
                txt = txt.replace(old, new)
                n += 1
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(txt)
        print(f"  [{n} fixes] {fpath.replace(ROOT,'')}")

print("\nAll done.")
