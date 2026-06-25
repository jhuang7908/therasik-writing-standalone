import sys
import re

files = ['docs/therasik_index.html', 'docs/index.html']

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We want to replace the <img> tag back to the <picture> block
    pattern = r'<img src="images/case-affinity-maturation\.svg"([^>]*)>'
    
    def replacer(match):
        img_tag = f'<img src="images/case-affinity-maturation.svg"{match.group(1)}>'
        return f'''<picture>
                <source srcset="images/case-affinity-maturation.webp" type="image/webp">
                <source srcset="images/case-affinity-maturation.jpg" type="image/jpeg">
                {img_tag}
              </picture>'''
    
    new_content = re.sub(pattern, replacer, content)
    
    if new_content != content:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Fixed {file}')
    else:
        print(f'No changes needed in {file} or pattern not found.')
