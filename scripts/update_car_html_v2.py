"""Generate the high-quality Therasik_CAR_KB.html.

This script uses the firewalled canonical CAR-T JSON to build a modern,
tabbed UI for the Therasik site, mirroring the Vaccine KB experience.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "therasik-web-source" / "car_kb_public.json"
OUT_PATH = ROOT / "docs" / "Therasik_CAR_KB.html"

TEMPLATE = """<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="Therasik ACTES CAR-T  —  237+ 、。">
  <meta name="robots" content="noai, noimageai">
  <meta name="AI-Training" content="opt-out">
  <title>CAR-T  | Therasik</title>
  <style>
    :root {
      --primary:#0d9488;
      --primary-dark:#0f766e;
      --text:#111827;
      --muted:#4b5563;
      --border:#e5e7eb;
      --soft:#f8fafc;
      --soft-2:#f1f5f9;
      --accent:#ecfdf5;
      --warning:#fff7ed;
      --tier1: #dcfce7; --tier1-txt: #166534;
      --tier2: #eef2ff; --tier2-txt: #3730a3;
      --tier3: #f1f5f9; --tier3-txt: #475569;
    }
    * { box-sizing:border-box; }
    body {
      margin:0;
      font-family:Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color:var(--text);
      background:#fff;
      line-height:1.55;
      padding-top:68px;
    }
    .topbar {
      position:fixed; top:0; left:0; right:0; height:68px;
      display:flex; align-items:center; justify-content:space-between;
      padding:0 24px; background:rgba(255,255,255,.94);
      backdrop-filter:blur(14px); border-bottom:1px solid rgba(13,148,136,.14); z-index:20;
    }
    .brand {
      font-family:Georgia, serif; font-size:28px; font-weight:700;
      color:#1f2937; text-decoration:none; letter-spacing:-.03em;
    }
    .brand .accent { color:var(--primary); }
    .page { max-width:1240px; margin:0 auto; padding:32px 22px 72px; }
    .hero {
      background:linear-gradient(135deg, #e6faf7 0%, #f8fffd 58%, #f3f8ff 100%);
      border:1px solid rgba(13,148,136,.14); border-radius:24px;
      padding:28px 28px 24px; margin-bottom:22px;
    }
    .hero h1 { margin:0 0 10px; font-size:38px; font-family:Georgia, serif; color:#0f172a; }
    .hero p { margin:0; max-width:880px; font-size:16px; color:#244b45; }
    
    .stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin:18px 0 20px; }
    .stat { border:1px solid var(--border); border-radius:16px; padding:14px; background:#fff; }
    .stat .value { font-size:26px; font-weight:700; color:var(--primary-dark); line-height:1; }
    .stat .label { margin-top:6px; font-size:12px; text-transform:uppercase; color:var(--muted); font-weight:700; }
    
    .search-row { display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:18px; position:sticky; top:80px; z-index:15; background:#fff; padding:10px 0; }
    .search-row input { flex:1; min-width:260px; border:1px solid var(--border); border-radius:12px; padding:11px 14px; font-size:14px; }
    
    .tabs { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:18px; }
    .tab { border:1px solid var(--border); background:#fff; color:var(--muted); padding:9px 14px; border-radius:999px; font-size:13px; font-weight:700; cursor:pointer; }
    .tab.active { color:#fff; border-color:var(--primary); background:var(--primary); }
    .panel { display:none; }
    .panel.active { display:block; }
    
    .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:14px; }
    details.card { border:1px solid var(--border); border-radius:16px; background:#fff; overflow:hidden; transition:all 0.2s; }
    details.card[open] { border-color:rgba(13,148,136,.35); box-shadow:0 10px 28px rgba(15,118,110,.08); }
    summary { list-style:none; cursor:pointer; padding:14px 16px; }
    summary::-webkit-details-marker { display:none; }
    
    .card-title { font-size:16px; font-weight:700; color:#0f172a; margin-bottom:4px; }
    .card-sub { font-size:12px; color:var(--muted); margin-bottom:10px; }
    
    .badge-row { display:flex; gap:6px; flex-wrap:wrap; }
    .badge { border-radius:999px; padding:3px 9px; font-size:11px; font-weight:700; }
    .tier-T1 { background:var(--tier1); color:var(--tier1-txt); }
    .tier-T2 { background:var(--tier2); color:var(--tier2-txt); }
    .tier-T3 { background:var(--tier3); color:var(--tier3-txt); }
    
    .card-body { padding:0 16px 16px; border-top:1px solid var(--border); font-size:13px; }
    .kv { margin-top:10px; display:grid; gap:6px; }
    .kv strong { color:#0f172a; margin-right:4px; }
    
    .playbook-card { border:1px solid #e2e8f0; border-radius:16px; padding:18px; background:linear-gradient(to bottom right, #fff, #f8fafc); }
    .playbook-card h3 { margin:0 0 10px; font-size:17px; color:var(--primary-dark); }
    .playbook-logic { margin-top:10px; padding:12px; background:#f1f5f9; border-radius:10px; font-size:13px; }
    .playbook-logic li { margin-bottom:4px; }

    @media (max-width: 768px) {
      .hero h1 { font-size: 28px; }
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<header class="topbar">
  <a href="therasik_index.html" class="brand">Thera<span class="accent">sik</span></a>
  <nav class="topnav">
    <a href="Therasik_Antibody_Guide.html"></a>
    <a href="Therasik_ADC_Database.html">ADC</a>
    <a href="Therasik_CAR_KB.html" class="primary">CAR-T</a>
    <a href="Therasik_Vaccine_KB.html"></a>
  </nav>
</header>

<main class="page">
  <section class="hero">
    <h1>ACTES CAR-T </h1>
    <p> 237+ 、。、 CAR 。</p>
    <div class="stats" id="hero-stats"></div>
  </section>

  <div class="search-row">
    <input type="text" id="mainSearch" placeholder="、、...">
    <div class="count" id="resultCount"></div>
  </div>

  <nav class="tabs">
    <button class="tab active" data-panel="elements"> (Elements)</button>
    <button class="tab" data-panel="targets"> (Targets)</button>
    <button class="tab" data-panel="methods"> (Methods)</button>
  </nav>

  <section class="panel active" id="panel-elements">
    <div class="grid" id="elementsGrid"></div>
  </section>

  <section class="panel" id="panel-targets">
    <div class="grid" id="targetsGrid"></div>
  </section>

  <section class="panel" id="panel-methods">
    <div class="grid" id="methodsGrid">
      <div id="playbookGrid" style="grid-column: 1/-1; display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 16px;"></div>
      <div id="assayGrid" style="grid-column: 1/-1; display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 14px; margin-top: 24px;"></div>
    </div>
  </section>
</main>

<script>
  var DATA = __JSON_DATA__;
  
  function init() {
    renderStats();
    renderElements(DATA.modules.elements);
    renderTargets(DATA.modules.targets);
    renderMethods(DATA.modules.methods);
    setupEvents();
  }

  function renderStats() {
    var counts = DATA._meta;
    document.getElementById('hero-stats').innerHTML = `
      <div class="stat"><div class="value">${counts.total_elements}</div><div class="label"></div></div>
      <div class="stat"><div class="value">${counts.total_targets}</div><div class="label"></div></div>
      <div class="stat"><div class="value">12</div><div class="label"></div></div>
      <div class="stat"><div class="value">${DATA.modules.methods.playbooks.length}</div><div class="label"></div></div>
    `;
  }

  function renderElements(items) {
    var grid = document.getElementById('elementsGrid');
    grid.innerHTML = items.map(el => `
      <details class="card" id="${el.record_id}">
        <summary>
          <div class="card-title">${esc(el.name)}</div>
          <div class="card-sub">${esc(el.category)} | ${esc(el.subcategory)}</div>
          <div class="badge-row">
            <span class="badge tier-${el.regulatory_tier}">${el.regulatory_tier}</span>
            ${el.clinical_relevance.approved_products.length ? '<span class="badge status-verified">FDA </span>' : ''}
          </div>
        </summary>
        <div class="card-body">
          <div class="kv">
            <div><strong>:</strong> ${esc(el.role)}</div>
            <div><strong>:</strong> ${esc(el.tier_justification)}</div>
            ${el.design_notes ? `<div><strong>:</strong> ${esc(el.design_notes)}</div>` : ''}
            <div><strong>:</strong> ${el.sequence === '[REDACTED — PRIVATE SEQUENCE]' ? ' ()' : ''}</div>
            ${el.evidence.pmids.length ? `<div><strong>:</strong> PMID: ${el.evidence.pmids.join(', ')}</div>` : ''}
          </div>
        </div>
      </details>
    `).join('');
  }

  function renderTargets(items) {
    var grid = document.getElementById('targetsGrid');
    grid.innerHTML = items.map(t => `
      <details class="card">
        <summary>
          <div class="card-title">${esc(t.name)}</div>
          <div class="card-sub">: ${(t.indications || []).join(', ')}</div>
          <div class="badge status-verified">${esc(t.clinical_status)}</div>
        </summary>
        <div class="card-body">
          <div class="kv">
            <div><strong>:</strong> ${(t.preferred_binders || []).join(' / ')}</div>
            <div><strong>:</strong> ${esc(t.notes)}</div>
          </div>
        </div>
      </details>
    `).join('');
  }

  function renderMethods(methods) {
    var pbGrid = document.getElementById('playbookGrid');
    pbGrid.innerHTML = '<h2> (Design Playbooks)</h2>' + methods.playbooks.map(pb => `
      <div class="playbook-card">
        <h3>${esc(pb.title)}</h3>
        <div class="playbook-logic">
          <strong>:</strong>
          <ul>${pb.core_logic.map(l => `<li>${esc(l)}</li>`).join('')}</ul>
        </div>
        <div class="kv" style="margin-top:10px;">
          <div><strong>:</strong> ${pb.recommended_elements.join(', ')}</div>
        </div>
      </div>
    `).join('');

    var asGrid = document.getElementById('assayGrid');
    asGrid.innerHTML = '<h2 style="grid-column:1/-1;"> (Assay Gates)</h2>' + methods.assay_catalog.map(a => `
      <div class="stat">
        <div style="font-weight:700; color:var(--primary-dark); margin-bottom:8px;">${esc(a.name)}</div>
        <div style="font-size:12px;"><strong>:</strong> ${esc(a.measures)}</div>
        <div style="font-size:12px; margin-top:4px;"><strong>:</strong> ${esc(a.when_required)}</div>
      </div>
    `).join('');
  }

  function setupEvents() {
    document.querySelectorAll('.tab').forEach(t => {
      t.onclick = () => {
        document.querySelectorAll('.tab, .panel').forEach(x => x.classList.remove('active'));
        t.classList.add('active');
        document.getElementById('panel-' + t.dataset.panel).classList.add('active');
      };
    });

    document.getElementById('mainSearch').oninput = function() {
      var q = this.value.toLowerCase();
      document.querySelectorAll('details.card').forEach(c => {
        var text = c.innerText.toLowerCase();
        c.style.display = text.includes(q) ? '' : 'none';
      });
    };
  }

  function esc(s) {
    if(!s) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  init();
</script>
</body>
</html>
"""

def main():
    if not JSON_PATH.exists():
        print("JSON not found.")
        return
    
    data = JSON_PATH.read_text(encoding="utf-8")
    page = TEMPLATE.replace("__JSON_DATA__", data)
    
    OUT_PATH.write_text(page, encoding="utf-8")
    print(f"Generated {OUT_PATH.name}")

if __name__ == "__main__":
    main()
