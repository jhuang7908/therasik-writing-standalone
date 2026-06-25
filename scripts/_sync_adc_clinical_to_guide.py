
import json
import os

PUBLIC_JSON = "data/adc_atlas/adc_master_public.json"

def format_adc_clinical_data():
    with open(PUBLIC_JSON, 'r', encoding='utf-8') as f:
        drugs = json.load(f)
    
    js_entries = []
    for d in drugs:
        # Map development stage to tier
        stage = d.get("development_stage", "").lower()
        tier = "T3"
        if "approved" in stage: tier = "T1"
        elif "phase" in stage or "clinical" in stage: tier = "T2"
        
        name = d['canonical_name']
        if d.get('brand_name'):
            name += f" ({d['brand_name']})"
            
        clinical = d.get("clinical_data", {})
        eff = clinical.get("efficacy", {})
        safety = clinical.get("safety", {})
        immuno = clinical.get("immunogenicity", {})
        dose = clinical.get("dose", {})

        # Formatted fields for display
        efficacy_str = f"ORR: {eff.get('orr', 'TBD')} | PFS: {eff.get('pfs', 'TBD')}"
        safety_str = f"Grade 3+ AE: {safety.get('grade3_plus_ae_rate', 'TBD')} | Common: {', '.join(safety.get('common_ae', [])) if safety.get('common_ae') else 'TBD'}"
        ada_str = f"ADA: {immuno.get('ada_incidence', 'TBD')}"
        dose_str = f"Dose: {dose.get('recommended_dose', 'TBD')} ({dose.get('schedule', 'TBD')})"

        entry = {
            'id': d['id'].lower().replace('-', ''),
            'cat': d.get('target', 'Multi-target'),
            'name': name,
            'alias': f"{d.get('company', 'Unknown')} | {d.get('target', 'Unknown')}",
            'brief': d.get('indication', ''),
            'examples': [d.get('payload_name', ''), d.get('linker_name', '')],
            'mechanism': f"{d.get('technical_audit', '')} <br><br> <strong>Clinical Profile:</strong><br>• {efficacy_str}<br>• {safety_str}<br>• {ada_str}<br>• {dose_str}",
            'receptors': f"Target: {d.get('target', 'N/A')} (DAR: {d.get('dar_mean', 'N/A')})",
            'tradeoffs': f"Payload: {d.get('payload_name', 'N/A')} ({d.get('payload_class', 'N/A')}) | Linker: {d.get('linker_name', 'N/A')}",
            'ref': f"<span>{d.get('source_primary', 'N/A')}</span>" + (f" · <span>Patents: {', '.join(d.get('patent_ids', []))}</span>" if d.get('patent_ids') else ""),
            'tier': tier
        }
        js_entries.append(entry)
    
    js_code = "const ADC_CLINICAL_DATA = [\n"
    for e in js_entries:
        line = "  {"
        for k, val in e.items():
            if k == 'examples':
                line += f"examples:[{', '.join([f'\"{x}\"' for x in val if x])}], "
            else:
                if isinstance(val, str):
                    val_esc = val.replace("'", "\\'").replace("\n", " ")
                    line += f"{k}:'{val_esc}', "
                else:
                    line += f"{k}:{val}, "
        line = line.strip(', ') + "},"
        js_code += line + "\n"
    js_code += "];"
    
    return js_code

def update_file(path):
    print(f"Updating ADC Clinical data in {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Add ADC_CLINICAL_DATA
    clinical_code = format_adc_clinical_data()
    if "const ADC_CLINICAL_DATA =" in content:
        # Replace existing
        import re
        content = re.sub(r"const ADC_CLINICAL_DATA = \[.*?\];", clinical_code, content, flags=re.DOTALL)
    else:
        # Insert before ADC_DATA or FC_DATA
        if "const ADC_DATA =" in content:
            content = content.replace("const ADC_DATA =", clinical_code + "\n\nconst ADC_DATA =")
        else:
            content = content.replace("const FC_DATA =", clinical_code + "\n\nconst FC_DATA =")
    
    # 2. Add domain to DOMAINS
    domain_json = """  adc_registry: {
    data: ADC_CLINICAL_DATA,
    note: '<strong>Clinical ADC Registry</strong> — Comprehensive database of approved and clinical-stage Antibody-Drug Conjugates. Includes target, conjugation tech, DAR, and latest clinical results.',
    catField: 'cat',
    cats: [...new Set(ADC_CLINICAL_DATA.map(d=>d.cat))].sort(),
    showTier: true,
    filterLabel: 'All Targets',
    card: renderFcCard,
  },"""
    
    if "adc_registry:" not in content:
        content = content.replace("const DOMAINS = {", "const DOMAINS = {\n" + domain_json)
        
    # 3. Add Tab Button
    tab_btn = '<button class="dtab" data-domain="adc_registry" onclick="switchDomain(\'adc_registry\', this)">ADC Registry</button>'
    if 'data-domain="adc_registry"' not in content:
        # Insert after existing adc tab
        if 'data-domain="adc"' in content:
            content = content.replace('switchDomain(\'adc\', this)">ADC Design</button>', 
                              'switchDomain(\'adc\', this)">ADC Design</button>\n    ' + tab_btn)
        else:
            content = content.replace('<button class="dtab" data-domain="fc"', tab_btn + '\n    <button class="dtab" data-domain="fc"')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Successfully updated {path}")

if __name__ == "__main__":
    files_to_update = [
        'docs/antibody-guide.html',
        'docs/Therasik_Antibody_Guide.html',
        'insynbio-web-source/antibody-guide.html',
        'therasik-web-source/Therasik_Antibody_Guide.html'
    ]
    
    for p in files_to_update:
        if os.path.exists(p):
            update_file(p)
        else:
            print(f"File not found: {p}")
