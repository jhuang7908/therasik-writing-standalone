
# Fix the integrity check script to look for the new panel IDs
path = r'd:\InSynBio-AI-Research\Antibody_Engineer_Suite\check_site_integrity.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read

content = content.replace("'panel-'", "'panel-payloads'")
content = content.replace("'panel-'", "'panel-linkers'")
content = content.replace('"panel-"', '"panel-payloads"')
content = content.replace('"panel-"', '"panel-linkers"')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("check_site_integrity.py updated")
