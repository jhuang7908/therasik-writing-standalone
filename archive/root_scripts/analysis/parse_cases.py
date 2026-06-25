import os
from bs4 import BeautifulSoup

directory = 'd:/InSynBio-AI-Research/Antibody_Engineer_Suite/insynbio-web-source'
files = [f for f in os.listdir(directory) if f.startswith('case_') and f.endswith('.html')]

for file in files:
    filepath = os.path.join(directory, file)
    with open(filepath, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        title = soup.title.string if soup.title else 'No Title'
        print(f"{file}: {title.strip()}")
