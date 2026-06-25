"""
Build ADC  v3 — aligned with site-wide patterns
Matches: vaccine_kb_data.html (tabs + click-exp cards + select filters)
         antibody-guide.html  (collapse-bar, exp-toggle, detail-grid)
         ada_database.html    (hero, controls bar, stats)
"""
import json, html as H
from pathlib import Path

def main():
    data_dir = Path('data/adc_atlas')
    master  = json.loads((data_dir / 'adc_master_internal.json').read_text(encoding='utf-8'))
    comps   = json.loads((data_dir / 'adc_components.json').read_text(encoding='utf-8'))
    rules   = json.loads((data_dir / 'adc_design_rules.json').read_text(encoding='utf-8'))

      = [c for c in comps if 'ADC-COMP-L' in c.get('id','')]
     = [c for c in comps if 'ADC-COMP-P' in c.get('id','')]
    antigens = {k:v for k,v in rules.get('antigen_properties', {}).items() if not k.startswith('_')}
    conj     = {k:v for k,v in rules.get('conjugation_technology', {}).items() if not k.startswith('_') and isinstance(v,dict)}
    experiments = rules.get('experimental_methods', {})
    payload_cls = rules.get('payload_classification', {})

    n_progs = len(master)
    n_ag    = len(antigens)
    n_pl    = len()
    n_lk    = len()
    n_cj    = len(conj)
    n_exp   = sum(len(v) for v in experiments.values())

    def esc(s):
        return H.escape(str(s)) if s else ''

    # --- classification helpers ---
    def stage_label(s):
        s = (s or '').lower()
        if 'approved' in s and 'resubmit' not in s: return ''
        if 'phase_3' in s or 'phase 3' in s: return ' 3 '
        if 'phase_2' in s or 'phase 2' in s: return ' 2 '
        if 'phase_1' in s or 'phase 1' in s: return ' 1 '
        if 'discontinued' in s: return ''
        return ''

    def stage_badge_cls(label):
        return {'':'badge-approved',' 3 ':'badge-phase3',' 2 ':'badge-phase2',
                ' 1 ':'badge-phase1','':'badge-disc'}.get(label,'badge-other')

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
            return ''
        if any(k in nl for k in ['exatecan','belotecan','topotecan','camptothecin','sn-38','dxd']):
            return ' I '
        if any(k in nl for k in ['amanitin','amatoxin','alpha-amanitin']):
            return 'RNA  II '
        if any(k in nl for k in ['thailanstatin','spliceostatin']):
            return ''
        if any(k in nl for k in ['navitoclax','bcl','abt-']):
            return 'Bcl-xL '
        if any(k in nl for k in ['protac','degrader']):
            return 'PROTAC '
        if any(k in nl for k in ['thorium','astatine','radium','lead-212','bismuth','lutetium','actinium','iodine-131','yttrium']):
            return ''
        if any(k in nl for k in ['tlr','sting','isac']):
            return ''
        if any(k in nl for k in ['gelonin','diphtheria','ricin','shiga','saporin','bouganin','pe38']):
            return ''
        if any(k in nl for k in ['dgn','pbd','calicheamicin','talirine','indolino','pyrrolobenzodiazepine','duocarmycin']):
            return 'DNA '
        if any(k in nl for k in ['il-15','il15','cytokine']):
            return ''
        return ''

    def linker_type_label(l):
        t = (l.get('type','') or '').lower()
        if t == 'cleavable': return ''
        if t == 'non-cleavable': return ''
        return ''

    def conj_homogeneity(v):
        h = str(v.get('dar_homogeneity','')).lower()
        if 'very_high' in h or 'very high' in h: return ''
        if 'high' in h: return ''
        if 'moderate' in h: return ''
        return ''

    # --- collect select option values ---
    stages_set = sorted(set(stage_label(p.get('development_stage','')) for p in master),
                       key=lambda x: ['',' 3 ',' 2 ',' 1 ','',''].index(x))
    targets_set = sorted(set(p.get('target','Unknown') for p in master))
    pl_cls_set = sorted(set(payload_cls_for(p.get('name','')) for p in ) - {''})
    lk_type_set = sorted(set(linker_type_label(l) for l in ))
    # Conjugation: ordered Very High → High → Moderate → Low
    _homo_order = ['','','','']
    cj_homo_set = sorted(set(conj_homogeneity(v) for v in conj.values()),
                        key=lambda x: _homo_order.index(x) if x in _homo_order else 99)
    # Antigen filters — multi-tag disease classification
    disease_antigen_map = rules.get('disease_antigen_map', {})
    _disease_tag_map = {}  # target_upper -> set of disease tags
    _dam_category_map = {
        'solid_tumor': '',
        'liquid_tumor': '',
        'autoimmune': '',
        'neurological': '',
        'other': '',
    }
    for disease_key, label in _dam_category_map.items():
        dmap = disease_antigen_map.get(disease_key, {})
        if isinstance(dmap, dict):
            for subtype, info in dmap.items():
                if isinstance(info, dict):
                    for t in info.get('primary', []) + info.get('secondary', []):
                        _disease_tag_map.setdefault(t.upper(), set()).add(label)

    _expr_base = {'solid_tumor': '', 'liquid_tumor': '', 'liquid_solid': ''}
    def ag_disease_tags(name, props):
        tags = set()
        base = _expr_base.get(props.get('expression', ''), '')
        if base:
            tags.add(base)
        if props.get('expression', '') == 'liquid_solid':
            tags.add('')
        tags.update(_disease_tag_map.get(name.upper(), set()))
        if not tags:
            tags.add('')
        return sorted(tags)

    _ag_disease_order = ['', '', '', '', '']
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
        
        # Clinical data enrichment
        clinical = p.get("clinical_data", {})
        eff = clinical.get("efficacy", {})
        safety = clinical.get("safety", {})
        immuno = clinical.get("immunogenicity", {})
        dose = clinical.get("dose", {})
        
        efficacy_html = ''
        if eff:
            orr = esc(eff.get('orr', 'TBD'))
            pfs = esc(eff.get('pfs', 'TBD'))
            efficacy_html = f'<div class="info-row"><span class="info-label"> (ORR/PFS)</span><span class="info-value">ORR: {orr} | PFS: {pfs}</span></div>'
            
        safety_html = ''
        if safety:
            ae_rate = esc(safety.get('grade3_plus_ae_rate', 'TBD'))
            common_ae = esc(', '.join(safety.get('common_ae', [])) if safety.get('common_ae') else 'TBD')
            safety_html = f'<div class="info-row"><span class="info-label"></span><span class="info-value">3+ AE: {ae_rate} | : {common_ae}</span></div>'

        immuno_html = ''
        if immuno:
            ada = esc(immuno.get('ada_incidence', 'TBD'))
            immuno_html = f'<div class="info-row"><span class="info-label"> (ADA)</span><span class="info-value">ADA : {ada}</span></div>'
            
        dose_html = ''
        if dose:
            rpd = esc(dose.get('recommended_dose', 'TBD'))
            sched = esc(dose.get('schedule', 'TBD'))
            dose_html = f'<div class="info-row"><span class="info-label"></span><span class="info-value">{rpd} ({sched})</span></div>'

        audit_raw = p.get('technical_audit','')
        if isinstance(audit_raw, dict):
            audit = esc(audit_raw.get('logic_check','') or '')
        else:
            audit = esc(str(audit_raw))
        failure = p.get('failure_analysis',{})
        is_failed = failure.get('is_failed', False)

        fail_html = ''
        if is_failed:
            fail_html = f'''<div class="info-row"><span class="info-label"></span><span class="info-value" style="color:#b91c1c">{esc(failure.get("reason_category","N/A"))} — {esc(failure.get("internal_insight",""))}</span></div>'''

        search_text = f'{p.get("canonical_name","").lower()} {tgt.lower()} {p.get("company","").lower()} {payload.lower()} {s.lower()}'

        return f'''<div class="card" onclick="toggleCard(this)" data-stage="{s}" data-target="{tgt}" data-search="{esc(search_text)}">
  <div class="card-header">
    <div><div class="card-title">{esc(p.get("canonical_name","Unknown"))}</div>
    <div class="card-subtitle">{esc(p.get("company",""))}</div></div>
    <span class="badge {bcls}">{s}</span>
  </div>
  <div class="card-body">
    <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:4px"><span class="badge badge-target">{tgt}</span></div>
    <div class="cc-brief">: {payload} · DAR: {dar} · : {linker}</div>
    <span class="expand-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:4px 0 4px"></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">{binder} ({bfmt})</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">{payload}</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">{linker}</span></div>
      <div class="info-row"><span class="info-label">DAR</span><span class="info-value">{dar}</span></div>
      <div class="info-row"><span class="info-label"></span><span class="info-value">{conjtech}</span></div>
      
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      {efficacy_html}
      {safety_html}
      {immuno_html}
      {dose_html}
      
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      {f'<div class="info-row"><span class="info-label"></span><span class="info-value">{audit}</span></div>' if audit else ''}
      <div class="info-row"><span class="info-label"></span><span class="info-value"><a href="https://clinicaltrials.gov/search?query={src}" target="_blank" onclick="event.stopPropagation()" style="color:var(--primary)">{src}</a></span></div>
      {fail_html}
    </div>
  </div>
</div>'''

    _conf_color = {'high':'#1a7a4a','moderate':'#b07800','low':'#cc3300'}
    _conf_label = {'high':'：','moderate':'：','low':'⚠ '}
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
        conf_label = _conf_label.get(conf,'：')
        ev_note = esc(props.get('evidence_note',''))
        refs = props.get('key_refs',[])
        refs_html = ''.join(f'<div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">{esc(r)}</span></div>' for r in refs)
        needs_review = props.get('needs_expert_review', False)
        review_warn = '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:4px;padding:6px 10px;font-size:11px;color:#856404;margin-bottom:8px">⚠  — 。</div>' if needs_review else ''
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
    <div class="cc-brief">: {density} · : {intern_rate} · : {het}</div>
    <div style="font-size:10px;color:{conf_color};font-weight:600;margin-top:2px">{conf_label}</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      {review_warn}
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:4px 0 4px"></div>
      {ir(" ()", density)}
      {ir(" ()", density_q)}
      {ir("", het)}
      {ir("", normal)}
      {ir("", offtum)}
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      {ir("", intern_rate)}
      {ir("", intern_mech)}
      {ir(" t½", intern_t12)}
      {ir("", recycling)}
      {ir("", shedding)}
      {ir("", prolif_sens)}
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:#888;margin:10px 0 4px;border-top:1px solid #eee;padding-top:8px"></div>
      {ir(" / CDx", biomarker)}
      {f'<div class="info-row"><span class="info-label"></span><span class="info-value" style="font-style:italic;color:#444">{ev_note}</span></div>' if ev_note else ''}
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
        byster = esc(p.get('byster_effect','?'))
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
        conf_label = _conf_label.get(conf,'：')
        ev_note = esc(p.get('evidence_note',''))
        refs = p.get('key_refs',[])
        refs_html = ''.join(f'<div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">{esc(r)}</span></div>' for r in refs)
        needs_review = p.get('needs_expert_review', False)
        review_warn = '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:4px;padding:6px 10px;font-size:11px;color:#856404;margin-bottom:8px">⚠  — 。</div>' if needs_review else ''
        search_text = f'{p.get("name","").lower()} {cls.lower()} {potency.lower()} {cell_cycle.lower()}'

        return f'''<div class="card" onclick="toggleCard(this)" data-cls="{esc(cls)}" data-search="{esc(search_text)}">
  <div class="card-header">
    <div class="card-title">{esc(p.get("name","Unknown"))}</div>
    <span class="badge badge-payload">{esc(cls)}</span>
  </div>
  <div class="card-body">
    <div class="cc-brief">IC50: {ic50} nM · : {cell_cycle[:30]}{"…" if len(cell_cycle)>30 else ""}</div>
    <div style="font-size:10px;color:{conf_color};font-weight:600;margin-top:2px">{conf_label}</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      {review_warn}
      {_section("")}
      {_info("", cls)}
      {_info("MoA", moa_detail)}
      {_info("IC50", f"{ic50} nM")}
      {_info("", potency)}
      {_info("", cell_cycle)}
      {_info("", byster)}
      {_section("")}
      {_info(" (DLTs)", dlts_str)}
      {_section("ADC ")}
      {_info(" DAR ", opt_dar)}
      {_info("log P ()", logp)}
      {_info("", compat_chem)}
      {_info("", resistance_str)}
      {_section("")}
      {_info("PubChem CID", cid_html)}
      {f'<div class="info-row"><span class="info-label"></span><span class="info-value" style="font-style:italic;color:#444">{ev_note}</span></div>' if ev_note else ''}
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
        conf_label = _conf_label.get(conf,'：')
        ev_note = esc(l.get('evidence_note',''))
        refs = l.get('key_refs',[])
        refs_html = ''.join(f'<div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">{esc(r)}</span></div>' for r in refs)
        needs_review = l.get('needs_expert_review', False)
        review_warn = '<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:4px;padding:6px 10px;font-size:11px;color:#856404;margin-bottom:8px">⚠  — 。</div>' if needs_review else ''
        search_text = f'{l.get("name","").lower()} {ltype.lower()} {mech.lower()}'

        return f'''<div class="card" onclick="toggleCard(this)" data-ltype="{ltype}" data-search="{esc(search_text)}">
  <div class="card-header">
    <div class="card-title">{esc(l.get("name","Unknown"))}</div>
    <span class="badge badge-linker">{ltype}</span>
  </div>
  <div class="card-body">
    <div class="cc-brief"> t½: {plasma_t12[:30]}{"…" if len(plasma_t12)>30 else ""} · : {cleavage_enzyme[:25]}{"…" if len(cleavage_enzyme)>25 else ""}</div>
    <div style="font-size:10px;color:{conf_color};font-weight:600;margin-top:2px">{conf_label}</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      {review_warn}
      {_section("")}
      {_info("", mech)}
      {_info("", cleavage_enzyme)}
      {_info(" t½", plasma_t12)}
      {_info("", tumor_cleavage)}
      {_info("", stab)}
      {_section("ADC ")}
      {_info("", compat_payload)}
      {_info("", conj_str)}
      {_info("", hydro)}
      {_info(" DAR ", opt_dar)}
      {_section("")}
      {_info("PubChem CID", cid)}
      {f'<div class="info-row"><span class="info-label"></span><span class="info-value" style="font-style:italic;color:#444">{ev_note}</span></div>' if ev_note else ''}
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
        refs_html = ''.join(f'<div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">{esc(r)}</span></div>' for r in refs)

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
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      {_section("")}
      {_info("", desc)}
      {_info(" DAR", dar)}
      {_info("", homo)}
      {_section("CMC ")}
      {_info("CMC ", cmc)}
      {_info("CMC ", cmc_det)}
      {_info(" / FTO", fto)}
      {_info("FTO ", fto_det)}
      {_section("")}
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
        refs_html = ''.join(f'<div class="info-row" style="font-size:11px;color:#666"><span class="info-label"></span><span class="info-value">{esc(r)}</span></div>' for r in refs)

        return f'''<div class="card" onclick="toggleCard(this)" data-search="{assay_name.lower()} {methods.lower()}">
  <div class="card-header">
    <div class="card-title">{esc(assay_name.replace("_"," ").title())}</div>
  </div>
  <div class="card-body">
    <div class="cc-brief">{purpose[:120]}{'…' if len(purpose)>120 else ''}</div>
    <span class="exp-toggle"></span>
    <div class="cc-detail">
      <div class="collapse-bar"><div class="collapse-progress"></div></div>
      {_section("")}
      {_info("", purpose)}
      {_info("", methods)}
      {f'<div class="info-row"><span class="info-label"></span><span class="info-value">{analytes}</span></div>' if analytes else ''}
      {_section("")}
      {_info("", proto)}
      {_info("", cell)}
      {_info("", sens)}
      {_section("")}
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
    ag_expr_opts = '\n'.join(f'    <option value="{e}">{e}</option>' for e in ['', '', '', '', ''])
    _ag_trans = {"high":"","moderate":"","low":""}
    ag_intern_opts = '\n'.join(f'    <option value="{i}">{_ag_trans.get(i,i)}</option>' for i in ag_intern_set)
    ag_het_opts = '\n'.join(f'    <option value="{h}">{_ag_trans.get(h,h)}</option>' for h in ag_het_set)
    ag_density_opts = '\n'.join(f'    <option value="{d}">{_ag_trans.get(d,d)}</option>' for d in ag_density_set)
    ag_risk_opts = '\n'.join(f'    <option value="{r}">{_ag_trans.get(r,r)}</option>' for r in ag_risk_set)

    # --- Build program cards ---
    prog_cards = '\n'.join(prog_card(p) for p in master)
    ag_cards = '\n'.join(ag_card(n, p) for n, p in antigens.items())
    pl_cards = '\n'.join(payload_card(p) for p in )
    lk_cards = '\n'.join(linker_card(l) for l in )
    _homo_sort_key = {'':0,'':1,'':2,'':3}
    cj_sorted = sorted(conj.items(), key=lambda kv: _homo_sort_key.get(conj_homogeneity(kv[1]),9))
    cj_cards = '\n'.join(conj_card(n, v) for n, v in cj_sorted)

    exp_cards_html = ''
    for cat, assays in experiments.items():
        exp_cards_html += f'<h3 class="section-title" style="font-size:20px;margin:20px 0 8px">{esc(cat.replace("_"," ").title())}</h3>\n'
        for aname, det in assays.items():
            exp_cards_html += exp_card(aname, det) + '\n'

    page = f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Therasik ADC  — {n_progs} , {n_ag} , {n_pl} , {n_lk} , {n_cj} 。">
<meta name="robots" content="noai, noimageai">
<meta name="AI-Training" content="opt-out">
<link rel="canonical" href="https://www.therasik.com/Therasik_ADC_Database.html">
<title>ADC  | Therasik</title>
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500&family=Noto+Sans+SC:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{ --primary:#2563eb; --primary-dark:#1e40af; --text:#1f2937; --text-muted:#6b7280; --border:#e5e7eb; --bg:#ffffff; --bg-alt:#f9fafb; --bg-alt2:#f3f4f6; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:'Noto Sans SC','Inter',-apple-system,sans-serif; font-size:15px; line-height:1.6; color:var(--text); background:var(--bg); -webkit-font-smoothing:antialiased; padding-top:60px; }}

  @media print {{
    body {{ display: none !important; }}
  }}

  /* ── Header ── */
  .top-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 32px;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(12px);
    border-bottom: 2px solid rgba(37, 99, 235, 0.1);
    position: fixed;
    width: 100%;
    top: 0;
    z-index: 2000;
  }}
  .br a {{
    text-decoration: none;
    color: inherit;
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'Cormorant Garamond', serif;
    font-weight: 700;
    font-size: 24px;
  }}
  .br-dot {{
    width: 12px;
    height: 12px;
    background: var(--primary);
    border-radius: 50%;
  }}
  .accent {{ color: var(--primary); }}
  .mobile-menu-btn {{ display: none; background: none; border: 1px solid var(--border); border-radius: 8px; padding: 6px 8px; cursor: pointer; color: var(--text); line-height: 0; }}
  .nav-close-btn {{ display: none; }}

  .top-header-nav {{ display: flex; align-items: center; gap: 4px; flex: 1; justify-content: center; }}
  .top-header-nav a {{
    padding: 7px 14px;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-muted);
    text-decoration: none;
    border-radius: 20px;
    transition: all 0.2s;
  }}
  .top-header-nav a:hover {{
    color: var(--primary);
    background: rgba(37, 99, 235, 0.06);
  }}

  /* Dropdown */
  .nav-dropdown {{ position: relative; display: inline-block; }}
  .dropdown-menu {{
    position: absolute;
    top: 100%;
    left: 50%;
    transform: translateX(-50%) translateY(10px);
    background: white;
    min-width: 240px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    border-radius: 12px;
    padding: 8px;
    opacity: 0;
    visibility: hidden;
    transition: all 0.2s;
    border: 1px solid var(--border);
  }}
  .nav-dropdown:hover .dropdown-menu, .nav-dropdown:focus-within .dropdown-menu {{
    opacity: 1;
    visibility: visible;
    transform: translateX(-50%) translateY(0);
  }}
  .dropdown-menu a {{
    display: block;
    padding: 10px 16px;
    border-radius: 8px;
    text-align: left;
    transition: background 0.2s;
  }}
  .dropdown-menu a:hover {{ background: var(--bg-alt); }}
  .menu-title {{ display: block; font-size: 14px; font-weight: 700; color: var(--text); }}
  .menu-desc {{ display: block; font-size: 11px; color: var(--text-muted); margin-top: 2px; }}

  @media (max-width: 768px) {{
    .mobile-menu-btn {{ display: block; }}
    .top-header {{ padding: 10px 16px; flex-wrap: nowrap; }}
    .top-header-nav {{ position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: #fff; flex-direction: column; justify-content: center; align-items: center; gap: 4px; z-index: 9999; opacity: 0; pointer-events: none; transition: opacity 0.25s; padding: 24px; overflow-y: auto; display: flex !important; }}
    .top-header-nav.open {{ opacity: 1; pointer-events: auto; }}
    .top-header-nav a {{ font-size: 18px; padding: 12px 24px; }}
    .nav-close-btn {{ display: block; position: absolute; top: 16px; right: 20px; background: none; border: none; font-size: 32px; color: var(--text); cursor: pointer; line-height: 1; padding: 4px 8px; }}
    .nav-dropdown .dropdown-menu {{ position: static; transform: none; opacity: 1; visibility: visible; box-shadow: none; border: none; padding: 0; width: 100%; text-align: center; }}
    .nav-dropdown .dropdown-menu a {{ text-align: center; }}
    .nav-dropdown > a::after {{ display: none; }}
  }}

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

  /* ── Cards — matches vaccine_kb + antibody-guide exp pattern ── */
  .card {{ background:#fff; border:1px solid var(--border); border-radius:10px; overflow:hidden; transition:box-shadow .15s,border-color .15s; cursor:pointer; }}
  .card:hover {{ border-color:var(--primary); box-shadow:0 4px 14px rgba(13,148,136,.09); }}
  .card.exped {{ border-color:var(--primary); box-shadow:0 4px 20px rgba(13,148,136,.12); }}
  .card.hidden {{ display:none; }}
  .card-header {{ display:flex; justify-content:space-between; align-items:flex-start; padding:12px 14px 8px; border-bottom:1px solid var(--border); }}
  .card-title {{ font-size:14px; font-weight:700; color:var(--text); line-height:1.3; }}
  .card-subtitle {{ font-size:11px; color:var(--text-muted); margin-top:2px; }}
  .card-body {{ padding:10px 14px 12px; }}
  .cc-brief {{ font-size:13px; color:var(--text-muted); line-height:1.4; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }}
  .card.exped .cc-brief {{ display:block; -webkit-line-clamp:unset; overflow:visible; }}

  /* ── Exp / collapse — exact match to vaccine_kb + antibody-guide ── */
  .cc-detail {{ display:none; margin-top:12px; padding-top:12px; border-top:1px solid var(--border); }}
  .card.exped .cc-detail {{ display:block; }}
  .cc-detail .collapse-bar {{ height:3px; background:#e5f7f5; border-radius:2px; margin-bottom:12px; overflow:hidden; }}
  .cc-detail .collapse-progress {{ height:100%; width:100%; background:var(--primary); border-radius:2px; transition:none; }}
  .card.countdown .cc-detail .collapse-progress {{ transition:width 5s linear; width:0% !important; }}
  .exp-toggle {{ font-size:10px; color:var(--primary); font-weight:600; float:right; margin-top:4px; text-transform:uppercase; letter-spacing:0.5px; }}
  .card .exp-toggle::after {{ content:'▼ Exp'; }}
  .card.exped .exp-toggle::after {{ content:'▲ '; }}

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

<header class="top-header">
  <div class="br">
    <a href="therasik_index.html">
      <span class="br-dot"></span>Thera<span class="accent">sik</span>
    </a>
  </div>
  <button class="mobile-menu-btn" onclick="document.querySelector('.top-header-nav').classList.add('open')">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
  </button>
  <nav class="top-header-nav">
    <button class="nav-close-btn" onclick="document.querySelector('.top-header-nav').classList.remove('open')">&times;</button>
    <a href="therasik_index.html"></a>
    <div class="nav-dropdown" tabindex="0">
      <a href="therasik_index.html#services"></a>
      <div class="dropdown-menu">
        <a href="Therasik_Antibody_Page.html">
          <span class="menu-title"></span>
          <span class="menu-desc">、、</span>
        </a>
        <a href="Therasik_ADC_Design_Page.html">
          <span class="menu-title"> ADC </span>
          <span class="menu-desc">--</span>
        </a>
        <a href="Therasik_CART_Page.html">
          <span class="menu-title"> CAR-T </span>
          <span class="menu-desc"></span>
        </a>
        <a href="Therasik_Bispecific_Page.html">
          <span class="menu-title"></span>
          <span class="menu-desc"></span>
        </a>
        <a href="Therasik_Vaccine_Design.html">
          <span class="menu-title"></span>
          <span class="menu-desc"> ·  · mRNA</span>
        </a>
      </div>
    </div>
    <div class="nav-dropdown" tabindex="0">
      <a href="#" style="color:#fff; background:var(--primary); border-radius:20px;"></a>
      <div class="dropdown-menu">
        <a href="Therasik_ADA_Database.html">
          <span class="menu-title">ADA </span>
          <span class="menu-desc"></span>
        </a>
        <a href="Therasik_ADC_Database.html">
          <span class="menu-title">ADC </span>
          <span class="menu-desc">100+  ADC </span>
        </a>
        <a href="Therasik_Antibody_Guide.html">
          <span class="menu-title"></span>
          <span class="menu-desc"></span>
        </a>
        <a href="Therasik_Vaccine_KB.html">
          <span class="menu-title"></span>
          <span class="menu-desc"></span>
        </a>
      </div>
    </div>
    <a href="Therasik_OurTech.html"></a>
  </nav>
</header>

<div class="page">
  <!-- Page header — same structure as vaccine_kb  antibody-guide -->
  <div class="page-header">
    <h1>ADC </h1>
    <p>， <strong>{n_progs} </strong>, <strong>{n_ag} </strong>, <strong>{n_pl}  (11 )</strong>, <strong>{n_lk} </strong>,  <strong>{n_cj} </strong> — — 、。</p>
    <p class="page-card-hint"><strong></strong> （ <a href="antibody-guide.html"></a>  <a href="vaccine_kb_data.html"></a>）：<strong></strong>；。  &ldquo;&#x25BC; Exp&rdquo; / &ldquo;&#x25B2; &rdquo;.</p>
  </div>

  <!-- Tab bar — horizontal underline, same as vaccine_kb -->
  <div class="tabs-bar">
    <button class="tab-btn active" data-tab="programs"> ({n_progs})</button>
    <button class="tab-btn" data-tab="antigens"> ({n_ag})</button>
    <button class="tab-btn" data-tab=""> ({n_pl})</button>
    <button class="tab-btn" data-tab=""> ({n_lk})</button>
    <button class="tab-btn" data-tab="conjugation"> ({n_cj})</button>
    <button class="tab-btn" data-tab="experiments"> ({n_exp})</button>
  </div>

  <!-- ═══ PROGRAMS ═══ -->
  <div class="tab-panel active" id="panel-programs">
    <h2 class="section-title">Clinical ADC Programs</h2>
    <p class="section-desc">Approved  late-stage clinical ADC programs with target, payload, linker, DAR, conjugation technology,  trial references. Includes failure analysis for discontinued programs.</p>
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
    <p class="section-desc">Detailed mapping of expression density, internalization rates, heterogeneity,  normal tissue expression for {n_ag} ADC-relevant targets.</p>
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
  <div class="tab-panel" id="panel-">
    <h2 class="section-title">Payload Molecules</h2>
    <p class="section-desc">From classic cytotoxins (MMAE, DXd) to emerging modalities (PROTACs, Radionuclides, ISACs). Includes SMILES structures  PubChem links.</p>
    <div class="ctrl-row">
      <input class="search-box" id="search" type="text" placeholder="Search payload name, class…">
      <select class="filter-sel" id="filterPayloadCls">
        <option value="">All </option>
{plcls_opts}
      </select>
      <span class="result-count" id="count"></span>
    </div>
    <div class="card-grid" id="grid">
{pl_cards}
    </div>
  </div>

  <!-- ═══ LINKERS ═══ -->
  <div class="tab-panel" id="panel-">
    <h2 class="section-title">Linker Chemistry</h2>
    <p class="section-desc">Cleavable (protease, pH, disulfide)  non-cleavable  matched to antigen internalization kinetics, with chemical structures.</p>
    <div class="ctrl-row">
      <input class="search-box" id="search" type="text" placeholder="Search linker name, mechanism…">
      <select class="filter-sel" id="filterLinkerType">
        <option value="">All types</option>
{lktype_opts}
      </select>
      <span class="result-count" id="count"></span>
    </div>
    <div class="card-grid" id="grid">
{lk_cards}
    </div>
  </div>

  <!-- ═══ CONJUGATION ═══ -->
  <div class="tab-panel" id="panel-conjugation">
    <h2 class="section-title">nologies</h2>
    <p class="section-desc">From stochastic cysteine to site-specific enzymatic (FGE, Sortase)  glycan remodeling — DAR homogeneity, CMC complexity,  patent / FTO analysis.</p>
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
    <p class="section-desc">In vitro  in vivo experimental methods for ADC characterization, from binding assays to PDX efficacy models.</p>
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
// Security: Anti-copy, Anti-right-click, Anti-print
(function() {{
  document.addEventListener('contextmenu', e => e.preventDefault());
  document.addEventListener('selectstart', e => e.preventDefault());
  document.addEventListener('copy', e => e.preventDefault());
  document.addEventListener('keydown', e => {{
    if ((e.ctrlKey || e.metaKey) && (e.key === 'c' || e.key === 'p' || e.key === 's' || e.key === 'u')) {{
      e.preventDefault();
    }}
  }});
}})();

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
    case '':
      filterGrid('grid', 'search', 'count', [
        {{ selectId: 'filterPayloadCls', attr: 'data-cls' }}
      ]);
      break;
    case '':
      filterGrid('grid', 'search', 'count', [
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
['searchPrograms','searchAntigens','search','search','searchConj','searchExp'].forEach(function(id) {{
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

    out_path = Path('docs/Therasik_ADC_Database.html')
    out_path.write_text(page, encoding='utf-8')
    print(f"Generated {out_path}  ({out_path.stat().st_size//1024} KB)")

if __name__ == '__main__':
    main()
