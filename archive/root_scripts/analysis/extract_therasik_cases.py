import os
from bs4 import BeautifulSoup

filepath = 'd:/InSynBio-AI-Research/Antibody_Engineer_Suite/therasik-web-source/therasik_index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

case_cards = soup.find_all(class_='case-card')
for i, card in enumerate(case_cards):
    tag = card.find(class_='case-tag').text.strip() if card.find(class_='case-tag') else ''
    title = card.find(class_='case-title').text.strip() if card.find(class_='case-title') else ''
    desc = card.find(class_='case-desc').text.strip() if card.find(class_='case-desc') else ''
    href = card.get('href', '')
    
    print(f"[{i+1}] {href}")
    print(f"Tag: {tag}")
    print(f"Title: {title}")
    print(f"Desc: {desc}")
    print()
