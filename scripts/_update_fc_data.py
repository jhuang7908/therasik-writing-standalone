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

def update_file(path):
    print(f"Updating {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the start and end of FC_DATA
    import re
    start_marker = "const FC_DATA = ["
    end_marker = "];"
    
    # Find the first occurrences
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print(f"Start marker not found in {path}")
        return
    
    # Find the closing ]; of the array
    # We need to be careful about nested arrays, but FC_DATA is usually a simple top-level array
    end_idx = content.find(end_marker, start_idx)
    if end_idx == -1:
        print(f"End marker not found in {path}")
        return
    
    new_fc_data = format_fc_data()
    new_content = content[:start_idx] + new_fc_data + content[end_idx + len(end_marker):]
    
    # Also sync DEV_DATA and WET_DATA from docs/antibody-guide.html if we are not in that file
    if path != 'docs/antibody-guide.html':
        with open('docs/antibody-guide.html', 'r', encoding='utf-8') as f_src:
            src_content = f_src.read()
            
        for var_name in ['DEV_DATA', 'WET_DATA', 'IMMUNO_DATA']:
            s_marker = f"const {var_name} = ["
            e_marker = "];"
            
            src_start = src_content.find(s_marker)
            src_end = src_content.find(e_marker, src_start)
            if src_start != -1 and src_end != -1:
                src_block = src_content[src_start:src_end + len(e_marker)]
                
                target_start = new_content.find(s_marker)
                target_end = new_content.find(e_marker, target_start)
                if target_start != -1 and target_end != -1:
                    new_content = new_content[:target_start] + src_block + new_content[target_end + len(e_marker):]

    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Successfully updated {path}")

if __name__ == "__main__":
    files_to_update = [
        'docs/antibody-guide.html',
        'docs/Therasik_Antibody_Guide.html',
        'insynbio-web-source/antibody-guide.html',
        'therasik-web-source/Therasik_Antibody_Guide.html'
    ]
    
    # Check which exist
    for p in files_to_update:
        if os.path.exists(p):
            update_file(p)
        else:
            print(f"File not found: {p}")
