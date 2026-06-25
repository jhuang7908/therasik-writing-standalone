import re

filepath = 'd:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source/pitch desk/InSynBio_Pitch_Deck.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace links pointing to pitch desk/ with root /
# E.g., href="case_bispecific_vhh_expression_optimization.html" -> href="../case_bispecific_vhh_expression_optimization.html"
# Or if it's already an absolute path, fix it.

# Let's inspect the actual HTML first to see what the links look like
links = re.findall(r'href="([^"]+)"', content)
for link in links:
    if 'case_' in link or 'vaccine_' in link or 'InSynBio_' in link:
        print(link)
