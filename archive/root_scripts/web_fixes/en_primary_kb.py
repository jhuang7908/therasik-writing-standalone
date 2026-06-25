"""
Convert all knowledge base pages to English-primary.
- Revert ADA detail panel labels back to English
- Fix Antibody Guide Fc×ADA tab to English
- Convert Chinese UI labels in ADC, CAR, Vaccine, Guide pages
"""
import re, os

ROOT = r'D:\InSynBio-AI-Research\Antibody_Engineer_Suite'

def fix(path, pairs):
    if not os.path.exists(path):
        print(f"SKIP (not found): {path}"); return
    txt = open(path, encoding='utf-8').read
    n_replaced = 0
    for old, new in pairs:
        if old in txt:
            txt = txt.replace(old, new)
            n_replaced += 1
        else:
            print(f"  NOT FOUND: {old[:60]!r}")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(txt)
    print(f"  {path.split(chr(92))[-1]}: {n_replaced}/{len(pairs)} replacements")

# ── ADA Database: revert Chinese labels back to English ──────────────────────
ADA_FIXES = [
    # Section headers
    ("mkSection(' ADA ',",  "mkSection('Clinical ADA Data',"),
    ("mkSection('',",  "mkSection('Clinical Context & Dosing',"),
    ("mkSection('Fc ',",         "mkSection('Fc Engineering',"),
    ("mkSection('MHC-II ',",  "mkSection('MHC-II Epitope Profile',"),
    ("mkSection('（SASA）',", "mkSection('Surface Immunogenicity (SASA)',"),
    ("mkSection('CMC ',",    "mkSection('CMC / Developability',"),
    ("mkSection(' ·  · ',", "mkSection('Germline / Sequence / Structure',"),
    # Field labels inside ADA section
    ("<div class=\"dk\">ADA </div>",     "<div class=\"dk\">ADA Incidence</div>"),
    ("<div class=\"dk\"></div>",        "<div class=\"dk\">Evidence Tier</div>"),
    ("<div class=\"dk\">ADA </div>",    "<div class=\"dk\">ADA Value (verbatim)</div>"),
    ("<div class=\"dk\">PMIDs</div>",            "<div class=\"dk\">PMIDs</div>"),
    ("<div class=\"dk\"></div>",         "<div class=\"dk\">Source URL</div>"),
    # Clinical context
    ("<div class=\"dk\"></div>",           "<div class=\"dk\">Indication</div>"),
    ("<div class=\"dk\"></div>",         "<div class=\"dk\">Disease Class</div>"),
    ("<div class=\"dk\"></div>",         "<div class=\"dk\">Route</div>"),
    ("<div class=\"dk\"></div>",           "<div class=\"dk\">Half-life</div>"),
    ("<div class=\"dk\"></div>",             "<div class=\"dk\">Dose</div>"),
    ("<div class=\"dk\"></div>",         "<div class=\"dk\">Dosing Frequency</div>"),
    ("<div class=\"dk\"></div>",         "<div class=\"dk\">Approval Year</div>"),
    ("<div class=\"dk\"></div>",         "<div class=\"dk\">Assay Platform</div>"),
    ("<div class=\"dk\">MTX </div>",         "<div class=\"dk\">MTX Co-medication</div>"),
    ("<div class=\"dk\"></div>",         "<div class=\"dk\">Immunosuppressant Context</div>"),
    ("<div class=\"dk\"></div>",         "<div class=\"dk\">Clinical Flags</div>"),
    # Fc section
    ("<div class=\"dk\"></div>",           "<div class=\"dk\">Isotype</div>"),
    ("<div class=\"dk\"></div>",     "<div class=\"dk\">Effector Function</div>"),
    ("<div class=\"dk\">Fc  / </div>", "<div class=\"dk\">Fc Notes / Design Context</div>"),
    # MHC
    (" <small></small>", "Net immunogenic clusters <small>(excl. tolerated)</small>"),
    ("<div class=\"dk\"></div>",           "<div class=\"dk\">Total clusters</div>"),
    ("<div class=\"dk\"></div>",         "<div class=\"dk\">High-binding</div>"),
    ("<div class=\"dk\"></div>",         "<div class=\"dk\">Medium-binding</div>"),
    ("<div class=\"dk\"></div>",     "<div class=\"dk\">Tolerated (silent)</div>"),
    ("<div class=\"dk\">TCIA </div>",        "<div class=\"dk\">TCIA Score</div>"),
    ("<div class=\"dk\">TCIA </div>",    "<div class=\"dk\">TCIA Risk Level</div>"),
    # Surface
    ("（VH+VL ）", "Hydrophilic surface fraction (VH+VL avg)"),
    (" =  = ； =  = ",
     "Higher = more hydrophilic surface = lower aggregation risk; lower = more hydrophobic patches = higher risk"),
    ("<div class=\"dk\">VH </div>",     "<div class=\"dk\">VH hydrophilic fraction</div>"),
    ("<div class=\"dk\">VL </div>",     "<div class=\"dk\">VL hydrophilic fraction</div>"),
    ("<div class=\"dk\"></div>",       "<div class=\"dk\">Surface patches (n)</div>"),
    ("<div class=\"dk\"></div>",         "<div class=\"dk\">Surface risk</div>"),
    ("<div class=\"dk\">（max9）</div>", "<div class=\"dk\">Hydrophobic patch (max9)</div>"),
    # CMC
    ("<div class=\"dk\"> pI</div>",        "<div class=\"dk\">pI (isoelectric point)</div>"),
    ("<div class=\"dk\">GRAVY</div>",  "<div class=\"dk\">GRAVY (hydrophobicity)</div>"),
    ("<div class=\"dk\"></div>",     "<div class=\"dk\">Instability index</div>"),
    ("<div class=\"dk\">（pH 7）</div>",   "<div class=\"dk\">Net charge @ pH 7</div>"),
    ("<div class=\"dk\">ADA V2 </div>",      "<div class=\"dk\">ADA V2 Score</div>"),
    ("<div class=\"dk\">ADA V2 </div>",      "<div class=\"dk\">ADA V2 Risk</div>"),
    ("<div class=\"dk\"></div>",       "<div class=\"dk\">Deamidation sites</div>"),
    ("<div class=\"dk\"></div>",       "<div class=\"dk\">Isomerization sites</div>"),
    ("<div class=\"dk\"></div>",     "<div class=\"dk\">Aggregation motifs</div>"),
    ("<div class=\"dk\">CMC </div>",     "<div class=\"dk\">CMC risk flags</div>"),
    # Germline
    ("<div class=\"dk\">VH </div>",          "<div class=\"dk\">VH Germline</div>"),
    ("<div class=\"dk\">VH </div>",        "<div class=\"dk\">VH Identity</div>"),
    ("<div class=\"dk\">VH </div>",          "<div class=\"dk\">VH Family</div>"),
    ("<div class=\"dk\">VL </div>",          "<div class=\"dk\">VL Germline</div>"),
    ("<div class=\"dk\">VL </div>",        "<div class=\"dk\">VL Identity</div>"),
    ("<div class=\"dk\">VL </div>",          "<div class=\"dk\">VL Family</div>"),
    ("<div class=\"dk\">VH-VL </div>",       "<div class=\"dk\">VH-VL angle</div>"),
    ("<div class=\"dk\"></div>",     "<div class=\"dk\">Interface contact pairs</div>"),
    ("<div class=\"dk\"></div>",             "<div class=\"dk\">Format</div>"),
    # Evidence
    ("<div class=\"dk\" style=\"margin-top:8px\"></div>", "<div class=\"dk\" style=\"margin-top:8px\">Evidence chain excerpt</div>"),
    # Value suffixes
    ("' ' : '—'}", "' days' : '—'}"),
    ("' mg' : '—'}", "' mg' : '—'}"),
    # Clinical flags
    ("''", "'Concomitant immunosuppressant'"),
    ("'Checkpoint '", "'Checkpoint inhibitor'"),
    ("''", "'Immune-depleting regimen'"),
    ("''", "'Oncology indication'"),
    # fc_effector_display
    ("''", "'No effector function'"),
    ("''", "'Reduced effector function'"),
    ("''", "'Normal effector function'"),
    ("''", "'Enhanced effector function'"),
    # Toggle buttons
    ("> ▾<", ">Show full text ▾<"),
    ("> ▴<",    ">Collapse ▴<"),
]

# ── Antibody Guide: convert new tab and static content to English ─────────────
GUIDE_FIXES = [
    # Tab button
    (">Fc × ADA <", ">Fc × Clinical ADA Impact<"),
    # Static content headers
    ("'Fc  ×  ADA '", "'Fc Engineering × Clinical ADA Impact'"),
    ("<strong>Fc  ×  ADA </strong>", "<strong>Fc Engineering × Clinical ADA Impact</strong>"),
    (" Therasik 138  ADA  Fc 。 FDA/EMA  PMID ， Tier A/B 。ADA （、、、）， Fc ，。",
     "Statistical analysis of 138 clinical ADA records from Therasik database, grouped by Fc engineering type. Data sourced from FDA/EMA prescribing information and PMID-verified publications (Tier A/B evidence). ADA rates are confounded by route, indication, assay generation and co-medication — use as a reference benchmark only."),
    # Stat card labels
    ("<div style=\"color:#9ca3af\"></div>", "<div style=\"color:#9ca3af\">Records</div>"),
    ("<div style=\"color:#9ca3af\"></div>",   "<div style=\"color:#9ca3af\">Range</div>"),
    ("<div style=\"color:#9ca3af\"></div>", "<div style=\"color:#9ca3af\">Low-risk</div>"),
    ("<div style=\"font-size:11px;color:#6b7280;margin-bottom:4px\"> ADA </div>",
     "<div style=\"font-size:11px;color:#6b7280;margin-bottom:4px\">Median ADA Rate</div>"),
    # Stat groups
    ("IgG1 ", "IgG1 Wild-type (normal effector)"),
    ("IgG2 / IgG4",    "IgG2 / IgG4 (reduced effector)"),
    ("Fc （LALA/N297）",     "Fc-silent (LALA/N297)"),
    ("ADCC ",              "ADCC-enhanced"),
    ("（YTE/LS）",     "Half-life extended (YTE/LS)"),
    ("ADC",      "ADC (antibody-drug conjugate)"),
    # Notes
    ("；ADA ",
     "Most common format; ADA rate heavily influenced by route and indication"),
    ("IgG4  SC ，ADA  IgG1 ",
     "IgG4 common in SC dosing; median ADA rate similar to IgG1"),
    (" ADA ，",
     "Fc silencing does not directly reduce antigenicity but limits immune activation"),
    ("（n=1），", "Very small sample (n=1); reference only"),
    ("YTE/LS  SC ， ADA",
     "YTE/LS used in long-acting SC formats; prolonged exposure may increase cumulative ADA"),
    ("ADC  ADA，",
     "ADC backbone doesn't alter ADA antigenicity; payload conjugation may increase immune complex risk"),
    # Warning box
    ("<div style=\"font-weight:700;color:#0d4a43;margin-bottom:10px\">⚠ </div>",
     "<div style=\"font-weight:700;color:#0d4a43;margin-bottom:10px\">⚠ Key Interpretation Caveats</div>"),
    ("<li><strong>：</strong>Gen 1 ELISA  Gen 3 ECL， 10 ，</li>",
     "<li><strong>Assay generation bias:</strong> Gen 1 ELISA sensitivity is ~10× lower than Gen 3 ECL; this analysis does not fully correct for cross-generation measurement differences</li>"),
    ("<li><strong>：</strong>SC  ADA  IV（ 2–5 ）， Fc （YTE  SC ）</li>",
     "<li><strong>Route confounding:</strong> SC dosing yields ~2–5× higher ADA rates than IV; Fc type and route are highly correlated (YTE commonly used for SC long-acting formulations)</li>"),
    ("<li><strong>：</strong>，ADA ； MTX  ADA  60–90%</li>",
     "<li><strong>Indication bias:</strong> Oncology patients are immunocompromised, systematically lowering ADA rates; autoimmune patients on MTX show 60–90% ADA reduction</li>"),
    ("<li><strong>：</strong>Fc （n=7） ADCC （n=1），，</li>",
     "<li><strong>Sample size:</strong> Fc-silent (n=7) and ADCC-enhanced (n=1) groups are too small for robust statistics; consult primary literature</li>"),
    ("<li><strong>：</strong>Fc 、 ADA，</li>",
     "<li><strong>Causality direction:</strong> Fc type modulates ADA indirectly via half-life, effector function and immune activation — it does not directly determine sequence antigenicity</li>"),
    # Quick guide
    ("<div style=\"font-weight:700;margin-bottom:12px;color:#374151\">📌 Fc </div>",
     "<div style=\"font-weight:700;margin-bottom:12px;color:#374151\">📌 Fc Engineering Quick-Select Guide</div>"),
    ("<div style=\"font-weight:700;font-size:12px;margin-bottom:4px\"> ADCC/CDC</div>",
     "<div style=\"font-weight:700;font-size:12px;margin-bottom:4px\">Need ADCC/CDC</div>"),
    ("<div style=\"font-size:12px;color:#6b7280\">IgG1 ， GASDALIE（S239D/I332E）；</div>",
     "<div style=\"font-size:12px;color:#6b7280\">IgG1 wild-type or GASDALIE (S239D/I332E) enhanced; monitor infusion reactions</div>"),
    ("<div style=\"font-weight:700;font-size:12px;margin-bottom:4px\"></div>",
     "<div style=\"font-weight:700;font-size:12px;margin-bottom:4px\">Silence effector function</div>"),
    ("<div style=\"font-size:12px;color:#6b7280\">LALA (L234A/L235A)  P329G；IgG4+S228P ；</div>",
     "<div style=\"font-size:12px;color:#6b7280\">LALA (L234A/L235A) or P329G; IgG4+S228P as alternative; standard for checkpoint blockade</div>"),
    ("<div style=\"font-weight:700;font-size:12px;margin-bottom:4px\"></div>",
     "<div style=\"font-weight:700;font-size:12px;margin-bottom:4px\">Extend half-life</div>"),
    ("<div style=\"font-size:12px;color:#6b7280\">LS (M428L/N434S)  YTE (M252Y/S254T/T256E)；SC ；</div>",
     "<div style=\"font-size:12px;color:#6b7280\">LS (M428L/N434S) or YTE (M252Y/S254T/T256E); preferred for SC dosing; monitor placental transfer</div>"),
    ("<div style=\"font-weight:700;font-size:12px;margin-bottom:4px\"></div>",
     "<div style=\"font-weight:700;font-size:12px;margin-bottom:4px\">Bispecific antibodies</div>"),
    ("<div style=\"font-size:12px;color:#6b7280\">Knob-into-Hole + ； DuoBody F405L/K409R；</div>",
     "<div style=\"font-size:12px;color:#6b7280\">Knob-into-Hole + disulfide optimization; or DuoBody F405L/K409R; verify heterodimer purity</div>"),
    # FC_ADA_STATS groups in the JS const
    ("grp:'IgG1 '", "grp:'IgG1 Wild-type (normal effector)'"),
    ("grp:'IgG2 / IgG4'",   "grp:'IgG2 / IgG4 (reduced effector)'"),
    ("grp:'Fc （LALA/N297）'",    "grp:'Fc-silent (LALA/N297)'"),
    ("grp:'ADCC '",             "grp:'ADCC-enhanced'"),
    ("grp:'（YTE/LS）'",    "grp:'Half-life extended (YTE/LS)'"),
    ("grp:'ADC'",     "grp:'ADC (antibody-drug conjugate)'"),
]

# Apply to both therasik-web-source and docs
for fname, fixes in [
    ('Therasik_ADA_Database.html', ADA_FIXES),
    ('Therasik_Antibody_Guide.html', GUIDE_FIXES),
]:
    for folder in ['therasik-web-source', 'docs']:
        path = os.path.join(ROOT, folder, fname)
        print(f"\n--- {folder}/{fname} ---")
        fix(path, fixes)

print("\nDone.")
