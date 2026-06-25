import re

filepath = 'd:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/pitch desk/Therasik_Pitch_Deck.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

links = re.findall(r'href="([^"]+)"', content)
for link in links:
    if 'case_' in link or 'Therasik_' in link or 'wechat_' in link:
        print(link)
