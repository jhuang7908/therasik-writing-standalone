"""
Revert ADA detail panel labels back to English (primary).
Keep all enriched fields and collapsible UI.
"""

TARGETS = [
    r'therasik-web-source\Therasik_ADA_Database.html',
    r'docs\Therasik_ADA_Database.html',
]

# mkSection title zh → en
TITLE_FIXES = [
    ("' ADA '",         "'Clinical ADA'"),
    ("''",         "'Clinical Context'"),
    ("'Fc '",                "'Fc Engineering'"),
    ("'MHC-II '",         "'MHC-II Epitope Profile'"),
    ("'（SASA）'",    "'Surface Immunogenicity (SASA)'"),
    ("'CMC '",           "'CMC / Developability'"),
    ("' ·  · '",     "'Germline / Sequence'"),
]

# detail-grid field labels zh → en
FIELD_FIXES = [
    # ADA section
    ("'ADA '",             "'ADA Incidence'"),
    ("''",               "'Evidence Tier'"),
    ("'ADA '",           "'ADA Display Value'"),
    ("''",               "'Source URL'"),
    ("''",           "'Evidence chain excerpt'"),
    # Clinical context
    ("''",                 "'Indication'"),
    ("''",               "'Disease Class'"),
    ("''",               "'Route'"),
    ("''",                 "'Half-life'"),
    ("''",                   "'Dose'"),
    ("''",               "'Frequency'"),
    ("''",               "'Approval Year'"),
    ("''",               "'Assay Platform'"),
    ("'MTX '",               "'MTX Co-med'"),
    ("''",               "'Immunosuppressant Context'"),
    ("''",               "'Clinical Flags'"),
    # Fc
    ("''",                 "'Fc Isotype'"),
    ("''",           "'Effector Status'"),
    ("'Fc  / '",     "'Fc Notes / Design'"),
    # MHC
    ("' <small></small>'",
     "'Net immunogenic clusters <small>(excl. tolerated)</small>'"),
    ("''",                 "'Total clusters'"),
    ("''",               "'High-binding'"),
    ("''",               "'Medium-binding'"),
    ("''",           "'Tolerated (silent)'"),
    ("'TCIA '",              "'TCIA Score'"),
    ("'TCIA '",          "'TCIA Risk Level'"),
    # SASA
    ("'（VH+VL ）'",
     "'Hydrophilic surface fraction (VH+VL avg)'"),
    ("' =  = ； =  = '",
     "'Higher = more hydrophilic surface = lower aggregation risk; lower = more hydrophobic patches = higher risk'"),
    ("'VH '",            "'VH hydrophilic fraction'"),
    ("'VL '",            "'VL hydrophilic fraction'"),
    ("''",             "'Surface patches (n)'"),
    ("''",               "'Surface risk'"),
    ("'（max9）'",       "'Hydrophobic patch (max9)'"),
    # CMC
    ("' pI'",              "'pI (isoelectric point)'"),
    ("'GRAVY'",        "'GRAVY (hydrophobicity)'"),
    ("''",           "'Instability index'"),
    ("'（pH 7）'",         "'Net charge @ pH 7'"),
    ("'ADA V2 '",            "'ADA V2 Score'"),
    ("'ADA V2 '",            "'ADA V2 Risk'"),
    ("''",             "'Deamidation sites'"),
    ("''",             "'Isomerization sites'"),
    ("''",           "'Aggregation motifs'"),
    ("'CMC '",           "'CMC flags'"),
    # Germline
    ("'VH '",                "'VH Germline'"),
    ("'VH '",              "'VH Identity'"),
    ("'VH '",                "'VH Family'"),
    ("'VL '",                "'VL Germline'"),
    ("'VL '",              "'VL Identity'"),
    ("'VL '",                "'VL Family'"),
    ("'VH-VL '",             "'VH-VL Angle'"),
    ("''",           "'Interface pairs'"),
    ("''",                   "'Format'"),
    # Misc
    ("''",         "'Concomitant immunosuppressant'"),
    ("'Checkpoint '",      "'Checkpoint inhibitor'"),
    ("''",           "'Immune-depleting regimen'"),
    ("''",             "'Oncology indication'"),
    # units
    ("d.half_life+' '",        "d.half_life+' days'"),
    ("d.vh_vl_angle.toFixed(1)+'°'",  "d.vh_vl_angle.toFixed(1)+'°'"),  # already ok
    # button text
    ("' ▾'",             "'Expand ▾'"),
    ("' ▴'",                 "'Collapse ▴'"),
    # panel header stat-label text
    ("''",         "'Net immunogenic clusters'"),
]

for target in TARGETS:
    txt = open(target, encoding='utf-8').read
    n = 0
    for zh, en in TITLE_FIXES + FIELD_FIXES:
        if zh in txt:
            txt = txt.replace(zh, en)
            n += 1
    # Also fix inline text in divs (not in quotes)
    inline = [
        (" <small></small>",
         "Net immunogenic clusters <small>(excl. tolerated)</small>"),
        (" =  = ； =  = ",
         "Higher = more hydrophilic surface = lower aggregation risk; lower = more hydrophobic patches"),
        ("PMIDs", "PMIDs"),  # already ok
    ]
    for zh, en in inline:
        if zh in txt:
            txt = txt.replace(zh, en)
            n += 1
    with open(target, 'w', encoding='utf-8') as f:
        f.write(txt)
    print(f"Updated {n} labels → {target}")

print("Done.")
