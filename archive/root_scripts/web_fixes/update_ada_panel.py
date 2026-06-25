"""
Update ADA detail panel: collapsible sections + new fields (Fc notes, CDRs, CMC flags).
"""
import re, shutil

TARGETS = [
    r'therasik-web-source\Therasik_ADA_Database.html',
    r'docs\Therasik_ADA_Database.html',
]

# ── 1. Add CSS for collapsible sections ─────────────────────────────────────
OLD_CSS = """.detail-section h3 {
    font-size:13px; font-weight:700; color:var(--text); margin:0 0 10px;
    text-transform:uppercase; letter-spacing:0.5px;
  }"""

NEW_CSS = """.detail-section h3 {
    font-size:13px; font-weight:700; color:var(--text); margin:0 0 10px;
    text-transform:uppercase; letter-spacing:0.5px;
    cursor:pointer; user-select:none; display:flex; align-items:center; justify-content:space-between;
  }
  .detail-section h3::after { content:'▾'; font-size:10px; opacity:0.45; font-style:normal; margin-left:4px; }
  .detail-section.collapsed h3::after { content:'▸'; }
  .detail-section.collapsed .ds-body { display:none; }
  .ds-body { }
  .fc-note-box {
    background:#f0fdf9; border:1px solid rgba(13,148,136,0.2); border-radius:8px;
    padding:10px 14px; font-size:12px; line-height:1.65; color:var(--text);
    margin-top:4px; white-space:pre-wrap; word-break:break-word;
  }
  .evidence-toggle { background:none; border:none; color:var(--primary); font-size:11.5px;
    cursor:pointer; padding:4px 0; text-decoration:underline; }
  .cdr-seq { font-family:monospace; font-size:11.5px; letter-spacing:0.06em;
    background:#f9fafb; border:1px solid var(--border); border-radius:4px;
    padding:3px 8px; display:inline-block; }"""

# ── 2. New openDetail function body ─────────────────────────────────────────
OLD_SECTIONS_START = "  const sections = [];\n\n  // ── ADA Evidence"
NEW_SECTIONS_START = """  const sections = [];

  // helper: wrap content in a collapsible section
  function mkSection(title, bodyHtml, collapsed=false) {
    return `<div class="detail-section${collapsed?' collapsed':''}">
      <h3>${title}</h3>
      <div class="ds-body">${bodyHtml}</div>
    </div>`;
  }

  // ── ADA Evidence"""

# Evidence box with toggle
OLD_EVIDENCE_BOX = """function evidenceBoxHtml(d) {
  const raw = evidenceText(d);
  if (!raw) return '';
  const maxLen = 4000;
  const clipped = raw.length > maxLen ? raw.substring(0, maxLen) + '…' : raw;
  return `<div class="dk" style="margin-top:8px">Evidence chain excerpt</div><div class="evidence-box">${escHtml(clipped)}</div>`;
}"""

NEW_EVIDENCE_BOX = """function evidenceBoxHtml(d) {
  const raw = evidenceText(d);
  if (!raw) return '';
  const SHORT = 400;
  const full = escHtml(raw);
  const short = raw.length > SHORT ? escHtml(raw.substring(0, SHORT)) + '…' : full;
  const id = 'ev-' + Math.random.toString(36).slice(2);
  if (raw.length <= SHORT) {
    return `<div class="dk" style="margin-top:8px"></div><div class="evidence-box">${full}</div>`;
  }
  return `<div class="dk" style="margin-top:8px"></div>
    <div class="evidence-box" id="${id}-short">${short}
      <br><button class="evidence-toggle" onclick="toggleEvidence('${id}')"> ▾</button>
    </div>
    <div class="evidence-box" id="${id}-full" style="display:none">${full}
      <br><button class="evidence-toggle" onclick="toggleEvidence('${id}')"> ▴</button>
    </div>`;
}

function toggleEvidence(id) {
  const s = document.getElementById(id+'-short');
  const f = document.getElementById(id+'-full');
  if (!s || !f) return;
  const isShort = s.style.display !== 'none';
  s.style.display = isShort ? 'none' : '';
  f.style.display = isShort ? '' : 'none';
}"""

# ── ADA section: replace h3 tag to use mkSection structure
OLD_ADA_SECTION = """  // ── ADA Evidence
  sections.push(`
    <div class="detail-section">
      <h3>Clinical ADA</h3>
      <div class="detail-grid">
        <div class="detail-item">
          <div class="dk">ADA Incidence</div>
          <div class="dv" style="font-size:20px;font-weight:700;color:${adaColor(d.ada_pct)}">${d.ada_pct !== null ? d.ada_pct.toFixed(1)+'%' : '—'}</div>
        </div>
        <div class="detail-item">
          <div class="dk">Evidence Tier</div>
          <div class="dv">${tierBadge(d.tier, d.citation_url)}</div>
        </div>
        <div class="detail-item wide">
          <div class="dk">ADA Display Value</div>
          <div class="dv" style="font-size:12px">${d.ada_display || '—'}</div>
        </div>
        ${d.pmids ? `<div class="detail-item wide"><div class="dk">PMIDs</div><div class="dv" style="font-size:11.5px">${String(d.pmids)}</div></div>` : ''}
        ${d.citation_url ? `<div class="detail-item wide"><div class="dk">Source URL</div><div class="dv"><a class="detail-link" href="${d.citation_url}" target="_blank">${d.citation_url.split('?')[0]}</a></div></div>` : ''}
      </div>
      ${evidenceBoxHtml(d)}
    </div>`);"""

NEW_ADA_SECTION = """  // ── ADA Evidence
  sections.push(mkSection(' ADA ', `
      <div class="detail-grid">
        <div class="detail-item">
          <div class="dk">ADA </div>
          <div class="dv" style="font-size:20px;font-weight:700;color:${adaColor(d.ada_pct)}">${d.ada_pct !== null ? d.ada_pct.toFixed(1)+'%' : '—'}</div>
        </div>
        <div class="detail-item">
          <div class="dk"></div>
          <div class="dv">${tierBadge(d.tier, d.citation_url)}</div>
        </div>
        <div class="detail-item wide">
          <div class="dk">ADA </div>
          <div class="dv" style="font-size:12px">${d.ada_display || '—'}</div>
        </div>
        ${d.pmids ? `<div class="detail-item wide"><div class="dk">PMIDs</div><div class="dv" style="font-size:11.5px">${String(d.pmids)}</div></div>` : ''}
        ${d.citation_url ? `<div class="detail-item wide"><div class="dk"></div><div class="dv"><a class="detail-link" href="${d.citation_url}" target="_blank" onclick="event.stopPropagation">${d.citation_url.split('?')[0]}</a></div></div>` : ''}
      </div>
      ${evidenceBoxHtml(d)}
    `));"""

OLD_CLINICAL_SECTION = """  // ── Clinical Context
  sections.push(`
    <div class="detail-section">
      <h3>Clinical Context</h3>
      <div class="detail-grid">
        <div class="detail-item"><div class="dk">Indication</div><div class="dv" style="font-size:12px">${d.indication || '—'}</div></div>
        <div class="detail-item"><div class="dk">Disease Class</div><div class="dv">${d.disease_class || '—'}</div></div>
        <div class="detail-item"><div class="dk">Route</div><div class="dv">${d.route || '—'}</div></div>
        <div class="detail-item"><div class="dk">Half-life</div><div class="dv">${d.half_life !== null ? d.half_life+' days' : '—'}</div></div>
        <div class="detail-item"><div class="dk">Dose</div><div class="dv">${d.dose_mg !== null ? d.dose_mg+' mg' : '—'}</div></div>
        <div class="detail-item"><div class="dk">Assay Generation</div><div class="dv">${d.assay_gen !== null ? 'Gen '+d.assay_gen : '—'} · ${d.assay_platform||'—'}</div></div>
        <div class="detail-item"><div class="dk">MTX Co-medication</div><div class="dv">${d.mtx || '—'}</div></div>
        <div class="detail-item"><div class="dk">Approval Year</div><div class="dv">${d.approval_year || '—'}</div></div>
        <div class="detail-item"><div class="dk">Fc Isotype</div><div class="dv">${d.fc_isotype ? 'IgG'+d.fc_isotype : '—'}</div></div>
        <div class="detail-item"><div class="dk">Fc Engineering</div><div class="dv" style="font-size:12px">${d.fc_engineering || '—'}</div></div>
        <div class="detail-item wide"><div class="dk">Fc Effector Status</div><div class="dv" style="font-size:12px">${d.fc_effector || '—'}</div></div>
      </div>
    </div>`);"""

NEW_CLINICAL_SECTION = """  // ── Clinical Context
  const fcNoteHtml = d.fc_mutation_notes
    ? `<div class="detail-item wide" style="margin-top:4px"><div class="dk">Fc  / </div><div class="fc-note-box">${escHtml(d.fc_mutation_notes)}</div></div>`
    : '';
  const concomitantFlags = [
    d.concomitant_immuno === true ? '' : null,
    d.checkpoint_inhibitor === true ? 'Checkpoint ' : null,
    d.immune_depleting === true ? '' : null,
    d.oncology === true ? '' : null,
  ].filter(Boolean).join(' · ');
  sections.push(mkSection('', `
      <div class="detail-grid">
        <div class="detail-item wide"><div class="dk"></div><div class="dv" style="font-size:12px">${d.indication || '—'}</div></div>
        <div class="detail-item"><div class="dk"></div><div class="dv">${d.disease_class || '—'}</div></div>
        <div class="detail-item"><div class="dk"></div><div class="dv">${d.route || '—'}</div></div>
        <div class="detail-item"><div class="dk"></div><div class="dv">${d.half_life !== null ? d.half_life+' ' : '—'}</div></div>
        <div class="detail-item"><div class="dk"></div><div class="dv">${d.dose_mg ? d.dose_mg+' mg' : '—'}</div></div>
        <div class="detail-item"><div class="dk"></div><div class="dv">${d.dose_freq || '—'}</div></div>
        <div class="detail-item"><div class="dk"></div><div class="dv">${d.approval_year || '—'}</div></div>
        <div class="detail-item"><div class="dk"></div><div class="dv">${d.assay_gen !== null ? 'Gen '+d.assay_gen : '—'}${d.assay_platform ? ' · '+d.assay_platform : ''}</div></div>
        <div class="detail-item"><div class="dk">MTX </div><div class="dv">${d.mtx || '—'}</div></div>
        ${d.immuno_context ? `<div class="detail-item wide"><div class="dk"></div><div class="dv" style="font-size:12px">${escHtml(d.immuno_context)}</div></div>` : ''}
        ${concomitantFlags ? `<div class="detail-item wide"><div class="dk"></div><div class="dv" style="font-size:11.5px;color:var(--primary)">${concomitantFlags}</div></div>` : ''}
      </div>
    `));

  // ── Fc Engineering
  sections.push(mkSection('Fc ', `
      <div class="detail-grid">
        <div class="detail-item"><div class="dk"></div><div class="dv">${d.fc_isotype ? 'IgG'+d.fc_isotype : '—'}</div></div>
        <div class="detail-item"><div class="dk"></div><div class="dv" style="font-size:12px">${d.fc_effector || '—'}</div></div>
        ${fcNoteHtml}
      </div>
    `, true));""" # collapsed by default

OLD_MHC_SECTION = """  // ── MHC-II / Immunogenicity
  const mhcNetColor = d.mhcii_net_clusters >= 8 ? '#b91c1c' : d.mhcii_net_clusters >= 4 ? '#92400e' : '#065f46';
  sections.push(`
    <div class="detail-section">
      <h3>MHC-II Epitope Profile</h3>
      <div style="background:var(--bg-alt);border-radius:var(--radius);padding:12px;margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <span style="font-size:11px;color:var(--text-muted)">Net immunogenic clusters <small>(excl. tolerated)</small></span>
          <span style="font-size:22px;font-weight:700;color:${mhcNetColor}">${d.mhcii_net_clusters !== null ? d.mhcii_net_clusters : '—'}</span>
        </div>
        ${mhcStackBar(d)}
      </div>
      <div class="detail-grid">
        <div class="detail-item"><div class="dk">Total clusters</div><div class="dv">${fmt(d.mhcii_clusters_total,0)}</div></div>
        <div class="detail-item"><div class="dk">High-binding</div><div class="dv" style="color:#b91c1c;font-weight:600">${fmt(d.mhcii_n_high,0)}</div></div>
        <div class="detail-item"><div class="dk">Medium-binding</div><div class="dv" style="color:#92400e;font-weight:600">${fmt(d.mhcii_n_medium,0)}</div></div>
        <div class="detail-item"><div class="dk">Tolerated (silent)</div><div class="dv" style="color:var(--text-muted)">${fmt(d.mhcii_n_tolerated,0)}</div></div>
        <div class="detail-item"><div class="dk">TCIA Score</div><div class="dv">${d.tcia_score !== null ? d.tcia_score.toFixed(4) : '—'}</div></div>
        <div class="detail-item"><div class="dk">TCIA Risk Level</div><div class="dv">${riskBadge(d.tcia_risk)}</div></div>
      </div>
    </div>`);"""

NEW_MHC_SECTION = """  // ── MHC-II / Immunogenicity
  const mhcNetColor = d.mhcii_net_clusters >= 8 ? '#b91c1c' : d.mhcii_net_clusters >= 4 ? '#92400e' : '#065f46';
  sections.push(mkSection('MHC-II ', `
      <div style="background:var(--bg-alt);border-radius:var(--radius);padding:12px;margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <span style="font-size:11px;color:var(--text-muted)"> <small></small></span>
          <span style="font-size:22px;font-weight:700;color:${mhcNetColor}">${d.mhcii_net_clusters !== null ? d.mhcii_net_clusters : '—'}</span>
        </div>
        ${mhcStackBar(d)}
      </div>
      <div class="detail-grid">
        <div class="detail-item"><div class="dk"></div><div class="dv">${fmt(d.mhcii_clusters_total,0)}</div></div>
        <div class="detail-item"><div class="dk"></div><div class="dv" style="color:#b91c1c;font-weight:600">${fmt(d.mhcii_n_high,0)}</div></div>
        <div class="detail-item"><div class="dk"></div><div class="dv" style="color:#92400e;font-weight:600">${fmt(d.mhcii_n_medium,0)}</div></div>
        <div class="detail-item"><div class="dk"></div><div class="dv" style="color:var(--text-muted)">${fmt(d.mhcii_n_tolerated,0)}</div></div>
        <div class="detail-item"><div class="dk">TCIA </div><div class="dv">${d.tcia_score !== null ? d.tcia_score.toFixed(4) : '—'}</div></div>
        <div class="detail-item"><div class="dk">TCIA </div><div class="dv">${riskBadge(d.tcia_risk)}</div></div>
      </div>
    `));"""

OLD_SURFACE_SECTION = """  // ── Surface (SASA)
  const hydroPct = d.hydrophilic_frac !== null ? (d.hydrophilic_frac * 100).toFixed(1) + '%' : '—';
  const hydroVhPct = d.hydrophilic_vh !== null ? (d.hydrophilic_vh * 100).toFixed(1) + '%' : '—';
  const hydroVlPct = d.hydrophilic_vl !== null ? (d.hydrophilic_vl * 100).toFixed(1) + '%' : '—';
  sections.push(`
    <div class="detail-section">
      <h3>Surface Immunogenicity (SASA)</h3>
      <div style="background:var(--bg-alt);border-radius:var(--radius);padding:12px;margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
          <span style="font-size:11px;color:var(--text-muted)">Hydrophilic surface fraction (VH+VL avg)</span>
          <span style="font-weight:700;font-size:15px;color:var(--primary)">${hydroPct}</span>
        </div>
        <div class="gauge-track" style="height:8px"><div class="gauge-fill hydro" style="width:${d.hydrophilic_frac!==null?Math.min(100,d.hydrophilic_frac*100):0}%"></div></div>
        <div style="font-size:10px;color:var(--text-muted);margin-top:4px">Higher = more hydrophilic surface = lower aggregation risk; lower = more hydrophobic patches = higher aggregation + potential immunogenicity</div>
      </div>
      <div class="detail-grid">
        <div class="detail-item"><div class="dk">VH hydrophilic fraction</div><div class="dv">${hydroVhPct}</div></div>
        <div class="detail-item"><div class="dk">VL hydrophilic fraction</div><div class="dv">${hydroVlPct}</div></div>
        <div class="detail-item"><div class="dk">Surface patches (n)</div><div class="dv">${fmt(d.surf_patches,0)}</div></div>
        <div class="detail-item"><div class="dk">Surface risk</div><div class="dv">${riskBadge(d.surf_risk)}</div></div>
        <div class="detail-item"><div class="dk">Hydrophobic patch (max9)</div><div class="dv">${d.hydro_patch !== null ? d.hydro_patch.toFixed(3) : '—'}</div></div>
      </div>
    </div>`);"""

NEW_SURFACE_SECTION = """  // ── Surface (SASA)
  const hydroPct = d.hydrophilic_frac !== null ? (d.hydrophilic_frac * 100).toFixed(1) + '%' : '—';
  const hydroVhPct = d.hydrophilic_vh !== null ? (d.hydrophilic_vh * 100).toFixed(1) + '%' : '—';
  const hydroVlPct = d.hydrophilic_vl !== null ? (d.hydrophilic_vl * 100).toFixed(1) + '%' : '—';
  sections.push(mkSection('（SASA）', `
      <div style="background:var(--bg-alt);border-radius:var(--radius);padding:12px;margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
          <span style="font-size:11px;color:var(--text-muted)">（VH+VL ）</span>
          <span style="font-weight:700;font-size:15px;color:var(--primary)">${hydroPct}</span>
        </div>
        <div class="gauge-track" style="height:8px"><div class="gauge-fill hydro" style="width:${d.hydrophilic_frac!==null?Math.min(100,d.hydrophilic_frac*100):0}%"></div></div>
        <div style="font-size:10px;color:var(--text-muted);margin-top:4px"> =  = ； =  = </div>
      </div>
      <div class="detail-grid">
        <div class="detail-item"><div class="dk">VH </div><div class="dv">${hydroVhPct}</div></div>
        <div class="detail-item"><div class="dk">VL </div><div class="dv">${hydroVlPct}</div></div>
        <div class="detail-item"><div class="dk"></div><div class="dv">${fmt(d.surf_patches,0)}</div></div>
        <div class="detail-item"><div class="dk"></div><div class="dv">${riskBadge(d.surf_risk)}</div></div>
        <div class="detail-item"><div class="dk">（max9）</div><div class="dv">${d.hydro_patch !== null ? d.hydro_patch.toFixed(3) : '—'}</div></div>
      </div>
    `, true));"""

OLD_CMC_SECTION = """  // ── CMC
  sections.push(`
    <div class="detail-section">
      <h3>CMC / Developability</h3>
      <div class="detail-grid">
        <div class="detail-item"><div class="dk">pI (isoelectric point)</div><div class="dv">${d.pI !== null ? d.pI.toFixed(2) : '—'}</div></div>
        <div class="detail-item"><div class="dk">GRAVY (hydrophobicity)</div><div class="dv">${d.gravy !== null ? d.gravy.toFixed(3) : '—'}</div></div>
        <div class="detail-item"><div class="dk">Instability index</div><div class="dv">${d.instability !== null ? d.instability.toFixed(1) : '—'}</div></div>
        <div class="detail-item"><div class="dk">Net charge @ pH 7</div><div class="dv">${d.net_charge !== null ? (d.net_charge > 0 ? '+' : '') + d.net_charge : '—'}</div></div>
        <div class="detail-item"><div class="dk">ADA V2 Score</div><div class="dv">${d.v2_score !== null ? d.v2_score.toFixed(4) : '—'}</div></div>
        <div class="detail-item"><div class="dk">ADA V2 Risk</div><div class="dv">${riskBadge(d.v2_risk)}</div></div>
      </div>
    </div>`);"""

NEW_CMC_SECTION = """  // ── CMC
  sections.push(mkSection('CMC ', `
      <div class="detail-grid">
        <div class="detail-item"><div class="dk"> pI</div><div class="dv">${d.pI !== null ? d.pI.toFixed(2) : '—'}</div></div>
        <div class="detail-item"><div class="dk">GRAVY</div><div class="dv">${d.gravy !== null ? d.gravy.toFixed(3) : '—'}</div></div>
        <div class="detail-item"><div class="dk"></div><div class="dv">${d.instability !== null ? d.instability.toFixed(1) : '—'}</div></div>
        <div class="detail-item"><div class="dk">（pH 7）</div><div class="dv">${d.net_charge !== null ? (d.net_charge > 0 ? '+' : '') + d.net_charge : '—'}</div></div>
        <div class="detail-item"><div class="dk">ADA V2 </div><div class="dv">${d.v2_score !== null ? d.v2_score.toFixed(4) : '—'}</div></div>
        <div class="detail-item"><div class="dk">ADA V2 </div><div class="dv">${riskBadge(d.v2_risk)}</div></div>
        ${d.deamidation_sites ? `<div class="detail-item wide"><div class="dk"></div><div class="dv" style="font-family:monospace;font-size:11.5px">${escHtml(d.deamidation_sites)}</div></div>` : ''}
        ${d.isomerization_sites ? `<div class="detail-item wide"><div class="dk"></div><div class="dv" style="font-family:monospace;font-size:11.5px">${escHtml(d.isomerization_sites)}</div></div>` : ''}
        ${d.agg_motifs ? `<div class="detail-item wide"><div class="dk"></div><div class="dv" style="font-size:12px">${escHtml(d.agg_motifs)}</div></div>` : ''}
        ${d.cmc_flags ? `<div class="detail-item wide"><div class="dk">CMC </div><div class="dv" style="font-size:12px;color:#b45309">${escHtml(d.cmc_flags)}</div></div>` : ''}
      </div>
    `, true));"""

OLD_GERMLINE_SECTION = """  // ── Germline
  sections.push(`
    <div class="detail-section">
      <h3>Germline / Sequence</h3>
      <div class="detail-grid">
        <div class="detail-item"><div class="dk">VH Germline</div><div class="dv" style="font-family:monospace;font-size:12px">${d.vh_germline||'—'}</div></div>
        <div class="detail-item"><div class="dk">VH Identity</div><div class="dv">${d.vh_identity !== null ? (d.vh_identity*100).toFixed(1)+'%' : '—'}</div></div>
        <div class="detail-item"><div class="dk">VL Germline</div><div class="dv" style="font-family:monospace;font-size:12px">${d.vl_germline||'—'}</div></div>
        <div class="detail-item"><div class="dk">VL Identity</div><div class="dv">${d.vl_identity !== null ? (d.vl_identity*100).toFixed(1)+'%' : '—'}</div></div>
        <div class="detail-item wide"><div class="dk">CDR-H3</div><div class="dv" style="font-family:monospace;font-size:12px;letter-spacing:0.05em">${d.cdr_h3||'—'}</div></div>
        <div class="detail-item"><div class="dk">Format</div><div class="dv" style="font-size:12px">${d.format_type||'—'}</div></div>
      </div>
    </div>`);"""

NEW_GERMLINE_SECTION = """  // ── Germline + CDR
  sections.push(mkSection(' ·  · ', `
      <div class="detail-grid">
        <div class="detail-item"><div class="dk">VH </div><div class="dv" style="font-family:monospace;font-size:12px">${d.vh_germline||'—'}</div></div>
        <div class="detail-item"><div class="dk">VH </div><div class="dv">${d.vh_identity !== null ? (d.vh_identity*100).toFixed(1)+'%' : '—'}</div></div>
        <div class="detail-item"><div class="dk">VH </div><div class="dv">${d.vh_family||'—'}</div></div>
        <div class="detail-item"><div class="dk">VL </div><div class="dv" style="font-family:monospace;font-size:12px">${d.vl_germline||'—'}</div></div>
        <div class="detail-item"><div class="dk">VL </div><div class="dv">${d.vl_identity !== null ? (d.vl_identity*100).toFixed(1)+'%' : '—'}</div></div>
        <div class="detail-item"><div class="dk">VL </div><div class="dv">${d.vl_family||'—'}</div></div>
        ${d.vh_cdr1 ? `<div class="detail-item"><div class="dk">CDR-H1</div><div class="dv"><span class="cdr-seq">${d.vh_cdr1}</span></div></div>` : ''}
        ${d.vh_cdr2 ? `<div class="detail-item"><div class="dk">CDR-H2</div><div class="dv"><span class="cdr-seq">${d.vh_cdr2}</span></div></div>` : ''}
        ${(d.vh_cdr3||d.cdr_h3) ? `<div class="detail-item wide"><div class="dk">CDR-H3</div><div class="dv"><span class="cdr-seq">${d.vh_cdr3||d.cdr_h3}</span></div></div>` : ''}
        ${d.vl_cdr1 ? `<div class="detail-item"><div class="dk">CDR-L1</div><div class="dv"><span class="cdr-seq">${d.vl_cdr1}</span></div></div>` : ''}
        ${d.vl_cdr2 ? `<div class="detail-item"><div class="dk">CDR-L2</div><div class="dv"><span class="cdr-seq">${d.vl_cdr2}</span></div></div>` : ''}
        ${d.vl_cdr3 ? `<div class="detail-item"><div class="dk">CDR-L3</div><div class="dv"><span class="cdr-seq">${d.vl_cdr3}</span></div></div>` : ''}
        ${d.vh_vl_angle !== null ? `<div class="detail-item"><div class="dk">VH-VL </div><div class="dv">${d.vh_vl_angle.toFixed(1)}°</div></div>` : ''}
        ${d.interface_pairs !== null ? `<div class="detail-item"><div class="dk"></div><div class="dv">${d.interface_pairs}</div></div>` : ''}
        <div class="detail-item"><div class="dk"></div><div class="dv" style="font-size:12px">${d.format_type||'—'}</div></div>
      </div>
    `, true));"""

# ── Add click handler for collapsible sections ────────────────────────────────
OLD_CLOSE_DETAIL = """function closeDetail {
  document.getElementById('detail-panel').classList.remove('open');
  document.getElementById('backdrop').classList.remove('open');
  document.querySelectorAll('tbody tr').forEach(tr => tr.classList.remove('selected'));
}"""

NEW_CLOSE_DETAIL = """function closeDetail {
  document.getElementById('detail-panel').classList.remove('open');
  document.getElementById('backdrop').classList.remove('open');
  document.querySelectorAll('tbody tr').forEach(tr => tr.classList.remove('selected'));
}

// Collapsible section click handler
document.getElementById('dp-body').addEventListener('click', function(e) {
  const h3 = e.target.closest('.detail-section h3');
  if (h3) {
    h3.closest('.detail-section').classList.toggle('collapsed');
    e.stopPropagation;
  }
});"""

REPLACEMENTS = [
    (OLD_CSS, NEW_CSS),
    (OLD_EVIDENCE_BOX, NEW_EVIDENCE_BOX),
    (OLD_SECTIONS_START, NEW_SECTIONS_START),
    (OLD_ADA_SECTION, NEW_ADA_SECTION),
    (OLD_CLINICAL_SECTION, NEW_CLINICAL_SECTION),
    (OLD_MHC_SECTION, NEW_MHC_SECTION),
    (OLD_SURFACE_SECTION, NEW_SURFACE_SECTION),
    (OLD_CMC_SECTION, NEW_CMC_SECTION),
    (OLD_GERMLINE_SECTION, NEW_GERMLINE_SECTION),
    (OLD_CLOSE_DETAIL, NEW_CLOSE_DETAIL),
]

for target in TARGETS:
    txt = open(target, encoding='utf-8').read
    for old, new in REPLACEMENTS:
        if old not in txt:
            print(f"WARNING: pattern not found in {target}:\n  {old[:80]}")
        else:
            txt = txt.replace(old, new, 1)
    with open(target, 'w', encoding='utf-8') as f:
        f.write(txt)
    print(f"Updated: {target}")

print("Done.")
