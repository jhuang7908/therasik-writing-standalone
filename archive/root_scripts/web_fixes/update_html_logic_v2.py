import json
import os

json_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\data\adc_atlas\adc_design_rules.json'
html_path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\therasik-web-source\Therasik_ADC_Database.html'

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

antigens = data['antigen_properties']

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read

for name, props in antigens.items:
    if not isinstance(props, dict): continue
    if 'design_logic' in props:
        logic = props['design_logic']
        
        # Search for the card title
        search_pattern = f'<div class="card-title">{name}'
        if search_pattern in html:
            start_pos = html.find(search_pattern)
            
            # Find the cc-detail start
            detail_marker = ' (Design Logic)</div>'
            logic_start = html.find(detail_marker, start_pos)
            
            if logic_start != -1:
                # Find the span containing the logic
                span_start = html.find('<span class="info-value"', logic_start)
                if span_start != -1:
                    content_start = html.find('>', span_start) + 1
                    content_end = html.find('</span>', content_start)
                    
                    if content_start != -1 and content_end != -1:
                        # Replace the logic content
                        html = html[:content_start] + logic + html[content_end:]

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print('Updated HTML with re-annotated design logic.')
