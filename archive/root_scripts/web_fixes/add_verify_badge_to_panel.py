"""
Add verify_status badge to ADA detail panel header.
VERIFIED → green shield; UNCERTAIN → amber warning; SOURCE_UNREACHABLE → gray.
"""

TARGETS = [
    r'therasik-web-source\Therasik_ADA_Database.html',
    r'docs\Therasik_ADA_Database.html',
    r'insynbio-web-source\ada_database.html',
]

# CSS to add (append before </style>)
BADGE_CSS = """
    /* Verification status badges */
    .vbadge { display:inline-flex;align-items:center;gap:4px;font-size:10.5px;
      font-weight:600;padding:2px 7px;border-radius:10px;margin-left:6px;
      vertical-align:middle;letter-spacing:0.02em; }
    .vbadge-verified    { background:#d1fae5;color:#065f46; }
    .vbadge-ctx         { background:#dbeafe;color:#1e40af; }
    .vbadge-uncertain   { background:#fef3c7;color:#92400e; }
    .vbadge-live        { background:#f3f4f6;color:#374151; }
    .vbadge-unreachable { background:#fee2e2;color:#991b1b; }
    .verify-note { font-size:11px;color:#6b7280;line-height:1.55;
      margin-top:6px;padding:6px 10px;background:#f9fafb;
      border-left:3px solid #e5e7eb;border-radius:0 4px 4px 0; }
"""

# JS function to build verify badge HTML
VERIFY_JS = """
function verifyBadge(d) {
  const vs = d.verify_status || '';
  const note = d.verify_note || '';
  if (!vs) return '';
  let cls, icon, label;
  if (vs === 'VERIFIED') {
    cls = 'vbadge-verified'; icon = '✓'; label = 'Verified';
  } else if (vs === 'VERIFIED_WITH_CONTEXT') {
    cls = 'vbadge-ctx'; icon = '✓'; label = 'Verified (context)';
  } else if (vs === 'UNCERTAIN') {
    cls = 'vbadge-uncertain'; icon = '⚠'; label = 'Uncertain';
  } else if (vs === 'SOURCE_LIVE') {
    cls = 'vbadge-live'; icon = '○'; label = 'Source live';
  } else if (vs === 'SOURCE_UNREACHABLE') {
    cls = 'vbadge-unreachable'; icon = '✕'; label = 'Source unreachable';
  } else {
    cls = 'vbadge-live'; icon = '?'; label = vs;
  }
  const noteHtml = note
    ? `<div class="verify-note"><strong>Verification note:</strong> ${escHtml(note)}</div>` : '';
  return `<span class="vbadge ${cls}">${icon} ${label}</span>${noteHtml}`;
}
"""

# Inject badge into dp-sub line (right of genetics/targets)
OLD_DP_SUB = """  document.getElementById('dp-sub').innerHTML = [
    originBadge(d.origin),
    d.genetics ? `<span style="font-size:11px;margin-left:4px;color:var(--text-muted)">${d.genetics}</span>` : ''
  ].join('') + `<span style="font-size:11px;margin-left:8px;color:var(--text-muted)">${d.targets || ''}</span>`;"""

NEW_DP_SUB = """  document.getElementById('dp-sub').innerHTML = [
    originBadge(d.origin),
    d.genetics ? `<span style="font-size:11px;margin-left:4px;color:var(--text-muted)">${d.genetics}</span>` : '',
    verifyBadge(d),
  ].join('') + `<span style="font-size:11px;margin-left:8px;color:var(--text-muted)">${d.targets || ''}</span>`;"""

# Also show verify_note in ADA section after evidence box
OLD_ADA_SECTION_END = "      ${evidenceBoxHtml(d)}\n    `));"
NEW_ADA_SECTION_END  = """      ${evidenceBoxHtml(d)}
      ${d.verify_note ? `<div class="verify-note" style="margin-top:8px"><strong>🔬 Verification note:</strong> ${escHtml(d.verify_note)}</div>` : ''}
    `));"""

for target in TARGETS:
    txt = open(target, encoding='utf-8').read()
    n = 0

    # 1. Add CSS before </style>
    if BADGE_CSS.strip()[:20] not in txt:
        txt = txt.replace('</style>', BADGE_CSS + '\n  </style>', 1)
        n += 1

    # 2. Add verifyBadge JS function before closeDetail
    if 'verifyBadge' not in txt:
        txt = txt.replace('function closeDetail()', VERIFY_JS + '\nfunction closeDetail()', 1)
        n += 1

    # 3. Inject badge into dp-sub
    if OLD_DP_SUB in txt:
        txt = txt.replace(OLD_DP_SUB, NEW_DP_SUB, 1)
        n += 1

    # 4. Add verify note after evidence box
    if OLD_ADA_SECTION_END in txt:
        txt = txt.replace(OLD_ADA_SECTION_END, NEW_ADA_SECTION_END, 1)
        n += 1

    with open(target, 'w', encoding='utf-8') as f:
        f.write(txt)
    print(f"  [{n} changes] {target}")

print("Done.")
