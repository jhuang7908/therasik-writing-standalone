"""Generate scenario-driven vaccine KB pages from the canonical schema."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path("D:/InSynBio-AI-Research/Antibody_Engineer_Suite")
JSON_PATH = ROOT / "docs" / "vaccine_kb_data.json"


BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="__LANG__">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="__META_DESCRIPTION__">
  <meta name="robots" content="noai, noimageai">
  <meta name="AI-Training" content="opt-out">
  <title>__TITLE__</title>
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
      position:fixed;
      top:0;
      left:0;
      right:0;
      height:68px;
      display:flex;
      align-items:center;
      justify-content:space-between;
      padding:0 24px;
      background:rgba(255,255,255,.94);
      backdrop-filter:blur(14px);
      border-bottom:1px solid rgba(13,148,136,.14);
      z-index:20;
    }
    .brand {
      font-family:Georgia, "Times New Roman", serif;
      font-size:28px;
      font-weight:700;
      color:#1f2937;
      text-decoration:none;
      letter-spacing:-.03em;
    }
    .brand .accent { color:var(--primary); }
    .topnav { display:flex; gap:10px; align-items:center; }
    .topnav a {
      text-decoration:none;
      color:var(--muted);
      font-size:14px;
      font-weight:600;
      padding:8px 14px;
      border-radius:999px;
    }
    .topnav a.primary {
      color:var(--primary-dark);
      background:rgba(13,148,136,.08);
      border:1px solid rgba(13,148,136,.18);
    }
    .page {
      max-width:1240px;
      margin:0 auto;
      padding:32px 22px 72px;
    }
    .hero {
      background:linear-gradient(135deg, #e6faf7 0%, #f8fffd 58%, #f3f8ff 100%);
      border:1px solid rgba(13,148,136,.14);
      border-radius:24px;
      padding:28px 28px 24px;
      margin-bottom:22px;
    }
    .hero h1 {
      margin:0 0 10px;
      font-size:38px;
      letter-spacing:-.03em;
      line-height:1.1;
      font-family:Georgia, "Times New Roman", serif;
      color:#0f172a;
    }
    .hero p {
      margin:0;
      max-width:880px;
      font-size:16px;
      color:#244b45;
    }
    .integrity {
      margin-top:16px;
      padding:12px 14px;
      background:#ecfdf5;
      border-left:4px solid var(--primary);
      border-radius:10px;
      font-size:13px;
      color:#065f46;
    }
    .stats {
      display:grid;
      grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
      gap:10px;
      margin:18px 0 20px;
    }
    .stat {
      border:1px solid var(--border);
      border-radius:16px;
      padding:14px;
      background:#fff;
    }
    .stat .value {
      font-size:26px;
      font-weight:700;
      color:var(--primary-dark);
      line-height:1;
    }
    .stat .label {
      margin-top:6px;
      font-size:12px;
      text-transform:uppercase;
      letter-spacing:.06em;
      color:var(--muted);
      font-weight:700;
    }
    .search-row {
      display:flex;
      gap:12px;
      align-items:center;
      flex-wrap:wrap;
      margin-bottom:18px;
    }
    .search-row input {
      flex:1;
      min-width:260px;
      border:1px solid var(--border);
      border-radius:12px;
      padding:11px 14px;
      font-size:14px;
    }
    .search-row .count {
      font-size:13px;
      color:var(--muted);
      font-weight:600;
    }
    .tabs {
      display:flex;
      gap:8px;
      flex-wrap:wrap;
      margin-bottom:18px;
    }
    .tab {
      border:1px solid var(--border);
      background:#fff;
      color:var(--muted);
      padding:9px 14px;
      border-radius:999px;
      font-size:13px;
      font-weight:700;
      cursor:pointer;
    }
    .tab.active {
      color:#fff;
      border-color:var(--primary);
      background:var(--primary);
    }
    .panel { display:none; }
    .panel.active { display:block; }
    .section-head {
      margin:8px 0 14px;
    }
    .section-head h2 {
      margin:0 0 6px;
      font-size:24px;
      letter-spacing:-.02em;
      font-family:Georgia, "Times New Roman", serif;
    }
    .section-head p {
      margin:0;
      color:var(--muted);
      max-width:860px;
      font-size:14px;
    }
    .grid {
      display:grid;
      grid-template-columns:repeat(auto-fill,minmax(290px,1fr));
      gap:14px;
    }
    details.card {
      border:1px solid var(--border);
      border-radius:16px;
      background:#fff;
      overflow:hidden;
    }
    details.card[open] {
      border-color:rgba(13,148,136,.35);
      box-shadow:0 10px 28px rgba(15,118,110,.08);
    }
    details.card summary {
      list-style:none;
      cursor:pointer;
      padding:14px 16px;
    }
    details.card summary::-webkit-details-marker { display:none; }
    .card-title {
      font-size:16px;
      font-weight:700;
      color:#0f172a;
      margin-bottom:4px;
    }
    .card-sub {
      font-size:12px;
      color:var(--muted);
      margin-bottom:10px;
    }
    .badge-row, .chip-row {
      display:flex;
      gap:6px;
      flex-wrap:wrap;
    }
    .badge, .chip {
      display:inline-flex;
      align-items:center;
      border-radius:999px;
      padding:4px 9px;
      font-size:11px;
      font-weight:700;
    }
    .badge {
      background:#eef2ff;
      color:#3730a3;
      border:1px solid #c7d2fe;
    }
    .badge.status-verified {
      background:#dcfce7;
      color:#166534;
      border-color:#bbf7d0;
    }
    .badge.status-curated, .badge.status-link-only {
      background:#fff7ed;
      color:#9a3412;
      border-color:#fed7aa;
    }
    .chip {
      background:#f8fafc;
      color:#334155;
      border:1px solid #e2e8f0;
      font-family:"Courier New", monospace;
      font-weight:600;
    }
    .card-body {
      padding:0 16px 16px;
      border-top:1px solid var(--border);
    }
    .kv {
      margin-top:12px;
      display:grid;
      gap:8px;
    }
    .kv div {
      font-size:13px;
      color:#334155;
    }
    .kv strong {
      color:#0f172a;
      margin-right:6px;
    }
    .small-list {
      margin:10px 0 0;
      padding-left:18px;
      color:#334155;
      font-size:13px;
    }
    .small-list li { margin-bottom:6px; }
    .source-link {
      display:inline-flex;
      margin-top:10px;
      text-decoration:none;
      color:var(--primary-dark);
      font-size:12px;
      font-weight:700;
    }
    .table-wrap {
      overflow:auto;
      border:1px solid var(--border);
      border-radius:16px;
      background:#fff;
    }
    table {
      width:100%;
      border-collapse:collapse;
      font-size:13px;
    }
    th, td {
      padding:10px 12px;
      border-bottom:1px solid var(--border);
      vertical-align:top;
      text-align:left;
    }
    th {
      background:var(--soft);
      font-size:11px;
      text-transform:uppercase;
      letter-spacing:.06em;
      color:var(--muted);
    }
    .stack {
      display:grid;
      gap:18px;
    }
    .subsection {
      padding:16px;
      border:1px solid var(--border);
      border-radius:18px;
      background:#fff;
    }
    .subsection h3 {
      margin:0 0 6px;
      font-size:18px;
    }
    .subsection p {
      margin:0 0 12px;
      font-size:13px;
      color:var(--muted);
    }
    .footer-note {
      margin-top:24px;
      font-size:12px;
      color:#64748b;
    }
    @media (max-width:760px) {
      body { padding-top:58px; }
      .topbar { height:58px; padding:0 14px; }
      .brand { font-size:22px; }
      .topnav a { padding:7px 10px; font-size:12px; }
      .hero { padding:22px 18px; }
      .hero h1 { font-size:30px; }
      .page { padding:18px 14px 56px; }
    }
  </style>
</head>
<body>
  <script>window.PAGE_TEXT = __TEXT_JSON__;</script>
  <header class="topbar">
    <a class="brand" href="__HOME_HREF__">__BRAND_PREFIX__<span class="accent">__BRAND_ACCENT__</span></a>
    <nav class="topnav">
      <a class="primary" href="__BACK_HREF__">__BACK_LABEL__</a>
      <a href="__HOME_HREF__">__HOME_LABEL__</a>
    </nav>
  </header>
  <main class="page">
    <section class="hero">
      <h1>__HERO_TITLE__</h1>
      <p>__HERO_SUBTITLE__</p>
      <div class="integrity">__INTEGRITY_NOTE__</div>
    </section>

    <section class="stats" id="stats"></section>

    <section class="search-row">
      <input id="globalSearch" type="text" placeholder="__SEARCH_PLACEHOLDER__">
      <div class="count" id="resultCount"></div>
    </section>

    <section class="tabs">
      <button class="tab active" data-panel="tumor">__TAB_TUMOR__</button>
      <button class="tab" data-panel="infectious">__TAB_INFECTIOUS__</button>
      <button class="tab" data-panel="tolerogenic">__TAB_TOLEROGENIC__</button>
      <button class="tab" data-panel="tcr">__TAB_TCR__</button>
      <button class="tab" data-panel="delivery">__TAB_DELIVERY__</button>
      <button class="tab" data-panel="methods">__TAB_METHODS__</button>
      <button class="tab" data-panel="benchmarks">__TAB_BENCHMARKS__</button>
    </section>

    <section class="panel active" id="panel-tumor">
      <div class="section-head">
        <h2>__TUMOR_TITLE__</h2>
        <p>__TUMOR_DESC__</p>
      </div>
      <div class="grid searchable-group" id="tumorGrid"></div>
    </section>

    <section class="panel" id="panel-infectious">
      <div class="section-head">
        <h2>__INFECTIOUS_TITLE__</h2>
        <p>__INFECTIOUS_DESC__</p>
      </div>
      <div class="grid searchable-group" id="infectiousGrid"></div>
    </section>

    <section class="panel" id="panel-tolerogenic">
      <div class="section-head">
        <h2>__TOLEROGENIC_TITLE__</h2>
        <p>__TOLEROGENIC_DESC__</p>
      </div>
      <div class="grid searchable-group" id="tolerogenicGrid"></div>
    </section>

    <section class="panel" id="panel-tcr">
      <div class="section-head">
        <h2>__TCR_TITLE__</h2>
        <p>__TCR_DESC__</p>
      </div>
      <div class="stack">
        <div class="subsection">
          <h3>__TCR_CLONES_TITLE__</h3>
          <p>__TCR_CLONES_DESC__</p>
          <div class="table-wrap searchable-group"><table>
            <thead><tr><th>Clone</th><th>Antigen</th><th>Epitope</th><th>HLA</th><th>PDB</th><th>Clinical</th></tr></thead>
            <tbody id="tcrCloneRows"></tbody>
          </table></div>
        </div>
        <div class="subsection">
          <h3>__TCR_RULES_TITLE__</h3>
          <p>__TCR_RULES_DESC__</p>
          <div class="grid searchable-group" id="tcrRuleGrid"></div>
        </div>
        <div class="subsection">
          <h3>__TCR_MOTIF_TITLE__</h3>
          <p>__TCR_MOTIF_DESC__</p>
          <div class="grid searchable-group" id="tcrMotifGrid"></div>
        </div>
      </div>
    </section>

    <section class="panel" id="panel-delivery">
      <div class="section-head">
        <h2>__DELIVERY_TITLE__</h2>
        <p>__DELIVERY_DESC__</p>
      </div>
      <div class="stack">
        <div class="subsection">
          <h3>__PLATFORM_TITLE__</h3>
          <p>__PLATFORM_DESC__</p>
          <div class="grid searchable-group" id="platformGrid"></div>
        </div>
        <div class="subsection">
          <h3>__ADJUVANT_TITLE__</h3>
          <p>__ADJUVANT_DESC__</p>
          <div class="grid searchable-group" id="adjuvantGrid"></div>
        </div>
        <div class="subsection">
          <h3>__HELPER_EPITOPE_TITLE__</h3>
          <p>__HELPER_EPITOPE_DESC__</p>
          <div class="grid searchable-group" id="helperGrid"></div>
        </div>
      </div>
    </section>

    <section class="panel" id="panel-methods">
      <div class="section-head">
        <h2>__METHODS_TITLE__</h2>
        <p>__METHODS_DESC__</p>
      </div>
      <div class="stack">
        <div class="subsection">
          <h3>__PLAYBOOKS_TITLE__</h3>
          <p>__PLAYBOOKS_DESC__</p>
          <div class="grid searchable-group" id="playbookGrid"></div>
        </div>
        <div class="subsection">
          <h3>__MRNA_RULES_TITLE__</h3>
          <p>__MRNA_RULES_DESC__</p>
          <div class="grid searchable-group" id="mrnaRuleGrid"></div>
        </div>
        <div class="subsection">
          <h3>__ASSAY_TITLE__</h3>
          <p>__ASSAY_DESC__</p>
          <div class="grid searchable-group" id="assayGrid"></div>
        </div>
        <div class="subsection">
          <h3>__PRIVATE_TITLE__</h3>
          <p>__PRIVATE_DESC__</p>
          <div class="grid searchable-group" id="feedbackGrid"></div>
        </div>
      </div>
    </section>

    <section class="panel" id="panel-benchmarks">
      <div class="section-head">
        <h2>__BENCHMARKS_TITLE__</h2>
        <p>__BENCHMARKS_DESC__</p>
      </div>
      <div class="grid searchable-group" id="benchmarkGrid"></div>
    </section>

    <div class="footer-note">__FOOTER_NOTE__</div>
  </main>

  <script>
    const TEXT = window.PAGE_TEXT;
    let DB = null;

    const esc = (value) => String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');

    function badge(value, statusClass='') {
      return `<span class="badge ${statusClass}">${esc(value)}</span>`;
    }

    function sourceLink(record) {
      const url = record?.evidence?.primary_source_url;
      return url ? `<a class="source-link" href="${url}" target="_blank">${TEXT.sourceLabel}</a>` : '';
    }

    function epitopeChips(record) {
      const bundles = record.epitopes || {};
      const all = []
        .concat(bundles.mhc_i || [])
        .concat(bundles.mhc_ii || [])
        .concat(bundles.mixed || []);
      return all.slice(0, 4).map((ep) => `<span class="chip">${esc(ep.peptide)} · ${esc(ep.hla)}</span>`).join('');
    }

    function renderStatCards(meta) {
      const cards = [
        [meta.module_counts.tumor_antigens, TEXT.statTumor],
        [meta.module_counts.infectious_antigens, TEXT.statInfectious],
        [meta.module_counts.tolerogenic_targets, TEXT.statTolerogenic],
        [meta.module_counts.platforms + meta.module_counts.adjuvants, TEXT.statDelivery],
        [meta.module_counts.tcr_clones + meta.module_counts.tcr_public_motifs, TEXT.statTcr],
        [meta.module_counts.neoantigen_benchmarks, TEXT.statBenchmarks],
      ];
      document.getElementById('stats').innerHTML = cards.map(([value, label]) =>
        `<div class="stat"><div class="value">${value}</div><div class="label">${label}</div></div>`
      ).join('');
    }

    function detailsCard({title, subtitle, badges = [], summary, body, searchText}) {
      return `
        <details class="card searchable" data-search="${esc(searchText).toLowerCase()}">
          <summary>
            <div class="card-title">${esc(title)}</div>
            <div class="card-sub">${esc(subtitle || '')}</div>
            <div class="badge-row">${badges.join('')}</div>
            ${summary ? `<div class="card-sub" style="margin-top:10px;font-size:13px;color:#334155">${esc(summary)}</div>` : ''}
          </summary>
          <div class="card-body">${body}</div>
        </details>
      `;
    }

    function renderTumorCards(items) {
      return items.map((item) => detailsCard({
        title: item.name,
        subtitle: `${item.gene || ''} · ${TEXT.rankLabel} #${item.priority_rank || '-'}`,
        badges: [
          badge(item.application_track),
          badge(item.specificity),
          badge(item.evidence.verification_status, `status-${item.evidence.verification_status.toLowerCase().replace(/_/g, '-')}`),
        ],
        summary: item.notes,
        searchText: JSON.stringify(item),
        body: `
          <div class="kv">
            <div><strong>${TEXT.contextLabel}</strong>${(item.disease_context || []).join(', ')}</div>
            <div><strong>${TEXT.locationLabel}</strong>${esc(item.cellular_location || '')}</div>
            <div><strong>${TEXT.clinicalLabel}</strong>${esc(item.clinical_signal || '')}</div>
            <div><strong>${TEXT.reasonLabel}</strong>${(item.machine_readable_justification || []).map((j) => esc(j.label)).join(', ')}</div>
          </div>
          <div class="chip-row" style="margin-top:12px">${epitopeChips(item)}</div>
          ${sourceLink(item)}
        `,
      })).join('');
    }

    function renderInfectiousCards(items) {
      return items.map((item) => detailsCard({
        title: item.pathogen,
        subtitle: `${item.antigen_name} · ${item.pathogen_type}`,
        badges: [
          badge(item.application_track),
          badge(`${(item.approved_vaccines || []).length} ${TEXT.approvedShort}`),
          badge(item.evidence.verification_status, `status-${item.evidence.verification_status.toLowerCase().replace(/_/g, '-')}`),
        ],
        summary: item.notes,
        searchText: JSON.stringify(item),
        body: `
          <div class="kv">
            <div><strong>${TEXT.contextLabel}</strong>${esc(item.disease || '')}</div>
            <div><strong>${TEXT.correlateLabel}</strong>${esc(item.immune_correlate || '')}</div>
            <div><strong>${TEXT.burdenLabel}</strong>${esc(item.global_burden || '')}</div>
            <div><strong>${TEXT.comparatorLabel}</strong>${(item.approved_vaccines || []).slice(0, 2).map((v) => esc(v.name)).join(' · ')}</div>
          </div>
          <div class="chip-row" style="margin-top:12px">${epitopeChips(item)}</div>
          ${sourceLink(item)}
        `,
      })).join('');
    }

    function renderTolerogenicCards(items) {
      return items.map((item) => detailsCard({
        title: item.target_antigen,
        subtitle: item.disease,
        badges: [
          badge(item.application_track),
          badge(item.clinical_status || TEXT.translationalLabel),
          badge(item.evidence.verification_status, `status-${item.evidence.verification_status.toLowerCase().replace(/_/g, '-')}`),
        ],
        summary: item.notes,
        searchText: JSON.stringify(item),
        body: `
          <div class="kv">
            <div><strong>${TEXT.approachLabel}</strong>${esc(item.vaccine_approach || '')}</div>
            <div><strong>${TEXT.hlaLabel}</strong>${(item.hla_association || []).join(', ')}</div>
            <div><strong>${TEXT.clinicalLabel}</strong>${esc(item.key_trial || '')}</div>
          </div>
          <div class="chip-row" style="margin-top:12px">${epitopeChips(item)}</div>
          ${sourceLink(item)}
        `,
      })).join('');
    }

    function renderTcrRows(items) {
      return items.map((item) => `
        <tr class="searchable" data-search="${esc(JSON.stringify(item)).toLowerCase()}">
          <td>${esc(item.clone_id)}</td>
          <td>${esc(item.antigen)}</td>
          <td>${esc(item.epitope)}</td>
          <td>${esc(item.hla)}</td>
          <td>${item.pdb ? `<a href="https://www.rcsb.org/structure/${item.pdb}" target="_blank">${esc(item.pdb)}</a>` : '-'}</td>
          <td>${esc(item.clinical_use)}</td>
        </tr>
      `).join('');
    }

    function renderRuleCards(items) {
      return items.map((item) => detailsCard({
        title: item.title,
        subtitle: item.entity_type,
        badges: [badge(item.evidence.evidence_tier), badge(item.evidence.primary_source_type)],
        summary: item.why,
        searchText: JSON.stringify(item),
        body: `
          <div class="kv">
            <div><strong>${TEXT.ifLabel}</strong>${esc(item.if || '')}</div>
            <div><strong>${TEXT.thenLabel}</strong>${esc(item.then || '')}</div>
          </div>
          ${sourceLink(item)}
        `,
      })).join('');
    }

    function renderMotifCards(items) {
      return items.map((item) => detailsCard({
        title: item.antigen,
        subtitle: `${item.epitope} · ${item.hla}`,
        badges: [badge(item.antigen_source), badge(`${item.num_unique_clonotypes} ${TEXT.clonotypesLabel}`)],
        summary: item.notes,
        searchText: JSON.stringify(item),
        body: `
          <div class="kv">
            <div><strong>TRBV</strong>${(item.trbv_bias || []).join(', ')}</div>
            <div><strong>TRAV</strong>${(item.trav_bias || []).join(', ')}</div>
            <div><strong>${TEXT.frequencyLabel}</strong>${esc(item.frequency_in_population || '')}</div>
          </div>
          ${sourceLink(item)}
        `,
      })).join('');
    }

    function renderDeliveryCards(items, kind) {
      return items.map((item) => {
        const subtitle = kind === 'platform'
          ? `${item.category} · ${item.cd8_induction || ''}`
          : `${item.category} · ${item.immune_profile || item.immune_role || ''}`;
        const summary = item.description || item.notes || item.immune_role || '';
        return detailsCard({
          title: item.name,
          subtitle,
          badges: [
            badge(item.evidence.evidence_tier),
            badge(item.evidence.verification_status, `status-${item.evidence.verification_status.toLowerCase().replace(/_/g, '-')}`),
          ],
          summary,
          searchText: JSON.stringify(item),
          body: `
            <div class="kv">
              ${kind === 'platform' ? `
                <div><strong>${TEXT.manufacturingLabel}</strong>${esc(item.manufacturing || '')}</div>
                <div><strong>${TEXT.coldChainLabel}</strong>${esc(item.cold_chain || '')}</div>
                <div><strong>${TEXT.compareLabel}</strong>${(item.approved_products || []).slice(0, 3).map((v) => esc(v)).join(' · ')}</div>
              ` : `
                <div><strong>${TEXT.mechanismLabel}</strong>${esc(item.mechanism || item.immune_role || '')}</div>
                <div><strong>${TEXT.compareLabel}</strong>${(item.approved_vaccines || item.use_cases || []).slice(0, 3).map((v) => esc(v.vaccine || v)).join(' · ')}</div>
              `}
            </div>
            ${sourceLink(item)}
          `,
        });
      }).join('');
    }

    function renderMethodCards(items) {
      return items.map((item) => detailsCard({
        title: item.title || item.name,
        subtitle: item.rule_type || item.entity_type,
        badges: [badge(item.evidence.evidence_tier), badge(item.evidence.verification_status, `status-${item.evidence.verification_status.toLowerCase().replace(/_/g, '-')}`)],
        summary: item.why || item.summary || item.when_required || item.name || item.title,
        searchText: JSON.stringify(item),
        body: `
          <div class="kv">
            ${item.applies_when ? `<div><strong>${TEXT.triggerLabel}</strong>${esc(item.applies_when)}</div>` : ''}
            ${item.when_required ? `<div><strong>${TEXT.triggerLabel}</strong>${esc(item.when_required)}</div>` : ''}
            ${item.core_logic ? `<div><strong>${TEXT.logicLabel}</strong>${esc(item.core_logic.join(' · '))}</div>` : ''}
            ${item.best_for ? `<div><strong>${TEXT.bestForLabel}</strong>${esc(item.best_for.join(' · '))}</div>` : ''}
            ${(item.default || item.parameters) ? `<div><strong>${TEXT.defaultLabel}</strong>${esc(JSON.stringify(item.default || item.parameters || {}, null, 0))}</div>` : ''}
          </div>
          ${sourceLink(item)}
        `,
      })).join('');
    }

    function renderFeedbackCards(items) {
      return items.map((item) => detailsCard({
        title: item.title,
        subtitle: item.entity_type,
        badges: [badge((item.inputs || []).length + ' ' + TEXT.inputsLabel), badge((item.wet_readouts || []).length + ' ' + TEXT.readoutsLabel)],
        summary: (item.decision_gates || []).join(' · '),
        searchText: JSON.stringify(item),
        body: `
          <ul class="small-list">${(item.decision_gates || []).map((gate) => `<li>${esc(gate)}</li>`).join('')}</ul>
        `,
      })).join('');
    }

    function renderBenchmarkCards(items) {
      return items.map((item) => detailsCard({
        title: item.title,
        subtitle: `${item.benchmark_type} · ${item.year}`,
        badges: [badge(item.evidence.evidence_tier), badge(item.year)],
        summary: item.pain_point,
        searchText: JSON.stringify(item),
        body: `
          <div class="kv">
            <div><strong>${TEXT.summaryLabel}</strong>${esc(item.summary || '')}</div>
            <div><strong>${TEXT.implicationLabel}</strong>${esc(item.design_implication || '')}</div>
          </div>
          ${sourceLink(item)}
        `,
      })).join('');
    }

    function applySearch() {
      const query = document.getElementById('globalSearch').value.trim().toLowerCase();
      const activePanel = document.querySelector('.panel.active');
      const nodes = activePanel ? activePanel.querySelectorAll('.searchable') : [];
      let visible = 0;
      nodes.forEach((node) => {
        const hit = !query || (node.dataset.search || '').includes(query);
        node.style.display = hit ? '' : 'none';
        if (hit) visible += 1;
      });
      document.getElementById('resultCount').textContent = `${visible} ${TEXT.resultsLabel}`;
    }

    function activateTab(panelId) {
      document.querySelectorAll('.tab').forEach((button) => {
        button.classList.toggle('active', button.dataset.panel === panelId);
      });
      document.querySelectorAll('.panel').forEach((panel) => {
        panel.classList.toggle('active', panel.id === `panel-${panelId}`);
      });
      applySearch();
    }

    async function init() {
      DB = await fetch('vaccine_kb_data.json').then((response) => response.json());
      const modules = DB.modules;
      renderStatCards(DB._meta);
      document.getElementById('tumorGrid').innerHTML = renderTumorCards(modules.antigens.tumor);
      document.getElementById('infectiousGrid').innerHTML = renderInfectiousCards(modules.antigens.infectious);
      document.getElementById('tolerogenicGrid').innerHTML = renderTolerogenicCards(modules.antigens.tolerogenic);
      document.getElementById('tcrCloneRows').innerHTML = renderTcrRows(modules.tcr.clones);
      document.getElementById('tcrRuleGrid').innerHTML = renderRuleCards(modules.tcr.design_rules);
      document.getElementById('tcrMotifGrid').innerHTML = renderMotifCards(modules.tcr.public_motifs);
      document.getElementById('platformGrid').innerHTML = renderDeliveryCards(modules.delivery.platforms, 'platform');
      document.getElementById('adjuvantGrid').innerHTML = renderDeliveryCards(modules.delivery.adjuvants, 'adjuvant');
      document.getElementById('helperGrid').innerHTML = renderDeliveryCards(modules.delivery.adjuvantic_epitopes, 'helper');
      document.getElementById('playbookGrid').innerHTML = renderMethodCards(modules.methods.design_playbooks);
      document.getElementById('mrnaRuleGrid').innerHTML = renderMethodCards(modules.methods.multi_epitope_mrna);
      document.getElementById('assayGrid').innerHTML = renderMethodCards(modules.methods.assay_catalog);
      document.getElementById('feedbackGrid').innerHTML = renderFeedbackCards(modules.methods.private_learning.feedback_patterns);
      document.getElementById('benchmarkGrid').innerHTML = renderBenchmarkCards(modules.methods.neoantigen_benchmarks);
      document.querySelectorAll('.tab').forEach((button) => button.addEventListener('click', () => activateTab(button.dataset.panel)));
      document.getElementById('globalSearch').addEventListener('input', applySearch);
      applySearch();
    }

    init();
  </script>
</body>
</html>
"""


EN_TEXT = {
    "lang": "en",
    "title": "Vaccine Design Methods & Evidence Base | InSynBio",
    "meta_description": "Evidence-backed vaccine design knowledge base covering cancer, infectious-disease, and tolerogenic programs with TCR, platform, mRNA, and benchmark modules.",
    "brand_prefix": "In",
    "brand_accent": "SynBio",
    "home_href": "index.html",
    "back_href": "vaccine_design.html",
    "back_label": "Vaccine Design Service",
    "home_label": "Home",
    "hero_title": "Vaccine Design Methods & Evidence Base",
    "hero_subtitle": "A private-knowledge-base style interface for decision support: ranked antigens, infectious comparators, tolerogenic targets, TCR-guided rules, multi-epitope mRNA logic, benchmark realism, and dry-wet learning patterns.",
    "integrity_note": "Single canonical database shared by site pages and runtime design logic. Records keep explicit evidence tier, verification status, and machine-readable justification. Broad infectious and tolerogenic tracks are restored as first-class modules.",
    "search_placeholder": "Search antigens, TCRs, platforms, methods, or benchmark pain points",
    "tab_tumor": "Tumor",
    "tab_infectious": "Infectious",
    "tab_tolerogenic": "Tolerogenic",
    "tab_tcr": "TCR",
    "tab_delivery": "Delivery",
    "tab_methods": "Methods",
    "tab_benchmarks": "Benchmarks",
    "tumor_title": "Shared Tumor Antigen Evidence",
    "tumor_desc": "Ranked tumor antigens stay visible, but now carry explicit translational reasons and provenance rather than only a browse card.",
    "infectious_title": "Infectious-Disease Antigen Track",
    "infectious_desc": "Infectious coverage is restored as a first-class module to support prophylactic, therapeutic, and rapid-update vaccine work.",
    "tolerogenic_title": "Tolerogenic / Autoimmune Track",
    "tolerogenic_desc": "Inverse-vaccine programs need self-antigen, HLA, and translational-risk context, so they live alongside cancer and infectious modules.",
    "tcr_title": "TCR-Guided Optimization Layer",
    "tcr_desc": "Clinical-grade TCR clones, public motifs, and explicit design rules are separated into a dedicated module instead of a side table.",
    "tcr_clones_title": "Validated TCR Clones",
    "tcr_clones_desc": "Only sequence-anchored records with explicit provenance are kept in the main clone table.",
    "tcr_rules_title": "TCR Design Rules",
    "tcr_rules_desc": "Rules encode why certain TCRs are safe, dangerous, or suitable for monitoring.",
    "tcr_motif_title": "Public TCR Motifs",
    "tcr_motif_desc": "Population-shared clonotype patterns useful for vaccine monitoring and TCR-guided optimization.",
    "delivery_title": "Platform, Adjuvant, and Helper Modules",
    "delivery_desc": "Delivery decisions stay connected to manufacturability, immune bias, and clinically grounded helper logic.",
    "platform_title": "Platforms",
    "platform_desc": "Clinically anchored architectures with manufacturing and cold-chain context.",
    "adjuvant_title": "Adjuvants",
    "adjuvant_desc": "Mechanism-aware adjuvant records that change platform choice, not just formulation footnotes.",
    "helper_epitope_title": "Adjuvantic / Helper Epitopes",
    "helper_epitope_desc": "Reusable helper modules for designs that need explicit CD4 support or memory leverage.",
    "methods_title": "Method Logic",
    "methods_desc": "Method objects expose the design logic that used to be trapped inside code or narrative prose.",
    "mrna_rules_title": "Multi-Epitope mRNA Rules",
    "mrna_rules_desc": "Construct-level logic for linkers, trafficking modules, delivery precedent, and junction quality gates.",
    "playbooks_title": "Design Playbooks",
    "playbooks_desc": "Stepwise logic objects for vaccine, TCR-guided, infectious-update, and mRNA programs.",
    "assay_title": "Assay Gates",
    "assay_desc": "Wet-lab gates that tell the design system what evidence is still missing before a candidate is credible.",
    "private_title": "Dry-Wet Feedback Patterns",
    "private_desc": "Private-learning schema and loop patterns reserved for internal data capture without mixing it into public evidence claims.",
    "benchmarks_title": "Benchmark Reality Layer",
    "benchmarks_desc": "Benchmark studies keep the system honest about neoantigen prediction accuracy and validation gaps.",
    "footer_note": "This page now reads directly from the canonical vaccine database. Any downstream UI or runtime change should start from that shared source of truth.",
}


ZH_TEXT = {
    "lang": "zh",
    "title": " | Therasik",
    "meta_description": "，、、， TCR、、mRNA  benchmark 。",
    "brand_prefix": "Thera",
    "brand_accent": "sik",
    "home_href": "index.html",
    "back_href": "Therasik_Vaccine_Design.html",
    "back_label": "",
    "home_label": "",
    "hero_title": "",
    "hero_subtitle": "，：、 comparator、、TCR 、 mRNA 、 benchmark  canonical schema 。",
    "integrity_note": " canonical 。、 machine-readable justification，。",
    "search_placeholder": "、TCR、、",
    "tab_tumor": "",
    "tab_infectious": "",
    "tab_tolerogenic": "",
    "tab_tcr": "TCR",
    "tab_delivery": "",
    "tab_methods": "",
    "tab_benchmarks": "Benchmark",
    "tumor_title": "",
    "tumor_desc": "，，。",
    "infectious_title": "",
    "infectious_desc": "，、。",
    "tolerogenic_title": " / ",
    "tolerogenic_desc": "、HLA ，，。",
    "tcr_title": "TCR ",
    "tcr_desc": " TCR、 motif ，。",
    "tcr_clones_title": " TCR ",
    "tcr_clones_desc": "。",
    "tcr_rules_title": "TCR ",
    "tcr_rules_desc": " TCR 、、。",
    "tcr_motif_title": " TCR Motif",
    "tcr_motif_desc": " TCR-guided epitope optimization 。",
    "delivery_title": "、 helper ",
    "delivery_desc": "，、、 helper 。",
    "platform_title": "",
    "platform_desc": "。",
    "adjuvant_title": "",
    "adjuvant_desc": "，。",
    "helper_epitope_title": "Helper / ",
    "helper_epitope_desc": " CD4 help ，。",
    "methods_title": "",
    "methods_desc": "，、。",
    "mrna_rules_title": " mRNA ",
    "mrna_rules_desc": " linker、trafficking、delivery  junction ，。",
    "playbooks_title": " Playbook",
    "playbooks_desc": "、TCR-guided、 mRNA 。",
    "assay_title": "",
    "assay_desc": "、，。",
    "private_title": "",
    "private_desc": "， schema ，。",
    "benchmarks_title": "Benchmark ",
    "benchmarks_desc": " benchmark ：，。",
    "footer_note": " canonical vaccine DB。，。",
}


COMMON_TEXT = {
    "statTumor": "Tumor",
    "statInfectious": "Infectious",
    "statTolerogenic": "Tolerogenic",
    "statDelivery": "Delivery",
    "statTcr": "TCR",
    "statBenchmarks": "Benchmarks",
    "sourceLabel": "Primary source",
    "questionsLabel": "Priority questions",
    "modulesLabel": "Recommended modules",
    "rankLabel": "Rank",
    "contextLabel": "Context",
    "locationLabel": "Location",
    "clinicalLabel": "Clinical signal",
    "reasonLabel": "Decision flags",
    "correlateLabel": "Immune correlate",
    "burdenLabel": "Burden",
    "comparatorLabel": "Comparators",
    "approachLabel": "Approach",
    "hlaLabel": "HLA",
    "translationalLabel": "Translational",
    "ifLabel": "If",
    "thenLabel": "Then",
    "clonotypesLabel": "clonotypes",
    "frequencyLabel": "Frequency",
    "manufacturingLabel": "Manufacturing",
    "coldChainLabel": "Cold chain",
    "compareLabel": "Comparators",
    "mechanismLabel": "Mechanism",
    "defaultLabel": "Default / parameters",
    "triggerLabel": "Trigger / required when",
    "logicLabel": "Core logic",
    "bestForLabel": "Best for",
    "inputsLabel": "inputs",
    "readoutsLabel": "readouts",
    "summaryLabel": "Summary",
    "implicationLabel": "Design implication",
    "resultsLabel": "results",
    "approvedShort": "approved",
}


TARGETS = {
    ROOT / "docs" / "vaccine_kb_data.html": EN_TEXT,
    ROOT / "insynbio-web-source" / "vaccine_kb_data.html": EN_TEXT,
    ROOT / "docs" / "Therasik_Vaccine_KB.html": ZH_TEXT,
    ROOT / "therasik-web-source" / "Therasik_Vaccine_KB.html": ZH_TEXT,
}


def build_page(text: dict[str, str]) -> str:
    payload = {**COMMON_TEXT, **text}
    html = BASE_TEMPLATE.replace("__TEXT_JSON__", json.dumps(payload, ensure_ascii=False))
    replacements = {
        "__LANG__": payload["lang"],
        "__META_DESCRIPTION__": payload["meta_description"],
        "__TITLE__": payload["title"],
        "__BRAND_PREFIX__": payload["brand_prefix"],
        "__BRAND_ACCENT__": payload["brand_accent"],
        "__HOME_HREF__": payload["home_href"],
        "__BACK_HREF__": payload["back_href"],
        "__BACK_LABEL__": payload["back_label"],
        "__HOME_LABEL__": payload["home_label"],
        "__HERO_TITLE__": payload["hero_title"],
        "__HERO_SUBTITLE__": payload["hero_subtitle"],
        "__INTEGRITY_NOTE__": payload["integrity_note"],
        "__SEARCH_PLACEHOLDER__": payload["search_placeholder"],
        "__TAB_TUMOR__": payload["tab_tumor"],
        "__TAB_INFECTIOUS__": payload["tab_infectious"],
        "__TAB_TOLEROGENIC__": payload["tab_tolerogenic"],
        "__TAB_TCR__": payload["tab_tcr"],
        "__TAB_DELIVERY__": payload["tab_delivery"],
        "__TAB_METHODS__": payload["tab_methods"],
        "__TAB_BENCHMARKS__": payload["tab_benchmarks"],
        "__TUMOR_TITLE__": payload["tumor_title"],
        "__TUMOR_DESC__": payload["tumor_desc"],
        "__INFECTIOUS_TITLE__": payload["infectious_title"],
        "__INFECTIOUS_DESC__": payload["infectious_desc"],
        "__TOLEROGENIC_TITLE__": payload["tolerogenic_title"],
        "__TOLEROGENIC_DESC__": payload["tolerogenic_desc"],
        "__TCR_TITLE__": payload["tcr_title"],
        "__TCR_DESC__": payload["tcr_desc"],
        "__TCR_CLONES_TITLE__": payload["tcr_clones_title"],
        "__TCR_CLONES_DESC__": payload["tcr_clones_desc"],
        "__TCR_RULES_TITLE__": payload["tcr_rules_title"],
        "__TCR_RULES_DESC__": payload["tcr_rules_desc"],
        "__TCR_MOTIF_TITLE__": payload["tcr_motif_title"],
        "__TCR_MOTIF_DESC__": payload["tcr_motif_desc"],
        "__DELIVERY_TITLE__": payload["delivery_title"],
        "__DELIVERY_DESC__": payload["delivery_desc"],
        "__PLATFORM_TITLE__": payload["platform_title"],
        "__PLATFORM_DESC__": payload["platform_desc"],
        "__ADJUVANT_TITLE__": payload["adjuvant_title"],
        "__ADJUVANT_DESC__": payload["adjuvant_desc"],
        "__HELPER_EPITOPE_TITLE__": payload["helper_epitope_title"],
        "__HELPER_EPITOPE_DESC__": payload["helper_epitope_desc"],
        "__METHODS_TITLE__": payload["methods_title"],
        "__METHODS_DESC__": payload["methods_desc"],
        "__MRNA_RULES_TITLE__": payload["mrna_rules_title"],
        "__MRNA_RULES_DESC__": payload["mrna_rules_desc"],
        "__PLAYBOOKS_TITLE__": payload["playbooks_title"],
        "__PLAYBOOKS_DESC__": payload["playbooks_desc"],
        "__ASSAY_TITLE__": payload["assay_title"],
        "__ASSAY_DESC__": payload["assay_desc"],
        "__PRIVATE_TITLE__": payload["private_title"],
        "__PRIVATE_DESC__": payload["private_desc"],
        "__BENCHMARKS_TITLE__": payload["benchmarks_title"],
        "__BENCHMARKS_DESC__": payload["benchmarks_desc"],
        "__FOOTER_NOTE__": payload["footer_note"],
    }
    for key, value in replacements.items():
        html = html.replace(key, value)
    return html


def main() -> None:
    if not JSON_PATH.exists():
        raise FileNotFoundError(f"Canonical DB missing: {JSON_PATH}")
    for path, text in TARGETS.items():
        path.write_text(build_page(text), encoding="utf-8")
        print(f"Wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
