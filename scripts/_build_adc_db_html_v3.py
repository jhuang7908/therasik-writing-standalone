"""
Build ADC Knowledge Base v3 — aligned with site-wide patterns
Matches: vaccine_kb_data.html (tabs + click-expand cards + select filters)
         antibody-guide.html  (collapse-bar, expand-toggle, detail-grid)
         ada_database.html    (hero, controls bar, stats)
"""
import json, html as H
from pathlib import Path

def main():
    data_dir = Path('data/adc_atlas')
    master  = json.loads((data_dir / 'adc_master_internal.json').read_text(encoding='utf-8'))
    comps   = json.loads((data_dir / 'adc_components.json').read_text(encoding='utf-8'))
    rules   = json.loads((data_dir / 'adc_design_rules.json').read_text(encoding='utf-8'))

    linkers  = [c for c in comps if 'ADC-COMP-L' in c.get('id','')]
    payloads = [c for c in comps if 'ADC-COMP-P' in c.get('id','')]
    antigens = {k:v for k,v in rules.get('antigen_properties', {}).items() if not k.startswith('_')}
    conj     = {k:v for k,v in rules.get('conjugation_technology', {}).items() if not k.startswith('_') and isinstance(v,dict)}
    experiments = rules.get('experimental_methods', {})
    payload_cls = rules.get('payload_classification', {})

    n_progs = len(master)
    n_ag    = len(antigens)
    n_pl    = len(payloads)
    n_lk    = len(linkers)
    n_cj    = len(conj)
    n_exp   = sum(len(v) for v in experiments.values())

    def esc(s):
        return H.escape(str(s)) if s else ''

    # --- classification helpers ---
    def stage_label(s):
        s = (s or '').lower()
        if 'approved' in s and 'resubmit' not in s: return 'Approved'
        if 'phase_3' in s or 'phase 3' in s: return 'Phase 3'
        if 'phase_2' in s or 'phase 2' in s: return 'Phase 2'
        if 'phase_1' in s or 'phase 1' in s: return 'Phase 1'
        if 'discontinued' in s: return 'Discontinued'
        return 'Other'

    def stage_badge_cls(label):
        return {'Approved':'badge-approved','Phase 3':'badge-phase3','Phase 2':'badge-phase2',
                'Phase 1':'badge-phase1','Discontinued':'badge-disc'}.get(label,'badge-other')

    def payload_cls_for(name):
        n = (name or '').upper()
        for cls_key, cls_info in payload_cls.items():
            if not isinstance(cls_info, dict): continue
            members = [m.upper() for m in cls_info.get('members',[])]
            if n in members:
                return cls_key.replace('_',' ').title()
        # Fuzzy fallback: keyword-based classification
        nl = n.lower()
        if any(k in nl for k in ['auristatin','mmad','tubulysin','cryptophycin','eribulin','pf-063']):
            return 'Tubulin Inhibitors'
        if any(k in nl for k in ['exatecan','belotecan','topotecan','camptothecin','sn-38','dxd']):
            return 'Topoisomerase I Inhibitors'
        if any(k in nl for k in ['amanitin','amatoxin','alpha-amanitin']):
            return 'Rna Polymerase Ii Inhibitors'
        if any(k in nl for k in ['thailanstatin','spliceostatin']):
            return 'Spliceosome Inhibitors'
        if any(k in nl for k in ['navitoclax','bcl','abt-']):
            return 'Bcl Xl Inhibitors'
        if any(k in nl for k in ['protac','degrader']):
            return 'Protac Payloads'
        if any(k in nl for k in ['thorium','astatine','radium','lead-212','bismuth','lutetium','actinium','iodine-131','yttrium']):
            return 'Radionuclides'
        if any(k in nl for k in ['tlr','sting','isac']):
            return 'Immune Stimulatory Agonists'
        if any(k in nl for k in ['gelonin','diphtheria','ricin','shiga','saporin','bouganin','pe38']):
            return 'Protein Toxins'
        if any(k in nl for k in ['dgn','pbd','calicheamicin','talirine','indolino','pyrrolobenzodiazepine','duocarmycin']):
            return 'Dna Damaging Agents'
        if any(k in nl for k in ['il-15','il15','cytokine']):
            return 'Immunomodulators'
        return 'Other'

    def linker_type_label(l):
        t = (l.get('type','') or '').lower()
        if t == 'cleavable': return 'Cleavable'
        if t == 'non-cleavable': return 'Non-cleavable'
        return 'Other'

    def conj_homogeneity(v):
        h = str(v.get('dar_homogeneity','')).lower()
        if 'very_high' in h or 'very high' in h: return 'Very High'
        if 'high' in h: return 'High'
        if 'moderate' in h: return 'Moderate'
        return 'Low'

    # --- collect select option values ---
    stages_set = sorted(set(stage_label(p.get('development_stage','')) for p in master),
                       key=lambda x: ['Approved','Phase 3','Phase 2','Phase 1','Discontinued','Other'].index(x))
    targets_set = sorted(set(p.get('target','Unknown') for p in master))
    pl_cls_set = sorted(set(payload_cls_for(p.get('name','')) for p in payloads) - {'Other'})
    lk_type_set = sorted(set(linker_type_label(l) for l in linkers))
    # Conjugation: ordered Very High → High → Moderate → Low
    _homo_order = ['Very High','High','Moderate','Low']
    cj_homo_set = sorted(set(conj_homogeneity(v) for v in conj.values()),
                        key=lambda x: _homo_order.index(x) if x in _homo_order else 99)
    # Antigen filters — multi-tag disease classification
    disease_antigen_map = rules.get('disease_antigen_map', {})
    _disease_tag_map = {}  # target_upper -> set of disease tags
    _dam_category_map = {
        'solid_tumor': 'Solid Tumor',
        'liquid_tumor': 'Liquid Tumor',
        'autoimmune': 'Autoimmune',
        'neurological': 'Neurological',
        'other': 'Other',
    }
    for disease_key, label in _dam_category_map.items():
        dmap = disease_antigen_map.get(disease_key, {})
        if isinstance(dmap, dict):
            for subtype, info in dmap.items():
                if isinstance(info, dict):
                    for t in info.get('primary', []) + info.get('secondary', []):
                        _disease_tag_map.setdefault(t.upper(), set()).add(label)

    _expr_base = {'solid_tumor': 'Solid Tumor', 'liquid_tumor': 'Liquid Tumor', 'liquid_solid': 'Solid Tumor'}
    def ag_disease_tags(name, props):
        tags = set()
        base = _expr_base.get(props.get('expression', ''), '')
        if base:
            tags.add(base)
        if props.get('expression', '') == 'liquid_solid':
            tags.add('Liquid Tumor')
        tags.update(_disease_tag_map.get(name.upper(), set()))
        if not tags:
            tags.add('Other')
        return sorted(tags)

    _ag_disease_order = ['Solid Tumor', 'Liquid Tumor', 'Autoimmune', 'Neurological', 'Other']
    ag_intern_set = ['high', 'moderate', 'low']
    ag_het_set = ['low', 'moderate', 'high']
    ag_density_set = ['high', 'moderate', 'low']
    ag_risk_set = ['low', 'moderate', 'high']

    # --- card builders ---
    def prog_card(p):
        s = stage_label(p.get('development_stage',''))
        bcls = stage_badge_cls(s)
        tgt = esc(p.get('target','Unknown'))
        payload = esc(p.get('payload_name','Unknown'))
        linker  = esc(p.get('linker_name','Unknown'))
        dar     = esc(p.get('dar_mean','?'))
        src     = esc(p.get('source_primary','N/A'))
        binder  = esc(p.get('binder_name','Unknown'))
        bfmt    = esc(p.get('binder_format','IgG1'))
        conjtech= esc(p.get('conjugation_technology','Unknown'))
        audit_raw = p.get('technical_audit','')
        if isinstance(audit_raw, dict):
            audit = esc(audit_raw.get('logic_check','') or '')
        else:
            audit = esc(str(audit_raw))
        failure = p.get('failure_analysis',{})
        is_failed = failure.get('is_failed', False)

        fail_html = ''
        if is_failed:
            fail_html = f'''<div class="info-row"><span class="info-label">Failure</span><span class="info-value" style="color:#b91c1c">{esc(failure.get("reason_category","N/A"))} — {esc(failure.get("internal_insight",""))}</span></div>'''

        search_text = f'{p.get("canonical_name","").lower()} {tgt.lower()} {p.get("company","").lower()} {payload.lower()} {s.lower()}'

        return f'''<div class="card" onclick="toggleCard(this)" data-stage="{s}" data-target="{tgt}" data-search="{esc(search_text)}">
  <div class="card-header">
    <div><div class="card-title">{esc(p.get("canonical_name","Unknown"))}</div>
    <div class="card-subtitle">{esc(p.get("company",""))}</div></div>
    <span class="badge {bcls}">{s}</span>
  </div>
  <div class="card-body">
    <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:4px"><span class="badge badge-target">{tgt}</span></div>
    <div class="cc-brief">Payload: {payload} · DAR: {dar} · Linker: {linker}</div>
    <span class="expand-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      <div class="info-row"><span class="info-label">Binder</span><span class="info-value">{binder} ({bfmt})</span></div>
      <div class="info-row"><span class="info-label">Payload</span><span class="info-value">{payload}</span></div>
      <div class="info-row"><span class="info-label">Linker</span><span class="info-value">{linker}</span></div>
      <div class="info-row"><span class="info-label">DAR</span><span class="info-value">{dar}</span></div>
      <div class="info-row"><span class="info-label">Conjugation</span><span class="info-value">{conjtech}</span></div>
      {f'<div class="info-row"><span class="info-label">Audit</span><span class="info-value">{audit}</span></div>' if audit else ''}
      <div class="info-row"><span class="info-label">Source</span><span class="info-value"><a href="https://clinicaltrials.gov/search?query={src}" target="_blank" onclick="event.stopPropagation()" style="color:var(--primary)">{src}</a></span></div>
      {fail_html}
    </div>
  </div>
</div>'''

    _conf_color = {'high':'#1a7a4a','moderate':'#b07800','low':'#cc3300'}
    _conf_label = {'high':'Evidence: High','moderate':'Evidence: Moderate','low':'⚠ Needs Expert Review'}
    def ag_card(name, props):
        tags = ag_disease_tags(name, props)
        tags_pipe = '|'.join(tags)
        badges_html = ' '.join(f'<span class="badge badge-target">{esc(t)}</span>' for t in tags)
        intern_rate = esc(props.get('internalization_rate','?'))
        density_raw = (props.get('density','?') or '?').lower()
        density_norm = 'high' if 'high' in density_raw else ('moderate' if 'moderate' in density_raw else ('low' if 'low' in density_raw else '?'))
        het_raw = (props.get('heterogeneity','?') or '?').lower()
        het_norm = 'high' if 'high' in het_raw else ('moderate' if 'moderate' in het_raw else ('low' if 'low' in het_raw else '?'))
        risk_raw = (props.get('on_target_off_tumor_risk','?') or '?').lower()
        risk_norm = 'high' if 'high' in risk_raw else ('moderate' if 'moderate' in risk_raw else ('low' if 'low' in risk_raw else '?'))
        density = esc(props.get('density','?'))
        het = esc(props.get('heterogeneity','?'))
        normal = esc(props.get('normal_tissue_expression','?'))
        offtum = esc(props.get('on_target_off_tumor_risk','?'))
        # new enrichment fields
        density_q = esc(str(props.get('density_quantitative','')))
        intern_t12 = esc(str(props.get('internalization_t12','')))
        intern_mech = esc(props.get('internalization_mechanism',''))
        recycling = esc(props.get('recycling_after_internalization',''))
        shedding = esc(props.get('shedding_rate',''))
        biomarker = esc(props.get('biomarker_assay',''))
        prolif_sens = esc(props.get('proliferation_sensitivity',''))
        conf = props.get('data_confidence','moderate')
        conf_color = _conf_color.get(conf,'#888')
        conf_label = _conf_label.get(conf,'Evidence: Moderate')
        ev_note = esc(props.get('evidence_note',''))
        refs = props.get('key_refs',[])
        refs_html = ''.join(f'<div class="info-row" style="font-size:11px;color:#666"><span class="info-label">Ref</span><span class="info-value">{esc(r)}</span></div>' for r in refs)
        needs_review = props.get('needs_expert_review', False)
        review_warn = '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:4px;padding:6px 10px;font-size:11px;color:#856404;margin-bottom:8px">⚠ Estimates from general literature context — verify against primary assay data before clinical decisions.</div>' if needs_review else ''
        search_text = f'{name.lower()} {" ".join(t.lower() for t in tags)} {intern_rate.lower()} {het.lower()} {density.lower()}'

        def ir(label, val):
            if not val or val == '?': return ''
            return f'<div class="info-row"><span class="info-label">{label}</span><span class="info-value">{val}</span></div>'

        return f'''<div class="card" onclick="toggleCard(this)" data-expr="{esc(tags_pipe)}" data-intern="{intern_rate.lower()}" data-het="{het_norm}" data-density="{density_norm}" data-risk="{risk_norm}" data-search="{esc(search_text)}">
  <div class="card-header">
    <div class="card-title">{esc(name)}</div>
    {badges_html}
  </div>
  <div class="card-body">
    <div class="cc-brief">Density: {density} · Internalization: {intern_rate} · Heterogeneity: {het}</div>
    <div style="font-size:10px;color:{conf_color};font-weight:600;margin-top:2px">{conf_label}</div>
    <span class="expand-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      {review_warn}
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:4px 0 4px">Expression &amp; Density</div>
      {ir("Density (qualitative)", density)}
      {ir("Density (quantitative)", density_q)}
      {ir("Heterogeneity", het)}
      {ir("Normal tissue", normal)}
      {ir("Off-tumor risk", offtum)}
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px">Internalization</div>
      {ir("Internalization rate", intern_rate)}
      {ir("Mechanism", intern_mech)}
      {ir("t½ internalization", intern_t12)}
      {ir("Post-internalization recycling", recycling)}
      {ir("Antigen shedding", shedding)}
      {ir("Proliferation sensitivity", prolif_sens)}
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px">Biomarker &amp; Detection</div>
      {ir("Biomarker assay / CDx", biomarker)}
      {f'<div class="info-row"><span class="info-label">Evidence note</span><span class="info-value" style="font-style:italic;color:#444">{ev_note}</span></div>' if ev_note else ''}
      {refs_html}
    </div>
  </div>
</div>'''

    def _info(label, val, style=''):
        if not val or val in ('?','N/A',''): return ''
        s = f' style="{style}"' if style else ''
        val_str = str(val)
        content = val_str if val_str.startswith('<') else esc(val_str)
        return f'<div class="info-row"{s}><span class="info-label">{label}</span><span class="info-value">{content}</span></div>'

    def _section(title):
        return f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px">{title}</div>'

    def payload_card(p):
        cls = payload_cls_for(p.get('name',''))
        mol = p.get('molecular_structure',{})
        smiles = esc(mol.get('smiles','N/A'))
        cid = mol.get('pubchem_cid','N/A')
        ref_url = mol.get('reference_url','')
        cid_html = f'<a href="{ref_url}" target="_blank" onclick="event.stopPropagation()" style="color:var(--primary)">{cid}</a>' if ref_url else esc(str(cid))
        potency = esc(p.get('potency','?'))
        ic50 = esc(str(p.get('ic50_nm','?')))
        bystander = esc(p.get('bystander_effect','?'))
        cell_cycle = esc(p.get('cell_cycle_dependency','?'))
        dlts = p.get('dlts',[])
        dlts_str = esc('; '.join(dlts)) if dlts else ''
        opt_dar = esc(str(p.get('optimal_dar_range','?')))
        logp = esc(str(p.get('log_p','?')))
        resistance = p.get('resistance_mechanisms',[])
        resistance_str = esc('; '.join(resistance)) if resistance else ''
        compat_chem = esc(str(p.get('compatible_linker_chemistry','?')))
        moa_detail = esc(p.get('moa_detail',''))
        conf = p.get('data_confidence','moderate')
        conf_color = _conf_color.get(conf,'#888')
        conf_label = _conf_label.get(conf,'Evidence: Moderate')
        ev_note = esc(p.get('evidence_note',''))
        refs = p.get('key_refs',[])
        refs_html = ''.join(f'<div class="info-row" style="font-size:11px;color:#666"><span class="info-label">Ref</span><span class="info-value">{esc(r)}</span></div>' for r in refs)
        needs_review = p.get('needs_expert_review', False)
        review_warn = '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:4px;padding:6px 10px;font-size:11px;color:#856404;margin-bottom:8px">⚠ Estimates from general literature — not verified against primary assay data. Expert validation required before clinical use.</div>' if needs_review else ''
        search_text = f'{p.get("name","").lower()} {cls.lower()} {potency.lower()} {cell_cycle.lower()}'

        return f'''<div class="card" onclick="toggleCard(this)" data-cls="{esc(cls)}" data-search="{esc(search_text)}">
  <div class="card-header">
    <div class="card-title">{esc(p.get("name","Unknown"))}</div>
    <span class="badge badge-payload">{esc(cls)}</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">IC50: {ic50} nM · Cell cycle: {cell_cycle[:30]}{"…" if len(cell_cycle)>30 else ""}</div>
    <div style="font-size:10px;color:{conf_color};font-weight:600;margin-top:2px">{conf_label}</div>
    <span class="expand-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      {review_warn}
      {_section("Mechanism & Potency")}
      {_info("Class", cls)}
      {_info("MoA", moa_detail)}
      {_info("IC50", f"{ic50} nM")}
      {_info("Potency tier", potency)}
      {_info("Cell cycle dependency", cell_cycle)}
      {_info("Bystander effect", bystander)}
      {_section("Clinical Safety")}
      {_info("Dose-limiting toxicities", dlts_str)}
      {_section("ADC Design Parameters")}
      {_info("Optimal DAR range", opt_dar)}
      {_info("log P (hydrophobicity)", logp)}
      {_info("Compatible linker chemistry", compat_chem)}
      {_info("Resistance mechanisms", resistance_str)}
      {_section("Structure & References")}
      {_info("PubChem CID", cid_html)}
      {f'<div class="info-row"><span class="info-label">Evidence note</span><span class="info-value" style="font-style:italic;color:#444">{ev_note}</span></div>' if ev_note else ''}
      {refs_html}
      <div class="info-row" style="flex-direction:column"><span class="info-label">SMILES</span><span class="info-value" style="font-family:monospace;font-size:11px;word-break:break-all;background:#f3f4f6;padding:4px 6px;border-radius:4px;margin-top:3px">{smiles}</span></div>
    </div>
  </div>
</div>'''

    def linker_card(l):
        ltype = linker_type_label(l)
        mol = l.get('molecular_structure',{})
        smiles = esc(mol.get('smiles','N/A'))
        cid = esc(str(mol.get('pubchem_cid','N/A')))
        mech = esc(l.get('mechanism','?'))
        stab = esc(l.get('stability','?'))
        plasma_t12 = esc(l.get('plasma_t12','?'))
        cleavage_enzyme = esc(l.get('cleavage_enzyme','?'))
        tumor_cleavage = esc(l.get('tumor_cleavage_efficiency','?'))
        compat_payload = esc(l.get('compatible_payload_chemistry','?'))
        conj_sites = l.get('compatible_conjugation_sites',[])
        conj_str = esc(', '.join(conj_sites)) if conj_sites else ''
        hydro = esc(l.get('hydrophilicity_note','?'))
        opt_dar = esc(l.get('optimal_dar_range_note','?'))
        conf = l.get('data_confidence','moderate')
        conf_color = _conf_color.get(conf,'#888')
        conf_label = _conf_label.get(conf,'Evidence: Moderate')
        ev_note = esc(l.get('evidence_note',''))
        refs = l.get('key_refs',[])
        refs_html = ''.join(f'<div class="info-row" style="font-size:11px;color:#666"><span class="info-label">Ref</span><span class="info-value">{esc(r)}</span></div>' for r in refs)
        needs_review = l.get('needs_expert_review', False)
        review_warn = '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:4px;padding:6px 10px;font-size:11px;color:#856404;margin-bottom:8px">⚠ Estimates from general literature — expert validation required.</div>' if needs_review else ''
        search_text = f'{l.get("name","").lower()} {ltype.lower()} {mech.lower()}'

        return f'''<div class="card" onclick="toggleCard(this)" data-ltype="{ltype}" data-search="{esc(search_text)}">
  <div class="card-header">
    <div class="card-title">{esc(l.get("name","Unknown"))}</div>
    <span class="badge badge-linker">{ltype}</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">Plasma t½: {plasma_t12[:30]}{"…" if len(plasma_t12)>30 else ""} · Enzyme: {cleavage_enzyme[:25]}{"…" if len(cleavage_enzyme)>25 else ""}</div>
    <div style="font-size:10px;color:{conf_color};font-weight:600;margin-top:2px">{conf_label}</div>
    <span class="expand-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      {review_warn}
      {_section("Cleavage & Stability")}
      {_info("Mechanism", mech)}
      {_info("Cleavage enzyme", cleavage_enzyme)}
      {_info("Plasma t½", plasma_t12)}
      {_info("Tumor cleavage efficiency", tumor_cleavage)}
      {_info("Plasma stability", stab)}
      {_section("ADC Design Compatibility")}
      {_info("Compatible payload chemistry", compat_payload)}
      {_info("Compatible conjugation sites", conj_str)}
      {_info("Hydrophilicity note", hydro)}
      {_info("Optimal DAR range", opt_dar)}
      {_section("Structure & References")}
      {_info("PubChem CID", cid)}
      {f'<div class="info-row"><span class="info-label">Evidence note</span><span class="info-value" style="font-style:italic;color:#444">{ev_note}</span></div>' if ev_note else ''}
      {refs_html}
      <div class="info-row" style="flex-direction:column"><span class="info-label">SMILES</span><span class="info-value" style="font-family:monospace;font-size:11px;word-break:break-all;background:#f3f4f6;padding:4px 6px;border-radius:4px;margin-top:3px">{smiles}</span></div>
    </div>
  </div>
</div>'''

    def conj_card(name, v):
        homo = conj_homogeneity(v)
        desc = esc(v.get('description',''))
        dar  = esc(v.get('typical_dar','?'))
        cmc  = esc(v.get('cmc_complexity','?'))
        fto  = esc(v.get('patent_freedom','?'))
        platform = esc(v.get('platform_name',''))
        dev  = esc(v.get('developer',''))
        cmc_det = esc(v.get('cmc_detail',''))
        fto_det = esc(v.get('fto_detail',''))
        refs = v.get('pmid_refs',[])
        refs_html = ''.join(f'<div class="info-row" style="font-size:11px;color:#666"><span class="info-label">Ref</span><span class="info-value">{esc(r)}</span></div>' for r in refs)

        search_text = f'{name.lower()} {desc.lower()} {fto.lower()} {homo.lower()} {platform.lower()} {dev.lower()}'

        return f'''<div class="card" onclick="toggleCard(this)" data-homo="{homo}" data-search="{esc(search_text)}">
  <div class="card-header">
    <div>
      <div class="card-title">{esc(name.replace("_"," ").title())}</div>
      {f'<div class="card-subtitle" style="font-size:11px;color:var(--primary)">{platform} — {dev}</div>' if platform else ''}
    </div>
    <span class="badge badge-conj">{homo}</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">DAR: {dar} · {desc[:80]}{'…' if len(desc)>80 else ''}</div>
    <span class="expand-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      {_section("Technology Profile")}
      {_info("Description", desc)}
      {_info("Typical DAR", dar)}
      {_info("Homogeneity", homo)}
      {_section("CMC & Patent")}
      {_info("CMC Complexity", cmc)}
      {_info("CMC Detail", cmc_det)}
      {_info("Patent / FTO", fto)}
      {_info("FTO Detail", fto_det)}
      {_section("References")}
      {refs_html}
    </div>
  </div>
</div>'''

    def exp_card(assay_name, details):
        methods = esc(', '.join(details.get('methods',[])))
        analytes = esc(', '.join(details.get('analytes',[]))) if 'analytes' in details else ''
        purpose = esc(details.get('purpose',''))
        proto = esc(details.get('protocol_summary',''))
        cell = esc(details.get('cell_line_recommendations',''))
        sens = esc(details.get('readout_sensitivity',''))
        refs = details.get('pmid_refs',[])
        refs_html = ''.join(f'<div class="info-row" style="font-size:11px;color:#666"><span class="info-label">Ref</span><span class="info-value">{esc(r)}</span></div>' for r in refs)

        return f'''<div class="card" onclick="toggleCard(this)" data-search="{assay_name.lower()} {methods.lower()}">
  <div class="card-header">
    <div class="card-title">{esc(assay_name.replace("_"," ").title())}</div>
  </div>
  <div class="card-body">
    <div class="cc-brief">{purpose[:120]}{'…' if len(purpose)>120 else ''}</div>
    <span class="expand-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      {_section("Assay Overview")}
      {_info("Purpose", purpose)}
      {_info("Methods", methods)}
      {f'<div class="info-row"><span class="info-label">Analytes</span><span class="info-value">{analytes}</span></div>' if analytes else ''}
      {_section("Protocol & Sensitivity")}
      {_info("Protocol Summary", proto)}
      {_info("Cell Lines", cell)}
      {_info("Sensitivity", sens)}
      {_section("References")}
      {refs_html}
    </div>
  </div>
</div>'''

    # --- Stage option tags ---
    stage_opts = '\n'.join(f'    <option value="{s}">{s}</option>' for s in stages_set)
    target_opts = '\n'.join(f'    <option value="{t}">{t}</option>' for t in targets_set[:30])
    plcls_opts = '\n'.join(f'    <option value="{c}">{c}</option>' for c in pl_cls_set)
    lktype_opts = '\n'.join(f'    <option value="{t}">{t}</option>' for t in lk_type_set)
    cjhomo_opts = '\n'.join(f'    <option value="{h}">{h}</option>' for h in cj_homo_set)
    ag_expr_opts = '\n'.join(f'    <option value="{e}">{e}</option>' for e in _ag_disease_order)
    ag_intern_opts = '\n'.join(f'    <option value="{i}">{i.title()}</option>' for i in ag_intern_set)
    ag_het_opts = '\n'.join(f'    <option value="{h}">{h.title()}</option>' for h in ag_het_set)
    ag_density_opts = '\n'.join(f'    <option value="{d}">{d.title()}</option>' for d in ag_density_set)
    ag_risk_opts = '\n'.join(f'    <option value="{r}">{r.title()}</option>' for r in ag_risk_set)

    # --- Build program cards ---
    prog_cards = '\n'.join(prog_card(p) for p in master)
    ag_cards = '\n'.join(ag_card(n, p) for n, p in antigens.items())
    pl_cards = '\n'.join(payload_card(p) for p in payloads)
    lk_cards = '\n'.join(linker_card(l) for l in linkers)
    _homo_sort_key = {'Very High':0,'High':1,'Moderate':2,'Low':3}
    cj_sorted = sorted(conj.items(), key=lambda kv: _homo_sort_key.get(conj_homogeneity(kv[1]),9))
    cj_cards = '\n'.join(conj_card(n, v) for n, v in cj_sorted)

    exp_cards_html = ''
    for cat, assays in experiments.items():
        exp_cards_html += f'<h3 class="section-title" style="font-size:20px;margin:20px 0 8px">{esc(cat.replace("_"," ").title())}</h3>\n'
        for aname, det in assays.items():
            exp_cards_html += exp_card(aname, det) + '\n'

    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="InSynBio ADC Knowledge Base — {n_progs} clinical programs, {n_ag} target antigens, {n_pl} payloads, {n_lk} linkers, {n_cj} conjugation technologies with expandable detail cards.">
<meta name="robots" content="noai, noimageai">
<meta name="AI-Training" content="opt-out">
<link rel="canonical" href="https://www.insynbio.com/adc_database.html">
<title>ADC Knowledge Base | InSynBio</title>
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500&display=swap" rel="stylesheet">
<style>
  :root {{ --primary:#0d9488; --primary-dark:#0f766e; --text:#111827; --text-muted:#4b5563; --border:#e5e7eb; --bg:#ffffff; --bg-alt:#f9fafb; --bg-alt2:#f3f4f6; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; font-size:15px; line-height:1.6; color:var(--text); background:var(--bg); -webkit-font-smoothing:antialiased; padding-top:60px; }}

  /* ── Top bar — matches vaccine_kb / antibody-guide ── */
  .top-bar {{ display:flex; align-items:center; justify-content:space-between; padding:10px 28px; background:rgba(255,255,255,0.95); backdrop-filter:blur(12px); border-bottom:2px solid rgba(13,148,136,0.1); position:fixed; width:100%; top:0; z-index:2000; }}
  .top-bar .brand {{ font-family:'Cormorant Garamond',serif; font-weight:700; font-size:22px; color:#1f2937; text-decoration:none; display:flex; align-items:center; gap:8px; }}
  .top-bar .brand span {{ color:#0d9488; }}
  .top-bar nav {{ display:flex; gap:6px; align-items:center; }}
  .top-bar nav a {{ padding:6px 14px; font-size:13px; color:var(--text-muted); text-decoration:none; border-radius:16px; font-weight:500; transition:all .15s; }}
  .top-bar nav a:hover {{ color:var(--primary); background:rgba(13,148,136,0.06); }}
  .top-bar nav a.back {{ color:var(--primary); background:rgba(13,148,136,0.08); border:1px solid rgba(13,148,136,0.2); }}

  /* ── Page layout ── */
  .page {{ max-width:1200px; margin:0 auto; padding:40px 32px 80px; }}

  /* ── Page header — matches vaccine_kb ── */
  .page-header {{ margin-bottom:32px; }}
  .page-header h1 {{ font-family:'Cormorant Garamond',serif; font-size:36px; font-weight:700; color:#111827; margin:0 0 8px; letter-spacing:-.02em; }}
  .page-header p {{ font-size:15px; color:var(--text-muted); margin:0; max-width:750px; line-height:1.7; }}
  .page-card-hint {{ font-size:14px; color:#4b5563; margin:12px 0 0; max-width:720px; line-height:1.6; padding:12px 14px; background:rgba(13,148,136,.06); border:1px solid rgba(13,148,136,.12); border-radius:10px; }}
  .page-card-hint a {{ color:var(--primary); font-weight:600; text-decoration:none; }}

  /* ── Tab bar — matches vaccine_kb ── */
  .tabs-bar {{ display:flex; gap:4px; flex-wrap:wrap; border-bottom:2px solid var(--border); margin-bottom:28px; padding-bottom:0; }}
  .tab-btn {{ padding:8px 18px; font-size:13.5px; font-weight:600; color:var(--text-muted); background:none; border:none; border-bottom:2px solid transparent; cursor:pointer; transition:all .15s; margin-bottom:-2px; border-radius:6px 6px 0 0; }}
  .tab-btn:hover {{ color:var(--primary); background:rgba(13,148,136,0.04); }}
  .tab-btn.active {{ color:var(--primary); border-bottom-color:var(--primary); background:rgba(13,148,136,0.05); }}
  .tab-panel {{ display:none; }}
  .tab-panel.active {{ display:block; }}

  /* ── Controls per tab — matches vaccine_kb / antibody-guide ── */
  .ctrl-row {{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:20px; }}
  .search-box {{ padding:8px 14px; border:1px solid var(--border); border-radius:8px; font-size:13.5px; width:100%; max-width:340px; color:var(--text); transition:border-color .2s; }}
  .search-box:focus {{ outline:none; border-color:var(--primary); box-shadow:0 0 0 3px rgba(13,148,136,.1); }}
  .filter-sel {{ padding:7px 12px; border:1px solid var(--border); border-radius:8px; font-size:13px; color:var(--text); background:#fff; cursor:pointer; }}
  .result-count {{ margin-left:auto; font-size:12px; color:var(--text-muted); font-weight:500; }}

  /* ── Section titles — matches vaccine_kb ── */
  .section-title {{ font-family:'Cormorant Garamond',serif; font-size:24px; font-weight:600; color:var(--text); margin:0 0 6px; }}
  .section-desc {{ color:var(--text-muted); font-size:13.5px; margin-bottom:16px; max-width:700px; }}

  /* ── Card grid — matches vaccine_kb (280px min) ── */
  .card-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:14px; }}

  /* ── Cards — matches vaccine_kb + antibody-guide expand pattern ── */
  .card {{ background:#fff; border:1px solid var(--border); border-radius:10px; overflow:hidden; transition:box-shadow .15s,border-color .15s; cursor:pointer; }}
  .card:hover {{ border-color:var(--primary); box-shadow:0 4px 14px rgba(13,148,136,.09); }}
  .card.expanded {{ border-color:var(--primary); box-shadow:0 4px 20px rgba(13,148,136,.12); }}
  .card.hidden {{ display:none; }}
  .card-header {{ display:flex; justify-content:space-between; align-items:flex-start; padding:12px 14px 8px; border-bottom:1px solid var(--border); }}
  .card-title {{ font-size:14px; font-weight:700; color:var(--text); line-height:1.3; }}
  .card-subtitle {{ font-size:11px; color:var(--text-muted); margin-top:2px; }}
  .card-body {{ padding:10px 14px 12px; }}
  .cc-brief {{ font-size:13px; color:var(--text-muted); line-height:1.4; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
  .card.expanded .cc-brief {{ display:block; -webkit-line-clamp:unset; overflow:visible; }}

  /* ── Expand / collapse — exact match to vaccine_kb + antibody-guide ── */
  .cc-detail {{ display:none; margin-top:12px; padding-top:12px; border-top:1px solid var(--border); }}
  .card.expanded .cc-detail {{ display:block; }}
  .cc-detail .collapse-bar {{ height:3px; background:#e5f7f5; border-radius:2px; margin-bottom:12px; overflow:hidden; }}
  .cc-detail .collapse-progress {{ height:100%; width:100%; background:var(--primary); border-radius:2px; transition:none; }}
  .card.countdown .cc-detail .collapse-progress {{ transition:width 5s linear; width:0% !important; }}
  .expand-toggle {{ font-size:10px; color:var(--primary); font-weight:600; float:right; margin-top:4px; text-transform:uppercase; letter-spacing:0.5px; }}
  .card .expand-toggle::after {{ content:'▼ Expand'; }}
  .card.expanded .expand-toggle::after {{ content:'▲ Collapse'; }}

  /* ── Info rows — matches vaccine_kb ── */
  .info-row {{ display:flex; gap:6px; margin-bottom:5px; align-items:baseline; }}
  .info-label {{ font-size:10.5px; font-weight:600; color:var(--text-muted); text-transform:uppercase; letter-spacing:.5px; min-width:80px; flex-shrink:0; }}
  .info-value {{ font-size:12.5px; color:var(--text); line-height:1.5; word-break:break-word; }}
  .info-value a {{ color:var(--primary); text-decoration:none; }}
  .info-value a:hover {{ text-decoration:underline; }}

  /* ── Badges — matches site-wide patterns ── */
  .badge {{ display:inline-block; font-size:10px; font-weight:600; padding:2px 7px; border-radius:16px; border:1px solid transparent; white-space:nowrap; }}
  .badge-approved {{ background:#d1fae5; color:#065f46; border-color:#a7f3d0; }}
  .badge-phase3 {{ background:#dbeafe; color:#1e40af; border-color:#bfdbfe; }}
  .badge-phase2 {{ background:#fef3c7; color:#92400e; border-color:#fde68a; }}
  .badge-phase1 {{ background:#fee2e2; color:#991b1b; border-color:#fecaca; }}
  .badge-disc {{ background:#f3f4f6; color:#6b7280; }}
  .badge-other {{ background:#f3f4f6; color:#6b7280; }}
  .badge-target {{ background:#f0fdfa; color:var(--primary-dark); border-color:rgba(13,148,136,.2); }}
  .badge-payload {{ background:#fef3c7; color:#92400e; border-color:#fde68a; }}
  .badge-linker {{ background:#ecfdf5; color:#065f46; border-color:#a7f3d0; }}
  .badge-conj {{ background:#ede9fe; color:#5b21b6; border-color:#ddd6fe; }}

  @media(max-width:700px) {{ .card-grid {{ grid-template-columns:1fr; }} .page {{ padding:24px 16px 60px; }} }}
</style>
</head>
<body>

<!-- ── Top bar ── -->
<div class="top-bar">
  <a href="InSynBio_ADC_Design_Page.html" class="brand">
    <svg width="24" height="20" viewBox="0 0 32 30" fill="none"><path d="M16 2L2 10V22L16 28L30 22V10L16 2Z" fill="#0d9488" fill-opacity="0.08" stroke="#0d9488" stroke-width="1.5" stroke-opacity="0.5"/><path d="M14.5 24 V 16" stroke="#0d9488" stroke-width="2.5" stroke-linecap="round"/><path d="M17.5 24 V 16" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round"/><line x1="13" y1="19" x2="19" y2="19" stroke="#9ca3af" stroke-width="1.5" stroke-linecap="round"/><line x1="13" y1="21" x2="19" y2="21" stroke="#9ca3af" stroke-width="1.5" stroke-linecap="round"/></svg>
    In<span>Syn</span>Bio
  </a>
  <nav>
    <a href="InSynBio_ADC_Design_Page.html" class="back">&larr; ADC Design Service</a>
    <a href="index.html">Home</a>
    <a href="InSynBio_Antibody_Developability_Assessment_Page.html">Antibody</a>
    <a href="InSynBio_CART_Design_Page.html">CAR-T</a>
  </nav>
</div>

<div class="page">
  <!-- Page header — same structure as vaccine_kb and antibody-guide -->
  <div class="page-header">
    <h1>ADC Knowledge Base</h1>
    <p>Comprehensive reference database covering <strong>{n_progs} clinical programs</strong>, <strong>{n_ag} target antigens</strong>, <strong>{n_pl} payloads (11 mechanism classes)</strong>, <strong>{n_lk} linkers</strong>, and <strong>{n_cj} conjugation technologies</strong> — with chemical structures, patent status, and failure analysis.</p>
    <p class="page-card-hint">Each entry is an <strong>expandable card</strong> (same pattern as the <a href="antibody-guide.html">antibody engineering reference</a> and <a href="vaccine_kb_data.html">vaccine knowledge base</a>): <strong>click the card</strong> to show full details; a teal accent bar appears above the detail block. The control reads &ldquo;&#x25BC; Expand&rdquo; / &ldquo;&#x25B2; Collapse&rdquo;.</p>
  </div>

  <!-- Tab bar — horizontal underline, same as vaccine_kb -->
  <div class="tabs-bar">
    <button class="tab-btn active" data-tab="programs">Clinical Programs ({n_progs})</button>
    <button class="tab-btn" data-tab="antigens">Target Antigens ({n_ag})</button>
    <button class="tab-btn" data-tab="payloads">Payloads ({n_pl})</button>
    <button class="tab-btn" data-tab="linkers">Linkers ({n_lk})</button>
    <button class="tab-btn" data-tab="conjugation">Conjugation Tech ({n_cj})</button>
    <button class="tab-btn" data-tab="experiments">Validation Assays ({n_exp})</button>
  </div>

  <!-- ═══ PROGRAMS ═══ -->
  <div class="tab-panel active" id="panel-programs">
    <h2 class="section-title">Clinical ADC Programs</h2>
    <p class="section-desc">Approved and late-stage clinical ADC programs with target, payload, linker, DAR, conjugation technology, and trial references. Includes failure analysis for discontinued programs.</p>
    <div class="ctrl-row">
      <input class="search-box" id="searchPrograms" type="text" placeholder="Search name, target, company, payload…">
      <select class="filter-sel" id="filterStage">
        <option value="">All stages</option>
{stage_opts}
      </select>
      <select class="filter-sel" id="filterTarget">
        <option value="">All targets</option>
{target_opts}
      </select>
      <span class="result-count" id="countPrograms"></span>
    </div>
    <div class="card-grid" id="gridPrograms">
{prog_cards}
    </div>
  </div>

  <!-- ═══ ANTIGENS ═══ -->
  <div class="tab-panel" id="panel-antigens">
    <h2 class="section-title">Target Antigen Profiles</h2>
    <p class="section-desc">Detailed mapping of expression density, internalization rates, heterogeneity, and normal tissue expression for {n_ag} ADC-relevant targets.</p>
    <div class="ctrl-row">
      <input class="search-box" id="searchAntigens" type="text" placeholder="Search antigen name, disease type…">
      <select class="filter-sel" id="filterAgExpr">
        <option value="">All disease types</option>
{ag_expr_opts}
      </select>
      <span class="result-count" id="countAntigens"></span>
    </div>
    <div class="ctrl-row" style="margin-top:-10px">
      <select class="filter-sel" id="filterAgIntern">
        <option value="">Internalization: All</option>
{ag_intern_opts}
      </select>
      <select class="filter-sel" id="filterAgHet">
        <option value="">Heterogeneity: All</option>
{ag_het_opts}
      </select>
      <select class="filter-sel" id="filterAgDensity">
        <option value="">Density: All</option>
{ag_density_opts}
      </select>
      <select class="filter-sel" id="filterAgRisk">
        <option value="">Off-Tumor Risk: All</option>
{ag_risk_opts}
      </select>
    </div>
    <div class="card-grid" id="gridAntigens">
{ag_cards}
    </div>
  </div>

  <!-- ═══ PAYLOADS ═══ -->
  <div class="tab-panel" id="panel-payloads">
    <h2 class="section-title">Payload Molecules</h2>
    <p class="section-desc">From classic cytotoxins (MMAE, DXd) to emerging modalities (PROTACs, Radionuclides, ISACs). Includes SMILES structures and PubChem links.</p>
    <div class="ctrl-row">
      <input class="search-box" id="searchPayloads" type="text" placeholder="Search payload name, class…">
      <select class="filter-sel" id="filterPayloadCls">
        <option value="">All mechanism classes</option>
{plcls_opts}
      </select>
      <span class="result-count" id="countPayloads"></span>
    </div>
    <div class="card-grid" id="gridPayloads">
{pl_cards}
    </div>
  </div>

  <!-- ═══ LINKERS ═══ -->
  <div class="tab-panel" id="panel-linkers">
    <h2 class="section-title">Linker Chemistry</h2>
    <p class="section-desc">Cleavable (protease, pH, disulfide) and non-cleavable linkers matched to antigen internalization kinetics, with chemical structures.</p>
    <div class="ctrl-row">
      <input class="search-box" id="searchLinkers" type="text" placeholder="Search linker name, mechanism…">
      <select class="filter-sel" id="filterLinkerType">
        <option value="">All types</option>
{lktype_opts}
      </select>
      <span class="result-count" id="countLinkers"></span>
    </div>
    <div class="card-grid" id="gridLinkers">
{lk_cards}
    </div>
  </div>

  <!-- ═══ CONJUGATION ═══ -->
  <div class="tab-panel" id="panel-conjugation">
    <h2 class="section-title">Conjugation Technologies</h2>
    <p class="section-desc">From stochastic cysteine to site-specific enzymatic (FGE, Sortase) and glycan remodeling — DAR homogeneity, CMC complexity, and patent / FTO analysis.</p>
    <div class="ctrl-row">
      <input class="search-box" id="searchConj" type="text" placeholder="Search technology, patent…">
      <select class="filter-sel" id="filterConjHomo">
        <option value="">All homogeneity</option>
{cjhomo_opts}
      </select>
      <span class="result-count" id="countConj"></span>
    </div>
    <div class="card-grid" id="gridConj">
{cj_cards}
    </div>
  </div>

  <!-- ═══ EXPERIMENTS ═══ -->
  <div class="tab-panel" id="panel-experiments">
    <h2 class="section-title">Validation Assay Recommendations</h2>
    <p class="section-desc">In vitro and in vivo experimental methods for ADC characterization, from binding assays to PDX efficacy models.</p>
    <div class="ctrl-row">
      <input class="search-box" id="searchExp" type="text" placeholder="Search assay, method…">
      <span class="result-count" id="countExp"></span>
    </div>
    <div id="gridExp">
{exp_cards_html}
    </div>
  </div>
</div>

<script>
/* ── Card toggle with auto-collapse countdown ── */
function toggleCard(card) {{
  var wasExpanded = card.classList.contains('expanded');
  card.classList.toggle('expanded');
  clearCountdown(card);
  if (wasExpanded) {{
    card.classList.remove('countdown');
    var bar = card.querySelector('.collapse-progress');
    if (bar) bar.style.width = '100%';
  }}
}}

function clearCountdown(card) {{
  if (card._collapseTimer) {{ clearTimeout(card._collapseTimer); card._collapseTimer = null; }}
  card.classList.remove('countdown');
  var bar = card.querySelector('.collapse-progress');
  if (bar) {{ bar.style.transition = 'none'; bar.style.width = '100%'; }}
}}

function startCountdown(card) {{
  if (!card.classList.contains('expanded')) return;
  clearCountdown(card);
  var bar = card.querySelector('.collapse-progress');
  if (bar) {{
    bar.style.transition = 'none';
    bar.style.width = '100%';
    bar.offsetHeight; /* force reflow — ensures 100% is painted */
    bar.style.transition = '';  /* clear inline override so CSS rule takes effect */
    bar.style.width = '';       /* clear inline override so CSS !important width:0% works */
    card.classList.add('countdown');
  }}
  card._collapseTimer = setTimeout(function() {{
    card.classList.remove('expanded','countdown');
    if (bar) {{ bar.style.transition = 'none'; bar.style.width = '100%'; }}
  }}, 5000);
}}

document.addEventListener('mouseover', function(e) {{
  var card = e.target.closest('.card.expanded');
  if (card) clearCountdown(card);
}});
document.addEventListener('mouseout', function(e) {{
  var card = e.target.closest('.card.expanded');
  if (card && !card.contains(e.relatedTarget)) startCountdown(card);
}});

/* ── Tab switching — exact same pattern as vaccine_kb ── */
document.querySelectorAll('.tab-btn').forEach(function(btn) {{
  btn.addEventListener('click', function() {{
    document.querySelectorAll('.tab-btn').forEach(function(b) {{ b.classList.remove('active'); }});
    document.querySelectorAll('.tab-panel').forEach(function(p) {{ p.classList.remove('active'); }});
    btn.classList.add('active');
    var panel = document.getElementById('panel-' + btn.dataset.tab);
    if (panel) panel.classList.add('active');
    filterActiveTab();
  }});
}});

/* ── Generic filter function ── */
function filterGrid(gridId, searchId, countId, filterConfigs) {{
  var q = document.getElementById(searchId).value.toLowerCase();
  var grid = document.getElementById(gridId);
  if (!grid) return;
  var cards = grid.querySelectorAll('.card');
  var n = 0;
  cards.forEach(function(card) {{
    var matchSearch = !q || (card.dataset.search || '').includes(q);
    var matchFilters = true;
    if (filterConfigs) {{
      filterConfigs.forEach(function(fc) {{
        var val = document.getElementById(fc.selectId).value;
        if (val && card.getAttribute(fc.attr) !== val) matchFilters = false;
      }});
    }}
    var show = matchSearch && matchFilters;
    card.classList.toggle('hidden', !show);
    if (show) n++;
  }});
  document.getElementById(countId).textContent = n + ' entries';
}}

function filterActiveTab() {{
  var activeTab = document.querySelector('.tab-btn.active').dataset.tab;
  switch (activeTab) {{
    case 'programs':
      filterGrid('gridPrograms', 'searchPrograms', 'countPrograms', [
        {{ selectId: 'filterStage', attr: 'data-stage' }},
        {{ selectId: 'filterTarget', attr: 'data-target' }}
      ]);
      break;
    case 'antigens':
      filterGridAntigens();
      break;
    case 'payloads':
      filterGrid('gridPayloads', 'searchPayloads', 'countPayloads', [
        {{ selectId: 'filterPayloadCls', attr: 'data-cls' }}
      ]);
      break;
    case 'linkers':
      filterGrid('gridLinkers', 'searchLinkers', 'countLinkers', [
        {{ selectId: 'filterLinkerType', attr: 'data-ltype' }}
      ]);
      break;
    case 'conjugation':
      filterGrid('gridConj', 'searchConj', 'countConj', [
        {{ selectId: 'filterConjHomo', attr: 'data-homo' }}
      ]);
      break;
    case 'experiments':
      var q = document.getElementById('searchExp').value.toLowerCase();
      var cards = document.querySelectorAll('#gridExp .card');
      var n = 0;
      cards.forEach(function(c) {{
        var show = !q || (c.dataset.search || '').includes(q);
        c.classList.toggle('hidden', !show);
        if (show) n++;
      }});
      document.getElementById('countExp').textContent = n + ' assays';
      break;
  }}
}}

/* ── Antigen custom filter (pipe-delimited multi-tag disease match) ── */
function filterGridAntigens() {{
  var q = document.getElementById('searchAntigens').value.toLowerCase();
  var fExpr = document.getElementById('filterAgExpr').value;
  var fIntern = document.getElementById('filterAgIntern').value;
  var fHet = document.getElementById('filterAgHet').value;
  var fDensity = document.getElementById('filterAgDensity').value;
  var fRisk = document.getElementById('filterAgRisk').value;
  var grid = document.getElementById('gridAntigens');
  var n = 0;
  grid.querySelectorAll('.card').forEach(function(card) {{
    var ok = true;
    if (q && !(card.dataset.search || '').includes(q)) ok = false;
    if (fExpr) {{
      var tags = (card.dataset.expr || '').split('|');
      if (tags.indexOf(fExpr) === -1) ok = false;
    }}
    if (fIntern && card.dataset.intern !== fIntern) ok = false;
    if (fHet && card.dataset.het !== fHet) ok = false;
    if (fDensity && card.dataset.density !== fDensity) ok = false;
    if (fRisk && card.dataset.risk !== fRisk) ok = false;
    card.classList.toggle('hidden', !ok);
    if (ok) n++;
  }});
  document.getElementById('countAntigens').textContent = n + ' entries';
}}

/* ── Bind events ── */
['searchPrograms','searchAntigens','searchPayloads','searchLinkers','searchConj','searchExp'].forEach(function(id) {{
  document.getElementById(id).addEventListener('input', filterActiveTab);
}});
['filterStage','filterTarget','filterPayloadCls','filterLinkerType','filterConjHomo','filterAgExpr','filterAgIntern','filterAgHet','filterAgDensity','filterAgRisk'].forEach(function(id) {{
  document.getElementById(id).addEventListener('change', filterActiveTab);
}});

/* ── Hash-based deep linking — same as vaccine_kb ── */
var hash = window.location.hash.replace('#','');
if (hash) {{
  var btn = document.querySelector('.tab-btn[data-tab="' + hash + '"]');
  if (btn) btn.click();
}}

/* ── Init ── */
filterActiveTab();
</script>
</body>
</html>'''

    out_path = Path('docs/adc_database.html')
    out_path.write_text(page, encoding='utf-8')
    print(f"Generated {out_path}  ({out_path.stat().st_size//1024} KB)")

if __name__ == '__main__':
    main()
