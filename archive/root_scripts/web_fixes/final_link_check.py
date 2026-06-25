import os

files = [
    'd:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source/pitch desk/InSynBio_Pitch_Deck.html',
    'd:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/pitch desk/Therasik_Pitch_Deck.html'
]

for file in files:
    print(f"--- {os.path.basename(file)} ---")
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        import re
        links = re.findall(r'href="([^"]+)"', content)
        for link in links:
            if 'case_' in link or 'InSynBio_' in link or 'Therasik_' in link or 'vaccine_' in link:
                print(link)
