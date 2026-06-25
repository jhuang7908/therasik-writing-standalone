"""
Build ADC Knowledge Base v2 — Full subcategory filter system
Mirrors the organization methodology of CAR-T and Antibody knowledge bases
"""
import json
from pathlib import Path

def main():
    data_dir = Path('data/adc_atlas')
    master  = json.loads((data_dir / 'adc_master_internal.json').read_text(encoding='utf-8'))
    comps   = json.loads((data_dir / 'adc_components.json').read_text(encoding='utf-8'))
    rules   = json.loads((data_dir / 'adc_design_rules.json').read_text(encoding='utf-8'))

    linkers  = [c for c in comps if 'ADC-COMP-L' in c.get('id','')]
    payloads = [c for c in comps if 'ADC-COMP-P' in c.get('id','')]
    antigens = rules.get('antigen_properties', {})
    conj     = rules.get('conjugation_technology', {})
    experiments = rules.get('experimental_methods', {})
    payload_cls = rules.get('payload_classification', {})
    clin_progs = master

    # --- subcategory helpers ---
    def stage_label(s):
        s = s or ''
        if 'approved' in s and 'resubmit' not in s: return 'Approved'
        if 'phase_3' in s: return 'Phase 3'
        if 'phase_2' in s: return 'Phase 2'
        if 'phase_1' in s: return 'Phase 1'
        if 'discontinued' in s: return 'Discontinued'
        return 'Other'

    def badge_color(label):
        return {
            'Approved':     ('#d1fae5','#065f46'),
            'Phase 3':      ('#dbeafe','#1e40af'),
            'Phase 2':      ('#e0e7ff','#3730a3'),
            'Phase 1':      ('#f3e8ff','#6d28d9'),
            'Discontinued': ('#fee2e2','#991b1b'),
        }.get(label, ('#f3f4f6','#374151'))

    def antigen_expr_label(props):
        e = props.get('expression','').replace('_',' ')
        return e if e else 'Unknown'

    def payload_cls_for(name):
        n = name.upper()
        for cls_key, cls_info in payload_cls.items():
            if not isinstance(cls_info, dict): continue
            members = [m.upper() for m in cls_info.get('members',[])]
            if n in members:
                return cls_key.replace('_',' ').title()
        return 'Unknown'

    def linker_type_label(l):
        t = l.get('type','').lower()
        if t == 'cleavable': return 'Cleavable'
        if t == 'non-cleavable': return 'Non-cleavable'
        return 'Other'

    def conj_homogeneity(v):
        h = str(v.get('dar_homogeneity','')).lower()
        if 'very_high' in h or 'very high' in h: return 'Very High (Site-Specific)'
        if 'high' in h: return 'High'
        if 'moderate' in h: return 'Moderate'
        return 'Low'

    # Build stage buckets for counts
    stage_counts = {}
    for p in clin_progs:
        s = stage_label(p.get('development_stage',''))
        stage_counts[s] = stage_counts.get(s, 0) + 1

    antigen_expr_counts = {}
    for n, p in antigens.items():
        if n.startswith('_'): continue
        l = antigen_expr_label(p)
        antigen_expr_counts[l] = antigen_expr_counts.get(l, 0) + 1

    payload_cls_counts = {}
    for p in payloads:
        c = payload_cls_for(p.get('name',''))
        payload_cls_counts[c] = payload_cls_counts.get(c, 0) + 1

    linker_type_counts = {}
    for l in linkers:
        t = linker_type_label(l)
        linker_type_counts[t] = linker_type_counts.get(t, 0) + 1

    conj_homogeneity_counts = {}
    for n, v in conj.items():
        if n.startswith('_'): continue
        if not isinstance(v, dict): continue
        h = conj_homogeneity(v)
        conj_homogeneity_counts[h] = conj_homogeneity_counts.get(h, 0) + 1

    # Helper: render filter pill
    def pill(label, count, filter_key, filter_val, active=False):
        cls = 'pill active' if active else 'pill'
        return f'<button class="{cls}" data-filter="{filter_key}" data-val="{filter_val}">{label} <span class="pill-count">{count}</span></button>'

    # Helper: render program card
    def prog_card(p):
        s = stage_label(p.get('development_stage',''))
        bg, fg = badge_color(s)
        tgt = p.get('target','Unknown')
        payload = p.get('payload_name','Unknown')
        linker  = p.get('linker_name','Unknown')
        dar     = p.get('dar_mean','Unknown')
        src     = p.get('source_primary','N/A')
        audit_txt = p.get('technical_audit',{}).get('logic_check','') or ''
        failure   = p.get('failure_analysis',{})
        is_failed = failure.get('is_failed', False)
        fail_html = ''
        if is_failed:
            fail_html = f'''<details><summary class="sum-fail">⚠ Failure Analysis</summary>
<div class="dc"><p><strong>Category:</strong> {failure.get("reason_category","N/A")}</p>
<p>{failure.get("internal_insight","")}</p></div></details>'''

        return f'''<div class="card" data-stage="{s}" data-target="{tgt}" data-search="{p.get("canonical_name","").lower()} {tgt.lower()} {p.get("company","").lower()} {payload.lower()}">
<div class="ch">
  <div><div class="ctitle">{p.get("canonical_name","Unknown")}</div>
    <div class="csub">{p.get("company","")}</div></div>
  <span class="badge" style="background:{bg};color:{fg}">{s}</span>
</div>
<div class="cb">
  <div class="kv-row">
    <span class="kv-key">Target</span><span class="tag-chip">{tgt}</span>
  </div>
  <div class="kv-row">
    <span class="kv-key">Payload</span><span>{payload}</span>
    <span class="kv-key" style="margin-left:12px">DAR</span><span>{dar}</span>
  </div>
  <div class="kv-row">
    <span class="kv-key">Linker</span><span>{linker}</span>
  </div>
  <details><summary>Technical Details</summary>
  <div class="dc">
    <p><strong>Binder:</strong> {p.get("binder_name","Unknown")} ({p.get("binder_format","IgG1")})</p>
    <p><strong>Conjugation:</strong> {p.get("conjugation_technology","Unknown")}</p>
    {f'<p><strong>Audit:</strong> {audit_txt}</p>' if audit_txt else ''}
    <p><strong>Source / Trial:</strong> <a href="https://clinicaltrials.gov/search?query={src}" target="_blank" style="color:var(--primary)">{src}</a></p>
  </div></details>
  {fail_html}
</div></div>'''

    # Helper: render antigen card
    def ag_card(name, props):
        expr = antigen_expr_label(props)
        bg_map = {'solid tumor':'#f0fdf4','liquid tumor':'#eff6ff','liquid_solid':'#fef9c3','autoimmune':'#fdf4ff'}
        bg = bg_map.get(props.get('expression',''),'#f9fafb')
        return f'''<div class="card" data-expr="{expr}" data-search="{name.lower()} {expr.lower()}">
<div class="ch">
  <div class="ctitle">{name}</div>
  <span class="badge" style="background:{bg};color:#374151;border:1px solid #e5e7eb">{expr}</span>
</div>
<div class="cb">
  <div class="kv-row"><span class="kv-key">Density</span><span>{props.get("density","?")}</span></div>
  <div class="kv-row"><span class="kv-key">Internalization</span><span>{props.get("internalization_rate","?")}</span></div>
  <div class="kv-row"><span class="kv-key">Heterogeneity</span><span>{props.get("heterogeneity","?")}</span></div>
  <details><summary>Safety Profile</summary>
  <div class="dc">
    <p><strong>Normal Tissue:</strong> {props.get("normal_tissue_expression","?")}</p>
    <p><strong>Off-Tumor Risk:</strong> {props.get("on_target_off_tumor_risk","?")}</p>
  </div></details>
</div></div>'''

    # Helper: render payload card
    def payload_card(p):
        cls = payload_cls_for(p.get('name',''))
        mol = p.get('molecular_structure',{})
        smiles = mol.get('smiles','N/A')
        cid = mol.get('pubchem_cid','N/A')
        cid_link = f'<a href="{mol["reference_url"]}" target="_blank" style="color:var(--primary)">{cid}</a>' if mol.get('reference_url') else cid
        return f'''<div class="card" data-cls="{cls}" data-search="{p.get("name","").lower()} {cls.lower()}">
<div class="ch">
  <div class="ctitle">{p.get("name","Unknown")}</div>
  <span class="badge" style="background:#fef3c7;color:#92400e">{cls}</span>
</div>
<div class="cb">
  <div class="kv-row"><span class="kv-key">Potency</span><span>{p.get("potency","?")}</span></div>
  <div class="kv-row"><span class="kv-key">Bystander</span><span>{p.get("bystander_effect","?")}</span></div>
  <details><summary>Chemical Structure</summary>
  <div class="dc">
    <p><strong>PubChem CID:</strong> {cid_link}</p>
    <p><strong>SMILES:</strong></p>
    <div class="smiles">{smiles}</div>
  </div></details>
</div></div>'''

    # Helper: render linker card
    def linker_card(l):
        ltype = linker_type_label(l)
        mol = l.get('molecular_structure',{})
        cid = mol.get('pubchem_cid','N/A')
        smiles = mol.get('smiles','N/A')
        return f'''<div class="card" data-ltype="{ltype}" data-search="{l.get("name","").lower()} {ltype.lower()} {l.get("mechanism","").lower()}">
<div class="ch">
  <div class="ctitle">{l.get("name","Unknown")}</div>
  <span class="badge" style="background:#ecfdf5;color:#065f46">{ltype}</span>
</div>
<div class="cb">
  <div class="kv-row"><span class="kv-key">Mechanism</span><span>{l.get("mechanism","?")}</span></div>
  <div class="kv-row"><span class="kv-key">Stability</span><span>{l.get("stability","?")}</span></div>
  <details><summary>Chemical Structure</summary>
  <div class="dc">
    <p><strong>PubChem CID:</strong> {cid}</p>
    <div class="smiles">{smiles}</div>
  </div></details>
</div></div>'''

    # Helper: render conjugation card
    def conj_card(name, v):
        h = conj_homogeneity(v)
        hbg = {'Very High (Site-Specific)':'#f0fdf4','High':'#eff6ff','Moderate':'#fefce8','Low':'#fff1f2'}.get(h,'#f9fafb')
        return f'''<div class="card" data-homo="{h}" data-search="{name.lower()} {v.get("description","").lower()} {v.get("patent_freedom","").lower()}">
<div class="ch">
  <div class="ctitle">{name.replace("_"," ").title()}</div>
  <span class="badge" style="background:{hbg};color:#374151;border:1px solid #e5e7eb">{h}</span>
</div>
<div class="cb">
  <div class="kv-row"><span class="kv-key">DAR</span><span>{v.get("typical_dar","?")}</span></div>
  <div class="kv-row"><span class="kv-key">Description</span><span style="font-size:12px">{v.get("description","?")}</span></div>
  <details><summary>CMC & FTO</summary>
  <div class="dc">
    <p><strong>CMC Complexity:</strong> {v.get("cmc_complexity","?")}</p>
    <p><strong>Patent / FTO:</strong> {v.get("patent_freedom","?")}</p>
  </div></details>
</div></div>'''

    # Helper: render experiment card
    def exp_card(assay_name, details):
        methods = ', '.join(details.get('methods',[]))
        analytes = ', '.join(details.get('analytes',[])) if 'analytes' in details else ''
        return f'''<div class="card">
<div class="ch"><div class="ctitle">{assay_name.replace("_"," ").title()}</div></div>
<div class="cb">
  <div class="kv-row"><span class="kv-key">Methods</span><span style="font-size:12px">{methods}</span></div>
  {f'<div class="kv-row"><span class="kv-key">Analytes</span><span style="font-size:12px">{analytes}</span></div>' if analytes else ''}
  <div class="kv-row" style="margin-top:8px"><p style="font-size:12px;color:#4b5563;margin:0">{details.get("purpose","")}</p></div>
</div></div>'''

    out = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="index, follow">
<meta name="robots" content="noai, noimageai">
<meta name="AI-Training" content="opt-out">
<link rel="canonical" href="https://www.insynbio.com/adc_database.html">
<title>ADC Knowledge Base | InSynBio</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Cormorant+Garamond:wght@600;700&display=swap" rel="stylesheet">
<style>
:root{{--primary:#0d9488;--primary-dark:#0f766e;--text:#111827;--muted:#4b5563;--border:#e5e7eb;--bg:#f9fafb;--card:#ffffff;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);}}

/* TOP HEADER */
.top-header{{display:flex;align-items:center;justify-content:space-between;padding:12px 32px;background:rgba(255,255,255,.97);backdrop-filter:blur(12px);border-bottom:2px solid rgba(13,148,136,.1);position:sticky;top:0;z-index:200;gap:16px;flex-wrap:wrap;}}
.brand{{font-family:'Cormorant Garamond',serif;font-weight:700;font-size:24px;color:#1f2937;text-decoration:none;display:flex;align-items:center;gap:8px;}}
.brand .syn{{color:var(--primary);font-style:italic;}}
.top-header-nav{{display:flex;gap:4px;flex:1;justify-content:center;flex-wrap:wrap;}}
.top-header-nav a{{padding:7px 14px;font-size:13px;color:var(--muted);text-decoration:none;border-radius:18px;transition:all .2s;font-weight:500;}}
.top-header-nav a:hover{{color:var(--primary);background:rgba(13,148,136,.07);}}
.top-header-nav a.active{{background:var(--primary);color:#fff;}}
.search-wrap{{display:flex;align-items:center;gap:8px;}}
#globalSearch{{padding:8px 14px;border:1px solid var(--border);border-radius:20px;font-size:13px;width:240px;outline:none;transition:border-color .2s;}}
#globalSearch:focus{{border-color:var(--primary);box-shadow:0 0 0 3px rgba(13,148,136,.12);}}

/* BODY LAYOUT */
.layout{{display:flex;height:calc(100vh - 60px);max-width:1600px;margin:0 auto;}}

/* SIDEBAR */
.sidebar{{width:240px;flex-shrink:0;border-right:1px solid var(--border);background:#fff;display:flex;flex-direction:column;overflow:hidden;}}
.sidebar-section{{padding:16px;border-bottom:1px solid var(--border);}}
.sidebar-section h4{{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:10px;}}
.tab-btn{{display:flex;justify-content:space-between;align-items:center;width:100%;padding:10px 12px;border:none;background:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500;color:var(--muted);transition:all .2s;text-align:left;margin-bottom:2px;}}
.tab-btn:hover{{background:rgba(13,148,136,.07);color:var(--primary);}}
.tab-btn.active{{background:rgba(13,148,136,.12);color:var(--primary-dark);font-weight:600;}}
.tab-btn .tab-count{{font-size:11px;font-weight:700;background:rgba(13,148,136,.1);color:var(--primary);padding:2px 7px;border-radius:10px;}}
.tab-btn.active .tab-count{{background:var(--primary);color:#fff;}}

/* FILTER PANE */
.filter-pane{{padding:16px;overflow-y:auto;flex:1;}}
.filter-pane h5{{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;margin-top:16px;}}
.filter-pane h5:first-child{{margin-top:0;}}
.pill{{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border:1px solid var(--border);border-radius:20px;font-size:12px;font-weight:500;cursor:pointer;background:#fff;color:var(--muted);transition:all .18s;margin:3px;}}
.pill:hover{{border-color:var(--primary);color:var(--primary);}}
.pill.active{{background:var(--primary);color:#fff;border-color:var(--primary);}}
.pill-count{{font-size:10px;font-weight:700;opacity:.8;}}
.pill-reset{{border-color:transparent;background:#f3f4f6;font-size:12px;padding:4px 10px;color:var(--muted);}}
.pill-reset:hover{{background:#e5e7eb;}}

/* MAIN CONTENT */
.main{{flex:1;display:flex;flex-direction:column;overflow:hidden;}}
.main-header{{padding:20px 28px 0;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}}
.main-header h2{{font-family:'Cormorant Garamond',serif;font-size:26px;font-weight:700;color:var(--text);}}
.result-count{{font-size:13px;color:var(--muted);font-weight:500;}}
.tab-panel{{display:none;flex:1;overflow-y:auto;padding:16px 28px 40px;}}
.tab-panel.active{{display:block;}}

/* GRID & CARDS */
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;transition:transform .18s,box-shadow .18s,border-color .18s;}}
.card:hover{{transform:translateY(-2px);border-color:var(--primary);box-shadow:0 6px 18px rgba(13,148,136,.1);}}
.card.hidden{{display:none;}}
.ch{{padding:14px 16px;border-bottom:1px solid var(--border);background:#fdfdfd;display:flex;justify-content:space-between;align-items:flex-start;gap:8px;}}
.ctitle{{font-size:14px;font-weight:600;color:var(--text);line-height:1.3;}}
.csub{{font-size:11px;color:var(--muted);margin-top:2px;}}
.badge{{font-size:11px;font-weight:600;padding:3px 9px;border-radius:12px;white-space:nowrap;flex-shrink:0;}}
.cb{{padding:14px 16px;font-size:13px;}}
.kv-row{{display:flex;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:6px;}}
.kv-key{{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;white-space:nowrap;}}
.tag-chip{{background:rgba(13,148,136,.08);color:var(--primary-dark);font-size:12px;font-weight:600;padding:2px 8px;border-radius:10px;}}

/* Details / Summary */
details{{margin-top:10px;border-radius:8px;border:1px solid var(--border);background:#f8fafc;}}
summary{{padding:8px 12px;cursor:pointer;font-size:12px;font-weight:600;color:var(--primary);list-style:none;display:flex;align-items:center;gap:6px;outline:none;}}
summary::-webkit-details-marker{{display:none;}}
summary::before{{content:"▸";transition:transform .2s;font-size:11px;}}
details[open] summary::before{{transform:rotate(90deg);}}
summary.sum-fail{{color:#dc2626;}}
.dc{{padding:10px 12px;border-top:1px solid var(--border);font-size:12px;color:var(--muted);line-height:1.6;}}
.dc p{{margin-bottom:6px;}}
.dc a{{color:var(--primary);}}
.smiles{{font-family:monospace;font-size:11px;word-break:break-all;background:#e5e7eb;padding:6px;border-radius:4px;margin-top:4px;}}

/* Section header in experiments */
.section-header{{grid-column:1/-1;border-bottom:2px solid var(--border);padding-bottom:8px;margin-top:8px;}}
.section-header h3{{font-family:'Cormorant Garamond',serif;font-size:22px;font-weight:700;color:var(--text);}}

/* Stats bar */
.stats-bar{{display:flex;gap:0;background:#fff;border-bottom:1px solid var(--border);padding:0 28px;flex-shrink:0;overflow-x:auto;}}
.stat{{padding:10px 20px;font-size:12px;font-weight:600;color:var(--muted);border-right:1px solid var(--border);white-space:nowrap;}}
.stat span{{display:block;font-size:20px;font-weight:700;color:var(--primary);}}

@media(max-width:900px){{
  .layout{{flex-direction:column;height:auto;}}
  .sidebar{{width:100%;height:auto;flex-direction:row;overflow-x:auto;}}
  .filter-pane{{display:flex;flex-wrap:wrap;padding:8px;}}
}}
</style>
</head>
<body>

<header class="top-header">
  <a href="index.html" class="brand">
    <svg width="28" height="24" viewBox="0 0 32 30" fill="none"><path d="M16 2L2 10V22L16 28L30 22V10L16 2Z" fill="#0d9488" fill-opacity=".05" stroke="#0d9488" stroke-width="1" stroke-opacity=".3"/><path d="M14.5 24 V 16" stroke="#0d9488" stroke-width="2.5" stroke-linecap="round"/><path d="M17.5 24 V 16" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round"/><line x1="13" y1="19" x2="19" y2="19" stroke="#9ca3af" stroke-width="1.5" stroke-linecap="round"/><line x1="13" y1="21" x2="19" y2="21" stroke="#9ca3af" stroke-width="1.5" stroke-linecap="round"/></svg>
    In<span class="syn">Syn</span>Bio
  </a>
  <nav class="top-header-nav">
    <a href="index.html">Home</a>
    <a href="InSynBio_ADC_Design_Page.html">ADC Design Service</a>
    <a href="InSynBio_CART_Design_Page.html">CAR-T Design</a>
    <a href="adc_database.html" class="active">ADC Knowledge Base</a>
  </nav>
  <div class="search-wrap">
    <input type="text" id="globalSearch" placeholder="Search across all entries…">
  </div>
</header>

<div class="layout">
  <!-- SIDEBAR -->
  <aside class="sidebar">
    <div class="sidebar-section">
      <h4>Categories</h4>
      <button class="tab-btn active" onclick="switchTab('programs')" id="btn-programs">
        Clinical Programs <span class="tab-count">{len(clin_progs)}</span>
      </button>
      <button class="tab-btn" onclick="switchTab('antigens')" id="btn-antigens">
        Target Antigens <span class="tab-count">{len([k for k in antigens if not k.startswith('_')])}</span>
      </button>
      <button class="tab-btn" onclick="switchTab('payloads')" id="btn-payloads">
        Payloads <span class="tab-count">{len(payloads)}</span>
      </button>
      <button class="tab-btn" onclick="switchTab('linkers')" id="btn-linkers">
        Linkers <span class="tab-count">{len(linkers)}</span>
      </button>
      <button class="tab-btn" onclick="switchTab('conjugation')" id="btn-conjugation">
        Conjugation Tech <span class="tab-count">{len([k for k in conj if not k.startswith('_') and isinstance(conj[k],dict)])}</span>
      </button>
      <button class="tab-btn" onclick="switchTab('experiments')" id="btn-experiments">
        Validation Assays <span class="tab-count">{sum(len(v) for v in experiments.values())}</span>
      </button>
    </div>

    <!-- Dynamic filter pane -->
    <div class="filter-pane" id="filterPane">
      <!-- Populated by JS -->
    </div>
  </aside>

  <!-- MAIN -->
  <div class="main">
    <!-- Stats bar -->
    <div class="stats-bar">
      <div class="stat"><span>{len(clin_progs)}</span>Programs</div>
      <div class="stat"><span>{len([k for k in antigens if not k.startswith('_')])}</span>Antigens</div>
      <div class="stat"><span>{len(payloads)}</span>Payloads</div>
      <div class="stat"><span>{len(linkers)}</span>Linkers</div>
      <div class="stat"><span>{len([k for k in conj if not k.startswith('_') and isinstance(conj[k],dict)])}</span>Conjugation Tech</div>
    </div>

    <div class="main-header">
      <h2 id="tabTitle">Clinical Programs</h2>
      <span class="result-count" id="resultCount"></span>
    </div>

    <!-- PROGRAMS -->
    <div class="tab-panel active" id="panel-programs">
      <div class="grid" id="grid-programs">
'''
    for p in clin_progs:
        out += prog_card(p) + '\n'
    out += '''      </div>
    </div>

    <!-- ANTIGENS -->
    <div class="tab-panel" id="panel-antigens">
      <div class="grid" id="grid-antigens">
'''
    for name, props in antigens.items():
        if name.startswith('_'): continue
        out += ag_card(name, props) + '\n'
    out += '''      </div>
    </div>

    <!-- PAYLOADS -->
    <div class="tab-panel" id="panel-payloads">
      <div class="grid" id="grid-payloads">
'''
    for p in payloads:
        out += payload_card(p) + '\n'
    out += '''      </div>
    </div>

    <!-- LINKERS -->
    <div class="tab-panel" id="panel-linkers">
      <div class="grid" id="grid-linkers">
'''
    for l in linkers:
        out += linker_card(l) + '\n'
    out += '''      </div>
    </div>

    <!-- CONJUGATION -->
    <div class="tab-panel" id="panel-conjugation">
      <div class="grid" id="grid-conjugation">
'''
    for name, v in conj.items():
        if name.startswith('_') or not isinstance(v, dict): continue
        out += conj_card(name, v) + '\n'
    out += '''      </div>
    </div>

    <!-- EXPERIMENTS -->
    <div class="tab-panel" id="panel-experiments">
      <div class="grid" id="grid-experiments">
'''
    for cat, assays in experiments.items():
        out += f'<div class="section-header"><h3>{cat.replace("_"," ").title()}</h3></div>\n'
        for name, details in assays.items():
            out += exp_card(name, details) + '\n'
    out += '''      </div>
    </div>

  </div><!-- .main -->
</div><!-- .layout -->

<script>
// ── Tab switching ─────────────────────────────────────────────
const TAB_META = {
  programs:    { title:'Clinical Programs',   attr:'data-stage',  filterAttr:'stage' },
  antigens:    { title:'Target Antigens',     attr:'data-expr',   filterAttr:'expr' },
  payloads:    { title:'Payloads',            attr:'data-cls',    filterAttr:'cls' },
  linkers:     { title:'Linkers',             attr:'data-ltype',  filterAttr:'ltype' },
  conjugation: { title:'Conjugation Technology', attr:'data-homo', filterAttr:'homo' },
  experiments: { title:'Validation Assays',   attr:null, filterAttr:null },
};

const FILTER_DEFS = {
  programs: {
    'Clinical Stage': [
      {label:'All',        val:'__all__'},
      {label:'Approved',   val:'Approved'},
      {label:'Phase 3',    val:'Phase 3'},
      {label:'Phase 2',    val:'Phase 2'},
      {label:'Phase 1',    val:'Phase 1'},
      {label:'Discontinued', val:'Discontinued'},
    ]
  },
  antigens: {
    'Tumor Type': [
      {label:'All',val:'__all__'},
      {label:'Solid Tumor',val:'solid tumor'},
      {label:'Liquid Tumor',val:'liquid tumor'},
      {label:'Both',val:'liquid_solid'},
    ],
    'Internalization Rate': [
      {label:'All',val:'__all__2'},
      {label:'High',val:'high'},
      {label:'Moderate',val:'moderate'},
      {label:'Low',val:'low'},
    ]
  },
  payloads: {
    'Mechanism Class': [
      {label:'All',val:'__all__'},
      {label:'Tubulin Inhibitors',val:'Tubulin Inhibitors'},
      {label:'TOP1 Inhibitors',val:'Topoisomerase I Inhibitors'},
      {label:'DNA Damaging',val:'Dna Damaging Agents'},
      {label:'Immunomodulators',val:'Immunomodulators'},
      {label:'Radionuclides',val:'Radionuclides'},
      {label:'Protein Toxins',val:'Protein Toxins'},
      {label:'PROTACs',val:'Protac Payloads'},
      {label:'RNA Pol II Inhib.',val:'Rna Polymerase Ii Inhibitors'},
      {label:'Spliceosome Inhib.',val:'Spliceosome Inhibitors'},
      {label:'KSP Inhibitors',val:'Ksp Inhibitors'},
      {label:'Bcl-xL Inhibitors',val:'Bcl Xl Inhibitors'},
    ]
  },
  linkers: {
    'Linker Type': [
      {label:'All',val:'__all__'},
      {label:'Cleavable',val:'Cleavable'},
      {label:'Non-Cleavable',val:'Non-cleavable'},
      {label:'Other',val:'Other'},
    ]
  },
  conjugation: {
    'DAR Homogeneity': [
      {label:'All',val:'__all__'},
      {label:'Very High (Site-Specific)',val:'Very High (Site-Specific)'},
      {label:'High',val:'High'},
      {label:'Moderate',val:'Moderate'},
      {label:'Low',val:'Low'},
    ]
  }
};

let currentTab = 'programs';
let activeFilters = {};

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('panel-' + tab).classList.add('active');
  document.getElementById('btn-' + tab).classList.add('active');
  document.getElementById('tabTitle').textContent = TAB_META[tab].title;
  activeFilters = {};
  renderFilterPane(tab);
  applyFilters();
}

function renderFilterPane(tab) {
  const pane = document.getElementById('filterPane');
  const defs = FILTER_DEFS[tab];
  if (!defs) { pane.innerHTML = ''; return; }
  let html = '';
  for (const [groupName, options] of Object.entries(defs)) {
    html += `<h5>${groupName}</h5><div>`;
    for (const opt of options) {
      const key = groupName;
      const isActive = activeFilters[key] === opt.val || opt.val.startsWith('__all__');
      html += `<button class="pill${isActive ? ' active' : ''}" onclick="toggleFilter('${key}','${opt.val}')">${opt.label}</button>`;
    }
    html += '</div>';
  }
  pane.innerHTML = html;
}

function toggleFilter(key, val) {
  if (val.startsWith('__all__')) {
    delete activeFilters[key];
  } else {
    if (activeFilters[key] === val) delete activeFilters[key];
    else activeFilters[key] = val;
  }
  renderFilterPane(currentTab);
  applyFilters();
}

function applyFilters() {
  const searchTerm = document.getElementById('globalSearch').value.toLowerCase();
  const grid = document.getElementById('grid-' + currentTab);
  if (!grid) return;
  const meta = TAB_META[currentTab];
  let visible = 0;
  
  grid.querySelectorAll('.card').forEach(card => {
    const searchText = (card.getAttribute('data-search') || '').toLowerCase();
    const matchSearch = !searchTerm || searchText.includes(searchTerm);

    let matchFilters = true;
    for (const [key, val] of Object.entries(activeFilters)) {
      // For programs: stage filter
      if (currentTab === 'programs' && key === 'Clinical Stage') {
        const stageVal = card.getAttribute('data-stage') || '';
        if (stageVal !== val) { matchFilters = false; break; }
      }
      // For antigens: expr or internalization
      if (currentTab === 'antigens' && key === 'Tumor Type') {
        const exprVal = (card.getAttribute('data-expr') || '').toLowerCase();
        if (!exprVal.includes(val.toLowerCase())) { matchFilters = false; break; }
      }
      if (currentTab === 'antigens' && key === 'Internalization Rate') {
        const searchTxt = (card.getAttribute('data-search') || '').toLowerCase();
        if (!searchTxt.includes(val.toLowerCase())) { matchFilters = false; break; }
      }
      // Payloads: class
      if (currentTab === 'payloads' && key === 'Mechanism Class') {
        const clsVal = card.getAttribute('data-cls') || '';
        if (clsVal !== val) { matchFilters = false; break; }
      }
      // Linkers: type
      if (currentTab === 'linkers' && key === 'Linker Type') {
        const ltypeVal = card.getAttribute('data-ltype') || '';
        if (ltypeVal !== val) { matchFilters = false; break; }
      }
      // Conjugation: homogeneity
      if (currentTab === 'conjugation' && key === 'DAR Homogeneity') {
        const homoVal = card.getAttribute('data-homo') || '';
        if (homoVal !== val) { matchFilters = false; break; }
      }
    }

    const show = matchSearch && matchFilters;
    card.classList.toggle('hidden', !show);
    if (show) visible++;
  });

  document.getElementById('resultCount').textContent = visible + ' entries';
}

// ── Global search ─────────────────────────────────────────────
document.getElementById('globalSearch').addEventListener('input', applyFilters);

// ── Init ──────────────────────────────────────────────────────
renderFilterPane('programs');
applyFilters();
</script>
</body>
</html>'''

    out_path = Path('docs/adc_database.html')
    out_path.write_text(out, encoding='utf-8')
    print(f"Generated {out_path}  ({out_path.stat().st_size//1024} KB)")

if __name__ == '__main__':
    main()
