import json
import re

# Fix JSON
json_path = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\docs\vaccine_kb_data.json"
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

fixes = {
    "SLLMWITQC": {"pmid": "15837741", "doi": "10.1084/jem.20042323", "source_url": "https://pubmed.ncbi.nlm.nih.gov/15837741/"},
    "ELAGIGILTV": {"pmid": "21795600", "doi": "10.4049/jimmunol.1101268", "source_url": "https://pubmed.ncbi.nlm.nih.gov/21795600/"}
}

for motif in data.get("tcr_motifs", []):
    if motif["epitope"] in fixes:
        motif.update(fixes[motif["epitope"]])

clone_fixes = {
    "1G4": {"pmid": "15837741", "doi": "10.1084/jem.20042323"},
    "1G4-c58": {"pmid": "17644531", "doi": "10.1093/protein/gzm033"},
    "Tebentafusp-TCR": {"pmid": "32102898", "doi": "10.4049/jimmunol.1900915"},
    "DMF5": {"pmid": "21795600", "doi": "10.4049/jimmunol.1101268"},
    "a3a": {"pmid": "26932757", "doi": "10.1038/srep18851"}
}

for clone in data.get("tcr_clones", []):
    if clone["clone_id"] in clone_fixes:
        clone.update(clone_fixes[clone["clone_id"]])

with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Fix HTML
html_path = r"D:\InSynBio-AI-Research\Antibody_Engineer_Suite\docs\vaccine_kb_data.html"
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace('PMID:15489334', 'PMID:15837741')
html = html.replace('https://pubmed.ncbi.nlm.nih.gov/15489334/', 'https://pubmed.ncbi.nlm.nih.gov/15837741/')
html = html.replace('PMID:19064726', 'PMID:21795600')
html = html.replace('https://pubmed.ncbi.nlm.nih.gov/19064726/', 'https://pubmed.ncbi.nlm.nih.gov/21795600/')

# The HTML also embeds the JSON in a script tag
json_str = json.dumps(data, ensure_ascii=False)
html = re.sub(r'const DATA = \{.*?\};', f'const DATA = {json_str};', html, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print("Fixed PMIDs in JSON and HTML")
