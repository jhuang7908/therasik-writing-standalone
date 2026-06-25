import re
path = 'api/static/console.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fixes:
content = content.replace('setTimeout( =>', 'setTimeout(() =>')
content = content.replace('setInterval( =>', 'setInterval(() =>')
content = content.replace('requestAnimationFrame( =>', 'requestAnimationFrame(() =>')
content = content.replace('.then( =>', '.then(() =>')
content = content.replace('.catch( =>', '.catch(() =>')
content = content.replace('catch(=>', 'catch(()=>')
content = content.replace('onclick="( =>', 'onclick="(() =>')
content = content.replace('${( =>', '${(() =>')
content = content.replace('` : ( =>', '` : (() =>')
content = content.replace(' = ( =>', ' = (() =>')
content = content.replace(' ? ( =>', ' ? (() =>')

# Properties in dictionaries
for key in ['vhvl', 'recheck-vhvl', 'structural-vhvl', 'cmc-igg', 'vhh-humanization', 'recheck-vhh', 'vhh-structural', 'cmc-vhh', 'vh-to-vhh', 'segmentation-vhvl', 'vhh-segmentation', 'cdna-optimization', 'cmc-bispecific']:
    content = content.replace(f'"{key}": =>', f'"{key}": () =>')

# Assignments
content = content.replace('onload = =>', 'onload = () =>')
content = content.replace('_smartcmcGetSelected = =>', '_smartcmcGetSelected = () =>')
content = content.replace('_smartcmcUpdatePreview = =>', '_smartcmcUpdatePreview = () =>')

# Find any remaining instances
matches = re.finditer(r'([^\w\)\]_]\s*)=>', content)
for m in matches:
    start = max(0, m.start() - 10)
    end = min(len(content), m.end() + 10)
    # Ignore spaces
    # It will match because we didn't use regex for the replacement, but let's just see if there are any that look like actual missing ()
    
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed specific arrow functions')