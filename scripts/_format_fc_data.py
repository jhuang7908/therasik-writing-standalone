import json
import os

def format_fc_data():
    with open('data/fc_atlas/fc_variants_atlas.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    js_entries = []
    for v in data['variants']:
        # Map JSON fields to JS fields
        entry = {
            'id': v['id'].lower().replace('_', ''),
            'cat': v['category'],
            'tier': v.get('tier', 'T3'),
            'name': v['name'],
            'alias': "/".join(v.get('mutations', [])) if 'mutations' in v else '',
            'brief': v.get('brief', v.get('mechanism', '').split('.')[0] + '.'),
            'examples': v.get('clinical_examples', []),
            'mechanism': v.get('mechanism', ''),
            'receptors': " · ".join([f"{rk}: {rv}" for rk, rv in v['receptors'].items()]) if isinstance(v.get('receptors'), dict) else str(v.get('receptors', '')),
            'tradeoffs': v.get('design_rationale', ''),
            'ref': ' · '.join([f'<a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/" target="_blank">PMID {pmid}</a>' for pmid in v.get('pmids', [])])
        }
        
        if 'ip_status' in v:
            entry['ip'] = v['ip_status']
            
        js_entries.append(entry)
    
    # Simple manual formatting to match the style
    js_code = "const FC_DATA = [\n"
    for e in js_entries:
        line = "  {"
        for k, val in e.items():
            if k == 'examples':
                line += f"examples:[{', '.join([f'\"{x}\"' for x in val])}], "
            elif k == 'ip':
                ip_str = "{" + ", ".join([f"{ik}:'{iv}'" for ik, iv in val.items()]) + "}"
                line += f"ip:{ip_str}, "
            else:
                # Escape single quotes in strings
                if isinstance(val, str):
                    val_esc = val.replace("'", "\\'")
                    line += f"{k}:'{val_esc}', "
                else:
                    line += f"{k}:{val}, "
        line = line.strip(', ') + "},"
        js_code += line + "\n"
    js_code += "];"
    
    return js_code

if __name__ == "__main__":
    print(format_fc_data())
