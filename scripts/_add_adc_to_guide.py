import json
import os

def format_adc_data():
    with open('data/adc_atlas/adc_components.json', 'r', encoding='utf-8') as f:
        comps = json.load(f)
    
    js_entries = []
    for c in comps:
        # Determine category based on ID prefix or fields
        cat = "Unknown"
        if c['id'].startswith('ADC-COMP-L'): cat = "Linkers"
        elif c['id'].startswith('ADC-COMP-P'): cat = "Payloads"
        elif c['id'].startswith('ADC-COMP-C'): cat = "Conjugation"
        
        entry = {
            'id': c['id'].lower().replace('-', ''),
            'cat': cat,
            'name': c['name'],
            'alias': c.get('type', c.get('class', '')),
            'brief': c.get('evidence_note', '').split('.')[0] + '.',
            'examples': c.get('key_refs', []),
            'mechanism': c.get('mechanism', c.get('moa_detail', '')),
            'receptors': f"Enzyme: {c.get('cleavage_enzyme', 'N/A')}" if cat == 'Linkers' else f"IC50: {c.get('ic50_nm', 'N/A')} nM",
            'tradeoffs': c.get('hydrophilicity_note', c.get('dlts', '')),
            'ref': ' · '.join([f'<span>{r}</span>' for r in c.get('key_refs', [])])
        }
        js_entries.append(entry)
    
    js_code = "const ADC_DATA = [\n"
    for e in js_entries:
        line = "  {"
        for k, val in e.items():
            if k == 'examples':
                line += f"examples:[{', '.join([f'\"{x}\"' for x in val])}], "
            else:
                if isinstance(val, str):
                    val_esc = val.replace("'", "\\'")
                    line += f"{k}:'{val_esc}', "
                else:
                    line += f"{k}:{val}, "
        line = line.strip(', ') + "},"
        js_code += line + "\n"
    js_code += "];"
    
    return js_code

def update_file(path):
    print(f"Adding ADC domain to {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Add ADC_DATA before FC_DATA or where others are
    if "const ADC_DATA =" not in content:
        adc_data_code = format_adc_data()
        content = content.replace("const FC_DATA =", adc_data_code + "\n\nconst FC_DATA =")
    
    # 2. Add ADC to DOMAINS
    adc_domain_json = """  adc: {
    data: ADC_DATA,
    note: '<strong>Antibody-Drug Conjugate (ADC) Components</strong> — Key linkers, payloads, and conjugation technologies used in clinical-stage ADCs. Includes mechanism of release, potency data, and clinical precedent.',
    catField: 'cat',
    cats: [...new Set(ADC_DATA.map(d=>d.cat))],
    showTier: false,
    filterLabel: 'All ADC Categories',
    card: renderFcCard,
  },"""
    
    if "adc:" not in content:
        content = content.replace("const DOMAINS = {", "const DOMAINS = {\n" + adc_domain_json)
        
    # 3. Add Tab Button
    tab_btn = '<button class="dtab" data-domain="adc" onclick="switchDomain(\'adc\', this)">ADC Design</button>'
    if 'data-domain="adc"' not in content:
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
