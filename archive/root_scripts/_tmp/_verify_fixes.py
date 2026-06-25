"""Verify specific fixes were applied correctly."""
import re
path = r'D:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/Therasik_ADC_Database.html'
content = open(path, encoding='utf-8').read

checks = [
    # (description, search_string, should_exist)
    ("Conjugation title fixed", "Conjugation Technologies</h2>", True),
    ("Old typo gone", "nologies</h2>", False),
    ("No double-escaped &amp;gt;", "&amp;gt;", False),
    ("MMAE subtitle added", "Seagen / Pfizer · Adcetris, Padcev, Polivy", True),
    ("DXd subtitle added", "Daiichi Sankyo · Enhertu (T-DXd)", True),
    ("DM1 subtitle added", "ImmunoGen · Kadcyla (T-DM1)", True),
    ("MMAE cc-brief fixed (no ellipsis)", "IC50: 0.1–1 nM ·  · : ", True),
    ("DXd cc-brief fixed", "IC50: 0.3 nM · Top I ", True),
    ("mc-vc-PABC cc-brief fixed", "t½: &gt;7 d  · : Cathepsin B", True),
    ("sec-hdr class added to CSS", "class=\"sec-hdr\"", True),
    (".sec-hdr CSS defined", ".sec-hdr {", True),
    ("Inline sec-hdr replaced", 'text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top', False),
    (" in Binding Affinity", "Binding Affinity", True),
    ("badge for Experiments Binding Assay", "badge-target\">Binding Assay<", True),
    ("badge for Experiments In Vivo", "badge-approved\">In Vivo<", True),
    ("badge for Experiments PK/Stability", "PK/Stability", True),
    ("Conj filter no duplicates - very_high gone", 'value="very_high"', False),
    ("Conj filter has new clean options", "All DAR Homogeneity", True),
    ("MMAE collapse-bar fixed", 'collapse-progress"></div></div>', True),
    (" in Conjugation section", "：", True),
    (" high in Conj", "：", True),
    ("Auristatin E cc-brief", "IC50: 0.5–5 nM · ", True),
    ("Thorium cc-brief fixed", "α  · : 40–80 μm", True),
    ("Alpha-amanitin cc-brief fixed", "RNA Pol II ", True),
    ("TLR7 cc-brief fixed", "TLR7  · ", True),
]

passed = 0
failed = 0
for desc, search, should_exist in checks:
    found = search in content
    ok = found == should_exist
    status = "✓" if ok else "✗"
    if not ok:
        failed += 1
        print(f"  {status} FAIL: {desc}")
        if should_exist:
            print(f"        NOT FOUND: '{search[:60]}'")
        else:
            # Find where it exists
            idx = content.find(search)
            print(f"        STILL EXISTS at byte {idx}: '...{content[idx:idx+80]}...'")
    else:
        passed += 1
        print(f"  {status} OK:   {desc}")

print(f"\n{'='*50}")
print(f"TOTAL: {passed} passed, {failed} failed")

# Count remaining ellipsis in cc-brief divs
ellipsis_count = len(re.findall(r'<div class="cc-brief">[^<]*…[^<]*</div>', content))
print(f"\nRemaining cc-brief with ellipsis: {ellipsis_count}")

# Count  instances
evidence_count = content.count('：')
print(f"Total  instances: {evidence_count}")

# Count developer subtitles (card-subtitle divs)
subtitle_count = len(re.findall(r'<div class="card-subtitle"', content))
print(f"Total card-subtitle divs: {subtitle_count}")
